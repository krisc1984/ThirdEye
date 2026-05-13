from __future__ import annotations

import shutil
import zipfile
from datetime import datetime, UTC
from pathlib import Path

from fastapi import UploadFile

from app.schemas.skill_management import ManagedSkillDetail, ManagedSkillSummary, SkillRegistryEntry
from app.services.storage import JsonStorage
from scripts.skill_agent import SkillLoader

SETTINGS_NAMESPACE = "settings"
SETTINGS_RECORD_ID = "skills-registry"


class SkillRegistryService:
    def __init__(self, storage: JsonStorage, skills_root: Path) -> None:
        self.storage = storage
        self.skills_root = skills_root.resolve()
        self.skills_root.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> list[ManagedSkillSummary]:
        loader = SkillLoader(self.skills_root)
        registry = self._load_registry(loader)
        items: list[ManagedSkillSummary] = []
        for name in loader.list_skills():
            skill = loader.skills.get(name, {})
            meta = skill.get("meta", {})
            entry = registry[name]
            items.append(
                ManagedSkillSummary(
                    name=name,
                    description=str(meta.get("description", "")),
                    enabled=entry.enabled,
                    source=entry.source,
                    installed_at=entry.installed_at,
                    path=str(skill.get("path", "")),
                )
            )
        return sorted(items, key=lambda item: item.name.lower())

    def get_skill(self, name: str) -> ManagedSkillDetail:
        loader = SkillLoader(self.skills_root)
        registry = self._load_registry(loader)
        skill = loader.skills.get(name)
        if skill is None:
            raise FileNotFoundError(name)
        meta = skill.get("meta", {})
        entry = registry[name]
        return ManagedSkillDetail(
            name=name,
            description=str(meta.get("description", "")),
            enabled=entry.enabled,
            source=entry.source,
            installed_at=entry.installed_at,
            path=str(skill.get("path", "")),
            content=str(skill.get("body", "")),
        )

    def enabled_skill_loader(self) -> SkillLoader:
        loader = SkillLoader(self.skills_root)
        registry = self._load_registry(loader)
        loader.skills = {
            name: payload
            for name, payload in loader.skills.items()
            if registry.get(name, SkillRegistryEntry(name=name)).enabled
        }
        return loader

    def set_enabled(self, name: str, enabled: bool) -> ManagedSkillDetail:
        loader = SkillLoader(self.skills_root)
        registry = self._load_registry(loader)
        if name not in loader.skills:
            raise FileNotFoundError(name)
        entry = registry[name]
        registry[name] = entry.model_copy(update={"enabled": enabled})
        self._save_registry(registry)
        return self.get_skill(name)

    async def install_zip(self, upload: UploadFile) -> ManagedSkillDetail:
        temp_dir = self.storage.root / "_tmp_skills"
        temp_dir.mkdir(parents=True, exist_ok=True)
        archive_path = temp_dir / (upload.filename or "skill.zip")
        data = await upload.read()
        archive_path.write_bytes(data)

        extract_dir = temp_dir / f"extract_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    member_path = (extract_dir / member.filename).resolve()
                    if extract_dir.resolve() not in member_path.parents and member_path != extract_dir.resolve():
                        raise ValueError("zip contains invalid path traversal entry")
                archive.extractall(extract_dir)

            skill_dir = self._locate_skill_dir(extract_dir)
            skill_name = skill_dir.name
            destination = self.skills_root / skill_name
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(skill_dir, destination)

            loader = SkillLoader(self.skills_root)
            registry = self._load_registry(loader)
            registry[skill_name] = SkillRegistryEntry(
                name=skill_name,
                enabled=True,
                source="uploaded",
                installed_at=datetime.now(UTC),
            )
            self._save_registry(registry)
            return self.get_skill(skill_name)
        finally:
            if archive_path.exists():
                archive_path.unlink()
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

    def delete_skill(self, name: str) -> None:
        loader = SkillLoader(self.skills_root)
        registry = self._load_registry(loader)
        if name not in loader.skills:
            raise FileNotFoundError(name)
        entry = registry[name]
        if entry.source != "uploaded":
            raise PermissionError("builtin skills cannot be deleted")
        skill_path = self.skills_root / name
        if skill_path.exists():
            shutil.rmtree(skill_path)
        registry.pop(name, None)
        self._save_registry(registry)

    def _locate_skill_dir(self, extract_dir: Path) -> Path:
        direct_skill = extract_dir / "SKILL.md"
        if direct_skill.exists():
            wrapped = extract_dir / extract_dir.name
            wrapped.mkdir(parents=True, exist_ok=True)
            shutil.copy2(direct_skill, wrapped / "SKILL.md")
            return wrapped

        candidates = [path.parent for path in extract_dir.rglob("SKILL.md")]
        if not candidates:
            raise ValueError("zip package does not contain SKILL.md")
        candidates.sort(key=lambda item: len(item.parts))
        return candidates[0]

    def _load_registry(self, loader: SkillLoader) -> dict[str, SkillRegistryEntry]:
        try:
            payload = self.storage.load_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID)
        except FileNotFoundError:
            payload = {"skills": []}
        raw_items = payload.get("skills", [])
        registry = {
            entry.name: entry
            for entry in (
                SkillRegistryEntry.model_validate(item)
                for item in raw_items
                if isinstance(item, dict)
            )
        }
        changed = False
        for name in loader.list_skills():
            if name not in registry:
                changed = True
                registry[name] = SkillRegistryEntry(name=name, enabled=True, source="builtin")
        missing = [name for name in registry if name not in loader.skills]
        for name in missing:
            changed = True
            registry.pop(name, None)
        if changed:
            self._save_registry(registry)
        return registry

    def _save_registry(self, registry: dict[str, SkillRegistryEntry]) -> None:
        payload = {
            "skills": [registry[name].model_dump(mode="json") for name in sorted(registry.keys())]
        }
        self.storage.save_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID, payload)

