from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Query, UploadFile

from app.core.config import settings
from app.schemas.knowledge_workspace import (
    KnowledgeWorkspaceBinding,
    KnowledgeWorkspaceFileContent,
    KnowledgeWorkspaceListing,
    KnowledgeWorkspaceSaveDocxRequest,
    KnowledgeWorkspaceSaveTextRequest,
    KnowledgeWorkspaceSettings,
    KnowledgeWorkspaceUpdateRequest,
    KnowledgeWorkspaceUploadResult,
)
from app.services.knowledge_workspace import KnowledgeWorkspaceService
from app.services.storage import JsonStorage

router = APIRouter(prefix="/knowledge-workspace", tags=["knowledge-workspace"])


def get_service() -> KnowledgeWorkspaceService:
    return KnowledgeWorkspaceService(JsonStorage(settings.data_dir))


@router.get("", response_model=KnowledgeWorkspaceSettings)
def get_knowledge_workspace_settings() -> KnowledgeWorkspaceSettings:
    return get_service().load_settings()


@router.put("", response_model=KnowledgeWorkspaceSettings)
def update_knowledge_workspace_settings(request: KnowledgeWorkspaceUpdateRequest) -> KnowledgeWorkspaceSettings:
    return get_service().save_settings(request.root_path)


@router.post("/pick-folder")
def pick_knowledge_workspace_folder() -> dict[str, str]:
    path = get_service().pick_folder()
    return {"path": str(path)}


@router.get("/binding", response_model=KnowledgeWorkspaceBinding)
def get_effective_knowledge_workspace(project_id: str | None = Query(default=None)) -> KnowledgeWorkspaceBinding:
    service = get_service()
    if project_id:
        return service.get_project_binding(project_id)
    settings_payload = service.load_settings()
    return KnowledgeWorkspaceBinding(
        project_id=None,
        default_root_path=settings_payload.default_root_path,
        project_root_path=None,
        effective_root_path=settings_payload.default_root_path,
        scope="global" if settings_payload.default_root_path is not None else "unconfigured",
        exists=bool(settings_payload.default_root_path and settings_payload.default_root_path.exists()),
    )


@router.get("/files", response_model=KnowledgeWorkspaceListing)
def list_knowledge_workspace_files(
    project_id: str | None = Query(default=None),
    query: str = Query(default=""),
) -> KnowledgeWorkspaceListing:
    return get_service().list_files(project_id=project_id, query=query)


@router.post("/files/upload", response_model=KnowledgeWorkspaceUploadResult)
async def upload_knowledge_workspace_files(
    project_id: str | None = Query(default=None),
    files: list[UploadFile] = File(...),
) -> KnowledgeWorkspaceUploadResult:
    return await get_service().upload_files(project_id=project_id, files=files)


@router.post("/files/save-text", response_model=KnowledgeWorkspaceUploadResult)
def save_knowledge_workspace_text_file(request: KnowledgeWorkspaceSaveTextRequest) -> KnowledgeWorkspaceUploadResult:
    return get_service().save_text_file(
        project_id=request.project_id,
        filename=request.filename,
        content=request.content,
    )


@router.post("/files/save-docx", response_model=KnowledgeWorkspaceUploadResult)
def save_knowledge_workspace_docx_file(request: KnowledgeWorkspaceSaveDocxRequest) -> KnowledgeWorkspaceUploadResult:
    return get_service().save_docx_file(
        project_id=request.project_id,
        filename=request.filename,
        content=request.content,
        source_relative_path=request.source_relative_path,
    )


@router.get("/files/content", response_model=KnowledgeWorkspaceFileContent)
def get_knowledge_workspace_file_content(
    project_id: str | None = Query(default=None),
    relative_path: str = Query(...),
) -> KnowledgeWorkspaceFileContent:
    return get_service().read_text_file(project_id=project_id, relative_path=relative_path)


@router.get("/files/docx/content", response_model=KnowledgeWorkspaceFileContent)
def get_knowledge_workspace_docx_content(
    project_id: str | None = Query(default=None),
    relative_path: str = Query(...),
) -> KnowledgeWorkspaceFileContent:
    return get_service().read_docx_file(project_id=project_id, relative_path=relative_path)


@router.get("/projects/{project_id}", response_model=KnowledgeWorkspaceBinding)
def get_project_knowledge_workspace(project_id: str) -> KnowledgeWorkspaceBinding:
    return get_service().get_project_binding(project_id)


@router.put("/projects/{project_id}", response_model=KnowledgeWorkspaceBinding)
def update_project_knowledge_workspace(
    project_id: str,
    request: KnowledgeWorkspaceUpdateRequest,
) -> KnowledgeWorkspaceBinding:
    return get_service().save_project_knowledge_root(project_id, request.root_path)
