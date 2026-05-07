from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.playbook import EvidenceLevel, RuleSeverity

ReviewMode = Literal["quick", "standard", "strict"]
OverallJudgement = Literal["通过", "有条件通过", "建议修改后再评审", "不建议采用"]


class ReviewRequest(BaseModel):
    playbook_id: str
    proposal: str
    mode: ReviewMode = "standard"
    model_provider_id: str | None = None


class ReviewFinding(BaseModel):
    severity: RuleSeverity
    confidence: float = Field(ge=0, le=1)
    evidence_level: EvidenceLevel
    rule_id: str | None = None
    problem: str
    impact: str
    suggested_change: str
    required_validation: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    id: str
    playbook_id: str
    mode: ReviewMode
    input: str
    overall_judgement: OverallJudgement
    key_risks: list[str] = Field(default_factory=list)
    playbook_conflicts: list[str] = Field(default_factory=list)
    suggested_changes: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    model_provider: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

