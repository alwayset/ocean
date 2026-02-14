"""Tool browsing, detail, and registration endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    RegisterToolRequest,
    RegisterToolResponse,
    StatsResponse,
    ToolDetail,
    ToolListResponse,
    ToolResult,
)
from src.config import settings
from src.db import get_db
from src.models.provider import Provider
from src.models.tool import Tool
from src.search.embeddings import build_tool_text, embed_text

from src.auth import require_api_key

router = APIRouter(prefix="/v1", tags=["tools"], dependencies=[Depends(require_api_key)])


@router.get("/tools", response_model=ToolListResponse)
async def list_tools(
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    protocol: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all indexed tools with pagination."""
    stmt = (
        select(Tool, Provider.domain.label("provider_domain"), Provider.name.label("provider_name"))
        .join(Provider, Tool.provider_id == Provider.id)
        .order_by(Tool.call_count.desc(), Tool.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if protocol:
        stmt = stmt.where(Tool.protocol == protocol)

    count_stmt = select(func.count(Tool.id))
    if protocol:
        count_stmt = count_stmt.where(Tool.protocol == protocol)

    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar() or 0

    tools = [
        ToolResult(
            id=row.Tool.id,
            provider_domain=row.provider_domain,
            provider_name=row.provider_name,
            name=row.Tool.name,
            description=row.Tool.description,
            protocol=row.Tool.protocol,
            input_schema=row.Tool.input_schema,
            endpoint=row.Tool.endpoint,
            relevance_score=0.0,
        )
        for row in rows
    ]

    return ToolListResponse(tools=tools, total=total, page=page, page_size=page_size)


@router.get("/tools/{tool_id}", response_model=ToolDetail)
async def get_tool(tool_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get full details for a specific tool."""
    stmt = (
        select(Tool, Provider.domain.label("provider_domain"), Provider.name.label("provider_name"))
        .join(Provider, Tool.provider_id == Provider.id)
        .where(Tool.id == tool_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")

    tool = row.Tool
    return ToolDetail(
        id=tool.id,
        provider_domain=row.provider_domain,
        provider_name=row.provider_name,
        name=tool.name,
        description=tool.description,
        protocol=tool.protocol,
        input_schema=tool.input_schema,
        output_schema=tool.output_schema,
        endpoint=tool.endpoint,
        metadata=tool.metadata_,
        call_count=tool.call_count,
        created_at=tool.created_at,
        last_seen=tool.last_seen,
    )


@router.post("/tools", response_model=RegisterToolResponse, status_code=201)
async def register_tool(req: RegisterToolRequest, db: AsyncSession = Depends(get_db)):
    """Register a new tool. Providers can submit their tools directly."""
    # Get or create provider
    stmt = select(Provider).where(Provider.domain == req.provider_domain)
    provider = (await db.execute(stmt)).scalar_one_or_none()
    if provider is None:
        provider = Provider(
            domain=req.provider_domain,
            name=req.provider_name or req.provider_domain,
            homepage_url=f"https://{req.provider_domain}",
        )
        db.add(provider)
        await db.flush()

    # Check for duplicates
    stmt = select(Tool).where(
        Tool.provider_id == provider.id,
        Tool.name == req.name,
        Tool.protocol == req.protocol,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Tool already registered")

    # Generate embedding
    text = build_tool_text(req.name, req.description, req.provider_domain)
    embedding = await embed_text(text)

    tool = Tool(
        provider_id=provider.id,
        name=req.name,
        description=req.description,
        protocol=req.protocol,
        input_schema=req.input_schema,
        output_schema=req.output_schema,
        endpoint=req.endpoint,
        embedding=embedding,
    )
    db.add(tool)
    await db.commit()

    return RegisterToolResponse(id=tool.id, message="Tool registered successfully")


@router.get("/stats", response_model=StatsResponse)
async def stats(db: AsyncSession = Depends(get_db)):
    """Get index statistics."""
    tool_count = (await db.execute(select(func.count(Tool.id)))).scalar() or 0
    provider_count = (await db.execute(select(func.count(Provider.id)))).scalar() or 0

    protocol_rows = (
        await db.execute(
            select(Tool.protocol, func.count(Tool.id)).group_by(Tool.protocol)
        )
    ).all()
    protocols = {row[0]: row[1] for row in protocol_rows}

    return StatsResponse(
        total_tools=tool_count,
        total_providers=provider_count,
        protocols=protocols,
    )
