"""Initial schema — providers, tools, quality_metrics

Revision ID: 001
Revises: None
Create Date: 2026-02-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "providers",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("domain", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("homepage_url", sa.String(512)),
        sa.Column("icon_url", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tools",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", sa.UUID(), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("protocol", sa.String(20), nullable=False),
        sa.Column("input_schema", sa.JSON()),
        sa.Column("output_schema", sa.JSON()),
        sa.Column("endpoint", sa.String(1024)),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column("embedding", Vector(768)),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("call_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_tools_provider_name_protocol",
        "tools",
        ["provider_id", "name", "protocol"],
        unique=True,
    )
    op.create_index("ix_tools_protocol", "tools", ["protocol"])
    # HNSW index for vector similarity search (supports >2000 dimensions)
    op.execute(
        "CREATE INDEX ix_tools_embedding ON tools USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "quality_metrics",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tool_id", sa.UUID(), sa.ForeignKey("tools.id"), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("uptime", sa.Float()),
        sa.Column("avg_latency_ms", sa.Integer()),
        sa.Column("p95_latency_ms", sa.Integer()),
        sa.Column("error_rate", sa.Float()),
        sa.Column("sample_count", sa.Integer()),
    )
    op.create_index("ix_quality_metrics_tool_id", "quality_metrics", ["tool_id"])


def downgrade() -> None:
    op.drop_table("quality_metrics")
    op.drop_table("tools")
    op.drop_table("providers")
    op.execute("DROP EXTENSION IF EXISTS vector")
