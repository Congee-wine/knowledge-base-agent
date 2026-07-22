from __future__ import annotations

from redis import Redis
from rq import Queue

from config import REDIS_URL


DOCUMENT_PROCESSING_QUEUE = "document-processing"


def create_redis_connection() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=False)


def get_document_processing_queue() -> Queue:
    return Queue(DOCUMENT_PROCESSING_QUEUE, connection=create_redis_connection())
