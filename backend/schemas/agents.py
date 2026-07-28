from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AgentWriteFields(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    avatar_key: str | None = Field(default=None, max_length=100, alias="avatarKey")
    system_prompt: str | None = Field(default=None, max_length=8000, alias="systemPrompt")
    welcome_message: str | None = Field(default=None, max_length=1000, alias="welcomeMessage")
    preset_questions: list[str] = Field(default_factory=list, max_length=10, alias="presetQuestions")
    allow_conversation_upload: bool = Field(default=True, alias="allowConversationUpload")
    allow_network_access: bool = Field(default=True, alias="allowNetworkAccess")
    interaction_type: Literal["text", "voice", "digital_human"] = Field(default="text", alias="interactionType")


class CreateAgentRequest(AgentWriteFields):
    pass


class UpdateAgentRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    avatar_key: str | None = Field(default=None, max_length=100, alias="avatarKey")
    system_prompt: str | None = Field(default=None, max_length=8000, alias="systemPrompt")
    welcome_message: str | None = Field(default=None, max_length=1000, alias="welcomeMessage")
    preset_questions: list[str] | None = Field(default=None, max_length=10, alias="presetQuestions")
    allow_conversation_upload: bool | None = Field(default=None, alias="allowConversationUpload")
    allow_network_access: bool | None = Field(default=None, alias="allowNetworkAccess")
    interaction_type: Literal["text", "voice", "digital_human"] | None = Field(default=None, alias="interactionType")


class AgentResponse(BaseModel):
    id: str
    kind: Literal["builtin", "personal"]
    name: str
    description: str | None
    avatar_key: str | None = Field(serialization_alias="avatarKey")
    system_prompt: str | None = Field(serialization_alias="systemPrompt")
    welcome_message: str | None = Field(serialization_alias="welcomeMessage")
    preset_questions: list[str] = Field(serialization_alias="presetQuestions")
    allow_conversation_upload: bool = Field(serialization_alias="allowConversationUpload")
    allow_network_access: bool = Field(serialization_alias="allowNetworkAccess")
    interaction_type: Literal["text", "voice", "digital_human"] = Field(serialization_alias="interactionType")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class AgentListResponse(BaseModel):
    items: list[AgentResponse]


class ChatEntryResponse(BaseModel):
    agent: AgentResponse


class DefaultAgentResponse(BaseModel):
    default_agent_id: str = Field(serialization_alias="defaultAgentId")


class AgentKnowledgeScopeRequest(BaseModel):
    node_ids: list[str] = Field(default_factory=list, alias="nodeIds", max_length=100)


class AgentKnowledgeScopeResponse(BaseModel):
    node_ids: list[str] = Field(serialization_alias="nodeIds")
