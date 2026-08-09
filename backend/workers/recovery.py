from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from database import get_connection
from workers.queue import EMBEDDING_QUEUE, create_redis_connection

logger = logging.getLogger(__name__)

STUCK_THRESHOLD_MINUTES = 15


def recover_stuck_jobs() -> None:
    """Recover jobs stuck in 'processing' status after Worker crash or RQ timeout."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=STUCK_THRESHOLD_MINUTES)
    _recover_stuck_ingestion_jobs(threshold)
    _recover_stuck_embedding_jobs(threshold)


def _recover_stuck_ingestion_jobs(threshold: datetime) -> None:
    """Handle stuck ingestion jobs by deleting failed document nodes."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT job.id, job.document_version_id, node.id AS node_id, node.owner_user_id
                FROM ingestion_jobs job
                JOIN document_versions version ON version.id = job.document_version_id
                JOIN knowledge_nodes node ON node.id = version.knowledge_node_id
                WHERE job.status = 'processing' AND job.started_at < %s""",
                (threshold,),
            )
            stuck_jobs = cursor.fetchall()

    if not stuck_jobs:
        return

    logger.warning("Found %d stuck ingestion jobs", len(stuck_jobs))
    for job in stuck_jobs:
        try:
            _remove_failed_document(str(job["node_id"]), str(job["owner_user_id"]))
            _mark_ingestion_failed(str(job["id"]), "PROCESSING_TIMEOUT", "文档处理超时，请重新上传")
            logger.info("Recovered stuck ingestion job %s", job["id"])
        except Exception:
            logger.exception("Failed to recover ingestion job %s", job["id"])


def _recover_stuck_embedding_jobs(threshold: datetime) -> None:
    """Re-enqueue stuck embedding jobs for retry."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, document_version_id
                FROM embedding_jobs
                WHERE status = 'processing' AND started_at < %s""",
                (threshold,),
            )
            stuck_jobs = cursor.fetchall()

    if not stuck_jobs:
        return

    logger.warning("Found %d stuck embedding jobs", len(stuck_jobs))
    queue = EMBEDDING_QUEUE
    redis_conn = create_redis_connection()

    for job in stuck_jobs:
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE embedding_jobs SET status = 'queued', started_at = NULL WHERE id = %s",
                        (str(job["id"]),),
                    )
                    cursor.execute(
                        "UPDATE document_versions SET index_status = 'pending' WHERE id = %s",
                        (str(job["document_version_id"]),),
                    )
            redis_conn.rpush(queue, str(job["id"]))
            logger.info("Re-enqueued stuck embedding job %s", job["id"])
        except Exception:
            logger.exception("Failed to recover embedding job %s", job["id"])


def _remove_failed_document(node_id: str, owner_user_id: str) -> None:
    """Delete document node and associated storage, matching existing failure cleanup."""
    from integrations.object_storage import remove_private_object

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s",
                (node_id, owner_user_id),
            )
            if cursor.fetchone() is None:
                return

            cursor.execute(
                """SELECT storage_key FROM document_versions
                WHERE knowledge_node_id = %s""",
                (node_id,),
            )
            storage_keys = [str(row["storage_key"]) for row in cursor.fetchall()]

            cursor.execute("DELETE FROM retrieval_candidates WHERE chunk_id IN (SELECT id FROM document_chunks WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id = %s))", (node_id,))
            cursor.execute("DELETE FROM agent_knowledge_scopes WHERE knowledge_node_id = %s", (node_id,))
            cursor.execute("DELETE FROM document_chunks WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id = %s)", (node_id,))
            cursor.execute("DELETE FROM ingestion_jobs WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id = %s)", (node_id,))
            cursor.execute("DELETE FROM embedding_jobs WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id = %s)", (node_id,))
            cursor.execute("DELETE FROM document_versions WHERE knowledge_node_id = %s", (node_id,))
            cursor.execute("DELETE FROM knowledge_nodes WHERE id = %s", (node_id,))

    for storage_key in storage_keys:
        try:
            remove_private_object(storage_key)
        except Exception:
            logger.exception("Failed to remove storage object during recovery", extra={"storage_key": storage_key})


def _mark_ingestion_failed(job_id: str, error_code: str, error_message: str) -> None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE ingestion_jobs SET status = 'failed', last_error_code = %s, finished_at = %s WHERE id = %s",
                (error_code, now, job_id),
            )
