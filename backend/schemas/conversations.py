from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.agents import AgentResponse


class CreateConversationRequest(BaseModel):
    agent_id: str = Field(alias="agentId")
    title: str | None = Field(default=None, min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    id: str
    agent_id: str = Field(serialization_alias="agentId")
    title: str | None
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    next_cursor: None = Field(default=None, serialization_alias="nextCursor")


class MessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    generation_status: Literal["complete", "interrupted", "failed"] = Field(serialization_alias="generationStatus")
    created_at: datetime = Field(serialization_alias="createdAt")


class ConversationDetailResponse(ConversationResponse):
    agent: AgentResponse
    messages: list[MessageResponse]
