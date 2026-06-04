from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.observability import (
    ObservabilityMetrics,
    ObservabilitySessionSummary,
    ObservabilityTimelineEntry,
    SessionEventRecord,
    SessionTaskRecord,
)
from app.services.review_session_event_log import ReviewSessionEventLog
from app.services.review_session_tasks import ReviewSessionTaskService
from app.services.storage import JsonStorage

router = APIRouter(prefix="/observability", tags=["observability"])


def _build_session_summary(session_record: dict[str, object], events: list[SessionEventRecord]) -> ObservabilitySessionSummary:
    anomaly_count = sum(1 for event in events if event.event_type == "anomaly_detected")
    evaluation_event = next(
        (event for event in reversed(events) if event.event_type == "evaluation_recorded"),
        None,
    )
    return ObservabilitySessionSummary(
        session_id=str(session_record.get("id") or ""),
        playbook_id=session_record.get("playbook_id"),
        status=session_record.get("status"),
        provider_id=session_record.get("resolved_provider_id"),
        evaluation_grade=evaluation_event.payload.get("grade") if evaluation_event else None,
        anomaly_count=anomaly_count,
        last_updated_at=session_record.get("updated_at"),
    )


def _timeline_entry_from_event(event: SessionEventRecord) -> ObservabilityTimelineEntry:
    title_map = {
        "session_started": "会话开始",
        "user_message": "用户消息",
        "assistant_message": "助手回复",
        "session_status_changed": "状态更新",
        "model_call_started": "模型调用开始",
        "model_call_completed": "模型调用完成",
        "tool_call_started": "工具调用开始",
        "tool_call_completed": "工具调用完成",
        "session_completed": "会话完成",
    }
    summary_map = {
        "session_started": "已创建 review session",
        "user_message": str(event.payload.get("content") or "收到用户消息"),
        "assistant_message": str(event.payload.get("content") or "生成助手回复"),
        "session_status_changed": str(event.payload.get("status") or "状态已更新"),
        "model_call_started": str(event.payload.get("model") or "模型调用中"),
        "model_call_completed": str(event.payload.get("result_raw") or "模型调用完成"),
        "tool_call_started": str(event.payload.get("tool_name") or "工具调用中"),
        "tool_call_completed": str(event.payload.get("tool_name") or "工具调用完成"),
        "session_completed": str(event.payload.get("latest_summary") or "会话完成"),
    }
    status = "info"
    if event.event_type in {"model_call_started", "tool_call_started"}:
        status = "running"
    elif event.event_type in {"model_call_completed", "tool_call_completed", "session_completed"}:
        status = "success"

    return ObservabilityTimelineEntry(
        event_id=event.event_id,
        sequence=event.sequence,
        event_type=event.event_type,
        timestamp=event.timestamp,
        title=title_map.get(event.event_type, event.event_type),
        summary=summary_map.get(event.event_type, event.event_type),
        status=status,
        payload=event.payload,
    )


@router.get("/sessions", response_model=list[ObservabilitySessionSummary])
def list_observability_sessions() -> list[ObservabilitySessionSummary]:
    storage = JsonStorage(settings.data_dir)
    event_log = ReviewSessionEventLog(settings.data_dir / "review-session-events")
    summaries: list[ObservabilitySessionSummary] = []

    for session_record in storage.list_json("review-sessions"):
        session_id = str(session_record.get("id") or "")
        if not session_id:
            continue
        if not event_log.event_log_path(session_id).exists():
            continue
        events = event_log.list_events(session_id)
        summaries.append(_build_session_summary(session_record, events))

    return summaries


@router.get("/sessions/{session_id}", response_model=ObservabilitySessionSummary)
def get_observability_session_detail(session_id: str) -> ObservabilitySessionSummary:
    storage = JsonStorage(settings.data_dir)
    session_record = storage.load_json("review-sessions", session_id)
    event_log = ReviewSessionEventLog(settings.data_dir / "review-session-events")
    events = event_log.list_events(session_id)
    return _build_session_summary(session_record, events)


@router.get("/sessions/{session_id}/timeline", response_model=list[ObservabilityTimelineEntry])
def get_observability_timeline(session_id: str) -> list[ObservabilityTimelineEntry]:
    event_log = ReviewSessionEventLog(settings.data_dir / "review-session-events")
    events = event_log.list_events(session_id)
    return [_timeline_entry_from_event(event) for event in events]


@router.get("/sessions/{session_id}/events", response_model=list[SessionEventRecord])
def get_observability_events(session_id: str) -> list[SessionEventRecord]:
    event_log = ReviewSessionEventLog(settings.data_dir / "review-session-events")
    return event_log.list_events(session_id)


@router.get("/sessions/{session_id}/tasks", response_model=list[SessionTaskRecord])
def get_observability_tasks(session_id: str) -> list[SessionTaskRecord]:
    event_log = ReviewSessionEventLog(settings.data_dir / "review-session-events")
    events = event_log.list_events(session_id)
    return ReviewSessionTaskService().build_tasks(events)


@router.get("/sessions/{session_id}/metrics", response_model=ObservabilityMetrics)
def get_observability_metrics(session_id: str) -> ObservabilityMetrics:
    event_log = ReviewSessionEventLog(settings.data_dir / "review-session-events")
    events = event_log.list_events(session_id)
    llm_turn_count = sum(1 for event in events if event.event_type == "model_call_started")
    tool_call_count = sum(1 for event in events if event.event_type == "tool_call_started")
    tool_error_count = sum(
        1
        for event in events
        if event.event_type == "tool_call_completed" and not bool(event.payload.get("ok", True))
    )
    return ObservabilityMetrics(
        llm_turn_count=llm_turn_count,
        tool_call_count=tool_call_count,
        tool_error_count=tool_error_count,
        tool_error_rate=(tool_error_count / tool_call_count) if tool_call_count else 0.0,
    )
