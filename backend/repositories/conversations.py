from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from database import get_connection


def create_conversation(user_id: str, agent_id: str, title: str | None) -> Mapping[str, Any]:
    conversation_id, now = uuid.uuid4(), datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO conversations (id, owner_user_id, agent_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                (conversation_id, user_id, agent_id, title, now, now),
            )
            return cursor.fetchone()


def list_conversations(user_id: str, agent_id: str, limit: int) -> list[Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM conversations WHERE owner_user_id = %s AND agent_id = %s
                ORDER BY updated_at DESC, id DESC LIMIT %s""",
                (user_id, agent_id, limit),
            )
            return cursor.fetchall()


def get_conversation(user_id: str, conversation_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM conversations WHERE id = %s AND owner_user_id = %s", (conversation_id, user_id))
            return cursor.fetchone()


def list_messages(conversation_id: str) -> list[Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at, id", (conversation_id,))
            return cursor.fetchall()
