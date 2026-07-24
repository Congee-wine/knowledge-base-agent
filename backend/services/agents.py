from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from repositories import agents as agent_repository
from schemas.agents import AgentResponse, CreateAgentRequest, UpdateAgentRequest
from services.errors import default_agent_must_be_cleared, immutable_agent, not_found


def list_agents(user_id: str) -> list[AgentResponse]:
    return [_to_response(row) for row in agent_repository.list_visible_agents(user_id)]


def get_agent(user_id: str, agent_id: str) -> AgentResponse:
    row = agent_repository.find_visible_agent(agent_id, user_id)
    if row is None:
        raise not_found()
    return _to_response(row)


def create_agent(user_id: str, data: CreateAgentRequest) -> AgentResponse:
    row = agent_repository.create_personal_agent(user_id, _create_values(data), data.preset_questions)
    return _to_response(row, data.preset_questions)


def update_agent(user_id: str, agent_id: str, data: UpdateAgentRequest) -> AgentResponse:
    visible_agent = agent_repository.find_visible_agent(agent_id, user_id)
    if visible_agent is None:
        raise not_found()
    if visible_agent["kind"] == "builtin":
        raise immutable_agent()
    row = agent_repository.update_personal_agent(agent_id, user_id, _update_values(data), data.preset_questions)
    if row is None:
        raise not_found()
    return _to_response(row, data.preset_questions)


def delete_agent(user_id: str, agent_id: str) -> None:
    visible_agent = agent_repository.find_visible_agent(agent_id, user_id)
    if visible_agent is None:
        raise not_found()
    if visible_agent["kind"] == "builtin":
        raise immutable_agent()
    if agent_repository.is_default_agent(user_id, agent_id):
        raise default_agent_must_be_cleared()
    if not agent_repository.soft_delete_personal_agent(agent_id, user_id):
        raise not_found()


def set_default_agent(user_id: str, agent_id: str) -> str:
    if agent_repository.find_owned_personal_agent(agent_id, user_id) is None:
        raise not_found()
    agent_repository.set_default_agent(user_id, agent_id)
    return agent_id


def clear_default_agent(user_id: str) -> None:
    agent_repository.clear_default_agent(user_id)


def resolve_chat_entry(user_id: str) -> AgentResponse:
    return _to_response(agent_repository.resolve_entry_agent(user_id))


def _create_values(data: CreateAgentRequest) -> dict[str, Any]:
    return {
        "name": data.name,
        "description": data.description,
        "avatar_key": data.avatar_key,
        "system_prompt": data.system_prompt,
        "welcome_message": data.welcome_message,
        "allow_conversation_upload": data.allow_conversation_upload,
        "allow_network_access": data.allow_network_access,
    }


def _update_values(data: UpdateAgentRequest) -> dict[str, Any]:
    field_map = {
        "name": data.name,
        "description": data.description,
        "avatar_key": data.avatar_key,
        "system_prompt": data.system_prompt,
        "welcome_message": data.welcome_message,
        "allow_conversation_upload": data.allow_conversation_upload,
        "allow_network_access": data.allow_network_access,
    }
    return {name: value for name, value in field_map.items() if name in data.model_fields_set}


def _to_response(row: Mapping[str, Any], preset_questions: list[str] | None = None) -> AgentResponse:
    return AgentResponse(
        id=str(row["id"]), kind=row["kind"], name=row["name"], description=row["description"],
        avatar_key=row["avatar_key"], system_prompt=row["system_prompt"], welcome_message=row["welcome_message"],
        preset_questions=preset_questions if preset_questions is not None else agent_repository.get_preset_questions(str(row["id"])),
        allow_conversation_upload=row["allow_conversation_upload"], created_at=row["created_at"], updated_at=row["updated_at"],
        allow_network_access=row["allow_network_access"],
    )
