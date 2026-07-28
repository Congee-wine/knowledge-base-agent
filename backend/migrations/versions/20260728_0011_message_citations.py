"""Store retrieval citations with assistant messages.

Revision ID: 20260728_0011
Revises: 20260728_0010
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0011"
down_revision = "20260728_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("citations_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    op.drop_column("messages", "citations_json")
