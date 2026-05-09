from __future__ import annotations

import json
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.distillation import run_playbook_distillation
from app.core.config import settings
from app.model_providers.llm_client import summarize_provider_error
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.playbook import PlaybookMetadata
from app.schemas.project import Project, ProjectScanSummary
from app.services.audit_log import AuditLogger
from app.services.evidence_builder import EvidenceBuilder
from app.services.playbook_generator import PlaybookGenerator
from app.services.project_scanner import ProjectScanner
from app.services.storage import JsonStorage, StorageError

router = APIRouter(prefix="/playbooks", tags=["playbooks"])

scanner = ProjectScanner()
evidence_builder = EvidenceBuilder()


class DistillPlaybookRequest(BaseModel):
    project_id: str
    model_provider_id: str | None = None


class PlaybookDetail(BaseModel):
    metadata: PlaybookMetadata
    skill_markdown: str
    project_summary: str
    rules: list[dict]
    evidence: list[dict]


@router.post("/distill", response_model=PlaybookMetadata)
def distill_playbook(request: DistillPlaybookRequest) -> PlaybookMetadata:
    storage = JsonStorage(settings.data_dir)
    generator = PlaybookGenerator(storage)
    try:
        project = _load_project(request.project_id)
        scan = scanner.scan(project.root_path)
        evidence = evidence_builder.build(project.id, scan)
        provider = _load_provider(request.model_provider_id) if request.model_provider_id else None
        try:
            artifacts = asyncio.run(
                run_playbook_distillation(
                    project,
                    scan,
                    evidence,
                    generator,
                    provider_config=provider,
                )
            )
        except Exception as error:
            if provider is None:
                raise
            artifacts = generator.generate(project, scan, evidence)
            artifacts.metadata.execution_mode = "deterministic"
            artifacts.metadata.resolved_provider_id = None
            artifacts.metadata.execution_note = f"LLM distillation failed and fell back to deterministic mode: {summarize_provider_error(error)}"
    except HTTPException:
        _log_distillation_event(request, success=False, artifact_paths=[], error_message="project or provider not found")
        raise
    generator.persist(artifacts)
    _log_distillation_event(
        request,
        success=True,
        artifact_paths=[
            str(artifacts.metadata.skill_path),
            str(artifacts.metadata.rules_path),
            str(artifacts.metadata.evidence_path),
        ],
        playbook_id=artifacts.metadata.id,
        error_message=artifacts.metadata.execution_note,
    )
    return artifacts.metadata


@router.get("", response_model=list[PlaybookMetadata])
def list_playbooks() -> list[PlaybookMetadata]:
    playbooks_root = settings.data_dir / "playbooks"
    if not playbooks_root.exists():
        return []
    records: list[PlaybookMetadata] = []
    for metadata_path in sorted(playbooks_root.glob("*/metadata.json")):
        records.append(PlaybookMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8")))
    return records


@router.get("/{playbook_id}", response_model=PlaybookDetail)
def get_playbook(playbook_id: str) -> PlaybookDetail:
    storage = JsonStorage(settings.data_dir)
    try:
        metadata = PlaybookMetadata.model_validate_json(
            storage.load_playbook_artifact(playbook_id, "metadata.json")
        )
        rules = json.loads(storage.load_playbook_artifact(playbook_id, "rules.json"))
        evidence_text = storage.load_playbook_artifact(playbook_id, "evidence.jsonl")
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="playbook not found") from error

    evidence = [json.loads(line) for line in evidence_text.splitlines() if line.strip()]
    return PlaybookDetail(
        metadata=metadata,
        skill_markdown=storage.load_playbook_artifact(playbook_id, "playbook.skill.md"),
        project_summary=storage.load_playbook_artifact(playbook_id, "project-summary.md"),
        rules=rules,
        evidence=evidence,
    )


@router.get("/{playbook_id}/artifact/{name}")
def get_playbook_artifact(playbook_id: str, name: str) -> dict[str, str]:
    storage = JsonStorage(settings.data_dir)
    allowed = {"playbook.skill.md", "project-summary.md", "rules.json", "evidence.jsonl", "metadata.json"}
    if name not in allowed:
        raise HTTPException(status_code=400, detail="unsupported artifact")
    try:
        content = storage.load_playbook_artifact(playbook_id, name)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="artifact not found") from error
    return {"name": name, "content": content}


@router.post("/{playbook_id}/regenerate", response_model=PlaybookMetadata)
def regenerate_playbook(playbook_id: str) -> PlaybookMetadata:
    storage = JsonStorage(settings.data_dir)
    try:
        metadata = PlaybookMetadata.model_validate_json(
            storage.load_playbook_artifact(playbook_id, "metadata.json")
        )
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="playbook not found") from error
    return distill_playbook(DistillPlaybookRequest(project_id=metadata.project_id))


def _load_project(project_id: str) -> Project:
    storage = JsonStorage(settings.data_dir)
    try:
        record = storage.load_json("projects", project_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="project not found") from error
    return Project.model_validate(record)


def _load_provider(provider_id: str) -> ModelProviderConfig:
    storage = JsonStorage(settings.data_dir)
    try:
        record = storage.load_json("model-providers", provider_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="model provider not found") from error
    return ModelProviderConfig.model_validate(record)


def _log_distillation_event(
    request: DistillPlaybookRequest,
    *,
    success: bool,
    artifact_paths: list[str],
    playbook_id: str | None = None,
    error_message: str | None = None,
) -> None:
    audit_logger = AuditLogger(settings.data_dir / "audit")
    audit_logger.log_event(
        {
            "workflow": "playbook_distillation",
            "project_id": request.project_id,
            "playbook_id": playbook_id,
            "provider_id": request.model_provider_id,
            "success": success,
            "artifact_paths": artifact_paths,
            "error": error_message,
        }
    )
