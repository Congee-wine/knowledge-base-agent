from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

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
from services import agents as agent_service


router = APIRouter(prefix="/api", tags=["agents"])


@router.get("/chat/entry", response_model=ChatEntryResponse)
def read_chat_entry(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> ChatEntryResponse:
    return ChatEntryResponse(agent=agent_service.resolve_chat_entry(current_user.id))


@router.get("/agents", response_model=AgentListResponse)
def read_agents(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentListResponse:
    return AgentListResponse(items=agent_service.list_agents(current_user.id))


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(data: CreateAgentRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentResponse:
    return agent_service.create_agent(current_user.id, data)


@router.delete("/agents/default", status_code=status.HTTP_204_NO_CONTENT)
def clear_default_agent(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> Response:
    agent_service.clear_default_agent(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def read_agent(agent_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentResponse:
    return agent_service.get_agent(current_user.id, agent_id)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, data: UpdateAgentRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> AgentResponse:
    return agent_service.update_agent(current_user.id, agent_id, data)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> Response:
    agent_service.delete_agent(current_user.id, agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/agents/{agent_id}/default", response_model=DefaultAgentResponse)
def make_default_agent(agent_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> DefaultAgentResponse:
    return DefaultAgentResponse(default_agent_id=agent_service.set_default_agent(current_user.id, agent_id))
