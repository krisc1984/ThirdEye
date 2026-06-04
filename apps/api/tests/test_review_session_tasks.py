from __future__ import annotations

from datetime import datetime

from app.schemas.observability import SessionEventRecord
from app.services.review_session_tasks import ReviewSessionTaskService


def _event(
    sequence: int,
    event_type: str,
    *,
    runtime_id: str | None = None,
    turn: int | None = None,
    payload: dict | None = None,
) -> SessionEventRecord:
    return SessionEventRecord(
        event_id=f"evt_{sequence}",
        session_id="rs_123",
        sequence=sequence,
        event_type=event_type,  # type: ignore[arg-type]
        timestamp=datetime.utcnow(),
        trace_id="trace_123",
        span_id=f"span_{sequence}",
        parent_span_id=None,
        runtime_id=runtime_id,
        turn=turn,
        payload=payload or {},
    )


def test_build_task_tree_from_review_session_events() -> None:
    service = ReviewSessionTaskService()
    events = [
        _event(1, "session_started", payload={"playbook_id": "pb_1"}),
        _event(2, "model_call_started", runtime_id="llm_turn_1", turn=1),
        _event(
            3,
            "tool_call_started",
            runtime_id="tool_call_1",
            turn=1,
            payload={"tool_name": "read_file", "tool_call_id": "tool_call_1"},
        ),
        _event(
            4,
            "tool_call_completed",
            runtime_id="tool_call_1",
            turn=1,
            payload={"tool_name": "read_file", "tool_call_id": "tool_call_1", "ok": True},
        ),
        _event(5, "model_call_completed", runtime_id="llm_turn_1", turn=1, payload={"ok": True}),
        _event(6, "session_completed", payload={"latest_summary": "done"}),
    ]

    tasks = service.build_tasks(events)

    assert [task.kind for task in tasks] == ["session", "llm_turn", "tool_call"]
    root_task = tasks[0]
    llm_task = tasks[1]
    tool_task = tasks[2]

    assert root_task.status == "succeeded"
    assert llm_task.parent_task_id == root_task.task_id
    assert llm_task.status == "succeeded"
    assert tool_task.parent_task_id == llm_task.task_id
    assert tool_task.status == "succeeded"
    assert tool_task.summary == "调用 read_file"
