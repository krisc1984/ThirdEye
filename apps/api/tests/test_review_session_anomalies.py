from __future__ import annotations

from datetime import datetime

from app.schemas.observability import SessionEventRecord
from app.services.review_session_anomalies import ReviewSessionAnomalyService


def _tool_event(sequence: int, runtime_id: str, ok: bool) -> SessionEventRecord:
    return SessionEventRecord(
        event_id=f"evt_{sequence}",
        session_id="rs_123",
        sequence=sequence,
        event_type="tool_call_completed",
        timestamp=datetime.utcnow(),
        trace_id="trace_123",
        span_id=f"span_{sequence}",
        runtime_id=runtime_id,
        turn=1,
        payload={
            "tool_name": "read_file",
            "tool_call_id": runtime_id,
            "ok": ok,
        },
    )


def test_detect_repeated_tool_failure_anomaly() -> None:
    service = ReviewSessionAnomalyService()
    events = [
        _tool_event(1, "tool_call_1", ok=False),
        _tool_event(2, "tool_call_2", ok=False),
        _tool_event(3, "tool_call_3", ok=False),
    ]

    anomalies = service.detect(events)

    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.code == "repeated_tool_failure"
    assert anomaly.severity == "high"
    assert anomaly.related_runtime_ids == ["tool_call_1", "tool_call_2", "tool_call_3"]
