from __future__ import annotations

from redis import Redis
from rq import Queue

from config import REDIS_URL


DOCUMENT_PROCESSING_QUEUE = "document-processing"
EMBEDDING_QUEUE = "embedding"
RETRIEVAL_QUEUE = "retrieval"
CHAT_GENERATION_QUEUE = "chat-generation"


def create_redis_connection() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=False)


def get_document_processing_queue() -> Queue:
    return Queue(DOCUMENT_PROCESSING_QUEUE, connection=create_redis_connection())


def get_embedding_queue() -> Queue:
    return Queue(EMBEDDING_QUEUE, connection=create_redis_connection())


def get_retrieval_queue() -> Queue:
    return Queue(RETRIEVAL_QUEUE, connection=create_redis_connection())


def get_chat_generation_queue() -> Queue:
    return Queue(CHAT_GENERATION_QUEUE, connection=create_redis_connection())
