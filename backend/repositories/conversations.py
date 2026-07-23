from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
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


def append_echo_messages(user_id: str, conversation_id: str, content: str) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]] | None:
    user_message_at = datetime.now(timezone.utc)
    assistant_message_at = user_message_at + timedelta(microseconds=1)
    user_message_id, assistant_message_id = uuid.uuid4(), uuid.uuid4()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT conversations.* FROM conversations
                JOIN agents ON agents.id = conversations.agent_id
                WHERE conversations.id = %s AND conversations.owner_user_id = %s
                AND agents.deleted_at IS NULL""",
                (conversation_id, user_id),
            )
            conversation = cursor.fetchone()
            if conversation is None:
                return None
            cursor.execute(
                """INSERT INTO messages (id, conversation_id, role, content, generation_status, created_at)
                VALUES (%s, %s, 'user', %s, 'complete', %s) RETURNING *""",
                (user_message_id, conversation_id, content, user_message_at),
            )
            user_message = cursor.fetchone()
            cursor.execute(
                """INSERT INTO messages (id, conversation_id, role, content, generation_status, created_at)
                VALUES (%s, %s, 'assistant', %s, 'complete', %s) RETURNING *""",
                (assistant_message_id, conversation_id, f"已收到你的消息：{content}", assistant_message_at),
            )
            assistant_message = cursor.fetchone()
            title = conversation["title"] or content[:50]
            cursor.execute(
                "UPDATE conversations SET title = %s, updated_at = %s WHERE id = %s RETURNING *",
                (title, assistant_message_at, conversation_id),
            )
            return cursor.fetchone(), user_message, assistant_message
