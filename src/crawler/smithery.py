"""Smithery registry crawler — fetch MCP servers and their tools from registry.smithery.ai."""

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

REGISTRY_BASE = "https://registry.smithery.ai"
PAGE_SIZE = 100
DETAIL_CONCURRENCY = 10  # parallel detail fetches
EMBED_BATCH_SIZE = 50


def _extract_domain(server: dict) -> str:
    """Extract a meaningful domain from a Smithery server entry."""
    # Try deployment URL first
    deployment_url = server.get("deploymentUrl") or ""
    if deployment_url:
        parsed = urlparse(deployment_url)
        if parsed.hostname and parsed.hostname not in ("server.smithery.ai", "localhost"):
            return parsed.hostname

    # Try homepage
    homepage = server.get("homepage") or ""
    if homepage and "smithery.ai" not in homepage:
        parsed = urlparse(homepage)
        if parsed.hostname:
            return parsed.hostname

    # Fall back to smithery qualified name as synthetic domain
    return f"smithery:{server.get('qualifiedName', 'unknown')}"


async def fetch_server_list(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all servers from the Smithery registry list endpoint."""
    all_servers = []
    page = 1

    while True:
        resp = await client.get(
            f"{REGISTRY_BASE}/servers",
            params={"page": page, "pageSize": PAGE_SIZE},
        )
        resp.raise_for_status()
        data = resp.json()

        servers = data.get("servers", [])
        all_servers.extend(servers)

        pagination = data.get("pagination", {})
        total_pages = pagination.get("totalPages", 1)
        logger.info(f"  Fetched page {page}/{total_pages} ({len(servers)} servers)")

        if page >= total_pages:
            break
        page += 1

    return all_servers


async def fetch_server_detail(
    client: httpx.AsyncClient, qualified_name: str, semaphore: asyncio.Semaphore
) -> dict | None:
    """Fetch a single server's detail (includes tools array)."""
    async with semaphore:
        try:
            resp = await client.get(
                f"{REGISTRY_BASE}/servers/{qualified_name}",
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"Failed to fetch detail for {qualified_name}: {e}")
    return None


async def crawl_smithery(db: AsyncSession) -> dict:
    """Crawl the Smithery registry for MCP tools.

    Strategy:
    1. Fetch all servers from list endpoint
    2. For deployed servers, fetch detail to get tool definitions
    3. Embed and store tools with deduplication
    """
    stats = {
        "servers_found": 0,
        "servers_with_tools": 0,
        "tools_added": 0,
        "tools_updated": 0,
        "providers_created": 0,
        "errors": 0,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Fetch all servers
        print("  Fetching server list from Smithery...")
        all_servers = await fetch_server_list(client)
        stats["servers_found"] = len(all_servers)
        print(f"  Found {len(all_servers)} servers total")

        # Step 2: Fetch details for deployed servers (they have actual tools)
        deployed = [s for s in all_servers if s.get("isDeployed")]
        print(f"  {len(deployed)} deployed servers — fetching tool details...")

        semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
        detail_tasks = [
            fetch_server_detail(client, s["qualifiedName"], semaphore)
            for s in deployed
        ]
        details = await asyncio.gather(*detail_tasks, return_exceptions=True)

        # Step 3: Process each server with tools
        # Collect all tools to embed in batches
        pending_tools: list[dict] = []  # (provider_info, tool_data, metadata)

        for server_summary, detail in zip(deployed, details):
            if isinstance(detail, Exception) or detail is None:
                stats["errors"] += 1
                continue

            tools = detail.get("tools", [])
            if not tools:
                continue

            stats["servers_with_tools"] += 1
            domain = _extract_domain(detail)
            server_name = detail.get("displayName") or server_summary.get("displayName") or domain
            description = detail.get("description") or server_summary.get("description", "")

            for tool in tools:
                if not isinstance(tool, dict) or "name" not in tool:
                    continue
                tool_desc = tool.get("description") or ""
                pending_tools.append({
                    "domain": domain,
                    "server_name": server_name,
                    "server_description": description,
                    "server_qualified_name": server_summary.get("qualifiedName", ""),
                    "server_use_count": server_summary.get("useCount", 0),
                    "server_verified": server_summary.get("verified", False),
                    "tool_name": tool["name"],
                    "tool_description": tool_desc,
                    "tool_input_schema": tool.get("inputSchema"),
                })

        print(f"  {len(pending_tools)} tools to process from {stats['servers_with_tools']} servers")

        # Step 4: Embed and store in batches (each batch is its own transaction)
        from src.db import async_session

        for batch_start in range(0, len(pending_tools), EMBED_BATCH_SIZE):
            batch = pending_tools[batch_start : batch_start + EMBED_BATCH_SIZE]

            # Build texts for embedding
            texts = [
                build_tool_text(t["tool_name"], t["tool_description"], t["domain"])
                for t in batch
            ]

            try:
                embeddings = await embed_texts(texts)
            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                stats["errors"] += len(batch)
                continue

            # Use a fresh session per batch to isolate errors
            async with async_session() as batch_db:
                batch_ok = True
                for tool_entry, embedding in zip(batch, embeddings):
                    try:
                        # Get or create provider
                        stmt = select(Provider).where(Provider.domain == tool_entry["domain"])
                        provider = (await batch_db.execute(stmt)).scalar_one_or_none()
                        if provider is None:
                            provider = Provider(
                                domain=tool_entry["domain"],
                                name=tool_entry["server_name"],
                                description=tool_entry["server_description"][:500] if tool_entry["server_description"] else "",
                                homepage_url=f"https://smithery.ai/server/{tool_entry['server_qualified_name']}",
                            )
                            batch_db.add(provider)
                            await batch_db.flush()
                            stats["providers_created"] += 1

                        # Check for existing tool
                        stmt = select(Tool).where(
                            Tool.provider_id == provider.id,
                            Tool.name == tool_entry["tool_name"],
                            Tool.protocol == "mcp",
                        )
                        existing = (await batch_db.execute(stmt)).scalar_one_or_none()

                        metadata = {
                            "source": "smithery",
                            "smithery_qualified_name": tool_entry["server_qualified_name"],
                            "use_count": tool_entry["server_use_count"],
                            "verified": tool_entry["server_verified"],
                        }

                        desc = tool_entry["tool_description"] or tool_entry["tool_name"]

                        if existing:
                            existing.description = desc
                            existing.input_schema = tool_entry["tool_input_schema"]
                            existing.embedding = embedding
                            existing.metadata_ = metadata
                            existing.last_seen = func.now()
                            stats["tools_updated"] += 1
                        else:
                            tool = Tool(
                                provider_id=provider.id,
                                name=tool_entry["tool_name"],
                                description=desc,
                                protocol="mcp",
                                input_schema=tool_entry["tool_input_schema"],
                                endpoint=f"https://smithery.ai/server/{tool_entry['server_qualified_name']}",
                                embedding=embedding,
                                metadata_=metadata,
                            )
                            batch_db.add(tool)
                            stats["tools_added"] += 1

                    except Exception as e:
                        logger.error(f"Error storing tool {tool_entry['tool_name']}: {e}")
                        stats["errors"] += 1
                        batch_ok = False
                        break

                if batch_ok:
                    await batch_db.commit()
                else:
                    await batch_db.rollback()

            processed = min(batch_start + EMBED_BATCH_SIZE, len(pending_tools))
            print(f"  Processed {processed}/{len(pending_tools)} tools...")

    return stats
