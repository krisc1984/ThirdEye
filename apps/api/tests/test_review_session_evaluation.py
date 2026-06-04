from __future__ import annotations

from app.schemas.observability import SessionAnomalyRecord
from app.services.review_session_observability import ReviewSessionObservabilityService


def test_build_evaluation_success_without_high_severity_anomalies(tmp_path) -> None:
    service = ReviewSessionObservabilityService(tmp_path)

    evaluation = service.build_evaluation(
        session_id="rs_123",
        event_id="evt_done",
        final_assistant_reply="这是最终回复",
        anomalies=[],
        tool_error_count=0,
        tool_call_count=2,
        terminal_status="completed",
        resume_count=0,
    )

    assert evaluation.grade == "success"


def test_build_evaluation_failed_when_no_reply_and_high_anomaly(tmp_path) -> None:
    service = ReviewSessionObservabilityService(tmp_path)
    anomaly = SessionAnomalyRecord(
        anomaly_id="an_1",
        session_id="rs_123",
        event_id="evt_1",
        code="repeated_tool_failure",
        severity="high",
        title="同一工具连续失败",
        summary="连续失败 3 次",
    )

    evaluation = service.build_evaluation(
        session_id="rs_123",
        event_id="evt_done",
        final_assistant_reply="",
        anomalies=[anomaly],
        tool_error_count=3,
        tool_call_count=3,
        terminal_status="failed",
        resume_count=1,
    )

    assert evaluation.grade == "failed"
