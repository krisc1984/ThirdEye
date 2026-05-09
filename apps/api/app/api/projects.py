from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.project import Project, ProjectScanSummary, normalize_slug
from app.services.project_scanner import ProjectScanner
from app.services.storage import JsonStorage

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectScanRequest(BaseModel):
    root_path: Path
    extra_ignore_patterns: list[str] = Field(default_factory=list)


class CreateProjectRequest(ProjectScanRequest):
    name: str | None = None


scanner = ProjectScanner()


def get_storage() -> JsonStorage:
    return JsonStorage(settings.data_dir)


@router.post("/scan", response_model=ProjectScanSummary)
def scan_project(request: ProjectScanRequest) -> ProjectScanSummary:
    try:
        return scanner.scan(request.root_path, request.extra_ignore_patterns)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("", response_model=Project)
def create_project(request: CreateProjectRequest) -> Project:
    summary = scan_project(request)
    root = request.root_path.resolve()
    name = request.name or root.name
    project = Project(
        id=f"proj_{uuid4().hex[:12]}",
        name=name,
        root_path=root,
        slug=normalize_slug(name),
        languages=sorted(summary.languages.keys()),
        frameworks=[],
        created_at=datetime.utcnow(),
    )
    payload = project.model_dump(mode="json")
    payload["latest_scan"] = summary.model_dump(mode="json")
    get_storage().save_json("projects", project.id, payload)
    return project


@router.get("", response_model=list[Project])
def list_projects() -> list[Project]:
    return [Project.model_validate(record) for record in get_storage().list_json("projects")]


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    try:
        record = get_storage().load_json("projects", project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="project not found") from error
    return Project.model_validate(record)


@router.delete("/{project_id}")
def delete_project(project_id: str) -> dict[str, str]:
    try:
        get_storage().delete_json("projects", project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="project not found") from error
    return {"status": "deleted", "project_id": project_id}
