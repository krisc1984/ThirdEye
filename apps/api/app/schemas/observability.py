from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ObservabilityEventType = Literal[
    "session_started",
    "user_message",
    "assistant_message",
    "model_call_started",
    "model_call_completed",
    "tool_call_started",
    "tool_call_completed",
    "session_status_changed",
    "task_created",
    "task_status_changed",
    "anomaly_detected",
    "evaluation_recorded",
    "session_completed",
    "decision_recorded",
    "replay_requested",
    "replay_compared",
    "task_waiting_child",
    "delegated_agent_started",
    "delegated_agent_completed",
]
SessionTaskKind = Literal["session", "llm_turn", "tool_call", "delegated_agent"]
SessionTaskStatus = Literal["pending", "planning", "running", "waiting_child", "succeeded", "failed", "cancelled"]
AnomalySeverity = Literal["low", "medium", "high"]
EvaluationGrade = Literal["success", "partial_success", "failed"]
TimelineStatus = Literal["running", "success", "error", "info"]


class SessionEventRecord(BaseModel):
    event_id: str
    session_id: str
    sequence: int = Field(ge=1)
    event_type: ObservabilityEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    runtime_id: str | None = None
    turn: int | None = Field(default=None, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class SessionTaskRecord(BaseModel):
    task_id: str
    session_id: str
    parent_task_id: str | None = None
    source_event_id: str | None = None
    title: str
    kind: SessionTaskKind
    status: SessionTaskStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str | None = None


class SessionAnomalyRecord(BaseModel):
    anomaly_id: str
    session_id: str
    event_id: str
    code: str
    severity: AnomalySeverity
    title: str
    summary: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    related_runtime_ids: list[str] = Field(default_factory=list)
    related_task_ids: list[str] = Field(default_factory=list)


class SessionEvaluationRecord(BaseModel):
    evaluation_id: str
    session_id: str
    event_id: str
    grade: EvaluationGrade
    summary: str
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    signals: dict[str, Any] = Field(default_factory=dict)


class ObservabilityMetrics(BaseModel):
    llm_turn_count: int = 0
    tool_call_count: int = 0
    tool_error_count: int = 0
    tool_error_rate: float = 0.0
    session_duration_ms: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    estimated_total_tokens: int = 0
    max_context_usage_percent: int = 0
    resume_count: int = 0
    avg_model_duration_ms: float = 0.0
    p95_model_duration_ms: float = 0.0
    avg_tool_duration_ms: float = 0.0
    slowest_tool_call: str | None = None


class ObservabilitySessionSummary(BaseModel):
    session_id: str
    playbook_id: str | None = None
    status: str | None = None
    provider_id: str | None = None
    model_name: str | None = None
    evaluation_grade: EvaluationGrade | None = None
    anomaly_count: int = 0
    last_updated_at: datetime | None = None
    metrics: ObservabilityMetrics = Field(default_factory=ObservabilityMetrics)


class ObservabilityTimelineEntry(BaseModel):
    event_id: str
    sequence: int = Field(ge=1)
    event_type: ObservabilityEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    title: str
    summary: str
    status: TimelineStatus = "info"
    payload: dict[str, Any] = Field(default_factory=dict)
