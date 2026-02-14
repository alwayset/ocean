import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config import settings
from src.models.base import Base, TimestampMixin, UUIDMixin


class Tool(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tools"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)  # mcp, webmcp, a2a, openapi
    input_schema: Mapped[dict | None] = mapped_column(JSONB)
    output_schema: Mapped[dict | None] = mapped_column(JSONB)
    endpoint: Mapped[str | None] = mapped_column(String(1024))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimensions)
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    call_count: Mapped[int] = mapped_column(Integer, default=0)

    provider: Mapped["Provider"] = relationship(back_populates="tools")  # noqa: F821
    quality_metrics: Mapped[list["QualityMetric"]] = relationship(  # noqa: F821
        back_populates="tool"
    )

    __table_args__ = (
        Index("ix_tools_provider_name_protocol", "provider_id", "name", "protocol", unique=True),
        Index("ix_tools_protocol", "protocol"),
    )
