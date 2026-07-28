from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateKnowledgeFolderRequest(BaseModel):
    parent_id: str | None = Field(default=None, alias="parentId")
    name: str = Field(min_length=1, max_length=255)


class UpdateKnowledgeNodeRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: str | None = Field(default=None, alias="parentId")

    def has_single_change(self) -> bool:
        return len(self.model_fields_set) == 1 and self.model_fields_set <= {"name", "parent_id"}


class KnowledgeNodeResponse(BaseModel):
    id: str
    parent_id: str | None = Field(serialization_alias="parentId")
    node_type: Literal["folder", "file"] = Field(serialization_alias="nodeType")
    name: str
    status: Literal["uploaded", "processing", "ready", "failed"] | None = None
    mime_type: str | None = Field(default=None, serialization_alias="mimeType")
    byte_size: int | None = Field(default=None, serialization_alias="byteSize")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    children: list["KnowledgeNodeResponse"] = Field(default_factory=list)


class KnowledgeTreeResponse(BaseModel):
    items: list[KnowledgeNodeResponse]
