from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from psycopg.errors import UniqueViolation

from database import get_connection


STREAM_REQUEST_SAVEPOINT = "stream_generation_request"
STREAM_REQUEST_UNIQUE_CONSTRAINT = "uq_messages_client_request_id"


def create_conversation(user_id: str, agent_id: str, title: str | None) -> tuple[Mapping[str, Any], bool]:
    conversation_id, now = uuid.uuid4(), datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if title is None:
                cursor.execute(
                    """INSERT INTO conversations (id, owner_user_id, agent_id, title, is_draft, created_at, updated_at)
                    VALUES (%s, %s, %s, NULL, true, %s, %s)
                    ON CONFLICT (owner_user_id, agent_id) WHERE is_draft DO NOTHING RETURNING *""",
                    (conversation_id, user_id, agent_id, now, now),
                )
                conversation = cursor.fetchone()
                if conversation is not None:
                    return conversation, True
                cursor.execute(
                    """SELECT * FROM conversations WHERE owner_user_id = %s AND agent_id = %s AND is_draft
                    ORDER BY updated_at DESC, id DESC LIMIT 1""",
                    (user_id, agent_id),
                )
                return cursor.fetchone(), False
            cursor.execute(
                """INSERT INTO conversations (id, owner_user_id, agent_id, title, is_draft, created_at, updated_at)
                VALUES (%s, %s, %s, %s, false, %s, %s) RETURNING *""",
                (conversation_id, user_id, agent_id, title, now, now),
            )
            return cursor.fetchone(), True


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
            cursor.execute("SELECT * FROM messages WHERE conversation_id = %s ORDER BY message_order", (conversation_id,))
            return cursor.fetchall()


def list_valid_history(conversation_id: str, before_message_order: int, limit: int) -> list[Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT role, content FROM (
                    SELECT role, content, message_order
                    FROM messages
                    WHERE conversation_id = %s
                      AND message_order < %s
                      AND generation_status = 'complete'
                      AND btrim(content) <> ''
                    ORDER BY message_order DESC
                    LIMIT %s
                ) AS recent_messages
                ORDER BY message_order""",
                (conversation_id, before_message_order, limit),
            )
            return cursor.fetchall()


def append_echo_messages(
    user_id: str, conversation_id: str, content: str, expected_agent_id: str | None = None
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            conversation = _find_active_conversation(cursor, user_id, conversation_id, expected_agent_id)
            if conversation is None:
                return None
            return _append_echo_messages(cursor, conversation, content)


def start_conversation_and_append_echo_messages(
    user_id: str, agent_id: str, content: str
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO conversations (id, owner_user_id, agent_id, title, is_draft, created_at, updated_at)
                VALUES (%s, %s, %s, %s, false, %s, %s) RETURNING *""",
                (uuid.uuid4(), user_id, agent_id, content[:50], now, now),
            )
            return _append_echo_messages(cursor, cursor.fetchone(), content)


def _find_active_conversation(
    cursor: Any, user_id: str, conversation_id: str, expected_agent_id: str | None
) -> Mapping[str, Any] | None:
    query = """SELECT conversations.* FROM conversations
        JOIN agents ON agents.id = conversations.agent_id
        WHERE conversations.id = %s AND conversations.owner_user_id = %s
        AND agents.deleted_at IS NULL"""
    parameters: tuple[str, ...] = (conversation_id, user_id)
    if expected_agent_id is not None:
        query += " AND conversations.agent_id = %s"
        parameters += (expected_agent_id,)
    cursor.execute(query, parameters)
    return cursor.fetchone()


