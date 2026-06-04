from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.observability import (
    ObservabilityTimelineEntry,
    SessionAnomalyRecord,
    SessionEvaluationRecord,
    SessionEventRecord,
    SessionTaskRecord,
)


def test_session_event_record_accepts_known_event_type() -> None:
    event = SessionEventRecord(
        event_id="evt_123",
        session_id="rs_123",
        sequence=1,
        event_type="session_started",
        timestamp=datetime.utcnow(),
        trace_id="trace_123",
        span_id="span_123",
        parent_span_id=None,
        runtime_id=None,
        turn=None,
        payload={"status": "idle"},
    )

    assert event.event_type == "session_started"


def test_session_event_record_rejects_unknown_event_type() -> None:
    with pytest.raises(ValidationError):
        SessionEventRecord(
            event_id="evt_123",
            session_id="rs_123",
            sequence=1,
            event_type="something_else",
            timestamp=datetime.utcnow(),
            trace_id="trace_123",
            span_id="span_123",
            payload={},
        )


def test_session_task_record_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        SessionTaskRecord(
            task_id="task_123",
            session_id="rs_123",
            title="root",
            kind="unknown",
            status="running",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )


def test_session_task_record_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        SessionTaskRecord(
            task_id="task_123",
            session_id="rs_123",
            title="root",
            kind="session",
            status="done",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )


def test_session_anomaly_record_rejects_unknown_severity() -> None:
    with pytest.raises(ValidationError):
        SessionAnomalyRecord(
            anomaly_id="an_123",
            session_id="rs_123",
            event_id="evt_123",
            code="repeated_tool_failure",
            severity="critical",
            title="bad",
            summary="bad",
            detected_at=datetime.utcnow(),
        )


def test_session_evaluation_record_rejects_unknown_grade() -> None:
    with pytest.raises(ValidationError):
        SessionEvaluationRecord(
            evaluation_id="eval_123",
            session_id="rs_123",
            event_id="evt_123",
            grade="warning",
            summary="summary",
            recorded_at=datetime.utcnow(),
            signals={"has_final_reply": True},
        )


def test_timeline_entry_accepts_public_render_shape() -> None:
    entry = ObservabilityTimelineEntry(
        event_id="evt_123",
        sequence=1,
        event_type="tool_call_completed",
        timestamp=datetime.utcnow(),
        title="工具调用完成",
        summary="write_file_chunk 调用完成",
        status="success",
        payload={"tool_name": "write_file_chunk"},
    )

    assert entry.status == "success"
