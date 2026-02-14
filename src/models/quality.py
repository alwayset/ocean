import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


class QualityMetric(Base, UUIDMixin):
    __tablename__ = "quality_metrics"

    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    uptime: Mapped[float | None] = mapped_column(Float)  # 0-1, rolling window
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer)
    p95_latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_rate: Mapped[float | None] = mapped_column(Float)  # 0-1
    sample_count: Mapped[int | None] = mapped_column(Integer)

    tool: Mapped["Tool"] = relationship(back_populates="quality_metrics")  # noqa: F821
