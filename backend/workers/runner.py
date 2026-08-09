from __future__ import annotations

import logging

from rq import Worker

from workers.queue import CHAT_GENERATION_QUEUE, DOCUMENT_PROCESSING_QUEUE, EMBEDDING_QUEUE, RETRIEVAL_QUEUE, create_redis_connection
from workers.recovery import recover_stuck_jobs

logger = logging.getLogger(__name__)


def _run_worker_with_recovery(queues: list[str], worker_name: str) -> None:
    """Start a Worker after recovering any stuck jobs from previous runs."""
    try:
        recover_stuck_jobs()
    except Exception:
        logger.exception("Job recovery failed for %s, starting worker anyway", worker_name)
    connection = create_redis_connection()
    worker = Worker(queues, connection=connection)
    worker.work()


def run_document_processing_worker() -> None:
    """Run the dedicated worker for document-processing jobs."""
    _run_worker_with_recovery([DOCUMENT_PROCESSING_QUEUE], "document-processing")


def run_embedding_worker() -> None:
    """Run the isolated Worker that owns the local embedding model."""
    _run_worker_with_recovery([EMBEDDING_QUEUE], "embedding")


def run_retrieval_worker() -> None:
    """Run the dedicated query embedding and reranking Worker."""
    connection = create_redis_connection()
    worker = Worker([RETRIEVAL_QUEUE], connection=connection)
    worker.work()


def run_chat_generation_worker() -> None:
    """Run the worker that owns model generation after SSE clients disconnect."""
    connection = create_redis_connection()
    worker = Worker([CHAT_GENERATION_QUEUE], connection=connection)
    worker.work()


if __name__ == "__main__":
    run_document_processing_worker()
