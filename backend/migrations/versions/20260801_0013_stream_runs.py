"""Add durable streaming runs for SSE resumption.

Revision ID: 20260801_0013
Revises: 20260729_0012
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260801_0013"
down_revision = "20260729_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_messages_generation_status", "messages", type_="check")
    op.create_check_constraint(
        "ck_messages_generation_status", "messages",
        "generation_status IN ('generating', 'complete', 'interrupted', 'failed', 'timed_out')",
    )
    op.create_table(
        "stream_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=False, unique=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assistant_message_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("use_knowledge_base", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('queued', 'generating', 'complete', 'failed', 'interrupted', 'timed_out')", name="ck_stream_runs_status"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["assistant_message_id"], ["messages.id"]),
    )
    op.create_index("ix_stream_runs_owner_status", "stream_runs", ["owner_user_id", "status"])
    op.create_index("ix_stream_runs_conversation_status", "stream_runs", ["conversation_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_stream_runs_conversation_status", table_name="stream_runs")
    op.drop_index("ix_stream_runs_owner_status", table_name="stream_runs")
    op.drop_table("stream_runs")
    op.drop_constraint("ck_messages_generation_status", "messages", type_="check")
    op.create_check_constraint("ck_messages_generation_status", "messages", "generation_status IN ('generating', 'complete', 'interrupted', 'failed')")
