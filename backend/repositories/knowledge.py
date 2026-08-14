from __future__ import annotations

import uuid
import json
from hashlib import sha256
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from database import get_connection
from config import BGE_MODEL_NAME
from retrieval.chunking import TextChunk


def list_nodes(user_id: str) -> Sequence[Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT node.*, version.processing_status, version.index_status, version.mime_type, version.byte_size
                FROM knowledge_nodes node
                LEFT JOIN document_versions version
                  ON version.knowledge_node_id = node.id AND version.is_current
                WHERE node.owner_user_id = %s
                ORDER BY node.parent_id NULLS FIRST, node.node_type DESC, lower(node.name), node.id""",
                (user_id,),
            )
            return cursor.fetchall()


def find_owned_node(node_id: str, user_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s", (node_id, user_id))
            return cursor.fetchone()


def find_owned_current_file_version(node_id: str, user_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT node.id AS node_id, node.name, version.storage_key, version.mime_type, version.processing_status
                FROM knowledge_nodes node
                JOIN document_versions version ON version.knowledge_node_id = node.id AND version.is_current
                WHERE node.id = %s AND node.owner_user_id = %s AND node.node_type = 'file'""",
                (node_id, user_id),
            )
            return cursor.fetchone()


def find_owned_current_version_for_retry(node_id: str, user_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT version.id AS version_id, version.processing_status, version.index_status
                FROM document_versions version
                JOIN knowledge_nodes node ON node.id = version.knowledge_node_id AND version.is_current
                WHERE node.id = %s AND node.owner_user_id = %s AND node.node_type = 'file'""",
                (node_id, user_id),
            )
            return cursor.fetchone()


def sibling_name_exists(user_id: str, parent_id: str | None, name: str, exclude_node_id: str | None = None) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT 1 FROM knowledge_nodes WHERE owner_user_id = %s AND parent_id IS NOT DISTINCT FROM %s
                AND lower(name) = lower(%s) AND (%s::uuid IS NULL OR id <> %s::uuid)""",
                (user_id, parent_id, name, exclude_node_id, exclude_node_id),
            )
            return cursor.fetchone() is not None


def create_folder(user_id: str, parent_id: str | None, name: str) -> Mapping[str, Any]:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO knowledge_nodes (id, owner_user_id, parent_id, node_type, name, created_at, updated_at)
                VALUES (%s, %s, %s, 'folder', %s, %s, %s) RETURNING *""",
                (uuid.uuid4(), user_id, parent_id, name, now, now),
            )
            return cursor.fetchone()


def create_uploaded_file(user_id: str, parent_id: str | None, name: str, storage_key: str, mime_type: str, content: bytes) -> Mapping[str, Any]:
    now, node_id = datetime.now(timezone.utc), uuid.uuid4()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO knowledge_nodes (id, owner_user_id, parent_id, node_type, name, created_at, updated_at)
                VALUES (%s, %s, %s, 'file', %s, %s, %s) RETURNING *""",
                (node_id, user_id, parent_id, name, now, now),
            )
            node = cursor.fetchone()
            cursor.execute(
                """INSERT INTO document_versions (id, knowledge_node_id, version_number, storage_key, mime_type, byte_size,
                content_hash, processing_status, is_current, created_at) VALUES (%s, %s, 1, %s, %s, %s, %s, 'uploaded', true, %s)""",
                (uuid.uuid4(), node_id, storage_key, mime_type, len(content), sha256(content).hexdigest(), now),
            )
            return node


def create_ingestion_job(node_id: str, user_id: str) -> str:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT version.id FROM document_versions version JOIN knowledge_nodes node ON node.id = version.knowledge_node_id
                WHERE node.id = %s AND node.owner_user_id = %s AND version.is_current""", (node_id, user_id))
            version = cursor.fetchone()
            if version is None:
                raise ValueError("Current document version not found")
            job_id = uuid.uuid4()
            cursor.execute(
                "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS attempt_number FROM ingestion_jobs WHERE document_version_id = %s",
                (version["id"],),
            )
            attempt_number = cursor.fetchone()["attempt_number"]
            cursor.execute("""INSERT INTO ingestion_jobs (id, document_version_id, status, attempt_number, created_at)
                VALUES (%s, %s, 'queued', %s, %s)""", (job_id, version["id"], attempt_number, now))
            return str(job_id)


def create_embedding_job(document_version_id: str) -> str:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(attempt_number), 0) + 1 AS attempt_number FROM embedding_jobs WHERE document_version_id = %s", (document_version_id,))
            attempt_number = cursor.fetchone()["attempt_number"]
            job_id = uuid.uuid4()
            cursor.execute("INSERT INTO embedding_jobs (id, document_version_id, status, attempt_number, created_at) VALUES (%s, %s, 'queued', %s, %s)", (job_id, document_version_id, attempt_number, now))
            cursor.execute("UPDATE document_versions SET index_status = 'pending' WHERE id = %s", (document_version_id,))
            return str(job_id)


def get_ingestion_job(job_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT job.id AS job_id, version.id AS version_id, version.storage_key, version.mime_type,
                node.id AS node_id, node.owner_user_id FROM ingestion_jobs job JOIN document_versions version ON version.id = job.document_version_id
                JOIN knowledge_nodes node ON node.id = version.knowledge_node_id WHERE job.id = %s""", (job_id,))
            return cursor.fetchone()


