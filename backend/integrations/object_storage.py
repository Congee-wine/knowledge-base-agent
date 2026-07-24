from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from minio import Minio

from config import (
    OBJECT_STORAGE_ACCESS_KEY,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_ENDPOINT,
    OBJECT_STORAGE_SECRET_KEY,
    OBJECT_STORAGE_SECURE,
)


@dataclass(frozen=True)
class ObjectStorageSettings:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    secure: bool


def get_object_storage_settings() -> ObjectStorageSettings:
    missing = [
        name
        for name, value in {
            "OBJECT_STORAGE_ENDPOINT": OBJECT_STORAGE_ENDPOINT,
            "OBJECT_STORAGE_ACCESS_KEY": OBJECT_STORAGE_ACCESS_KEY,
            "OBJECT_STORAGE_SECRET_KEY": OBJECT_STORAGE_SECRET_KEY,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Object storage is not configured: {', '.join(missing)}")
    return ObjectStorageSettings(
        endpoint=OBJECT_STORAGE_ENDPOINT,
        access_key=OBJECT_STORAGE_ACCESS_KEY,
        secret_key=OBJECT_STORAGE_SECRET_KEY,
        bucket=OBJECT_STORAGE_BUCKET,
        secure=OBJECT_STORAGE_SECURE,
    )


def create_object_storage_client() -> Minio:
    settings = get_object_storage_settings()
    return Minio(
        settings.endpoint,
        access_key=settings.access_key,
        secret_key=settings.secret_key,
        secure=settings.secure,
    )


def put_private_object(object_key: str, content: bytes, content_type: str) -> None:
    client = create_object_storage_client()
    settings = get_object_storage_settings()
    client.put_object(settings.bucket, object_key, BytesIO(content), len(content), content_type=content_type)


def read_private_object(object_key: str):
    client = create_object_storage_client()
    settings = get_object_storage_settings()
    return client.get_object(settings.bucket, object_key)


def remove_private_object(object_key: str) -> None:
    client = create_object_storage_client()
    settings = get_object_storage_settings()
    client.remove_object(settings.bucket, object_key)
