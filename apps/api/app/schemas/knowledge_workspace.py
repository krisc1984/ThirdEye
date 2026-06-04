from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class KnowledgeWorkspaceSettings(BaseModel):
    default_root_path: Path | None = None


class KnowledgeWorkspaceBinding(BaseModel):
    project_id: str | None = None
    default_root_path: Path | None = None
    project_root_path: Path | None = None
    effective_root_path: Path | None = None
    scope: str = "unconfigured"
    exists: bool = False


class KnowledgeWorkspaceUpdateRequest(BaseModel):
    root_path: Path | None = None


class KnowledgeWorkspaceItem(BaseModel):
    name: str
    relative_path: str
    path: Path
    is_dir: bool
    size_bytes: int = 0
    updated_at: datetime


class KnowledgeWorkspaceListing(BaseModel):
    root_path: Path | None = None
    query: str = ""
    items: list[KnowledgeWorkspaceItem] = Field(default_factory=list)
    total_items: int = 0


class KnowledgeWorkspaceUploadResult(BaseModel):
    root_path: Path
    uploaded_files: list[str] = Field(default_factory=list)


class KnowledgeWorkspaceFileContent(BaseModel):
    root_path: Path
    relative_path: str
    content: str
    truncated: bool = False
    content_type: str = "text"


class KnowledgeWorkspaceSaveTextRequest(BaseModel):
    project_id: str | None = None
    filename: str
    content: str


class KnowledgeWorkspaceSaveDocxRequest(BaseModel):
    project_id: str | None = None
    filename: str
    content: str
    source_relative_path: str | None = None
