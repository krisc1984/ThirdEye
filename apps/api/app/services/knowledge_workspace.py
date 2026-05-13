from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, UploadFile

from app.schemas.knowledge_workspace import (
    KnowledgeWorkspaceBinding,
    KnowledgeWorkspaceFileContent,
    KnowledgeWorkspaceItem,
    KnowledgeWorkspaceListing,
    KnowledgeWorkspaceSettings,
    KnowledgeWorkspaceUploadResult,
)
from app.schemas.project import Project
from app.services.storage import JsonStorage, StorageError


SETTINGS_NAMESPACE = "settings"
SETTINGS_RECORD_ID = "knowledge-workspace"
MAX_LIST_ITEMS = 500
MAX_UPLOAD_FILE_BYTES = 25 * 1024 * 1024
MAX_TEXT_FILE_BYTES = 512 * 1024
TEXT_FILE_EXTENSIONS = {".md", ".markdown", ".txt"}


class KnowledgeWorkspaceService:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def load_settings(self) -> KnowledgeWorkspaceSettings:
        try:
            payload = self.storage.load_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID)
        except (FileNotFoundError, StorageError):
            return KnowledgeWorkspaceSettings()
        return KnowledgeWorkspaceSettings.model_validate(payload)

    def save_settings(self, root_path: Path | None) -> KnowledgeWorkspaceSettings:
        normalized = self._normalize_optional_root(root_path)
        settings = KnowledgeWorkspaceSettings(default_root_path=normalized)
        self.storage.save_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID, settings.model_dump(mode="json"))
        return settings

    def load_project(self, project_id: str) -> dict:
        try:
            return self.storage.load_json("projects", project_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail="project not found") from error

    def save_project_knowledge_root(self, project_id: str, root_path: Path | None) -> KnowledgeWorkspaceBinding:
        payload = self.load_project(project_id)
        normalized = self._normalize_optional_root(root_path)
        payload["knowledge_root_path"] = str(normalized) if normalized is not None else None
        self.storage.save_json("projects", project_id, payload)
        return self.get_project_binding(project_id)

    def get_project_binding(self, project_id: str) -> KnowledgeWorkspaceBinding:
        payload = self.load_project(project_id)
        project = Project.model_validate(payload)
        settings = self.load_settings()
        effective_root = project.knowledge_root_path or settings.default_root_path
        if project.knowledge_root_path is not None:
            scope = "project"
        elif settings.default_root_path is not None:
            scope = "global"
        else:
            scope = "unconfigured"
        return KnowledgeWorkspaceBinding(
            project_id=project.id,
            default_root_path=settings.default_root_path,
            project_root_path=project.knowledge_root_path,
            effective_root_path=effective_root,
            scope=scope,
            exists=bool(effective_root and effective_root.exists() and effective_root.is_dir()),
        )

    def list_files(self, *, project_id: str | None, query: str = "") -> KnowledgeWorkspaceListing:
        binding = self._resolve_binding(project_id)
        root_path = binding.effective_root_path
        if root_path is None:
            return KnowledgeWorkspaceListing(root_path=None, query=query, items=[], total_items=0)
        if not root_path.exists() or not root_path.is_dir():
            raise HTTPException(status_code=400, detail="knowledge workspace path does not exist or is not a directory")

        normalized_query = query.strip().lower()
        items: list[KnowledgeWorkspaceItem] = []
        paths = sorted(root_path.rglob("*"), key=lambda item: (item.is_file(), str(item).lower()))
        for path in paths:
            relative_path = str(path.relative_to(root_path)).replace("\\", "/")
            haystack = relative_path.lower()
            if normalized_query and normalized_query not in haystack:
                continue
            stat = path.stat()
            items.append(
                KnowledgeWorkspaceItem(
                    name=path.name,
                    relative_path=relative_path,
                    path=path,
                    is_dir=path.is_dir(),
                    size_bytes=0 if path.is_dir() else stat.st_size,
                    updated_at=datetime.fromtimestamp(stat.st_mtime),
                )
            )
            if len(items) >= MAX_LIST_ITEMS:
                break

        return KnowledgeWorkspaceListing(
            root_path=root_path,
            query=query,
            items=items,
            total_items=len(items),
        )

    async def upload_files(self, *, project_id: str | None, files: Iterable[UploadFile]) -> KnowledgeWorkspaceUploadResult:
        binding = self._resolve_binding(project_id)
        root_path = binding.effective_root_path
        if root_path is None:
            raise HTTPException(status_code=400, detail="knowledge workspace path is not configured")
        if not root_path.exists() or not root_path.is_dir():
            raise HTTPException(status_code=400, detail="knowledge workspace path does not exist or is not a directory")

        uploaded_files: list[str] = []
        for file in files:
            filename = Path(file.filename or "").name.strip()
            if not filename:
                continue
            target_path = (root_path / filename).resolve()
            if target_path.parent != root_path.resolve():
                raise HTTPException(status_code=400, detail="invalid upload filename")
            content = await file.read()
            if len(content) > MAX_UPLOAD_FILE_BYTES:
                raise HTTPException(status_code=400, detail=f"file too large: {filename}")
            target_path.write_bytes(content)
            uploaded_files.append(filename)
        return KnowledgeWorkspaceUploadResult(root_path=root_path, uploaded_files=uploaded_files)

    def save_text_file(self, *, project_id: str | None, filename: str, content: str) -> KnowledgeWorkspaceUploadResult:
        binding = self._resolve_binding(project_id)
        root_path = binding.effective_root_path
        if root_path is None:
            raise HTTPException(status_code=400, detail="knowledge workspace path is not configured")
        if not root_path.exists() or not root_path.is_dir():
            raise HTTPException(status_code=400, detail="knowledge workspace path does not exist or is not a directory")

        normalized_name = Path(filename).name.strip()
        if not normalized_name:
            raise HTTPException(status_code=400, detail="invalid filename")
        if not normalized_name.lower().endswith(".md"):
            raise HTTPException(status_code=400, detail="only markdown files are supported")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_TEXT_FILE_BYTES:
            raise HTTPException(status_code=400, detail="markdown content too large")

        target_path = (root_path / normalized_name).resolve()
        if target_path.parent != root_path.resolve():
            raise HTTPException(status_code=400, detail="invalid filename")
        target_path.write_text(content, encoding="utf-8")
        return KnowledgeWorkspaceUploadResult(root_path=root_path, uploaded_files=[normalized_name])

    def read_text_file(self, *, project_id: str | None, relative_path: str) -> KnowledgeWorkspaceFileContent:
        binding = self._resolve_binding(project_id)
        root_path = binding.effective_root_path
        if root_path is None:
            raise HTTPException(status_code=400, detail="knowledge workspace path is not configured")
        if not root_path.exists() or not root_path.is_dir():
            raise HTTPException(status_code=400, detail="knowledge workspace path does not exist or is not a directory")

        normalized_relative = relative_path.strip().replace("\\", "/").lstrip("/")
        if not normalized_relative:
            raise HTTPException(status_code=400, detail="relative_path is required")

        root_resolved = root_path.resolve()
        target_path = (root_resolved / normalized_relative).resolve()
        try:
            target_path.relative_to(root_resolved)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="invalid relative_path") from error
        if not target_path.exists() or not target_path.is_file():
            raise HTTPException(status_code=404, detail="knowledge workspace file not found")
        if target_path.suffix.lower() not in TEXT_FILE_EXTENSIONS:
            raise HTTPException(status_code=400, detail="only text and markdown files are supported")

        raw = target_path.read_bytes()
        truncated = len(raw) > MAX_TEXT_FILE_BYTES
        content = raw[:MAX_TEXT_FILE_BYTES].decode("utf-8", errors="replace")
        return KnowledgeWorkspaceFileContent(
            root_path=root_resolved,
            relative_path=normalized_relative,
            content=content,
            truncated=truncated,
        )

    def pick_folder(self) -> Path:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"folder picker unavailable: {error}") from error

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="选择资料区文件夹")
        root.destroy()
        if not selected:
            raise HTTPException(status_code=400, detail="folder selection cancelled")
        path = Path(selected).resolve()
        if not path.exists() or not path.is_dir():
            raise HTTPException(status_code=400, detail="selected folder does not exist")
        return path

    def _resolve_binding(self, project_id: str | None) -> KnowledgeWorkspaceBinding:
        if project_id:
            return self.get_project_binding(project_id)
        settings = self.load_settings()
        root_path = settings.default_root_path
        return KnowledgeWorkspaceBinding(
            project_id=None,
            default_root_path=settings.default_root_path,
            project_root_path=None,
            effective_root_path=root_path,
            scope="global" if root_path is not None else "unconfigured",
            exists=bool(root_path and root_path.exists() and root_path.is_dir()),
        )

    def _normalize_optional_root(self, root_path: Path | None) -> Path | None:
        if root_path is None:
            return None
        normalized = root_path.resolve()
        if not normalized.exists():
            raise HTTPException(status_code=400, detail="knowledge workspace path does not exist")
        if not normalized.is_dir():
            raise HTTPException(status_code=400, detail="knowledge workspace path must be a directory")
        return normalized
