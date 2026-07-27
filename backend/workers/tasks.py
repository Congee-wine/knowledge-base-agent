from __future__ import annotations

from datetime import datetime, timezone
from platform import system

from database import get_connection
from integrations.object_storage import create_object_storage_client, get_object_storage_settings


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
