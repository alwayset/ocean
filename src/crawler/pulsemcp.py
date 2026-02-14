"""PulseMCP crawler — fetch MCP server metadata from pulsemcp.com."""

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

API_BASE = "https://api.pulsemcp.com/v0beta"
PAGE_SIZE = 250  # practical max for v0beta
EMBED_BATCH_SIZE = 50


def _extract_domain(server: dict) -> str:
    """Extract domain from a PulseMCP server entry."""
    source_url = server.get("source_code_url") or ""
    if source_url:
        parsed = urlparse(source_url)
        # For GitHub repos, use org/repo as identifier
        if parsed.hostname == "github.com" and parsed.path:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return f"pulsemcp:{parts[0]}/{parts[1]}"

    # Use the PulseMCP URL slug
    pulsemcp_url = server.get("url", "")
    if pulsemcp_url:
        slug = pulsemcp_url.rstrip("/").split("/")[-1]
        if slug:
            return f"pulsemcp:{slug}"

    return f"pulsemcp:{server.get('name', 'unknown')}"


async def fetch_all_servers(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all servers from PulseMCP using offset pagination."""
    all_servers = []
    offset = 0

    while True:
        resp = await client.get(
            f"{API_BASE}/servers",
            params={"count_per_page": PAGE_SIZE, "offset": offset},
        )
        resp.raise_for_status()
        data = resp.json()

        servers = data.get("servers", [])
        total = data.get("total_count", 0)
        all_servers.extend(servers)

        print(f"  Fetched offset {offset}: {len(servers)} servers (total: {total})")

        if not data.get("next") or not servers:
            break
        offset += PAGE_SIZE
        await asyncio.sleep(1)  # Rate limit: 1 req/sec

    return all_servers


async def crawl_pulsemcp(db: AsyncSession) -> dict:
    """Crawl PulseMCP for MCP server metadata.

    Like Glama, PulseMCP doesn't expose individual tools,
    so each server becomes a single tool entry.
    """
    stats = {
        "servers_found": 0,
        "tools_added": 0,
        "tools_updated": 0,
        "providers_created": 0,
        "errors": 0,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        print("  Fetching servers from PulseMCP...")
        all_servers = await fetch_all_servers(client)
        stats["servers_found"] = len(all_servers)
        print(f"  Found {len(all_servers)} servers")

        # Filter: need at least a description
        servers_with_desc = [
            s for s in all_servers
            if s.get("short_description") or s.get("EXPERIMENTAL_ai_generated_description")
        ]
        print(f"  {len(servers_with_desc)} servers have descriptions")

        for batch_start in range(0, len(servers_with_desc), EMBED_BATCH_SIZE):
            batch = servers_with_desc[batch_start : batch_start + EMBED_BATCH_SIZE]

            texts = [
                build_tool_text(
                    s.get("name", "unknown"),
                    s.get("EXPERIMENTAL_ai_generated_description") or s.get("short_description", ""),
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
                    server_name = server.get("name", domain)
                    description = (
                        server.get("EXPERIMENTAL_ai_generated_description")
                        or server.get("short_description", "")
                    )

                    stmt = select(Provider).where(Provider.domain == domain)
                    provider = (await db.execute(stmt)).scalar_one_or_none()
                    if provider is None:
                        provider = Provider(
                            domain=domain,
                            name=server_name,
                            description=description[:500] if description else "",
                            homepage_url=server.get("url") or server.get("source_code_url", ""),
                        )
                        db.add(provider)
                        await db.flush()
                        stats["providers_created"] += 1

                    stmt = select(Tool).where(
                        Tool.provider_id == provider.id,
                        Tool.name == server_name,
                        Tool.protocol == "mcp",
                    )
                    existing = (await db.execute(stmt)).scalar_one_or_none()

                    metadata = {
                        "source": "pulsemcp",
                        "github_stars": server.get("github_stars"),
                        "package_registry": server.get("package_registry"),
                        "package_name": server.get("package_name"),
                        "package_download_count": server.get("package_download_count"),
                        "source_code_url": server.get("source_code_url"),
                    }

                    if existing:
                        existing.description = description or existing.description
                        existing.embedding = embedding
                        existing.metadata_ = metadata
                        existing.last_seen = func.now()
                        stats["tools_updated"] += 1
                    else:
                        tool = Tool(
                            provider_id=provider.id,
                            name=server_name,
                            description=description,
                            protocol="mcp",
                            endpoint=server.get("url", ""),
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
