from __future__ import annotations

from datetime import datetime

import pytest

from app.schemas.observability import SessionEventRecord
from app.services.review_session_event_log import ReviewSessionEventLog
from app.services.storage import StorageError


def _build_event(*, sequence: int, event_id: str = "evt_1") -> SessionEventRecord:
    return SessionEventRecord(
        event_id=event_id,
        session_id="rs_123",
        sequence=sequence,
        event_type="session_started",
        timestamp=datetime.utcnow(),
        trace_id="trace_123",
        span_id="span_123",
        payload={"status": "idle"},
    )


def test_append_and_list_events_preserves_order(tmp_path) -> None:
    event_log = ReviewSessionEventLog(tmp_path)

    event_log.append_event("rs_123", _build_event(sequence=1, event_id="evt_1"))
    event_log.append_event("rs_123", _build_event(sequence=2, event_id="evt_2"))

    events = event_log.list_events("rs_123")

    assert [event.event_id for event in events] == ["evt_1", "evt_2"]
    assert [event.sequence for event in events] == [1, 2]


def test_next_sequence_advances_with_existing_lines(tmp_path) -> None:
    event_log = ReviewSessionEventLog(tmp_path)
    event_log.append_event("rs_123", _build_event(sequence=1, event_id="evt_1"))

    assert event_log.next_sequence("rs_123") == 2


def test_append_event_keeps_existing_jsonl_lines(tmp_path) -> None:
    event_log = ReviewSessionEventLog(tmp_path)
    event_log.append_event("rs_123", _build_event(sequence=1, event_id="evt_1"))
    event_log.append_event("rs_123", _build_event(sequence=2, event_id="evt_2"))

    path = event_log.event_log_path("rs_123")
    lines = path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2


def test_rejects_path_traversal_session_ids(tmp_path) -> None:
    event_log = ReviewSessionEventLog(tmp_path)

    with pytest.raises(StorageError):
        event_log.event_log_path("../outside")
