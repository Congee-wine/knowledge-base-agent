from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from repositories import agents as agent_repository
from repositories import conversations as conversation_repository
from schemas.agents import AgentResponse
from schemas.conversations import ConversationDetailResponse, ConversationResponse, EchoMessageResponse, MessageResponse
from services.agents import get_agent
from services.errors import not_found
from services.agent_runtime import ModelMessage, stream_answer
from integrations.deepseek import DeepSeekError


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
    messages = [_message_response(row) for row in conversation_repository.list_messages(str(conversation["id"]))]
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


def stream_message(user_id: str, agent_id: str, conversation_id: str | None, content: str, request_id: str) -> Iterator[dict[str, object]]:
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
        history: list[ModelMessage] = []
        answer = ""
        try:
            yield {"type": "status", "stage": "generating", "text": "正在生成回答"}
            for delta in stream_answer(agent.system_prompt, history, content):
                answer += delta
                yield {"type": "answer_delta", "content": delta}
            conversation_repository.complete_stream_generation(str(assistant_message["id"]), answer)
            yield {"type": "message_end", "messageId": str(assistant_message["id"]), "generationStatus": "complete"}
        except DeepSeekError:
            conversation_repository.fail_stream_generation(str(assistant_message["id"]), answer)
            yield {"type": "error", "code": "MODEL_UNAVAILABLE", "message": "模型服务暂时不可用", "retryable": True}
        except Exception:
            conversation_repository.fail_stream_generation(str(assistant_message["id"]), answer)
            yield {"type": "error", "code": "RUNTIME_FAILED", "message": "回答生成失败，请稍后重试", "retryable": True}

    return events()


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


def _message_response(row: Mapping[str, Any]) -> MessageResponse:
    return MessageResponse(
        id=str(row["id"]), role=row["role"], content=row["content"],
        generation_status=row["generation_status"], created_at=row["created_at"],
    )
