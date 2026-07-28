from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.agents import AgentWriteFields


class StreamHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class StreamRequest(BaseModel):
    request_id: str = Field(alias="requestId", min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=4000)
    after_sequence: int = Field(default=0, alias="afterSequence", ge=0)
    use_knowledge_base: bool = Field(default=False, alias="useKnowledgeBase")

    @field_validator("content")
    @classmethod
    def normalize_content(cls, content: str) -> str:
        content = content.strip()
        if not content:
            raise ValueError("消息内容不能为空")
        return content


class PreviewStreamRequest(StreamRequest):
    draft_agent: AgentWriteFields = Field(alias="draftAgent")
    history: list[StreamHistoryMessage] = Field(default_factory=list, max_length=10)


class InterruptStreamRequest(BaseModel):
    content: str = Field(default="", max_length=4000)
