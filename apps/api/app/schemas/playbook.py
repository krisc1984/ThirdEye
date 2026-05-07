from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EvidenceLevel = Literal["confirmed", "inferred", "preference", "unknown"]
RuleSeverity = Literal["blocker", "major", "minor", "nit"]
PlaybookStatus = Literal["draft", "active", "archived"]


class EvidenceItem(BaseModel):
    id: str
    project_id: str
    source_type: Literal["code", "doc", "test", "config", "example"]
    path: str
    symbol: str | None = None
    summary: str
    evidence_level: EvidenceLevel
    metadata: dict[str, str] = Field(default_factory=dict)


class PlaybookRule(BaseModel):
    id: str
    category: str
    name: str
    default_severity: RuleSeverity
    applicability: list[str] = Field(default_factory=list)
    description: str
    evidence_ids: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    review_prompts: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_must_not_be_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("evidence ids must not be blank")
        return value


class PlaybookMetadata(BaseModel):
    id: str
    project_id: str
    name: str
    version: str
    status: PlaybookStatus = "draft"
    skill_path: Path
    rules_path: Path
    evidence_path: Path
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        parts = value.split(".")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise ValueError("version must use semantic version format, e.g. 1.0.0")
        return value

