"""Add streaming generation request identity and state.

Revision ID: 20260725_0006
Revises: 20260725_0005
Create Date: 2026-07-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260725_0006"
down_revision = "20260725_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("client_request_id", sa.Text(), nullable=True))
    op.create_index("uq_messages_client_request_id", "messages", ["client_request_id"], unique=True, postgresql_where=sa.text("client_request_id IS NOT NULL"))
    op.drop_constraint("ck_messages_generation_status", "messages", type_="check")
    op.create_check_constraint("ck_messages_generation_status", "messages", "generation_status IN ('generating', 'complete', 'interrupted', 'failed')")


def downgrade() -> None:
    op.drop_constraint("ck_messages_generation_status", "messages", type_="check")
    op.create_check_constraint("ck_messages_generation_status", "messages", "generation_status IN ('complete', 'interrupted', 'failed')")
    op.drop_index("uq_messages_client_request_id", table_name="messages")
    op.drop_column("messages", "client_request_id")
