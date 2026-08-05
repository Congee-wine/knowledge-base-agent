from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from psycopg.errors import UniqueViolation

from database import get_connection


FINAL_STATUSES = {"complete", "failed", "interrupted", "timed_out"}


def create_or_get(request_id: str, user_id: str, conversation_id: str, assistant_message_id: str, use_knowledge_base: bool) -> tuple[Mapping[str, Any], bool]:
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """INSERT INTO stream_runs (
                        id, request_id, owner_user_id, conversation_id, assistant_message_id, use_knowledge_base, status, last_sequence, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'queued', 0, %s) RETURNING *""",
                    (uuid.uuid4(), request_id, user_id, conversation_id, assistant_message_id, use_knowledge_base, now),
                )
                return cursor.fetchone(), True
            except UniqueViolation:
                connection.rollback()
                run = find_for_user(request_id, user_id)
                if run is None:
                    raise
                return run, False


def find_for_user(request_id: str, user_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM stream_runs WHERE request_id = %s AND owner_user_id = %s", (request_id, user_id))
            return cursor.fetchone()


def get(run_id: str) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM stream_runs WHERE id = %s", (run_id,))
            return cursor.fetchone()


def list_for_conversation(conversation_id: str) -> dict[str, Mapping[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM stream_runs WHERE conversation_id = %s", (conversation_id,))
            return {str(row["assistant_message_id"]): row for row in cursor.fetchall()}


def mark_generating(run_id: str) -> Mapping[str, Any] | None:
    now = datetime.now(timezone.utc)
    return _update(run_id, "generating", started_at=now)


def mark_terminal(run_id: str, status: str, error_code: str | None = None, error_message: str | None = None) -> Mapping[str, Any] | None:
    if status not in FINAL_STATUSES:
        raise ValueError("stream run status must be terminal")
    return _update(run_id, status, finished_at=datetime.now(timezone.utc), error_code=error_code, error_message=error_message)


def update_last_sequence(run_id: str, sequence: int) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE stream_runs SET last_sequence = GREATEST(last_sequence, %s) WHERE id = %s", (sequence, run_id))


def _update(run_id: str, status: str, **values: object) -> Mapping[str, Any] | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE stream_runs SET status = %s,
                    started_at = COALESCE(%s, started_at),
                    finished_at = %s,
                    error_code = %s,
                    error_message = %s
                WHERE id = %s AND status NOT IN ('complete', 'failed', 'interrupted', 'timed_out')
                RETURNING *""",
                (status, values.get("started_at"), values.get("finished_at"), values.get("error_code"), values.get("error_message"), run_id),
            )
            return cursor.fetchone()
