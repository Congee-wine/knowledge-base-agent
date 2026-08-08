from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from repositories import knowledge as knowledge_repository
from schemas.knowledge import KnowledgeNodeResponse
from integrations.object_storage import put_private_object, remove_private_object
from config import DOCUMENT_MAX_FILE_SIZE_BYTES, DOCUMENT_PROCESSING_TIMEOUT_SECONDS
from services.document_validation import validate_document_upload
from services.errors import document_not_failed, document_queue_unavailable, file_too_large, invalid_knowledge_move, invalid_parent_node, knowledge_depth_limit_exceeded, knowledge_name_conflict, not_found
from workers.queue import get_document_processing_queue, get_embedding_queue


logger = logging.getLogger(__name__)


def list_knowledge_tree(user_id: str) -> list[KnowledgeNodeResponse]:
    return _build_tree(knowledge_repository.list_nodes(user_id))


def create_folder(user_id: str, parent_id: str | None, name: str) -> KnowledgeNodeResponse:
    normalized_name = name.strip()
    if not normalized_name:
        raise knowledge_name_conflict("文件夹名称不能为空")
    if parent_id is not None:
        parent = knowledge_repository.find_owned_node(parent_id, user_id)
        if parent is None:
            raise not_found()
        if parent["node_type"] != "folder":
            raise invalid_parent_node()
        if knowledge_repository.get_node_depth(parent_id, user_id) + 1 > 5:
            raise knowledge_depth_limit_exceeded()
    if knowledge_repository.sibling_name_exists(user_id, parent_id, normalized_name):
        raise knowledge_name_conflict("同一文件夹中已存在同名资料")
    return _to_node(knowledge_repository.create_folder(user_id, parent_id, normalized_name))


def upload_file(user_id: str, parent_id: str | None, filename: str, content_type: str | None, content: bytes) -> KnowledgeNodeResponse:
    filename = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    if len(content) > DOCUMENT_MAX_FILE_SIZE_BYTES:
        raise file_too_large()
    validate_document_upload(filename, content_type, content)
    if parent_id is not None:
        parent = knowledge_repository.find_owned_node(parent_id, user_id)
        if parent is None:
            raise not_found()
        if parent["node_type"] != "folder":
            raise invalid_parent_node()
    if knowledge_repository.sibling_name_exists(user_id, parent_id, filename):
        raise knowledge_name_conflict("同一文件夹中已存在同名资料")
    storage_key = f"knowledge-files/{user_id}/{uuid.uuid4()}/{filename}"
    put_private_object(storage_key, content, content_type or "application/octet-stream")
    try:
        node = knowledge_repository.create_uploaded_file(
            user_id, parent_id, filename, storage_key, content_type or "application/octet-stream", content,
        )
    except Exception:
        try:
            remove_private_object(storage_key)
        except Exception:
            logger.exception("upload rollback cleanup failed", extra={"storage_key": storage_key})
        raise
    _enqueue_document_processing(str(node["id"]), user_id)
    return _to_node(node)


def rename_node(user_id: str, node_id: str, name: str) -> KnowledgeNodeResponse:
    node = knowledge_repository.find_owned_node(node_id, user_id)
    if node is None:
        raise not_found()
    normalized_name = name.strip()
    if not normalized_name or knowledge_repository.sibling_name_exists(user_id, str(node["parent_id"]) if node["parent_id"] else None, normalized_name, node_id):
        raise knowledge_name_conflict("同一文件夹中已存在同名资料")
    return _to_node(knowledge_repository.update_node(node_id, user_id, name=normalized_name))


