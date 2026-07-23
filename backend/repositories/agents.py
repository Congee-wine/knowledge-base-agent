from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from database import get_connection


BUILTIN_AGENT_ID = "00000000-0000-0000-0000-000000000001"


def list_visible_agents(user_id: str) -> list[Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM agents
                WHERE deleted_at IS NULL AND (kind = 'builtin' OR owner_user_id = %s)
                ORDER BY CASE WHEN kind = 'builtin' THEN 0 ELSE 1 END, updated_at DESC""",
                (user_id,),
            )
            return cursor.fetchall()


def find_visible_agent(agent_id: str, user_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM agents WHERE id = %s AND deleted_at IS NULL
                AND (kind = 'builtin' OR owner_user_id = %s)""",
                (agent_id, user_id),
            )
            return cursor.fetchone()


def find_owned_personal_agent(agent_id: str, user_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM agents WHERE id = %s AND owner_user_id = %s
                AND kind = 'personal' AND deleted_at IS NULL""",
                (agent_id, user_id),
            )
            return cursor.fetchone()


def get_preset_questions(agent_id: str) -> list[str]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT content FROM agent_preset_questions WHERE agent_id = %s ORDER BY display_order",
                (agent_id,),
            )
            return [row["content"] for row in cursor.fetchall()]


def create_personal_agent(user_id: str, values: Mapping[str, Any], questions: Iterable[str]) -> Mapping[str, Any]:
    agent_id, now = uuid.uuid4(), datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO agents (
                    id, owner_user_id, kind, name, description, avatar_key, system_prompt,
                    welcome_message, allow_conversation_upload, created_at, updated_at
                ) VALUES (%s, %s, 'personal', %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *""",
                (agent_id, user_id, values["name"], values["description"], values["avatar_key"],
                 values["system_prompt"], values["welcome_message"], values["allow_conversation_upload"], now, now),
            )
            row = cursor.fetchone()
            _replace_questions(cursor, agent_id, questions)
            return row


def update_personal_agent(agent_id: str, user_id: str, values: Mapping[str, Any], questions: list[str] | None) -> Mapping[str, Any] | None:
    if not values:
        row = find_owned_personal_agent(agent_id, user_id)
        if row is not None and questions is not None:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    _replace_questions(cursor, agent_id, questions)
        return row
    assignments = ", ".join(f"{column} = %s" for column in values)
    parameters = [*values.values(), datetime.now(timezone.utc), agent_id, user_id]
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE agents SET {assignments}, updated_at = %s WHERE id = %s AND owner_user_id = %s "
                "AND kind = 'personal' AND deleted_at IS NULL RETURNING *",
                parameters,
            )
            row = cursor.fetchone()
            if row is not None and questions is not None:
                _replace_questions(cursor, agent_id, questions)
            return row


def clear_default_agent(user_id: str) -> None:
    _upsert_default_agent(user_id, None)


def set_default_agent(user_id: str, agent_id: str) -> None:
    _upsert_default_agent(user_id, agent_id)


def is_default_agent(user_id: str, agent_id: str) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM user_preferences WHERE user_id = %s AND default_agent_id = %s", (user_id, agent_id))
            return cursor.fetchone() is not None


def soft_delete_personal_agent(agent_id: str, user_id: str) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE agents SET deleted_at = %s, updated_at = %s
                WHERE id = %s AND owner_user_id = %s AND kind = 'personal' AND deleted_at IS NULL""",
                (datetime.now(timezone.utc), datetime.now(timezone.utc), agent_id, user_id),
            )
            return cursor.rowcount == 1


def resolve_entry_agent(user_id: str) -> Mapping[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT a.* FROM user_preferences preferences
                JOIN agents a ON a.id = preferences.default_agent_id
                WHERE preferences.user_id = %s AND a.owner_user_id = %s
                AND a.kind = 'personal' AND a.deleted_at IS NULL""",
                (user_id, user_id),
            )
            row = cursor.fetchone()
            if row is not None:
                return row
            cursor.execute("SELECT * FROM agents WHERE id = %s AND kind = 'builtin'", (BUILTIN_AGENT_ID,))
            return cursor.fetchone()


def _replace_questions(cursor: Any, agent_id: uuid.UUID, questions: Iterable[str]) -> None:
    cursor.execute("DELETE FROM agent_preset_questions WHERE agent_id = %s", (agent_id,))
    cursor.executemany(
        """INSERT INTO agent_preset_questions (id, agent_id, content, display_order, created_at)
        VALUES (%s, %s, %s, %s, %s)""",
        [(uuid.uuid4(), agent_id, question, index, datetime.now(timezone.utc)) for index, question in enumerate(questions)],
    )


def _upsert_default_agent(user_id: str, agent_id: str | None) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO user_preferences (user_id, default_agent_id, updated_at) VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET default_agent_id = EXCLUDED.default_agent_id,
                updated_at = EXCLUDED.updated_at""",
                (user_id, agent_id, datetime.now(timezone.utc)),
            )
