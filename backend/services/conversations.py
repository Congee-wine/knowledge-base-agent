from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from repositories import agents as agent_repository
from repositories import conversations as conversation_repository
from schemas.agents import AgentResponse
from schemas.conversations import ConversationDetailResponse, ConversationResponse, MessageResponse
from services.agents import get_agent
from services.errors import not_found


def create_conversation(user_id: str, agent_id: str, title: str | None) -> ConversationResponse:
    _ensure_active_agent(user_id, agent_id)
    return _conversation_response(conversation_repository.create_conversation(user_id, agent_id, title))


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
