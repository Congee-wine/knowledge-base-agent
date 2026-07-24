"""Add agent interaction type.

Revision ID: 20260724_0005
Revises: 20260724_0004
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0005"
down_revision = "20260724_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("interaction_type", sa.Text(), nullable=False, server_default=sa.text("'text'")))
    op.create_check_constraint("ck_agents_interaction_type", "agents", "interaction_type IN ('text', 'voice', 'digital_human')")
    op.alter_column("agents", "interaction_type", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_agents_interaction_type", "agents", type_="check")
    op.drop_column("agents", "interaction_type")
