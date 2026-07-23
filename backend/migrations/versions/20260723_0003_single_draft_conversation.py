"""Allow one draft conversation per user and agent.

Revision ID: 20260723_0003
Revises: 20260723_0002
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0003"
down_revision = "20260723_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute(
        """WITH ranked_drafts AS (
            SELECT id, row_number() OVER (
                PARTITION BY owner_user_id, agent_id ORDER BY updated_at DESC, id DESC
            ) AS position
            FROM conversations
            WHERE title IS NULL
              AND NOT EXISTS (SELECT 1 FROM messages WHERE messages.conversation_id = conversations.id)
        )
        UPDATE conversations
        SET is_draft = true
        FROM ranked_drafts
        WHERE conversations.id = ranked_drafts.id AND ranked_drafts.position = 1"""
    )
    op.execute(
        """CREATE UNIQUE INDEX uq_conversations_one_draft_per_owner_agent
        ON conversations (owner_user_id, agent_id) WHERE is_draft"""
    )
    op.alter_column("conversations", "is_draft", server_default=None)


def downgrade() -> None:
    op.execute("DROP INDEX uq_conversations_one_draft_per_owner_agent")
    op.drop_column("conversations", "is_draft")