def move_node(user_id: str, node_id: str, parent_id: str | None) -> KnowledgeNodeResponse:
    node = knowledge_repository.find_owned_node(node_id, user_id)
    if node is None:
        raise not_found()
    if parent_id is not None:
        parent = knowledge_repository.find_owned_node(parent_id, user_id)
        if parent is None or parent["node_type"] != "folder":
            raise invalid_parent_node()
        if knowledge_repository.is_descendant(node_id, parent_id, user_id):
            raise invalid_knowledge_move()
        if knowledge_repository.get_node_depth(parent_id, user_id) + 1 + knowledge_repository.get_tree_height(node_id, user_id) > 5:
            raise knowledge_depth_limit_exceeded()
    elif knowledge_repository.get_tree_height(node_id, user_id) > 5:
        raise knowledge_depth_limit_exceeded()
    if knowledge_repository.sibling_name_exists(user_id, parent_id, str(node["name"]), node_id):
        raise knowledge_name_conflict("目标文件夹中已存在同名资料")
    return _to_node(knowledge_repository.update_node(node_id, user_id, parent_id=parent_id))


def delete_node(user_id: str, node_id: str) -> None:
    storage_keys = knowledge_repository.delete_node_tree(node_id, user_id)
    if storage_keys is None:
        raise not_found()
    for storage_key in storage_keys:
        try:
            remove_private_object(storage_key)
        except Exception:
            # Database deletion is authoritative; object cleanup can be retried once uploads exist.
            logger.exception("knowledge object cleanup failed", extra={"storage_key": storage_key})


def retry_embedding(user_id: str, node_id: str) -> None:
    version = knowledge_repository.find_owned_current_version_for_retry(node_id, user_id)
    if version is None:
        raise not_found()
    if version["processing_status"] != "ready" or version["index_status"] != "failed":
        raise document_not_failed()
    job_id = knowledge_repository.create_embedding_job(str(version["version_id"]))
    try:
        get_embedding_queue().enqueue("workers.tasks.process_document_embedding", job_id, job_timeout=900)
    except Exception:
        logger.exception("embedding retry enqueue failed", extra={"node_id": node_id, "job_id": job_id})
        raise document_queue_unavailable()


def _enqueue_document_processing(node_id: str, user_id: str) -> None:
    job_id = knowledge_repository.create_ingestion_job(node_id, user_id)
    try:
        get_document_processing_queue().enqueue(
            "workers.tasks.process_document_ingestion",
            job_id,
            job_timeout=DOCUMENT_PROCESSING_TIMEOUT_SECONDS,
        )
    except Exception as error:
        logger.exception("document processing enqueue failed", extra={"node_id": node_id, "job_id": job_id})
        knowledge_repository.fail_ingestion(job_id, "DOCUMENT_QUEUE_UNAVAILABLE", "文档处理队列暂不可用，请稍后重试")
        _remove_failed_upload(node_id, user_id)
        raise document_queue_unavailable() from error


def _remove_failed_upload(node_id: str, user_id: str) -> None:
    storage_keys = knowledge_repository.delete_node_tree(node_id, user_id)
    for storage_key in storage_keys or []:
        try:
            remove_private_object(storage_key)
        except Exception:
            logger.exception("failed upload cleanup failed", extra={"storage_key": storage_key})


def _build_tree(rows: Sequence[Mapping[str, Any]]) -> list[KnowledgeNodeResponse]:
    nodes = {str(row["id"]): _to_node(row) for row in rows}
    roots: list[KnowledgeNodeResponse] = []
    for row in rows:
        node = nodes[str(row["id"])]
        parent_id = row["parent_id"]
        if parent_id is None:
            roots.append(node)
        elif parent := nodes.get(str(parent_id)):
            parent.children.append(node)
    return roots


def _to_node(row: Mapping[str, Any]) -> KnowledgeNodeResponse:
    return KnowledgeNodeResponse(
        id=str(row["id"]), parent_id=str(row["parent_id"]) if row["parent_id"] else None,
        node_type=row["node_type"], name=row["name"], status=row.get("processing_status"),
        index_status=row.get("index_status"),
        mime_type=row.get("mime_type"), byte_size=row.get("byte_size"),
        created_at=row["created_at"], updated_at=row["updated_at"],
    )
