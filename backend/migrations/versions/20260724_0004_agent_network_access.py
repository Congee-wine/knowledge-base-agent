"""Add personal agent network visibility setting.

Revision ID: 20260724_0004
Revises: 20260723_0003
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0004"
down_revision = "20260723_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("allow_network_access", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("agents", "allow_network_access", server_default=None)


def downgrade() -> None:
    op.drop_column("agents", "allow_network_access")
