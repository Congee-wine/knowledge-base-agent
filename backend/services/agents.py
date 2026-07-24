from __future__ import annotations

from collections.abc import Mapping
import logging
import uuid
from typing import Any

from minio.error import S3Error

from repositories import agents as agent_repository
from integrations.object_storage import put_private_object, read_private_object, remove_private_object
from schemas.agents import AgentResponse, CreateAgentRequest, UpdateAgentRequest
from services.errors import default_agent_must_be_cleared, immutable_agent, not_found, object_storage_unavailable


logger = logging.getLogger(__name__)


MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024
AVATAR_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


class AgentAvatarValidationError(ValueError):
    pass


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
    if visible_agent["avatar_key"] and str(visible_agent["avatar_key"]).startswith("agent-avatars/"):
        try:
            remove_private_object(str(visible_agent["avatar_key"]))
        except Exception:
            logger.exception("Unable to remove deleted agent avatar: agent_id=%s", agent_id)


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
        "interaction_type": data.interaction_type,
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
        "interaction_type": data.interaction_type,
    }
    return {name: value for name, value in field_map.items() if name in data.model_fields_set}


def _to_response(row: Mapping[str, Any], preset_questions: list[str] | None = None) -> AgentResponse:
    return AgentResponse(
        id=str(row["id"]), kind=row["kind"], name=row["name"], description=row["description"],
        avatar_key=row["avatar_key"], system_prompt=row["system_prompt"], welcome_message=row["welcome_message"],
        preset_questions=preset_questions if preset_questions is not None else agent_repository.get_preset_questions(str(row["id"])),
        allow_conversation_upload=row["allow_conversation_upload"], created_at=row["created_at"], updated_at=row["updated_at"],
        allow_network_access=row["allow_network_access"],
        interaction_type=row["interaction_type"],
    )


def validate_avatar_upload(content: bytes) -> tuple[str, str]:
    if not content:
        raise AgentAvatarValidationError("头像文件不能为空")
    if len(content) > MAX_AVATAR_SIZE_BYTES:
        raise AgentAvatarValidationError("头像文件不能超过 5MB")
    content_type = _detect_avatar_content_type(content)
    if content_type is None:
        raise AgentAvatarValidationError("头像仅支持 PNG、JPG、JPEG、GIF 或 WEBP 格式")
    return content_type, AVATAR_CONTENT_TYPES[content_type]


def create_agent_with_avatar(user_id: str, name: str, description: str | None, avatar: bytes | None) -> AgentResponse:
    data = CreateAgentRequest(name=name, description=description, interactionType="text")
    avatar_key = None
    if avatar is not None:
        avatar_content_type, extension = validate_avatar_upload(avatar)
        avatar_key = f"agent-avatars/{user_id}/{uuid.uuid4()}{extension}"
        try:
            put_private_object(avatar_key, avatar, avatar_content_type)
        except S3Error as error:
            logger.exception("Unable to store agent avatar: code=%s", error.code)
            raise object_storage_unavailable() from error
    try:
        return create_agent(user_id, data.model_copy(update={"avatar_key": avatar_key}))
    except Exception:
        if avatar_key is not None:
            remove_private_object(avatar_key)
        raise


def read_agent_avatar(user_id: str, agent_id: str) -> tuple[bytes, str]:
    agent = get_agent(user_id, agent_id)
    if agent.avatar_key is None or not agent.avatar_key.startswith("agent-avatars/"):
        raise not_found()
    response = read_private_object(agent.avatar_key)
    try:
        return response.read(), response.headers.get("Content-Type", "application/octet-stream")
    finally:
        response.close()
        response.release_conn()


def _detect_avatar_content_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        return "image/webp"
    return None
