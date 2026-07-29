from __future__ import annotations

import time

from rq.job import Job

from config import RETRIEVAL_QUERY_TIMEOUT_SECONDS
from workers.queue import create_redis_connection, get_retrieval_queue


QUERY_TIMEOUT_SECONDS = RETRIEVAL_QUERY_TIMEOUT_SECONDS


def embed_query(text: str) -> list[float]:
    connection = create_redis_connection()
    job = get_retrieval_queue().enqueue("workers.tasks.embed_query_text", text, job_timeout=QUERY_TIMEOUT_SECONDS, result_ttl=60)
    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        job = Job.fetch(job.id, connection=connection)
        if job.is_finished:
            result = job.return_value()
            if isinstance(result, list): return [float(value) for value in result]
            raise RuntimeError("Embedding worker returned an invalid query vector")
        if job.is_failed: raise RuntimeError("Embedding worker failed to create query vector")
        time.sleep(0.1)
    raise TimeoutError("Embedding worker did not return a query vector in time")


def rerank_query_candidates(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    connection = create_redis_connection()
    job = get_retrieval_queue().enqueue(
        "workers.tasks.rerank_query_candidates", query, passages, job_timeout=QUERY_TIMEOUT_SECONDS, result_ttl=60,
    )
    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        job = Job.fetch(job.id, connection=connection)
        if job.is_finished:
            result = job.return_value()
            if isinstance(result, list):
                return [float(value) for value in result]
            raise RuntimeError("Embedding worker returned invalid reranker scores")
        if job.is_failed:
            raise RuntimeError("Embedding worker failed to rerank candidates")
        time.sleep(0.1)
    raise TimeoutError("Embedding worker did not return reranker scores in time")
