"""MCP server crawler — discovers tools via .well-known/mcp/server.json endpoints."""

import asyncio
import logging
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.provider import Provider
from src.models.tool import Tool
from src.search.embeddings import build_tool_text, embed_texts

logger = logging.getLogger(__name__)


async def crawl_domain(client: httpx.AsyncClient, domain: str) -> dict | None:
    """Try to fetch .well-known/mcp/server.json from a domain."""
    url = f"https://{domain}/.well-known/mcp/server.json"
    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Found MCP server at {domain}")
            return data
    except Exception as e:
        logger.debug(f"No MCP server at {domain}: {e}")
    return None


def extract_tools_from_server_json(data: dict) -> list[dict]:
    """Extract tool definitions from an MCP server.json response."""
    tools = []

    # server.json can have tools at top level or nested under capabilities
    raw_tools = data.get("tools", [])
    if not raw_tools:
        capabilities = data.get("capabilities", {})
        raw_tools = capabilities.get("tools", [])

    for tool in raw_tools:
        if isinstance(tool, dict) and "name" in tool:
            tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", tool.get("input_schema")),
                "output_schema": tool.get("outputSchema", tool.get("output_schema")),
            })

    return tools


async def get_or_create_provider(db: AsyncSession, domain: str, server_data: dict) -> Provider:
    """Get existing provider or create a new one."""
    stmt = select(Provider).where(Provider.domain == domain)
    provider = (await db.execute(stmt)).scalar_one_or_none()

    if provider is None:
        provider = Provider(
            domain=domain,
            name=server_data.get("name", domain),
            description=server_data.get("description"),
            homepage_url=f"https://{domain}",
        )
        db.add(provider)
        await db.flush()

    return provider


async def upsert_tools(
    db: AsyncSession,
    provider: Provider,
    tools_data: list[dict],
    domain: str,
) -> int:
    """Insert or update tools for a provider. Returns count of new/updated tools."""
    if not tools_data:
        return 0

    # Generate embeddings for all tools in batch
    texts = [
        build_tool_text(t["name"], t.get("description", ""), domain)
        for t in tools_data
    ]
    embeddings = await embed_texts(texts)

    count = 0
    for tool_data, embedding in zip(tools_data, embeddings):
        stmt = select(Tool).where(
            Tool.provider_id == provider.id,
            Tool.name == tool_data["name"],
            Tool.protocol == "mcp",
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.description = tool_data.get("description", existing.description)
            existing.input_schema = tool_data.get("input_schema")
            existing.output_schema = tool_data.get("output_schema")
            existing.embedding = embedding
            from sqlalchemy import func
            existing.last_seen = func.now()
        else:
            tool = Tool(
                provider_id=provider.id,
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                protocol="mcp",
                input_schema=tool_data.get("input_schema"),
                output_schema=tool_data.get("output_schema"),
                endpoint=f"https://{domain}/.well-known/mcp/server.json",
                embedding=embedding,
            )
            db.add(tool)
            count += 1

    await db.flush()
    return count


async def crawl_domains(db: AsyncSession, domains: list[str]) -> dict:
    """Crawl a list of domains for MCP servers. Returns summary stats."""
    stats = {"total": len(domains), "found": 0, "tools_added": 0, "errors": 0}

    semaphore = asyncio.Semaphore(settings.crawl_concurrency)

    async def crawl_one(domain: str):
        async with semaphore:
            async with httpx.AsyncClient(timeout=settings.crawl_timeout_seconds) as client:
                data = await crawl_domain(client, domain)
                if data is None:
                    return

                stats["found"] += 1
                tools_data = extract_tools_from_server_json(data)
                if tools_data:
                    provider = await get_or_create_provider(db, domain, data)
                    added = await upsert_tools(db, provider, tools_data, domain)
                    stats["tools_added"] += added

    tasks = [crawl_one(domain) for domain in domains]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, Exception):
            stats["errors"] += 1
            logger.error(f"Crawl error: {r}")

    await db.commit()
    return stats
