from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from dependencies import get_current_user
from schemas.auth import UserResponse
from schemas.conversations import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
)
from services import conversations as conversation_service


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
def read_conversations(
    agent_id: str = Query(alias="agentId"),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
) -> ConversationListResponse:
    return ConversationListResponse(items=conversation_service.list_conversations(current_user.id, agent_id, limit))


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(data: CreateConversationRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> ConversationResponse:
    return conversation_service.create_conversation(current_user.id, data.agent_id, data.title)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def read_conversation(conversation_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> ConversationDetailResponse:
    return conversation_service.get_conversation(current_user.id, conversation_id)
