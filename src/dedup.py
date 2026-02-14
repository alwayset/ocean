"""Deduplicate tools across data sources.

Strategy:
1. Exact duplicates (same name + description): keep the one with richest metadata
   Priority: smithery > seed > pulsemcp > other
2. Leave near-duplicates (same name, different description) — handle at search layer
"""

import asyncio

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import async_session
from src.models.tool import Tool

SOURCE_PRIORITY = {"smithery": 0, "seed": 1, "webmcp_crawl": 2, "pulsemcp": 3}


def _source_rank(tool: Tool) -> int:
    source = (tool.metadata_ or {}).get("source", "unknown")
    return SOURCE_PRIORITY.get(source, 99)


async def dedup_exact():
    """Remove exact duplicate tools (same name + description).

    For each group, keep the tool with the highest source priority.
    """
    async with async_session() as db:
        # Find all exact duplicate groups
        result = await db.execute(text("""
            SELECT name, description, array_agg(id::text) as ids, COUNT(*) as cnt
            FROM tools
            WHERE description IS NOT NULL AND description != ''
            GROUP BY name, description
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
        """))
        groups = result.fetchall()

        total_removed = 0
        for group in groups:
            name, description, id_strs, count = group
            # Fetch all tools in this group
            ids = [i for i in id_strs]
            stmt = select(Tool).where(Tool.id.in_(ids))
            tools = (await db.execute(stmt)).scalars().all()

            # Sort by source priority (lower = better)
            tools_sorted = sorted(tools, key=_source_rank)

            # Keep the first (best), delete the rest
            to_remove = tools_sorted[1:]
            for tool in to_remove:
                await db.delete(tool)
                total_removed += 1

        await db.commit()
        return total_removed


async def dedup_stats():
    """Print dedup statistics."""
    async with async_session() as db:
        total = (await db.execute(text("SELECT COUNT(*) FROM tools"))).scalar()
        exact_dupes = (await db.execute(text("""
            SELECT SUM(cnt - 1) FROM (
                SELECT COUNT(*) as cnt FROM tools
                WHERE description IS NOT NULL AND description != ''
                GROUP BY name, description
                HAVING COUNT(*) > 1
            ) sub
        """))).scalar() or 0

        print(f"\nDedup Analysis:")
        print(f"  Total tools: {total}")
        print(f"  Exact duplicates (removable): {int(exact_dupes)}")
        print(f"  After dedup: {total - int(exact_dupes)}")


async def run():
    await dedup_stats()
    print("\nRunning dedup...")
    removed = await dedup_exact()
    print(f"Removed {removed} exact duplicates")
    await dedup_stats()


if __name__ == "__main__":
    asyncio.run(run())
