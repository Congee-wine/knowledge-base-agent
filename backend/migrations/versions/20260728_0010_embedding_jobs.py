"""Add versioned embedding jobs.

Revision ID: 20260728_0010
Revises: 20260727_0009
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0010"
down_revision = "20260727_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_versions", sa.Column("index_status", sa.Text(), nullable=False, server_default="pending"))
    op.create_check_constraint("ck_document_versions_index_status", "document_versions", "index_status IN ('pending', 'processing', 'ready', 'failed')")
    op.create_table(
        "embedding_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('queued', 'processing', 'succeeded', 'failed')", name="ck_embedding_jobs_status"),
        sa.CheckConstraint("attempt_number > 0", name="ck_embedding_jobs_attempt"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.UniqueConstraint("document_version_id", "attempt_number", name="uq_embedding_jobs_version_attempt"),
    )
    op.create_index("ix_embedding_jobs_version_status", "embedding_jobs", ["document_version_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_embedding_jobs_version_status", table_name="embedding_jobs")
    op.drop_table("embedding_jobs")
    op.drop_constraint("ck_document_versions_index_status", "document_versions", type_="check")
    op.drop_column("document_versions", "index_status")
