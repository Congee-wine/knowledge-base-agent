from __future__ import annotations

from rq import Worker

from workers.queue import DOCUMENT_PROCESSING_QUEUE, EMBEDDING_QUEUE, create_redis_connection


def run_document_processing_worker() -> None:
    """Run the dedicated worker for document-processing jobs."""
    connection = create_redis_connection()
    worker = Worker([DOCUMENT_PROCESSING_QUEUE], connection=connection)
    worker.work()


def run_embedding_worker() -> None:
    """Run the isolated Worker that owns the local embedding model."""
    connection = create_redis_connection()
    worker = Worker([EMBEDDING_QUEUE], connection=connection)
    worker.work()


if __name__ == "__main__":
    run_document_processing_worker()