def get_embedding_job(job_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT job.id AS job_id, version.id AS version_id, node.owner_user_id
                FROM embedding_jobs job JOIN document_versions version ON version.id = job.document_version_id
                JOIN knowledge_nodes node ON node.id = version.knowledge_node_id WHERE job.id = %s""", (job_id,))
            return cursor.fetchone()


def mark_embedding_processing(job_id: str) -> None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE embedding_jobs SET status = 'processing', started_at = %s WHERE id = %s", (now, job_id))
            cursor.execute("UPDATE document_versions SET index_status = 'processing' WHERE id = (SELECT document_version_id FROM embedding_jobs WHERE id = %s)", (job_id,))


def list_version_chunks(version_id: str) -> Sequence[Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT content, page_number FROM document_chunks WHERE document_version_id = %s ORDER BY ordinal", (version_id,))
            return cursor.fetchall()


def replace_version_chunks_with_embeddings(version_id: str, owner_user_id: str, chunks: list[TextChunk], vectors: list[list[float]]) -> None:
    if len(chunks) != len(vectors):
        raise ValueError("Chunk and vector counts differ")
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM document_chunks WHERE document_version_id = %s", (version_id,))
            rows = []
            for ordinal, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                metadata = json.dumps({"sectionTitle": chunk.section_title, "paragraphOrdinal": chunk.paragraph_ordinal})
                vector_text = "[" + ",".join(str(value) for value in vector) + "]"
                rows.append((uuid.uuid4(), owner_user_id, version_id, ordinal, chunk.content, chunk.page_number, metadata, vector_text, BGE_MODEL_NAME, now))
            cursor.executemany("""INSERT INTO document_chunks (id, owner_user_id, document_version_id, ordinal, content, page_number, metadata_json, embedding, embedding_model, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector, %s, %s)""", rows)


def complete_embedding(job_id: str) -> None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE embedding_jobs SET status = 'succeeded', finished_at = %s WHERE id = %s", (now, job_id))
            cursor.execute("UPDATE document_versions SET index_status = 'ready' WHERE id = (SELECT document_version_id FROM embedding_jobs WHERE id = %s)", (job_id,))


def fail_embedding(job_id: str, error_code: str) -> None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE embedding_jobs SET status = 'failed', last_error_code = %s, finished_at = %s WHERE id = %s", (error_code, now, job_id))
            cursor.execute("UPDATE document_versions SET index_status = 'failed' WHERE id = (SELECT document_version_id FROM embedding_jobs WHERE id = %s)", (job_id,))


def mark_ingestion_processing(job_id: str) -> None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE ingestion_jobs SET status = 'processing', started_at = %s WHERE id = %s", (now, job_id))
            cursor.execute("""UPDATE document_versions SET processing_status = 'processing'
                WHERE id = (SELECT document_version_id FROM ingestion_jobs WHERE id = %s)""", (job_id,))


def complete_ingestion(job_id: str, chunks: list[tuple[str, int | None]]) -> str | None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT document_version_id FROM ingestion_jobs WHERE id = %s", (job_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            version_id = row["document_version_id"]
            cursor.execute("SELECT owner_user_id FROM knowledge_nodes node JOIN document_versions version ON version.knowledge_node_id = node.id WHERE version.id = %s", (version_id,))
            owner_id = cursor.fetchone()["owner_user_id"]
            cursor.execute("DELETE FROM document_chunks WHERE document_version_id = %s", (version_id,))
            cursor.executemany("""INSERT INTO document_chunks (id, owner_user_id, document_version_id, ordinal, content, page_number, metadata_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, '{}'::jsonb, %s)""", [(uuid.uuid4(), owner_id, version_id, index, content, page, now) for index, (content, page) in enumerate(chunks)])
            cursor.execute("UPDATE document_versions SET processing_status = 'ready', processed_at = %s, failure_code = NULL, failure_message = NULL WHERE id = %s", (now, version_id))
            cursor.execute("UPDATE ingestion_jobs SET status = 'succeeded', finished_at = %s WHERE id = %s", (now, job_id))
            return str(version_id)


def fail_ingestion(job_id: str, error_code: str, error_message: str) -> None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT document_version_id FROM ingestion_jobs WHERE id = %s", (job_id,))
            row = cursor.fetchone()
            if row is None:
                return
            cursor.execute("UPDATE document_versions SET processing_status = 'failed', failure_code = %s, failure_message = %s WHERE id = %s", (error_code, error_message[:500], row["document_version_id"]))
            cursor.execute("UPDATE ingestion_jobs SET status = 'failed', last_error_code = %s, finished_at = %s WHERE id = %s", (error_code, now, job_id))


def update_node(node_id: str, user_id: str, *, name: str | None = None, parent_id: str | None = None) -> Mapping[str, Any] | None:
    field, value = ("name", name) if name is not None else ("parent_id", parent_id)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE knowledge_nodes SET {field} = %s, updated_at = %s WHERE id = %s AND owner_user_id = %s RETURNING *",
                (value, datetime.now(timezone.utc), node_id, user_id),
            )
            return cursor.fetchone()


def is_descendant(node_id: str, candidate_parent_id: str, user_id: str) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE descendants AS (
                    SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL
                    SELECT child.id FROM knowledge_nodes child JOIN descendants parent ON child.parent_id = parent.id
                    WHERE child.owner_user_id = %s
                ) SELECT 1 FROM descendants WHERE id = %s""",
                (node_id, user_id, user_id, candidate_parent_id),
            )
            return cursor.fetchone() is not None


