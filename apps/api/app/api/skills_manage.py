from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.skill_management import ManagedSkillDetail, ManagedSkillSummary, SkillToggleRequest, SkillUploadResult
from app.services.skill_registry import SkillRegistryService
from app.services.storage import JsonStorage

router = APIRouter(prefix="/skills/manage", tags=["skills-manage"])
API_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = API_ROOT / "skills"


def get_service() -> SkillRegistryService:
    return SkillRegistryService(JsonStorage(settings.data_dir), SKILLS_ROOT)


@router.get("", response_model=list[ManagedSkillSummary])
def list_managed_skills() -> list[ManagedSkillSummary]:
    return get_service().list_skills()


@router.get("/{name}", response_model=ManagedSkillDetail)
def get_managed_skill(name: str) -> ManagedSkillDetail:
    try:
        return get_service().get_skill(name)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="skill not found") from error


@router.post("/upload", response_model=SkillUploadResult)
async def upload_skill_zip(file: UploadFile = File(...)) -> SkillUploadResult:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="only zip packages are supported")
    try:
        installed = await get_service().install_zip(file)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return SkillUploadResult(installed=installed)


@router.post("/{name}/toggle", response_model=ManagedSkillDetail)
def toggle_skill(name: str, request: SkillToggleRequest) -> ManagedSkillDetail:
    try:
        return get_service().set_enabled(name, request.enabled)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="skill not found") from error


@router.delete("/{name}")
def delete_skill(name: str) -> dict[str, str]:
    try:
        get_service().delete_skill(name)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="skill not found") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"status": "deleted", "name": name}
