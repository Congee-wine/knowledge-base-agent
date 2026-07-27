"""Add stable per-conversation message ordering.

Revision ID: 20260727_0008
Revises: 20260727_0007
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("message_order", sa.BigInteger(), nullable=True))
    op.execute(
        """WITH ordered_messages AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY conversation_id
                ORDER BY created_at, id
            ) AS message_order
            FROM messages
        )
        UPDATE messages
        SET message_order = ordered_messages.message_order
        FROM ordered_messages
        WHERE messages.id = ordered_messages.id"""
    )
    op.alter_column("messages", "message_order", nullable=False)
    op.create_unique_constraint(
        "uq_messages_conversation_message_order",
        "messages",
        ["conversation_id", "message_order"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_messages_conversation_message_order", "messages", type_="unique")
    op.drop_column("messages", "message_order")
