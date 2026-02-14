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
        print("  search <query>   Search for tools by intent")
        print("  crawl            Crawl seed domains for MCP servers")
        print("  seed             Seed DB with curated tool data")
        print("  stats            Show index statistics")
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
    elif command == "seed":
        asyncio.run(seed())
    elif command == "stats":
        asyncio.run(stats())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
