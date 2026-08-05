from __future__ import annotations

from collections.abc import Iterator, Mapping
import logging
from typing import Any

from repositories import agents as agent_repository
from repositories import conversations as conversation_repository
from repositories import stream_events, stream_runs as stream_run_repository
from schemas.agents import AgentResponse
from schemas.conversations import ConversationDetailResponse, ConversationResponse, EchoMessageResponse, MessageResponse
from services.agents import get_agent
from services.errors import not_found
from services.agent_runtime import ModelMessage, stream_with_retrieval
from integrations.deepseek import DeepSeekError
from workers.queue import get_chat_generation_queue


logger = logging.getLogger(__name__)


def create_conversation(user_id: str, agent_id: str, title: str | None) -> tuple[ConversationResponse, bool]:
    _ensure_active_agent(user_id, agent_id)
    conversation, created = conversation_repository.create_conversation(user_id, agent_id, title)
    return _conversation_response(conversation), created


def list_conversations(user_id: str, agent_id: str, limit: int) -> list[ConversationResponse]:
    _ensure_active_agent(user_id, agent_id)
    return [_conversation_response(row) for row in conversation_repository.list_conversations(user_id, agent_id, limit)]


def get_conversation(user_id: str, conversation_id: str) -> ConversationDetailResponse:
    conversation = conversation_repository.get_conversation(user_id, conversation_id)
    if conversation is None:
        raise not_found()
    agent = get_agent(user_id, str(conversation["agent_id"]))
    runs = stream_run_repository.list_for_conversation(str(conversation["id"]))
    messages = [_message_response(row, runs.get(str(row["id"]))) for row in conversation_repository.list_messages(str(conversation["id"]))]
    return ConversationDetailResponse(**_conversation_response(conversation).model_dump(), agent=agent, messages=messages)


def append_echo_messages(user_id: str, conversation_id: str, content: str) -> EchoMessageResponse:
    result = conversation_repository.append_echo_messages(user_id, conversation_id, content)
    if result is None:
        raise not_found()
    conversation, user_message, assistant_message = result
    return EchoMessageResponse(
        conversation=_conversation_response(conversation),
        user_message=_message_response(user_message),
        assistant_message=_message_response(assistant_message),
    )


def send_echo_message(
    user_id: str, agent_id: str, conversation_id: str | None, content: str
) -> EchoMessageResponse:
    if conversation_id is None:
        _ensure_active_agent(user_id, agent_id)
        result = conversation_repository.start_conversation_and_append_echo_messages(user_id, agent_id, content)
    else:
        result = conversation_repository.append_echo_messages(user_id, conversation_id, content, agent_id)
    if result is None:
        raise not_found()
    conversation, user_message, assistant_message = result
    return EchoMessageResponse(
        conversation=_conversation_response(conversation),
        user_message=_message_response(user_message),
        assistant_message=_message_response(assistant_message),
    )


def stream_message(user_id: str, agent_id: str, conversation_id: str | None, content: str, request_id: str, use_knowledge_base: bool = False) -> Iterator[dict[str, object]]:
    agent = _ensure_active_agent(user_id, agent_id)
    result = conversation_repository.start_stream_generation(user_id, agent_id, conversation_id, content, request_id)
    if result is None:
        raise not_found()
    conversation, user_message, assistant_message, created = result

    def events() -> Iterator[dict[str, object]]:
        yield {"type": "message_start", "conversationId": str(conversation["id"]), "userMessageId": str(user_message["id"]), "assistantMessageId": str(assistant_message["id"])}
        if not created:
            status = assistant_message["generation_status"]
            if status == "complete":
                yield {"type": "answer_delta", "content": assistant_message["content"]}
                yield {"type": "message_end", "messageId": str(assistant_message["id"]), "generationStatus": "complete"}
            elif status == "generating":
                yield {"type": "error", "code": "REQUEST_IN_PROGRESS", "message": "该请求正在生成中，请稍后重试", "retryable": False}
            else:
                yield {"type": "error", "code": "GENERATION_FAILED", "message": "上次生成已失败，请重新发送消息", "retryable": True}
            return
        history = _load_valid_history(conversation, user_message)
        answer = ""
        citations: list[dict[str, object]] = []
        try:
            for event in stream_with_retrieval(
                user_id, agent_id, agent.kind, agent.system_prompt, history, content, use_knowledge_base,
                agent.name, agent.description,
            ):
                if event["type"] == "answer_delta": answer += str(event["content"])
                if event["type"] == "sources": citations = list(event["items"])
                yield event
            conversation_repository.complete_stream_generation(str(assistant_message["id"]), answer, citations)
            yield {"type": "message_end", "messageId": str(assistant_message["id"]), "generationStatus": "complete"}
        except DeepSeekError:
            conversation_repository.fail_stream_generation(str(assistant_message["id"]), answer)
            yield {"type": "error", "code": "MODEL_UNAVAILABLE", "message": "模型服务暂时不可用", "retryable": True}
        except Exception:
            conversation_repository.fail_stream_generation(str(assistant_message["id"]), answer)
            yield {"type": "error", "code": "RUNTIME_FAILED", "message": "回答生成失败，请稍后重试", "retryable": True}

    return events()


def open_stream_subscription(user_id: str, agent_id: str, conversation_id: str | None, content: str, request_id: str, after_sequence: int, use_knowledge_base: bool) -> Iterator[dict[str, object]]:
    _ensure_active_agent(user_id, agent_id)
    result = conversation_repository.start_stream_generation(user_id, agent_id, conversation_id, content, request_id)
    if result is None:
        raise not_found()
    conversation, _, assistant_message, _ = result
    run, created = stream_run_repository.create_or_get(request_id, user_id, str(conversation["id"]), str(assistant_message["id"]), use_knowledge_base)
    if created:
        get_chat_generation_queue().enqueue("workers.tasks.process_chat_generation", str(run["id"]), bool(run["use_knowledge_base"]), job_timeout=330)
    return stream_events.subscribe(str(run["id"]), after_sequence)


def interrupt_stream_message(user_id: str, assistant_message_id: str, content: str) -> MessageResponse:
    message = conversation_repository.interrupt_stream_generation_for_user(user_id, assistant_message_id, content)
    if message is None:
        raise not_found()
    return _message_response(message)


def _load_valid_history(conversation: Mapping[str, Any], user_message: Mapping[str, Any]) -> list[ModelMessage]:
    rows = conversation_repository.list_valid_history(
        str(conversation["id"]), int(user_message["message_order"]), 10
    )
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def _ensure_active_agent(user_id: str, agent_id: str) -> AgentResponse:
    agent = agent_repository.find_visible_agent(agent_id, user_id)
    if agent is None:
        raise not_found()
    return get_agent(user_id, agent_id)


def _conversation_response(row: Mapping[str, Any]) -> ConversationResponse:
    return ConversationResponse(
        id=str(row["id"]), agent_id=str(row["agent_id"]), title=row["title"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _message_response(row: Mapping[str, Any], run: Mapping[str, Any] | None = None) -> MessageResponse:
    return MessageResponse(
        id=str(row["id"]), role=row["role"], content=row["content"],
        generation_status=row["generation_status"], created_at=row["created_at"], citations=row.get("citations_json") or [],
        request_id=str(run["request_id"]) if run is not None else None,
        last_sequence=int(run["last_sequence"]) if run is not None else None,
    )