def _append_echo_messages(
    cursor: Any, conversation: Mapping[str, Any], content: str
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    user_message_at = datetime.now(timezone.utc)
    assistant_message_at = user_message_at
    user_message_id, assistant_message_id = uuid.uuid4(), uuid.uuid4()
    conversation_id = str(conversation["id"])
    user_order, assistant_order = _reserve_message_orders(cursor, conversation_id)
    cursor.execute(
        """INSERT INTO messages (id, conversation_id, role, content, generation_status, message_order, created_at)
        VALUES (%s, %s, 'user', %s, 'complete', %s, %s) RETURNING *""",
        (user_message_id, conversation_id, content, user_order, user_message_at),
    )
    user_message = cursor.fetchone()
    cursor.execute(
        """INSERT INTO messages (id, conversation_id, role, content, generation_status, reply_to_message_id, message_order, created_at)
        VALUES (%s, %s, 'assistant', %s, 'complete', %s, %s, %s) RETURNING *""",
        (assistant_message_id, conversation_id, f"已收到你的消息：{content}", user_message_id, assistant_order, assistant_message_at),
    )
    assistant_message = cursor.fetchone()
    title = conversation["title"] or content[:50]
    cursor.execute(
        "UPDATE conversations SET title = %s, is_draft = false, updated_at = %s WHERE id = %s RETURNING *",
        (title, assistant_message_at, conversation_id),
    )
    conversation = cursor.fetchone()
    return conversation, user_message, assistant_message


def start_stream_generation(
    user_id: str, agent_id: str, conversation_id: str | None, content: str, request_id: str
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], bool] | None:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            existing = _find_existing_stream_request(cursor, request_id, user_id)
            if existing is not None:
                return existing["conversation"], existing["user_message"], existing["assistant_message"], False
            cursor.execute(f"SAVEPOINT {STREAM_REQUEST_SAVEPOINT}")
            try:
                conversation = _get_or_create_stream_conversation(
                    cursor, user_id, agent_id, conversation_id, content, now
                )
                if conversation is None:
                    cursor.execute(f"RELEASE SAVEPOINT {STREAM_REQUEST_SAVEPOINT}")
                    return None
                user_message, assistant_message = _insert_stream_message_pair(
                    cursor, conversation["id"], content, request_id, now
                )
                conversation = _activate_conversation(cursor, conversation["id"], content, now)
            except UniqueViolation as error:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {STREAM_REQUEST_SAVEPOINT}")
                if getattr(error.diag, "constraint_name", None) != STREAM_REQUEST_UNIQUE_CONSTRAINT:
                    raise
                existing = _find_existing_stream_request(cursor, request_id, user_id)
                if existing is None:
                    raise _stream_request_unrecoverable_error() from error
                cursor.execute(f"RELEASE SAVEPOINT {STREAM_REQUEST_SAVEPOINT}")
                return existing["conversation"], existing["user_message"], existing["assistant_message"], False
            cursor.execute(f"RELEASE SAVEPOINT {STREAM_REQUEST_SAVEPOINT}")
            return conversation, user_message, assistant_message, True


def _get_or_create_stream_conversation(
    cursor: Any, user_id: str, agent_id: str, conversation_id: str | None, content: str, now: datetime
) -> Mapping[str, Any] | None:
    if conversation_id is not None:
        return _find_active_conversation(cursor, user_id, conversation_id, agent_id)
    cursor.execute(
        """INSERT INTO conversations (id, owner_user_id, agent_id, title, is_draft, created_at, updated_at)
        VALUES (%s, %s, %s, %s, false, %s, %s) RETURNING *""",
        (uuid.uuid4(), user_id, agent_id, content[:50], now, now),
    )
    return cursor.fetchone()


