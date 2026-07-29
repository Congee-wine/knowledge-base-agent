"""Add retrieval diagnostics and keyword-search index.

Revision ID: 20260729_0012
Revises: 20260728_0011
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260729_0012"
down_revision = "20260728_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX ix_document_chunks_content_trgm ON document_chunks USING gin (content gin_trgm_ops)")
    op.create_table(
        "retrieval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
    )
    op.create_index("ix_retrieval_runs_owner_created", "retrieval_runs", ["owner_user_id", "created_at"])
    op.create_table(
        "retrieval_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("retrieval_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vector_rank", sa.Integer(), nullable=True),
        sa.Column("keyword_rank", sa.Integer(), nullable=True),
        sa.Column("fusion_rank", sa.Integer(), nullable=True),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("discard_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["retrieval_run_id"], ["retrieval_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"]),
    )
    op.create_index("ix_retrieval_candidates_run", "retrieval_candidates", ["retrieval_run_id"])


def downgrade() -> None:
    op.drop_index("ix_retrieval_candidates_run", table_name="retrieval_candidates")
    op.drop_table("retrieval_candidates")
    op.drop_index("ix_retrieval_runs_owner_created", table_name="retrieval_runs")
    op.drop_table("retrieval_runs")
    op.drop_index("ix_document_chunks_content_trgm", table_name="document_chunks")
