"""Glama registry crawler — fetch MCP server metadata from glama.ai."""

import asyncio
import logging
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.provider import Provider
from src.models.tool import Tool
from src.search.embeddings import build_tool_text, embed_texts

logger = logging.getLogger(__name__)

API_BASE = "https://glama.ai/api/mcp/v1"
PAGE_SIZE = 100
EMBED_BATCH_SIZE = 50


def _extract_domain(server: dict) -> str:
    """Extract domain from a Glama server entry."""
    repo_url = (server.get("repository") or {}).get("url", "")
    if repo_url:
        parsed = urlparse(repo_url)
        # Use namespace/slug as identifier since repo is usually github.com
        namespace = server.get("namespace", "")
        slug = server.get("slug", "")
        if namespace:
            return f"glama:{namespace}/{slug}" if slug else f"glama:{namespace}"

    return f"glama:{server.get('id', 'unknown')}"


async def fetch_all_servers(client: httpx.AsyncClient, max_pages: int = 0) -> list[dict]:
    """Fetch all servers from Glama using cursor-based pagination."""
    all_servers = []
    cursor = None
    page = 0

    while True:
        params = {"first": PAGE_SIZE}
        if cursor:
            params["after"] = cursor

        resp = await client.get(f"{API_BASE}/servers", params=params)
        resp.raise_for_status()
        data = resp.json()

        servers = data.get("servers", [])
        all_servers.extend(servers)
        page += 1

        page_info = data.get("pageInfo", {})
        logger.info(f"  Fetched page {page} ({len(servers)} servers, total so far: {len(all_servers)})")
        print(f"  Fetched page {page} ({len(servers)} servers, total: {len(all_servers)})")

        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            break

        if max_pages and page >= max_pages:
            print(f"  Reached max_pages limit ({max_pages})")
            break

    return all_servers


async def crawl_glama(db: AsyncSession, max_pages: int = 0) -> dict:
    """Crawl Glama registry for MCP server metadata.

    Note: Glama's API returns empty tools arrays, so we store servers
    as single-tool providers (the server itself is the "tool").
    """
    stats = {
        "servers_found": 0,
        "tools_added": 0,
        "tools_updated": 0,
        "providers_created": 0,
        "errors": 0,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        print("  Fetching servers from Glama...")
        all_servers = await fetch_all_servers(client, max_pages=max_pages)
        stats["servers_found"] = len(all_servers)
        print(f"  Found {len(all_servers)} servers")

        # Filter: only servers with a description (otherwise no embedding value)
        servers_with_desc = [s for s in all_servers if s.get("description")]
        print(f"  {len(servers_with_desc)} servers have descriptions")

        # Since Glama doesn't expose individual tools via API,
        # we treat each server as a single "tool" entry
        for batch_start in range(0, len(servers_with_desc), EMBED_BATCH_SIZE):
            batch = servers_with_desc[batch_start : batch_start + EMBED_BATCH_SIZE]

            texts = [
                build_tool_text(
                    s.get("name", s.get("slug", "unknown")),
                    s.get("description", ""),
                    _extract_domain(s),
                )
                for s in batch
            ]

            try:
                embeddings = await embed_texts(texts)
            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                stats["errors"] += len(batch)
                continue

            for server, embedding in zip(batch, embeddings):
                try:
                    domain = _extract_domain(server)
                    server_name = server.get("name") or server.get("slug") or domain

                    stmt = select(Provider).where(Provider.domain == domain)
                    provider = (await db.execute(stmt)).scalar_one_or_none()
                    if provider is None:
                        provider = Provider(
                            domain=domain,
                            name=server_name,
                            description=server.get("description", ""),
                            homepage_url=server.get("url") or f"https://glama.ai/mcp/servers/{server.get('id', '')}",
                        )
                        db.add(provider)
                        await db.flush()
                        stats["providers_created"] += 1

                    # Use server name as tool name (since we don't have individual tools)
                    tool_name = server_name
                    stmt = select(Tool).where(
                        Tool.provider_id == provider.id,
                        Tool.name == tool_name,
                        Tool.protocol == "mcp",
                    )
                    existing = (await db.execute(stmt)).scalar_one_or_none()

                    metadata = {
                        "source": "glama",
                        "glama_id": server.get("id", ""),
                        "namespace": server.get("namespace", ""),
                        "attributes": server.get("attributes", []),
                        "repo_url": (server.get("repository") or {}).get("url", ""),
                    }

                    if existing:
                        existing.description = server.get("description", existing.description)
                        existing.embedding = embedding
                        existing.metadata_ = metadata
                        existing.last_seen = func.now()
                        stats["tools_updated"] += 1
                    else:
                        tool = Tool(
                            provider_id=provider.id,
                            name=tool_name,
                            description=server.get("description", ""),
                            protocol="mcp",
                            endpoint=server.get("url") or f"https://glama.ai/mcp/servers/{server.get('id', '')}",
                            embedding=embedding,
                            metadata_=metadata,
                        )
                        db.add(tool)
                        stats["tools_added"] += 1

                except Exception as e:
                    logger.error(f"Error storing server {server.get('name')}: {e}")
                    stats["errors"] += 1

            await db.flush()
            processed = min(batch_start + EMBED_BATCH_SIZE, len(servers_with_desc))
            print(f"  Processed {processed}/{len(servers_with_desc)} servers...")

    await db.commit()
    return stats
