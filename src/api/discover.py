"""Discovery API — the core product endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import DiscoverRequest, DiscoverResponse, ToolResult
from src.db import get_db
from src.search.ranking import discover_tools

router = APIRouter(prefix="/v1", tags=["discovery"])


@router.post("/discover", response_model=DiscoverResponse)
async def discover(request: DiscoverRequest, db: AsyncSession = Depends(get_db)):
    """Discover tools matching a natural language intent.

    Agents call this endpoint with a description of what they need.
    Returns ranked tools with schemas ready for invocation.
    """
    constraints = request.constraints or {}

    results = await discover_tools(
        db,
        request.intent,
        limit=request.limit,
        protocol=constraints.get("protocol"),
        min_reliability=constraints.get("min_reliability"),
        provider_domain=constraints.get("provider"),
    )

    return DiscoverResponse(
        query=request.intent,
        results=[ToolResult(**r) for r in results],
        total=len(results),
    )
