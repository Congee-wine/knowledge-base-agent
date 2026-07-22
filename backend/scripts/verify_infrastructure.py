from __future__ import annotations

import time
from io import BytesIO
from uuid import uuid4

from integrations.object_storage import create_object_storage_client, get_object_storage_settings
from workers.queue import get_document_processing_queue


JOB_TIMEOUT_SECONDS = 15


def ensure_private_bucket() -> str:
    client = create_object_storage_client()
    settings = get_object_storage_settings()
    if not client.bucket_exists(settings.bucket):
        client.make_bucket(settings.bucket)
    return settings.bucket


def verify_object_storage(bucket_name: str) -> None:
    client = create_object_storage_client()
    object_name = f"infrastructure-check/{uuid4()}.txt"
    payload = b"knowledge-base-agent infrastructure check"
    try:
        client.put_object(
            bucket_name,
            object_name,
            BytesIO(payload),
            len(payload),
            content_type="text/plain",
        )
        response = client.get_object(bucket_name, object_name)
        try:
            if response.read() != payload:
                raise RuntimeError("Object storage returned unexpected verification content.")
        finally:
            response.close()
            response.release_conn()
    finally:
        client.remove_object(bucket_name, object_name)


def verify_worker_job() -> None:
    queue = get_document_processing_queue()
    job = queue.enqueue("workers.tasks.run_infrastructure_probe")
    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        job.refresh()
        if job.is_finished:
            result = job.return_value()
            if result and result.get("message") == "Worker 已运行" and result.get("execution_platform") == "Linux":
                return
            raise RuntimeError("Worker did not execute the verification job in the expected Linux container.")
        if job.is_failed:
            raise RuntimeError(f"Worker verification job failed: {job.exc_info}")
        time.sleep(0.5)
    raise TimeoutError("Worker did not finish the verification job within 15 seconds.")


def main() -> None:
    queue = get_document_processing_queue()
    if not queue.connection.ping():
        raise RuntimeError("Redis ping failed.")
    bucket_name = ensure_private_bucket()
    verify_object_storage(bucket_name)
    verify_worker_job()
    print("Infrastructure verification passed: Redis, MinIO, and RQ Worker are available.")


if __name__ == "__main__":
    main()
