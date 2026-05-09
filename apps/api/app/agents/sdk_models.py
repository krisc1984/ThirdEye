from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.playbook import RuleSeverity
from app.schemas.review import OverallJudgement


class ReviewFindingOutput(BaseModel):
    severity: RuleSeverity
    confidence: float = Field(ge=0, le=1)
    evidence_level: str
    rule_id: str | None = None
    problem: str
    impact: str
    suggested_change: str
    required_validation: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewAgentOutput(BaseModel):
    overall_judgement: OverallJudgement
    key_risks: list[str] = Field(default_factory=list)
    playbook_conflicts: list[str] = Field(default_factory=list)
    suggested_changes: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    findings: list[ReviewFindingOutput] = Field(default_factory=list)


class DistilledRuleOutput(BaseModel):
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


class DistillationAgentOutput(BaseModel):
    rules: list[DistilledRuleOutput] = Field(default_factory=list)
    skill_markdown: str | None = None
    execution_note: str | None = None
