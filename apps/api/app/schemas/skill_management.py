from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SkillSource = Literal["builtin", "uploaded"]


class SkillRegistryEntry(BaseModel):
    name: str
    enabled: bool = True
    source: SkillSource = "builtin"
    installed_at: datetime | None = None


class ManagedSkillSummary(BaseModel):
    name: str
    description: str = ""
    enabled: bool = True
    source: SkillSource = "builtin"
    installed_at: datetime | None = None
    path: str


class ManagedSkillDetail(ManagedSkillSummary):
    content: str = ""


class SkillToggleRequest(BaseModel):
    enabled: bool


class SkillUploadResult(BaseModel):
    installed: ManagedSkillDetail

