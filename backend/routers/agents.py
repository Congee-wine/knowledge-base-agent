from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import Response as FastApiResponse, StreamingResponse
import json

from dependencies import get_current_user
from schemas.agents import (
    AgentListResponse,
    AgentResponse,
    ChatEntryResponse,
    CreateAgentRequest,
    DefaultAgentResponse,
    UpdateAgentRequest,
)
from schemas.auth import UserResponse
from schemas.streaming import PreviewStreamRequest
from services import agents as agent_service
from services import agent_preview


router = APIRouter(prefix="/api", tags=["agents"])


def _preview_sse(events, request_id: str):
    for sequence, payload in enumerate(events, start=1):
        data = {"requestId": request_id, "sequence": sequence, "mode": "preview", **payload}
        yield f"id: {request_id}:{sequence}\nevent: {data['type']}\ndata: {json.dumps(data)}\n\n"


@router.get("/chat/entry", response_model=ChatEntryResponse)
def read_chat_entry(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> ChatEntryResponse:
    return ChatEntryResponse(agent=agent_service.resolve_chat_entry(current_user.id))


@router.get("/agents", response_model=AgentListResponse)
def read_agents(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentListResponse:
    return AgentListResponse(items=agent_service.list_agents(current_user.id))


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(data: CreateAgentRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentResponse:
    return agent_service.create_agent(current_user.id, data)


@router.post("/agents/bootstrap", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_bootstrap(
    name: Annotated[str, Form()],
    description: Annotated[str | None, Form()] = None,
    avatar: Annotated[UploadFile | None, File()] = None,
    current_user: UserResponse = Depends(get_current_user),
) -> AgentResponse:
    avatar_content = await avatar.read() if avatar is not None else None
    try:
        return agent_service.create_agent_with_avatar(current_user.id, name, description, avatar_content)
    except agent_service.AgentAvatarValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.delete("/agents/default", status_code=status.HTTP_204_NO_CONTENT)
def clear_default_agent(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> Response:
    agent_service.clear_default_agent(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/agents/{agent_id}/avatar")
def read_agent_avatar(agent_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> FastApiResponse:
    content, content_type = agent_service.read_agent_avatar(current_user.id, agent_id)
    return FastApiResponse(content=content, media_type=content_type, headers={"Cache-Control": "private, max-age=300"})


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def read_agent(agent_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentResponse:
    return agent_service.get_agent(current_user.id, agent_id)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, data: UpdateAgentRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentResponse:
    return agent_service.update_agent(current_user.id, agent_id, data)


@router.post("/agents/{agent_id}/preview/messages:stream")
def stream_agent_preview(agent_id: str, data: PreviewStreamRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> StreamingResponse:
    events = agent_preview.stream_preview(current_user.id, agent_id, data)
    return StreamingResponse(_preview_sse(events, data.request_id), media_type="text/event-stream")


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> Response:
    agent_service.delete_agent(current_user.id, agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/agents/{agent_id}/default", response_model=DefaultAgentResponse)
def make_default_agent(agent_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> DefaultAgentResponse:
    return DefaultAgentResponse(default_agent_id=agent_service.set_default_agent(current_user.id, agent_id))
