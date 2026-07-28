from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from io import BytesIO
import logging
from platform import system

from database import get_connection
from integrations.object_storage import create_object_storage_client, get_object_storage_settings, read_private_object, remove_private_object
from repositories import knowledge as knowledge_repository
from retrieval.chunking import SourceText, split_mixed
from integrations.embeddings import embed_texts
from workers.queue import get_embedding_queue
from config import DOCUMENT_EMBEDDING_BATCH_SIZE


logger = logging.getLogger(__name__)


def run_infrastructure_probe() -> dict[str, str]:
    """Return a small result that proves an RQ worker executed this task."""
    return {
        "message": "Worker 已运行",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "execution_platform": system(),
    }


def _verify_database_connection() -> None:
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as error:
        raise RuntimeError("Document worker cannot connect to PostgreSQL.") from error


def _verify_private_bucket() -> str:
    settings = get_object_storage_settings()
    try:
        bucket_exists = create_object_storage_client().bucket_exists(settings.bucket)
    except Exception as error:
        raise RuntimeError("Document worker cannot access MinIO.") from error
    if not bucket_exists:
        raise RuntimeError(f"Document worker cannot find private bucket: {settings.bucket}.")
    return settings.bucket


def run_document_processing_probe() -> dict[str, str]:
    """Verify document-worker dependencies without creating domain data or loading models."""
    _verify_database_connection()
    bucket_name = _verify_private_bucket()
    return {
        "message": "Document worker dependencies are reachable",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "execution_platform": system(),
        "database": "ok",
        "object_storage_bucket": bucket_name,
    }


def process_document_ingestion(job_id: str) -> None:
    job = knowledge_repository.get_ingestion_job(job_id)
    if job is None:
        return
    try:
        knowledge_repository.mark_ingestion_processing(job_id)
        response = read_private_object(str(job["storage_key"]))
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()
        chunks = _extract_chunks(str(job["mime_type"]), content)
        if not chunks:
            raise ValueError("Document contains no extractable text")
        version_id = knowledge_repository.complete_ingestion(job_id, chunks)
        if isinstance(version_id, str):
            _enqueue_embedding(version_id)
    except Exception:
        knowledge_repository.fail_ingestion(job_id, "DOCUMENT_PROCESSING_FAILED", "文档解析失败，请确认文件内容后重试")
        _remove_failed_document(job)
        raise


def _remove_failed_document(job: Mapping[str, object]) -> None:
    try:
        storage_keys = knowledge_repository.delete_node_tree(str(job["node_id"]), str(job["owner_user_id"]))
        for storage_key in storage_keys or []:
            remove_private_object(storage_key)
    except Exception:
        logger.exception("failed document cleanup failed", extra={"job_id": str(job["job_id"])})


def _extract_chunks(mime_type: str, content: bytes) -> list[tuple[str, int | None]]:
    if mime_type == "application/pdf":
        import fitz

        document = fitz.open(stream=content, filetype="pdf")
        return [(page.get_text().strip(), index + 1) for index, page in enumerate(document) if page.get_text().strip()]
    if "wordprocessingml" in mime_type:
        from docx import Document

        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
        return [(text, None)] if text else []
    text = content.decode("utf-8").strip()
    return [(text, None)] if text else []


def _enqueue_embedding(document_version_id: str) -> None:
    try:
        embedding_job_id = knowledge_repository.create_embedding_job(document_version_id)
        get_embedding_queue().enqueue("workers.tasks.process_document_embedding", embedding_job_id, job_timeout=900)
    except Exception:
        logger.exception("embedding enqueue failed", extra={"document_version_id": document_version_id})


def process_document_embedding(job_id: str) -> None:
    """Convert extracted document text into source-aware chunks and BGE-M3 vectors."""
    job = knowledge_repository.get_embedding_job(job_id)
    if job is None:
        return
    try:
        knowledge_repository.mark_embedding_processing(job_id)
        source_texts = [SourceText(row["content"], row["page_number"]) for row in knowledge_repository.list_version_chunks(str(job["version_id"]))]
        chunks = split_mixed(source_texts)
        if not chunks:
            raise ValueError("Document contains no indexable chunks")
        vectors = _embed_in_batches([chunk.content for chunk in chunks])
        knowledge_repository.replace_version_chunks_with_embeddings(str(job["version_id"]), str(job["owner_user_id"]), chunks, vectors)
        knowledge_repository.complete_embedding(job_id)
    except Exception:
        knowledge_repository.fail_embedding(job_id, "DOCUMENT_EMBEDDING_FAILED")
        logger.exception("document embedding failed", extra={"job_id": job_id})
        raise


def _embed_in_batches(contents: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(contents), DOCUMENT_EMBEDDING_BATCH_SIZE):
        vectors.extend(embed_texts(contents[start:start + DOCUMENT_EMBEDDING_BATCH_SIZE]))
    return vectors


def embed_query_text(content: str) -> list[float]:
    """Short synchronous-request task; model ownership remains in embedding Worker."""
    return embed_texts([content])[0]
