from typing import Annotated

import json

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse

from dependencies import get_current_user
from schemas.auth import UserResponse
from schemas.conversations import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    CreateMessageRequest,
    EchoMessageResponse,
    SendMessageRequest,
)
from schemas.streaming import StreamRequest
from services import conversations as conversation_service


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _sse(events, request_id: str):
    for sequence, payload in enumerate(events, start=1):
        data = {"requestId": request_id, "sequence": sequence, **payload}
        yield f"id: {request_id}:{sequence}\nevent: {data['type']}\ndata: {json.dumps(data)}\n\n"


@router.get("", response_model=ConversationListResponse)
def read_conversations(
    agent_id: str = Query(alias="agentId"),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
) -> ConversationListResponse:
    return ConversationListResponse(items=conversation_service.list_conversations(current_user.id, agent_id, limit))


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(data: CreateConversationRequest, response: Response, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> ConversationResponse:
    conversation, created = conversation_service.create_conversation(current_user.id, data.agent_id, data.title)
    if not created:
        response.status_code = status.HTTP_200_OK
    return conversation


@router.post("/{conversation_id}/messages", response_model=EchoMessageResponse, status_code=status.HTTP_201_CREATED)
def create_echo_message(
    conversation_id: str,
    data: CreateMessageRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> EchoMessageResponse:
    return conversation_service.append_echo_messages(current_user.id, conversation_id, data.content)


@router.post("/messages", response_model=EchoMessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    data: SendMessageRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> EchoMessageResponse:
    return conversation_service.send_echo_message(
        current_user.id, data.agent_id, data.conversation_id, data.content
    )


@router.post("/messages:stream")
def stream_message(
    data: StreamRequest,
    agent_id: str = Query(alias="agentId"),
    conversation_id: str | None = Query(default=None, alias="conversationId"),
    current_user: UserResponse = Depends(get_current_user),
) -> StreamingResponse:
    events = conversation_service.stream_message(current_user.id, agent_id, conversation_id, data.content, data.request_id)
    return StreamingResponse(_sse(events, data.request_id), media_type="text/event-stream")


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def read_conversation(conversation_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> ConversationDetailResponse:
    return conversation_service.get_conversation(current_user.id, conversation_id)
