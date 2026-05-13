from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings
from app.services.skill_registry import SkillRegistryService
from app.services.storage import JsonStorage
from scripts.skill_agent import SkillLoader

router = APIRouter(prefix="/skills", tags=["skills"])
API_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = API_ROOT / "skills"


@router.get("")
def list_skills() -> list[dict[str, str]]:
    service = SkillRegistryService(JsonStorage(settings.data_dir), SKILLS_ROOT)
    loader = service.enabled_skill_loader()
    skills: list[dict[str, str]] = []
    for name in loader.list_skills():
        meta = loader.skills.get(name, {}).get("meta", {})
        skills.append(
            {
                "name": name,
                "description": str(meta.get("description", "")),
            }
        )
    return skills
