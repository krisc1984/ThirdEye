from __future__ import annotations

from app.schemas.observability import SessionAnomalyRecord, SessionEventRecord


class ReviewSessionAnomalyService:
    def detect(self, events: list[SessionEventRecord]) -> list[SessionAnomalyRecord]:
        tool_failures = [
            event
            for event in events
            if event.event_type == "tool_call_completed" and not bool(event.payload.get("ok", True))
        ]
        if len(tool_failures) < 3:
            return []

        return [
            SessionAnomalyRecord(
                anomaly_id="an_repeated_tool_failure",
                session_id=tool_failures[-1].session_id,
                event_id=tool_failures[-1].event_id,
                code="repeated_tool_failure",
                severity="high",
                title="同一工具连续失败",
                summary=f"{tool_failures[-1].payload.get('tool_name') or 'tool'} 连续失败 {len(tool_failures)} 次",
                detected_at=tool_failures[-1].timestamp,
                related_runtime_ids=[event.runtime_id or "" for event in tool_failures],
                related_task_ids=[],
            )
        ]
