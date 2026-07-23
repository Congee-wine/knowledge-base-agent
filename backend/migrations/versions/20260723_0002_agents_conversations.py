"""Create agents, preferences, conversations, and messages.

Revision ID: 20260723_0002
Revises: 20260720_0001
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260723_0002"
down_revision = "20260720_0001"
branch_labels = None
depends_on = None

BUILTIN_AGENT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("avatar_key", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("welcome_message", sa.Text(), nullable=True),
        sa.Column("allow_conversation_upload", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('builtin', 'personal')", name="ck_agents_kind"),
        sa.CheckConstraint(
            "(kind = 'builtin' AND owner_user_id IS NULL) OR (kind = 'personal' AND owner_user_id IS NOT NULL)",
            name="ck_agents_owner_by_kind",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
    )
    op.create_index("ix_agents_owner_active_updated", "agents", ["owner_user_id", "deleted_at", "updated_at"])
    op.execute(
        """CREATE UNIQUE INDEX uq_personal_agent_active_name
        ON agents (owner_user_id, lower(name)) WHERE kind = 'personal' AND deleted_at IS NULL"""
    )
    op.create_table(
        "user_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("default_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["default_agent_id"], ["agents.id"]),
    )
    op.create_table(
        "agent_preset_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.UniqueConstraint("agent_id", "display_order", name="uq_agent_preset_question_order"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
    )
    op.create_index("ix_conversations_owner_agent_updated", "conversations", ["owner_user_id", "agent_id", "updated_at"])
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generation_status", sa.Text(), nullable=False, server_default="complete"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        sa.CheckConstraint("generation_status IN ('complete', 'interrupted', 'failed')", name="ck_messages_generation_status"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])
    op.execute(
        f"""INSERT INTO agents (
            id, owner_user_id, kind, name, description, avatar_key, system_prompt,
            welcome_message, allow_conversation_upload, created_at, updated_at
        ) VALUES (
            '{BUILTIN_AGENT_ID}', NULL, 'builtin', 'AI 管家',
            '系统内置的通用 AI 助手', 'builtin-ai-manager', NULL,
            '你好，我是 AI 管家，有什么可以帮助你？', false, now(), now()
        ) ON CONFLICT (id) DO NOTHING"""
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_owner_agent_updated", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("agent_preset_questions")
    op.drop_table("user_preferences")
    op.execute("DROP INDEX uq_personal_agent_active_name")
    op.drop_index("ix_agents_owner_active_updated", table_name="agents")
    op.drop_table("agents")
