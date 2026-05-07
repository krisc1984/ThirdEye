from datetime import datetime
from pathlib import Path
import re

from pydantic import BaseModel, Field, field_validator


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


class Project(BaseModel):
    id: str
    name: str
    root_path: Path
    slug: str
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_project_slug(cls, value: str) -> str:
        return normalize_slug(value)


class ProjectScanSummary(BaseModel):
    root_path: Path
    total_files: int = 0
    scanned_files: int = 0
    skipped_files: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    docs: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    entrypoint_candidates: list[str] = Field(default_factory=list)
    sensitive_warnings: list[str] = Field(default_factory=list)

