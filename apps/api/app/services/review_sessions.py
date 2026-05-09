from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.schemas.review import ReviewChatMessage, ReviewConversationSession, ReviewResponse
from app.services.storage import JsonStorage


@dataclass(frozen=True)
class ReviewSessionState:
    session: ReviewConversationSession
    sqlite_session: Any


class ReviewSessionStore:
    def __init__(self, storage: JsonStorage, data_root: Path) -> None:
        self.storage = storage
        self.sqlite_db_path = data_root / "review_sessions" / "agent_memory.sqlite3"
        self.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        playbook_id: str,
        project_id: str | None,
        mode: str,
        model_provider_id: str | None,
        opening_message: str | None = None,
    ) -> ReviewSessionState:
        session_id = f"rs_{uuid4().hex[:12]}"
        now = datetime.utcnow()
        messages: list[ReviewChatMessage] = []
        if opening_message and opening_message.strip():
            messages.append(
                ReviewChatMessage(
                    id=f"msg_{uuid4().hex[:12]}",
                    role="user",
                    content=opening_message.strip(),
                    created_at=now,
                )
            )
        session = ReviewConversationSession(
            id=session_id,
            playbook_id=playbook_id,
            project_id=project_id,
            mode=mode,  # type: ignore[arg-type]
            status="idle",
            execution_mode="llm" if model_provider_id else "deterministic",
            resolved_provider_id=model_provider_id,
            messages=messages,
            created_at=now,
            updated_at=now,
        )
        self._save(session)
        return ReviewSessionState(session=session, sqlite_session=self.open_sqlite_session(session_id))

    def load(self, session_id: str) -> ReviewSessionState:
        record = self.storage.load_json("review-sessions", session_id)
        session = ReviewConversationSession.model_validate(record)
        return ReviewSessionState(session=session, sqlite_session=self.open_sqlite_session(session_id))

    def append_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
    ) -> ReviewConversationSession:
        state = self.load(session_id).session
        state.messages.append(
            ReviewChatMessage(
                id=f"msg_{uuid4().hex[:12]}",
                role=role,  # type: ignore[arg-type]
                content=content,
            )
        )
        state.updated_at = datetime.utcnow()
        self._save(state)
        return state

    def save_resume_state(
        self,
        session_id: str,
        *,
        resume_state_json: dict[str, Any],
        resume_reason: str,
    ) -> ReviewConversationSession:
        self.storage.save_json("review-session-resume", session_id, resume_state_json)
        state = self.load(session_id).session
        state.resume_available = True
        state.resume_reason = resume_reason  # type: ignore[assignment]
        state.updated_at = datetime.utcnow()
        self._save(state)
        return state

    def load_resume_state(self, session_id: str) -> dict[str, Any]:
        return self.storage.load_json("review-session-resume", session_id)

    def clear_resume_state(self, session_id: str) -> ReviewConversationSession:
        resume_path = self.storage.root / "review-session-resume" / f"{session_id}.json"
        if resume_path.exists():
            resume_path.unlink()
        state = self.load(session_id).session
        state.resume_available = False
        state.resume_reason = None
        state.updated_at = datetime.utcnow()
        self._save(state)
        return state

    def mark_resume_available(
        self,
        session_id: str,
        *,
        resume_reason: str,
        execution_note: str | None = None,
    ) -> ReviewConversationSession:
        state = self.load(session_id).session
        state.resume_available = True
        state.resume_reason = resume_reason  # type: ignore[assignment]
        if execution_note is not None:
            state.execution_note = execution_note
        state.updated_at = datetime.utcnow()
        self._save(state)
        return state

    def attach_review_result(
        self,
        session_id: str,
        *,
        summary: str,
        review: ReviewResponse | None,
        execution_mode: str,
        resolved_provider_id: str | None,
        execution_note: str | None,
    ) -> ReviewConversationSession:
        state = self.load(session_id).session
        state.latest_summary = summary
        state.last_review = review
        state.execution_mode = execution_mode  # type: ignore[assignment]
        state.resolved_provider_id = resolved_provider_id
        state.execution_note = execution_note
        state.resume_available = False
        state.resume_reason = None
        state.updated_at = datetime.utcnow()
        self._save(state)
        resume_path = self.storage.root / "review-session-resume" / f"{session_id}.json"
        if resume_path.exists():
            resume_path.unlink()
        return state

    def update_status(
        self,
        session_id: str,
        *,
        status: str,
        execution_note: str | None = None,
    ) -> ReviewConversationSession:
        state = self.load(session_id).session
        state.status = status  # type: ignore[assignment]
        if execution_note is not None:
            state.execution_note = execution_note
        state.updated_at = datetime.utcnow()
        self._save(state)
        return state

    def open_sqlite_session(self, session_id: str) -> Any:
        try:
            from agents import SQLiteSession
        except ModuleNotFoundError:
            return None

        return SQLiteSession(session_id=session_id, db_path=self.sqlite_db_path)

    def _save(self, session: ReviewConversationSession) -> None:
        self.storage.save_json("review-sessions", session.id, session.model_dump(mode="json"))
