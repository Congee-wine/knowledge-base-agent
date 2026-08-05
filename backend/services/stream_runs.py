from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any

from config import (
    STREAM_ANSWER_FLUSH_CHARACTERS,
    STREAM_ANSWER_FLUSH_INTERVAL_MILLISECONDS,
    STREAM_GENERATION_TIMEOUT_SECONDS,
    STREAM_INTERRUPT_CHECK_INTERVAL_MILLISECONDS,
    STREAM_SEQUENCE_CHECKPOINT_SECONDS,
)
from integrations.deepseek import DeepSeekError
from repositories import conversations as conversation_repository
from repositories import stream_events, stream_runs as stream_run_repository
from services.agent_runtime import stream_with_retrieval
from services.agents import get_agent


logger = logging.getLogger(__name__)


def execute_stream_run(run_id: str, use_knowledge_base: bool) -> None:
    run = stream_run_repository.get(run_id)
    if run is None or run["status"] != "queued":
        return
    active_run = stream_run_repository.mark_generating(run_id)
    if active_run is None:
        return
    publisher = StreamEventPublisher(run_id, int(active_run["last_sequence"]))
    assistant_message_id = str(active_run["assistant_message_id"])
    user_id = str(active_run["owner_user_id"])
    conversation_id = str(active_run["conversation_id"])
    message = _load_message_context(conversation_id, assistant_message_id)
    if message is None:
        _terminal_failure(publisher, assistant_message_id, "", "failed", "STREAM_CONTEXT_MISSING", "流式任务上下文不存在")
        return
    agent = get_agent(user_id, str(message["agent_id"]))
    answer = ""
    citations: list[dict[str, object]] = []
    started = time.monotonic()
    answer_buffer = ""
    last_answer_flush_at = started
    last_interrupt_check_at = started

    def flush_answer_buffer() -> None:
        nonlocal answer_buffer, last_answer_flush_at
        if not answer_buffer:
            return
        publisher.publish({"type": "answer_delta", "content": answer_buffer})
        answer_buffer = ""
        last_answer_flush_at = time.monotonic()

    try:
        publisher.publish({"type": "message_start", "conversationId": conversation_id, "userMessageId": str(message["user_message_id"]), "assistantMessageId": assistant_message_id})
        history = _load_history(conversation_id, int(message["user_message_order"]))
        for event in stream_with_retrieval(user_id, str(message["agent_id"]), agent.kind, agent.system_prompt, history, str(message["user_content"]), use_knowledge_base, agent.name, agent.description):
            now = time.monotonic()
            if now - started >= STREAM_GENERATION_TIMEOUT_SECONDS:
                raise StreamRunTimedOut()
            if (now - last_interrupt_check_at) * 1000 >= STREAM_INTERRUPT_CHECK_INTERVAL_MILLISECONDS:
                last_interrupt_check_at = now
                interrupted = _was_interrupted(assistant_message_id)
            else:
                interrupted = False
            if interrupted:
                flush_answer_buffer()
                stream_run_repository.mark_terminal(run_id, "interrupted")
                publisher.publish_terminal("message_end", {"messageId": assistant_message_id, "generationStatus": "interrupted"})
                return
            if event["type"] == "answer_delta":
                content = str(event["content"])
                answer += content
                answer_buffer += content
                elapsed_milliseconds = (now - last_answer_flush_at) * 1000
                if len(answer_buffer) >= STREAM_ANSWER_FLUSH_CHARACTERS or elapsed_milliseconds >= STREAM_ANSWER_FLUSH_INTERVAL_MILLISECONDS:
                    flush_answer_buffer()
                continue
            flush_answer_buffer()
            if event["type"] == "sources": citations = list(event["items"])
            publisher.publish(event)
        flush_answer_buffer()
        conversation_repository.complete_stream_generation(assistant_message_id, answer, citations)
        stream_run_repository.mark_terminal(run_id, "complete")
        publisher.publish_terminal("message_end", {"messageId": assistant_message_id, "generationStatus": "complete"})
    except StreamRunTimedOut:
        flush_answer_buffer()
        _terminal_failure(publisher, assistant_message_id, answer, "timed_out", "STREAM_TIMED_OUT", "回答生成超时")
    except DeepSeekError:
        flush_answer_buffer()
        _terminal_failure(publisher, assistant_message_id, answer, "failed", "MODEL_UNAVAILABLE", "模型服务暂时不可用")
    except Exception:
        logger.exception("stream run failed", extra={"stream_run_id": run_id})
        flush_answer_buffer()
        _terminal_failure(publisher, assistant_message_id, answer, "failed", "RUNTIME_FAILED", "回答生成失败，请稍后重试")


def _load_message_context(conversation_id: str, assistant_message_id: str) -> Mapping[str, Any] | None:
    from database import get_connection
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT assistant.id AS assistant_message_id, user_message.id AS user_message_id, user_message.content AS user_content, user_message.message_order AS user_message_order, conversations.agent_id FROM messages AS assistant JOIN messages AS user_message ON user_message.id = assistant.reply_to_message_id JOIN conversations ON conversations.id = assistant.conversation_id WHERE assistant.id = %s AND assistant.conversation_id = %s""", (assistant_message_id, conversation_id))
            return cursor.fetchone()


def _load_history(conversation_id: str, user_message_order: int) -> list[dict[str, str]]:
    return [{"role": row["role"], "content": row["content"]} for row in conversation_repository.list_valid_history(conversation_id, user_message_order, 10)]


def _was_interrupted(assistant_message_id: str) -> bool:
    from database import get_connection
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT generation_status FROM messages WHERE id = %s", (assistant_message_id,))
            row = cursor.fetchone()
            return row is None or row["generation_status"] != "generating"


def _terminal_failure(publisher: "StreamEventPublisher", assistant_message_id: str, answer: str, status: str, code: str, message: str) -> None:
    conversation_repository.fail_stream_generation(assistant_message_id, answer, status=status)
    stream_run_repository.mark_terminal(publisher.run_id, status, code, message)
    publisher.publish_terminal("error", {"code": code, "message": message, "retryable": False})


class StreamEventPublisher:
    def __init__(self, run_id: str, sequence: int) -> None:
        self.run_id = run_id
        self.sequence = sequence
        self.last_checkpoint_at = time.monotonic()

    def publish(self, event: Mapping[str, object], force_checkpoint: bool = False) -> None:
        self.sequence += 1
        stream_events.publish(self.run_id, self.sequence, event)
        if force_checkpoint or time.monotonic() - self.last_checkpoint_at >= STREAM_SEQUENCE_CHECKPOINT_SECONDS:
            stream_run_repository.update_last_sequence(self.run_id, self.sequence)
            self.last_checkpoint_at = time.monotonic()

    def publish_terminal(self, event_type: str, payload: Mapping[str, object]) -> None:
        self.publish({"type": event_type, **payload}, force_checkpoint=True)
        stream_events.expire_after_terminal(self.run_id)


class StreamRunTimedOut(Exception):
    pass
