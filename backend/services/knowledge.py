from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from repositories import knowledge as knowledge_repository
from schemas.knowledge import KnowledgeNodeResponse
from integrations.object_storage import remove_private_object
from services.errors import invalid_knowledge_move, invalid_parent_node, knowledge_depth_limit_exceeded, knowledge_name_conflict, not_found, processing_unavailable


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


def request_failed_file_reprocess(_: str, __: str) -> None:
    """Reserve the API boundary until phase 3.2 can enqueue document jobs safely."""
    raise processing_unavailable()


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
        created_at=row["created_at"], updated_at=row["updated_at"],
    )
