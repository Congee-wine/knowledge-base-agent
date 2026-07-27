"""Create private knowledge-tree and document-processing foundation.

Revision ID: 20260727_0009
Revises: 20260727_0008
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision = "20260727_0009"
down_revision = "20260727_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("node_type IN ('folder', 'file')", name="ck_knowledge_nodes_type"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_knowledge_nodes_name"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["knowledge_nodes.id"]),
    )
    op.create_index("ix_knowledge_nodes_owner_parent_name", "knowledge_nodes", ["owner_user_id", "parent_id", "name"])
    op.execute("""CREATE UNIQUE INDEX uq_knowledge_root_node_name
        ON knowledge_nodes (owner_user_id, lower(name)) WHERE parent_id IS NULL""")
    op.execute("""CREATE UNIQUE INDEX uq_knowledge_child_node_name
        ON knowledge_nodes (owner_user_id, parent_id, lower(name)) WHERE parent_id IS NOT NULL""")

    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("knowledge_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("processing_status", sa.Text(), nullable=False, server_default="uploaded"),
        sa.Column("failure_code", sa.Text(), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("version_number > 0", name="ck_document_versions_number"),
        sa.CheckConstraint("byte_size >= 0", name="ck_document_versions_byte_size"),
        sa.CheckConstraint("processing_status IN ('uploaded', 'processing', 'ready', 'failed')", name="ck_document_versions_status"),
        sa.ForeignKeyConstraint(["knowledge_node_id"], ["knowledge_nodes.id"]),
        sa.UniqueConstraint("knowledge_node_id", "version_number", name="uq_document_versions_node_number"),
    )
    op.create_index("ix_document_versions_node_status", "document_versions", ["knowledge_node_id", "processing_status"])
    op.execute("""CREATE UNIQUE INDEX uq_document_versions_current
        ON document_versions (knowledge_node_id) WHERE is_current""")

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('queued', 'processing', 'succeeded', 'failed')", name="ck_ingestion_jobs_status"),
        sa.CheckConstraint("attempt_number > 0", name="ck_ingestion_jobs_attempt"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.UniqueConstraint("document_version_id", "attempt_number", name="uq_ingestion_jobs_version_attempt"),
    )
    op.create_index("ix_ingestion_jobs_version_status", "ingestion_jobs", ["document_version_id", "status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_document_chunks_ordinal"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.UniqueConstraint("document_version_id", "ordinal", name="uq_document_chunks_version_ordinal"),
    )
    op.create_index("ix_document_chunks_owner_version_ordinal", "document_chunks", ["owner_user_id", "document_version_id", "ordinal"])

    op.create_table(
        "agent_knowledge_scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["knowledge_node_id"], ["knowledge_nodes.id"]),
        sa.UniqueConstraint("owner_user_id", "agent_id", "knowledge_node_id", name="uq_agent_knowledge_scope"),
    )
    op.create_index("ix_agent_knowledge_scopes_owner_agent", "agent_knowledge_scopes", ["owner_user_id", "agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_knowledge_scopes_owner_agent", table_name="agent_knowledge_scopes")
    op.drop_table("agent_knowledge_scopes")
    op.drop_index("ix_document_chunks_owner_version_ordinal", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_ingestion_jobs_version_status", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.execute("DROP INDEX uq_document_versions_current")
    op.drop_index("ix_document_versions_node_status", table_name="document_versions")
    op.drop_table("document_versions")
    op.execute("DROP INDEX uq_knowledge_child_node_name")
    op.execute("DROP INDEX uq_knowledge_root_node_name")
    op.drop_index("ix_knowledge_nodes_owner_parent_name", table_name="knowledge_nodes")
    op.drop_table("knowledge_nodes")
