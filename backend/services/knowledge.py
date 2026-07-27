from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from repositories import knowledge as knowledge_repository
from schemas.knowledge import KnowledgeNodeResponse
from services.errors import invalid_parent_node, knowledge_name_conflict, not_found, processing_unavailable


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
    if knowledge_repository.sibling_name_exists(user_id, parent_id, normalized_name):
        raise knowledge_name_conflict("同一文件夹中已存在同名资料")
    return _to_node(knowledge_repository.create_folder(user_id, parent_id, normalized_name))


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