def _insert_stream_message_pair(
    cursor: Any, conversation_id: object, content: str, request_id: str, now: datetime
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    user_message_id, assistant_message_id = uuid.uuid4(), uuid.uuid4()
    user_order, assistant_order = _reserve_message_orders(cursor, conversation_id)
    cursor.execute(
        """INSERT INTO messages (id, conversation_id, role, content, generation_status, message_order, created_at)
        VALUES (%s, %s, 'user', %s, 'complete', %s, %s) RETURNING *""",
        (user_message_id, str(conversation_id), content, user_order, now),
    )
    user_message = cursor.fetchone()
    cursor.execute(
        """INSERT INTO messages (id, conversation_id, role, content, generation_status, client_request_id, reply_to_message_id, message_order, created_at)
        VALUES (%s, %s, 'assistant', '', 'generating', %s, %s, %s, %s) RETURNING *""",
        (assistant_message_id, str(conversation_id), request_id, user_message_id, assistant_order, now),
    )
    return user_message, cursor.fetchone()


def _reserve_message_orders(cursor: Any, conversation_id: object) -> tuple[int, int]:
    cursor.execute("SELECT id FROM conversations WHERE id = %s FOR UPDATE", (str(conversation_id),))
    if cursor.fetchone() is None:
        raise _not_found_error()
    cursor.execute(
        "SELECT COALESCE(MAX(message_order), 0) + 1 AS first_order FROM messages WHERE conversation_id = %s",
        (str(conversation_id),),
    )
    first_order = cursor.fetchone()["first_order"]
    return first_order, first_order + 1


def _activate_conversation(
    cursor: Any, conversation_id: object, content: str, now: datetime
) -> Mapping[str, Any]:
    cursor.execute(
        """UPDATE conversations
        SET title = CASE WHEN is_draft THEN COALESCE(NULLIF(title, ''), %s) ELSE title END,
            is_draft = false,
            updated_at = %s
        WHERE id = %s
        RETURNING *""",
        (content[:50], now, str(conversation_id)),
    )
    return cursor.fetchone()


def complete_stream_generation(assistant_message_id: str, content: str) -> Mapping[str, Any]:
    return _update_stream_status(assistant_message_id, content, "complete")


def interrupt_stream_generation(assistant_message_id: str, content: str) -> Mapping[str, Any]:
    return _update_stream_status(assistant_message_id, content, "interrupted")


def interrupt_stream_generation_for_user(
    user_id: str, assistant_message_id: str, content: str
) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE messages AS assistant
                SET content = %s, generation_status = 'interrupted'
                FROM conversations
                WHERE assistant.id = %s
                  AND assistant.conversation_id = conversations.id
                  AND conversations.owner_user_id = %s
                  AND assistant.role = 'assistant'
                  AND assistant.generation_status = 'generating'
                RETURNING assistant.*""",
                (content, assistant_message_id, user_id),
            )
            message = cursor.fetchone()
            if message is None:
                return None
            cursor.execute(
                "UPDATE conversations SET updated_at = %s WHERE id = %s",
                (datetime.now(timezone.utc), message["conversation_id"]),
            )
            return message


def fail_stream_generation(assistant_message_id: str, content: str) -> Mapping[str, Any]:
    return _update_stream_status(assistant_message_id, content, "failed")


def _update_stream_status(assistant_message_id: str, content: str, status: str) -> Mapping[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE messages SET content = %s, generation_status = %s
                WHERE id = %s AND role = 'assistant' AND generation_status = 'generating'
                RETURNING *""",
                (content, status, assistant_message_id),
            )
            message = cursor.fetchone()
            if message is None:
                raise _not_found_error()
            cursor.execute(
                "UPDATE conversations SET updated_at = %s WHERE id = %s",
                (datetime.now(timezone.utc), message["conversation_id"]),
            )
            return message


def _find_existing_stream_request(
    cursor: Any, request_id: str, user_id: str
) -> Mapping[str, Any] | None:
    cursor.execute(
        """SELECT
            c.id AS conversation_id, c.agent_id, c.title, c.is_draft,
            c.owner_user_id, c.created_at, c.updated_at,
            assistant.id AS assistant_message_id,
            assistant.content AS assistant_content,
            assistant.generation_status AS assistant_generation_status,
            assistant.message_order AS assistant_message_order,
            assistant.created_at AS assistant_created_at,
            user_message.id AS user_message_id,
            user_message.content AS user_content,
            user_message.role AS user_role,
            user_message.generation_status AS user_generation_status,
            user_message.message_order AS user_message_order,
            user_message.created_at AS user_created_at
        FROM messages AS assistant
        JOIN conversations AS c ON c.id = assistant.conversation_id
        JOIN messages AS user_message
            ON user_message.id = assistant.reply_to_message_id
           AND user_message.conversation_id = assistant.conversation_id
        WHERE assistant.client_request_id = %s
          AND assistant.role = 'assistant'
          AND c.owner_user_id = %s
        LIMIT 1""",
        (request_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    conversation = {
        "id": row["conversation_id"],
        "agent_id": row["agent_id"],
        "title": row["title"],
        "is_draft": row["is_draft"],
        "owner_user_id": row["owner_user_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    user_message = {
        "id": row["user_message_id"],
        "conversation_id": row["conversation_id"],
        "content": row["user_content"],
        "role": row["user_role"],
        "generation_status": row["user_generation_status"],
        "message_order": row["user_message_order"],
        "created_at": row["user_created_at"],
    }
    assistant_message = {
        "id": row["assistant_message_id"],
        "conversation_id": row["conversation_id"],
        "content": row["assistant_content"],
        "role": "assistant",
        "generation_status": row["assistant_generation_status"],
        "client_request_id": request_id,
        "reply_to_message_id": row["user_message_id"],
        "message_order": row["assistant_message_order"],
        "created_at": row["assistant_created_at"],
    }
    return {"conversation": conversation, "user_message": user_message, "assistant_message": assistant_message}


def _not_found_error() -> Exception:
    from services.errors import not_found
    return not_found()


def _stream_request_unrecoverable_error() -> Exception:
    from services.errors import stream_request_unrecoverable
    return stream_request_unrecoverable()
