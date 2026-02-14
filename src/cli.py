"""CLI for Ocean — crawl, seed, search, stats."""

import asyncio
import sys


async def crawl():
    """Run a full crawl of seed domains."""
    from src.crawler.mcp import crawl_domains
    from src.crawler.seed import collect_seed_domains
    from src.db import async_session

    print("Collecting seed domains...")
    domains = await collect_seed_domains()
    print(f"Found {len(domains)} domains to crawl")

    async with async_session() as db:
        print("Crawling...")
        stats = await crawl_domains(db, domains)
        print(f"\nCrawl complete:")
        print(f"  Domains scanned: {stats['total']}")
        print(f"  MCP servers found: {stats['found']}")
        print(f"  New tools added: {stats['tools_added']}")
        if stats['errors']:
            print(f"  Errors: {stats['errors']}")


async def crawl_smithery():
    """Crawl Smithery registry for MCP tools."""
    from src.crawler.smithery import crawl_smithery as _crawl
    from src.db import async_session

    print("\n=== Crawling Smithery ===")
    async with async_session() as db:
        stats = await _crawl(db)
    print(f"\nSmithery crawl complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


async def crawl_glama(max_pages: int = 0):
    """Crawl Glama registry for MCP server metadata."""
    from src.crawler.glama import crawl_glama as _crawl
    from src.db import async_session

    print("\n=== Crawling Glama ===")
    async with async_session() as db:
        stats = await _crawl(db, max_pages=max_pages)
    print(f"\nGlama crawl complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


async def crawl_pulsemcp():
    """Crawl PulseMCP for MCP server metadata."""
    from src.crawler.pulsemcp import crawl_pulsemcp as _crawl
    from src.db import async_session

    print("\n=== Crawling PulseMCP ===")
    async with async_session() as db:
        stats = await _crawl(db)
    print(f"\nPulseMCP crawl complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


async def crawl_all():
    """Crawl all registries sequentially."""
    await crawl_smithery()
    await crawl_glama()
    await crawl_pulsemcp()


async def seed():
    """Seed the database with curated MCP tool data."""
    from src.seed_data import seed as run_seed
    await run_seed()


async def search(query: str, limit: int = 10):
    """Semantic search for tools matching a query."""
    from src.db import async_session
    from src.search.ranking import discover_tools

    async with async_session() as db:
        results = await discover_tools(db, query, limit=limit)

    if not results:
        print("No tools found.")
        return

    print(f"\nResults for: \"{query}\"\n")
    for i, r in enumerate(results, 1):
        score = r["relevance_score"]
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {i:2d}. [{bar}] {score:.2f}  {r['provider_name']}  →  {r['name']}")
        print(f"      {r['description'][:80]}")
        print(f"      protocol: {r['protocol']}  endpoint: {r['endpoint']}")
        print()


def gen_key():
    """Generate a new API key."""
    from src.auth import generate_api_key
    key = generate_api_key()
    print(f"\nNew API key: {key}")
    print("Use it in requests: curl -H 'X-API-Key: {key}' ...")
    print()


async def dedup():
    """Remove duplicate tools from the index."""
    from src.dedup import run as run_dedup
    await run_dedup()


async def stats():
    """Print index stats."""
    from sqlalchemy import func, select

    from src.db import async_session
    from src.models.provider import Provider
    from src.models.tool import Tool

    async with async_session() as db:
        tool_count = (await db.execute(select(func.count(Tool.id)))).scalar()
        provider_count = (await db.execute(select(func.count(Provider.id)))).scalar()
        print(f"\nOcean Index Stats")
        print(f"  Tools:     {tool_count}")
        print(f"  Providers: {provider_count}")

        rows = (
            await db.execute(
                select(Tool.protocol, func.count(Tool.id)).group_by(Tool.protocol)
            )
        ).all()
        print(f"\n  By protocol:")
        for protocol, count in rows:
            print(f"    {protocol}: {count}")
        print()


def main():
    if len(sys.argv) < 2:
        print("Ocean — Semantic discovery engine for AI agent tools\n")
        print("Usage: python -m src.cli <command> [args]\n")
        print("Commands:")
        print("  search <query>        Search for tools by intent")
        print("  crawl                 Crawl seed domains for .well-known/mcp")
        print("  crawl-smithery        Crawl Smithery registry (~7K tools)")
        print("  crawl-glama [pages]   Crawl Glama registry (~17K servers)")
        print("  crawl-pulsemcp        Crawl PulseMCP registry (~8K servers)")
        print("  crawl-all             Crawl all registries")
        print("  seed                  Seed DB with curated tool data")
        print("  gen-key               Generate a new API key")
        print("  dedup                 Remove duplicate tools")
        print("  stats                 Show index statistics")
        sys.exit(1)

    command = sys.argv[1]
    if command == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not query:
            print("Usage: python -m src.cli search <query>")
            sys.exit(1)
        asyncio.run(search(query))
    elif command == "crawl":
        asyncio.run(crawl())
    elif command == "crawl-smithery":
        asyncio.run(crawl_smithery())
    elif command == "crawl-glama":
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        asyncio.run(crawl_glama(max_pages))
    elif command == "crawl-pulsemcp":
        asyncio.run(crawl_pulsemcp())
    elif command == "crawl-all":
        asyncio.run(crawl_all())
    elif command == "seed":
        asyncio.run(seed())
    elif command == "gen-key":
        gen_key()
    elif command == "dedup":
        asyncio.run(dedup())
    elif command == "stats":
        asyncio.run(stats())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
