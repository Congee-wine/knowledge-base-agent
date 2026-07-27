"""Add message reply relation and cross-conversation reference guard.

Revision ID: 20260727_0007
Revises: 20260725_0006
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0007"
down_revision = "20260725_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("reply_to_message_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_index("ix_messages_reply_to_message_id", "messages", ["reply_to_message_id"])

    op.create_check_constraint(
        "ck_messages_reply_to_role",
        "messages",
        "reply_to_message_id IS NULL OR role = 'assistant'",
    )

    op.create_unique_constraint("uq_messages_id_conversation_id", "messages", ["id", "conversation_id"])

    op.create_foreign_key(
        "fk_messages_reply_to_message_id",
        "messages",
        "messages",
        ["reply_to_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_messages_reply_conversation",
        "messages",
        "messages",
        ["reply_to_message_id", "conversation_id"],
        ["id", "conversation_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_reply_conversation", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_reply_to_message_id", "messages", type_="foreignkey")
    op.drop_constraint("uq_messages_id_conversation_id", "messages", type_="unique")
    op.drop_constraint("ck_messages_reply_to_role", "messages", type_="check")
    op.drop_index("ix_messages_reply_to_message_id", table_name="messages")
    op.drop_column("messages", "reply_to_message_id")
