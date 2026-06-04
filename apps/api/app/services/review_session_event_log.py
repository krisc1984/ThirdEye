from __future__ import annotations

import json
from pathlib import Path

from app.schemas.observability import SessionEventRecord
from app.services.storage import StorageError


class ReviewSessionEventLog:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def event_log_path(self, session_id: str) -> Path:
        self._validate_session_id(session_id)
        return self.root / f"{session_id}.jsonl"

    def append_event(self, session_id: str, event: SessionEventRecord) -> Path:
        path = self.event_log_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
            handle.write("\n")
        return path

    def list_events(self, session_id: str) -> list[SessionEventRecord]:
        path = self.event_log_path(session_id)
        if not path.exists():
            return []

        events: list[SessionEventRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                events.append(SessionEventRecord.model_validate_json(stripped))
        return events

    def next_sequence(self, session_id: str) -> int:
        events = self.list_events(session_id)
        if not events:
            return 1
        return events[-1].sequence + 1

    def _validate_session_id(self, session_id: str) -> None:
        parts = Path(session_id).parts
        if not session_id or any(part in {"..", ".", ""} for part in parts) or Path(session_id).is_absolute():
            raise StorageError(f"invalid session id: {session_id!r}")
