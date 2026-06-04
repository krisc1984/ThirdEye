from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.observability import SessionAnomalyRecord, SessionEvaluationRecord, SessionEventRecord
from app.services.review_session_anomalies import ReviewSessionAnomalyService
from app.services.review_session_event_log import ReviewSessionEventLog


class ReviewSessionObservabilityService:
    def __init__(self, data_root: Path | str) -> None:
        self.event_log = ReviewSessionEventLog(Path(data_root) / "review-session-events")

    def append_event(
        self,
        session_id: str,
        *,
        event_type: str,
        payload: dict[str, object] | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        runtime_id: str | None = None,
        turn: int | None = None,
    ) -> SessionEventRecord:
        event = SessionEventRecord(
            event_id=f"evt_{uuid4().hex[:12]}",
            session_id=session_id,
            sequence=self.event_log.next_sequence(session_id),
            event_type=event_type,  # type: ignore[arg-type]
            timestamp=datetime.utcnow(),
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            runtime_id=runtime_id,
            turn=turn,
            payload=payload or {},
        )
        self.event_log.append_event(session_id, event)
        return event

    def build_evaluation(
        self,
        *,
        session_id: str,
        event_id: str,
        final_assistant_reply: str,
        anomalies: list[SessionAnomalyRecord],
        tool_error_count: int,
        tool_call_count: int,
        terminal_status: str,
        resume_count: int,
    ) -> SessionEvaluationRecord:
        high_severity_anomalies = [item for item in anomalies if item.severity == "high"]
        tool_error_rate = (tool_error_count / tool_call_count) if tool_call_count else 0.0
        has_final_reply = bool(final_assistant_reply.strip())

        if not has_final_reply or terminal_status == "failed" or high_severity_anomalies:
            grade = "failed"
            summary = "会话失败或存在高风险异常"
        elif tool_error_rate > 0 or resume_count > 0:
            grade = "partial_success"
            summary = "会话完成，但存在一定执行波动"
        else:
            grade = "success"
            summary = "会话顺利完成"

        return SessionEvaluationRecord(
            evaluation_id=f"eval_{uuid4().hex[:12]}",
            session_id=session_id,
            event_id=event_id,
            grade=grade,  # type: ignore[arg-type]
            summary=summary,
            recorded_at=datetime.utcnow(),
            signals={
                "has_final_reply": has_final_reply,
                "high_severity_anomaly_count": len(high_severity_anomalies),
                "tool_error_rate": tool_error_rate,
                "resume_count": resume_count,
                "terminal_status": terminal_status,
            },
        )

    def record_detected_anomalies(self, session_id: str) -> list[SessionAnomalyRecord]:
        events = self.event_log.list_events(session_id)
        anomalies = ReviewSessionAnomalyService().detect(events)
        for anomaly in anomalies:
            self.append_event(
                session_id,
                event_type="anomaly_detected",
                runtime_id=anomaly.related_runtime_ids[-1] if anomaly.related_runtime_ids else None,
                payload={
                    "code": anomaly.code,
                    "severity": anomaly.severity,
                    "title": anomaly.title,
                    "summary": anomaly.summary,
                    "related_runtime_ids": anomaly.related_runtime_ids,
                    "related_task_ids": anomaly.related_task_ids,
                },
            )
        return anomalies

    def record_evaluation(
        self,
        *,
        session_id: str,
        final_assistant_reply: str,
        anomalies: list[SessionAnomalyRecord],
        tool_error_count: int,
        tool_call_count: int,
        terminal_status: str,
        resume_count: int,
    ) -> SessionEvaluationRecord:
        evaluation = self.build_evaluation(
            session_id=session_id,
            event_id=f"evt_eval_{uuid4().hex[:8]}",
            final_assistant_reply=final_assistant_reply,
            anomalies=anomalies,
            tool_error_count=tool_error_count,
            tool_call_count=tool_call_count,
            terminal_status=terminal_status,
            resume_count=resume_count,
        )
        self.append_event(
            session_id,
            event_type="evaluation_recorded",
            payload={
                "grade": evaluation.grade,
                "summary": evaluation.summary,
                "signals": evaluation.signals,
            },
        )
        return evaluation