def get_node_depth(node_id: str, user_id: str) -> int:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL SELECT parent.id, parent.parent_id FROM knowledge_nodes parent
                    JOIN ancestors child ON child.parent_id = parent.id WHERE parent.owner_user_id = %s
                ) SELECT count(*) - 1 AS depth FROM ancestors""",
                (node_id, user_id, user_id),
            )
            return int(cursor.fetchone()["depth"])


def get_tree_height(node_id: str, user_id: str) -> int:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE descendants AS (
                    SELECT id, 0 AS depth FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL SELECT child.id, parent.depth + 1 FROM knowledge_nodes child
                    JOIN descendants parent ON child.parent_id = parent.id WHERE child.owner_user_id = %s
                ) SELECT max(depth) AS height FROM descendants""",
                (node_id, user_id, user_id),
            )
            return int(cursor.fetchone()["height"])


def delete_node_tree(node_id: str, user_id: str) -> list[str] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s", (node_id, user_id))
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                """WITH RECURSIVE tree AS (
                    SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id
                    WHERE child.owner_user_id = %s
                ) SELECT storage_key FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree)""",
                (node_id, user_id, user_id),
            )
            storage_keys = [str(row["storage_key"]) for row in cursor.fetchall()]
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM retrieval_candidates WHERE chunk_id IN (SELECT id FROM document_chunks WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree)))""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM agent_knowledge_scopes WHERE knowledge_node_id IN (SELECT id FROM tree)""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM document_chunks WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree))""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM ingestion_jobs WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree))""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM embedding_jobs WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree))""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree)""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM knowledge_nodes WHERE id IN (SELECT id FROM tree)""", (node_id, user_id, user_id))
            return storage_keys


def list_agent_scope_node_ids(user_id: str, agent_id: str) -> list[str]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT knowledge_node_id FROM agent_knowledge_scopes
                WHERE owner_user_id = %s AND agent_id = %s ORDER BY created_at, id""",
                (user_id, agent_id),
            )
            return [str(row["knowledge_node_id"]) for row in cursor.fetchall()]


def has_agent_scope(user_id: str, agent_id: str) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT EXISTS (
                    SELECT 1 FROM agent_knowledge_scopes
                    WHERE owner_user_id = %s AND agent_id = %s
                ) AS has_scope""",
                (user_id, agent_id),
            )
            row = cursor.fetchone()
            return bool(row["has_scope"])


def replace_agent_scope_node_ids(user_id: str, agent_id: str, node_ids: list[str]) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if node_ids:
                cursor.execute("SELECT id FROM knowledge_nodes WHERE owner_user_id = %s AND id = ANY(%s::uuid[])", (user_id, node_ids))
                if len(cursor.fetchall()) != len(set(node_ids)):
                    raise ValueError("Knowledge scope contains an inaccessible node")
            cursor.execute("DELETE FROM agent_knowledge_scopes WHERE owner_user_id = %s AND agent_id = %s", (user_id, agent_id))
            cursor.executemany("INSERT INTO agent_knowledge_scopes (id, owner_user_id, agent_id, knowledge_node_id, created_at) VALUES (%s, %s, %s, %s, %s)", [(uuid.uuid4(), user_id, agent_id, node_id, datetime.now(timezone.utc)) for node_id in dict.fromkeys(node_ids)])
