from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.playbook import EvidenceLevel, RuleSeverity

ReviewMode = Literal["quick", "standard", "strict"]
OverallJudgement = Literal["通过", "有条件通过", "建议修改后再评审", "不建议采用"]
ResumeReason = Literal["tool_approval", "runtime_error", "cancelled_by_user"]


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
    execution_mode: Literal["deterministic", "llm"] = "deterministic"
    resolved_provider_id: str | None = None
    execution_note: str | None = None
    overall_judgement: OverallJudgement
    key_risks: list[str] = Field(default_factory=list)
    playbook_conflicts: list[str] = Field(default_factory=list)
    suggested_changes: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    model_provider: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewChatMessage(BaseModel):
    id: str
    role: Literal["system", "user", "assistant", "tool", "llm"]
    content: str
    runtime_id: str | None = None
    call_status: Literal["running", "success", "error"] | None = None
    provider_id: str | None = None
    model_name: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_arguments: str | None = None
    tool_result: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewSessionCreateRequest(BaseModel):
    playbook_id: str
    project_id: str | None = None
    model_provider_id: str | None = None
    mode: ReviewMode = "standard"
    opening_message: str | None = None


class ReviewSessionSendRequest(BaseModel):
    message: str


class ReviewReportAssistantRequest(BaseModel):
    session_id: str
    playbook_id: str
    markdown: str
    instruction: str


class ReviewReportAssistantResponse(BaseModel):
    reply: str
    suggested_markdown: str
    execution_mode: Literal["deterministic", "llm"] = "deterministic"
    resolved_provider_id: str | None = None
    execution_note: str | None = None


class ReviewSessionContextUsageBreakdown(BaseModel):
    messages_tokens: int = 0
    system_prompt_tokens: int = 0
    playbook_tokens: int = 0


class ReviewSessionContextUsage(BaseModel):
    model_name: str | None = None
    provider_name: str | None = None
    context_window: int = 0
    used_tokens: int = 0
    remaining_tokens: int = 0
    usage_percent: int = 0
    breakdown: ReviewSessionContextUsageBreakdown = Field(default_factory=ReviewSessionContextUsageBreakdown)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewConversationSession(BaseModel):
    id: str
    playbook_id: str
    project_id: str | None = None
    mode: ReviewMode
    status: Literal["idle", "running"] = "idle"
    resume_available: bool = False
    resume_reason: ResumeReason | None = None
    execution_mode: Literal["deterministic", "llm"] = "deterministic"
    resolved_provider_id: str | None = None
    execution_note: str | None = None
    latest_summary: str | None = None
    last_review: ReviewResponse | None = None
    context_usage: ReviewSessionContextUsage | None = None
    messages: list[ReviewChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("resume_reason", mode="before")
    @classmethod
    def _normalize_resume_reason(cls, value: str | None) -> str | None:
        legacy_mapping = {
            "interruption": "tool_approval",
            "error": "runtime_error",
            "cancelled": "cancelled_by_user",
        }
        if value is None:
            return None
        return legacy_mapping.get(value, value)
