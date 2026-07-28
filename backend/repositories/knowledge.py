from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from database import get_connection


def list_nodes(user_id: str) -> Sequence[Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT node.*, version.processing_status
                FROM knowledge_nodes node
                LEFT JOIN document_versions version
                  ON version.knowledge_node_id = node.id AND version.is_current
                WHERE node.owner_user_id = %s
                ORDER BY node.parent_id NULLS FIRST, node.node_type DESC, lower(node.name), node.id""",
                (user_id,),
            )
            return cursor.fetchall()


def find_owned_node(node_id: str, user_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s", (node_id, user_id))
            return cursor.fetchone()


def sibling_name_exists(user_id: str, parent_id: str | None, name: str, exclude_node_id: str | None = None) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT 1 FROM knowledge_nodes WHERE owner_user_id = %s AND parent_id IS NOT DISTINCT FROM %s
                AND lower(name) = lower(%s) AND (%s::uuid IS NULL OR id <> %s::uuid)""",
                (user_id, parent_id, name, exclude_node_id, exclude_node_id),
            )
            return cursor.fetchone() is not None


def create_folder(user_id: str, parent_id: str | None, name: str) -> Mapping[str, Any]:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO knowledge_nodes (id, owner_user_id, parent_id, node_type, name, created_at, updated_at)
                VALUES (%s, %s, %s, 'folder', %s, %s, %s) RETURNING *""",
                (uuid.uuid4(), user_id, parent_id, name, now, now),
            )
            return cursor.fetchone()


def update_node(node_id: str, user_id: str, *, name: str | None = None, parent_id: str | None = None) -> Mapping[str, Any] | None:
    field, value = ("name", name) if name is not None else ("parent_id", parent_id)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE knowledge_nodes SET {field} = %s, updated_at = %s WHERE id = %s AND owner_user_id = %s RETURNING *",
                (value, datetime.now(timezone.utc), node_id, user_id),
            )
            return cursor.fetchone()


def is_descendant(node_id: str, candidate_parent_id: str, user_id: str) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE descendants AS (
                    SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL
                    SELECT child.id FROM knowledge_nodes child JOIN descendants parent ON child.parent_id = parent.id
                    WHERE child.owner_user_id = %s
                ) SELECT 1 FROM descendants WHERE id = %s""",
                (node_id, user_id, user_id, candidate_parent_id),
            )
            return cursor.fetchone() is not None


def get_node_depth(node_id: str, user_id: str) -> int:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL SELECT parent.id, parent.parent_id FROM knowledge_nodes parent
                    JOIN ancestors child ON child.parent_id = parent.id WHERE parent.owner_user_id = %s
                ) SELECT count(*) - 1 AS depth FROM ancestors""",
                (node_id, user_id, user_id),
            )
            return int(cursor.fetchone()["depth"])


def get_tree_height(node_id: str, user_id: str) -> int:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE descendants AS (
                    SELECT id, 0 AS depth FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL SELECT child.id, parent.depth + 1 FROM knowledge_nodes child
                    JOIN descendants parent ON child.parent_id = parent.id WHERE child.owner_user_id = %s
                ) SELECT max(depth) AS height FROM descendants""",
                (node_id, user_id, user_id),
            )
            return int(cursor.fetchone()["height"])


def delete_node_tree(node_id: str, user_id: str) -> list[str] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s", (node_id, user_id))
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                """WITH RECURSIVE tree AS (
                    SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s
                    UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id
                    WHERE child.owner_user_id = %s
                ) SELECT storage_key FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree)""",
                (node_id, user_id, user_id),
            )
            storage_keys = [str(row["storage_key"]) for row in cursor.fetchall()]
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM agent_knowledge_scopes WHERE knowledge_node_id IN (SELECT id FROM tree)""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM document_chunks WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree))""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM ingestion_jobs WHERE document_version_id IN (SELECT id FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree))""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM document_versions WHERE knowledge_node_id IN (SELECT id FROM tree)""", (node_id, user_id, user_id))
            cursor.execute("""WITH RECURSIVE tree AS (SELECT id FROM knowledge_nodes WHERE id = %s AND owner_user_id = %s UNION ALL SELECT child.id FROM knowledge_nodes child JOIN tree ON child.parent_id = tree.id WHERE child.owner_user_id = %s) DELETE FROM knowledge_nodes WHERE id IN (SELECT id FROM tree)""", (node_id, user_id, user_id))
            return storage_keys


def list_agent_scope_node_ids(user_id: str, agent_id: str) -> list[str]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT knowledge_node_id FROM agent_knowledge_scopes
                WHERE owner_user_id = %s AND agent_id = %s ORDER BY created_at, id""",
                (user_id, agent_id),
            )
            return [str(row["knowledge_node_id"]) for row in cursor.fetchall()]
