from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.playbook import EvidenceLevel, RuleSeverity

ReviewMode = Literal["quick", "standard", "strict"]
OverallJudgement = Literal["通过", "有条件通过", "建议修改后再评审", "不建议采用"]
ResumeReason = Literal["tool_approval", "runtime_error", "cancelled_by_user"]
CodeChangeStatus = Literal["added", "modified", "deleted", "renamed", "copied", "unknown"]
CodeFindingCategory = Literal[
    "security",
    "correctness",
    "testing",
    "maintainability",
    "performance",
    "observability",
]


class ReviewRequest(BaseModel):
    playbook_id: str
    proposal: str
    mode: ReviewMode = "standard"
    model_provider_id: str | None = None


class CodeReviewChangedFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    old_path: str | None = Field(default=None, max_length=500)
    status: CodeChangeStatus = "modified"
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    patch: str = Field(default="", max_length=200_000)
    language: str | None = Field(default=None, max_length=60)

    @field_validator("path", "old_path", mode="before")
    @classmethod
    def _normalize_relative_path(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip().replace("\\", "/")
        if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
            raise ValueError("code review paths must be relative project paths")
        return normalized


class CodeReviewRequest(BaseModel):
    playbook_id: str
    project_id: str | None = None
    agent_id: str | None = "code-review-agent"
    mode: ReviewMode = "strict"
    model_provider_id: str | None = None
    base_ref: str | None = Field(default=None, max_length=120)
    head_ref: str | None = Field(default=None, max_length=120)
    diff_text: str | None = Field(default=None, max_length=500_000)
    changed_files: list[CodeReviewChangedFile] = Field(default_factory=list)
    focus: list[str] = Field(default_factory=list, max_length=12)
    reviewer_note: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _require_change_source(self) -> "CodeReviewRequest":
        if self.changed_files or (self.diff_text and self.diff_text.strip()) or self.project_id:
            return self
        raise ValueError("provide changed_files, diff_text, or project_id")


class CodeReviewChangeListRequest(BaseModel):
    project_id: str
    base_ref: str | None = Field(default=None, max_length=120)
    head_ref: str | None = Field(default=None, max_length=120)
    paths: list[str] = Field(default_factory=list, max_length=80)
    include_patch: bool = True

    @field_validator("paths", mode="before")
    @classmethod
    def _normalize_paths(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            path = item.strip().replace("\\", "/")
            if path and not path.startswith("/") and ".." not in path.split("/"):
                normalized.append(path)
        return normalized


class CodeReviewBranchListRequest(BaseModel):
    project_id: str


class CodeReviewBranchListResponse(BaseModel):
    project_id: str
    root_path: str
    current_branch: str | None = None
    branches: list[str]


class CodeReviewProjectFile(BaseModel):
    path: str
    name: str
    directory: str
    language: str | None = None
    size_bytes: int = Field(default=0, ge=0)
    updated_at: datetime


class CodeReviewProjectFileListRequest(BaseModel):
    project_id: str
    query: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=800, ge=1, le=5000)


class CodeReviewProjectFileListResponse(BaseModel):
    project_id: str
    root_path: str
    files: list[CodeReviewProjectFile]
    total_files: int = 0
    truncated: bool = False


class CodeReviewFileDiffRequest(BaseModel):
    project_id: str
    path: str = Field(min_length=1, max_length=500)
    base_ref: str | None = Field(default=None, max_length=120)
    head_ref: str | None = Field(default=None, max_length=120)
    include_content: bool = True

    @field_validator("path", mode="before")
    @classmethod
    def _normalize_path(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip().replace("\\", "/")
        if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
            raise ValueError("code review paths must be relative project paths")
        return normalized


class CodeReviewFileDiffResponse(BaseModel):
    project_id: str
    root_path: str
    path: str
    base_ref: str | None = None
    head_ref: str | None = None
    status: CodeChangeStatus = "unknown"
    additions: int = 0
    deletions: int = 0
    patch: str = ""
    language: str | None = None
    content: str = ""
    content_truncated: bool = False


class CodeReviewFileFinding(BaseModel):
    file_path: str
    severity: RuleSeverity
    category: CodeFindingCategory
    title: str
    detail: str
    suggestion: str
    line: int | None = Field(default=None, ge=1)
    confidence: float = Field(default=0.74, ge=0, le=1)


class CodeReviewChangeListResponse(BaseModel):
    project_id: str
    root_path: str
    base_ref: str | None = None
    head_ref: str | None = None
    changed_files: list[CodeReviewChangedFile]
    total_files: int = 0
    total_additions: int = 0
    total_deletions: int = 0


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


class CodeReviewResponse(BaseModel):
    id: str
    review: ReviewResponse
    changed_files: list[CodeReviewChangedFile]
    file_findings: list[CodeReviewFileFinding] = Field(default_factory=list)
    summary_markdown: str
    total_files: int = 0
    total_additions: int = 0
    total_deletions: int = 0
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
    agent_id: str | None = None
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
    agent_id: str | None = None
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
