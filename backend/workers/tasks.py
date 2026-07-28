from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from io import BytesIO
import logging
from platform import system

from database import get_connection
from integrations.object_storage import create_object_storage_client, get_object_storage_settings, read_private_object, remove_private_object
from repositories import knowledge as knowledge_repository


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
        knowledge_repository.complete_ingestion(job_id, chunks)
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
