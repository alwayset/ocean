"""Search and ranking engine using pgvector similarity search."""

import uuid

from sqlalchemy import select, func, case, literal
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tool import Tool
from src.models.provider import Provider
from src.models.quality import QualityMetric
from src.search.embeddings import embed_query


async def discover_tools(
    db: AsyncSession,
    intent: str,
    *,
    limit: int = 10,
    protocol: str | None = None,
    min_reliability: float | None = None,
    provider_domain: str | None = None,
) -> list[dict]:
    """Semantic search for tools matching an intent.

    Returns tools ranked by vector similarity, deduplicated by name+description.
    Fetches extra candidates to ensure enough unique results after dedup.
    """
    query_embedding = await embed_query(intent)

    # Cosine distance — lower is more similar
    distance = Tool.embedding.cosine_distance(query_embedding).label("distance")

    # Fetch 3x the limit to have room for dedup
    fetch_limit = limit * 3

    stmt = (
        select(
            Tool,
            Provider.domain.label("provider_domain"),
            Provider.name.label("provider_name"),
            distance,
        )
        .join(Provider, Tool.provider_id == Provider.id)
        .where(Tool.embedding.isnot(None))
        .order_by(distance)
        .limit(fetch_limit)
    )

    if protocol:
        stmt = stmt.where(Tool.protocol == protocol)

    if provider_domain:
        stmt = stmt.where(Provider.domain == provider_domain)

    rows = (await db.execute(stmt)).all()

    # Deduplicate: for tools with the same name, keep only the highest-ranked one
    seen_names: set[str] = set()
    results = []
    for row in rows:
        tool = row.Tool
        dedup_key = tool.name.lower()

        if dedup_key in seen_names:
            continue
        seen_names.add(dedup_key)

        relevance = max(0.0, 1.0 - row.distance)

        results.append({
            "id": tool.id,
            "provider_domain": row.provider_domain,
            "provider_name": row.provider_name,
            "name": tool.name,
            "description": tool.description,
            "protocol": tool.protocol,
            "input_schema": tool.input_schema,
            "endpoint": tool.endpoint,
            "relevance_score": round(relevance, 4),
            "reliability": None,
            "avg_latency_ms": None,
        })

        if len(results) >= limit:
            break

    # Filter by reliability if requested (post-filter for now)
    if min_reliability is not None:
        results = [r for r in results if r["reliability"] is None or r["reliability"] >= min_reliability]

    return results
