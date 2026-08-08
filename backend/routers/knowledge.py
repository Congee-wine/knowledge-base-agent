from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import JSONResponse

from dependencies import get_current_user
from schemas.auth import UserResponse
from schemas.knowledge import CreateKnowledgeFolderRequest, HtmlDocumentPreviewResponse, KnowledgeNodeResponse, KnowledgeTreeResponse, TextDocumentPreviewResponse, UpdateKnowledgeNodeRequest
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


@router.post("/files", response_model=KnowledgeNodeResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_file(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    parent_id: Annotated[str | None, Form(alias="parentId")] = None,
) -> KnowledgeNodeResponse:
    return knowledge_service.upload_file(current_user.id, parent_id, file.filename or "", file.content_type, await file.read())


@router.get("/files/{node_id}/preview", response_model=TextDocumentPreviewResponse | HtmlDocumentPreviewResponse)
def read_document_preview(node_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> Response:
    from services.document_preview import get_document_preview

    preview = get_document_preview(current_user.id, node_id)
    if preview.kind == "pdf":
        return Response(
            content=preview.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline",
                "X-Document-Name": quote(preview.name, safe=""),
                "X-Content-Type-Options": "nosniff",
            },
        )
    if preview.kind == "html":
        return JSONResponse({"kind": "html", "name": preview.name, "html": preview.content})
    return JSONResponse({"kind": "text", "name": preview.name, "content": preview.content, "isMarkdown": preview.is_markdown})


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


@router.post("/files/{node_id}/retry-embedding", status_code=status.HTTP_202_ACCEPTED)
def retry_embedding(node_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> Response:
    knowledge_service.retry_embedding(current_user.id, node_id)
    return Response(status_code=status.HTTP_202_ACCEPTED)
