"""API request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# --- Discovery ---


class DiscoverRequest(BaseModel):
    intent: str = Field(..., description="Natural language description of what the agent needs")
    constraints: dict | None = Field(
        default=None,
        description="Optional filters: protocol, min_reliability, provider, etc.",
    )
    limit: int = Field(default=10, ge=1, le=50)


class ToolResult(BaseModel):
    id: uuid.UUID
    provider_domain: str
    provider_name: str | None
    name: str
    description: str
    protocol: str
    input_schema: dict | None
    endpoint: str | None
    relevance_score: float
    reliability: float | None = None
    avg_latency_ms: int | None = None

    model_config = {"from_attributes": True}


class DiscoverResponse(BaseModel):
    query: str
    results: list[ToolResult]
    total: int


# --- Tools ---


class ToolDetail(BaseModel):
    id: uuid.UUID
    provider_domain: str
    provider_name: str | None
    name: str
    description: str
    protocol: str
    input_schema: dict | None
    output_schema: dict | None
    endpoint: str | None
    metadata: dict
    call_count: int
    created_at: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


class ToolListResponse(BaseModel):
    tools: list[ToolResult]
    total: int
    page: int
    page_size: int


# --- Registration ---


class RegisterToolRequest(BaseModel):
    provider_domain: str = Field(..., description="Domain of the tool provider (e.g. 'github.com')")
    provider_name: str | None = Field(default=None, description="Human-readable provider name")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="What the tool does")
    protocol: str = Field(default="mcp", description="Protocol: mcp, webmcp, a2a, openapi")
    input_schema: dict | None = None
    output_schema: dict | None = None
    endpoint: str | None = None


class RegisterToolResponse(BaseModel):
    id: uuid.UUID
    message: str


# --- Stats ---


class StatsResponse(BaseModel):
    total_tools: int
    total_providers: int
    protocols: dict[str, int]
