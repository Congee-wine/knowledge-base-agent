from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from dependencies import get_current_user
from schemas.auth import UserResponse
from schemas.knowledge import CreateKnowledgeFolderRequest, KnowledgeNodeResponse, KnowledgeTreeResponse, UpdateKnowledgeNodeRequest
from services import knowledge as knowledge_service


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/nodes", response_model=KnowledgeTreeResponse)
def read_knowledge_tree(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> KnowledgeTreeResponse:
    return KnowledgeTreeResponse(items=knowledge_service.list_knowledge_tree(current_user.id))


@router.post("/nodes", response_model=KnowledgeNodeResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_folder(
    data: CreateKnowledgeFolderRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> KnowledgeNodeResponse:
    return knowledge_service.create_folder(current_user.id, data.parent_id, data.name)


@router.patch("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
def update_knowledge_node(node_id: str, data: UpdateKnowledgeNodeRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> KnowledgeNodeResponse:
    if not data.has_single_change():
        from services.errors import invalid_knowledge_update
        raise invalid_knowledge_update()
    if data.name is not None:
        return knowledge_service.rename_node(current_user.id, node_id, data.name)
    return knowledge_service.move_node(current_user.id, node_id, data.parent_id)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_node(node_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> Response:
    knowledge_service.delete_node(current_user.id, node_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/files/{file_id}/reprocess", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def reprocess_failed_file(
    file_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> Response:
    knowledge_service.request_failed_file_reprocess(current_user.id, file_id)
    return Response(status_code=status.HTTP_501_NOT_IMPLEMENTED)
