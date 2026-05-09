from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.agents.review import run_review
from app.agents.sdk_chat import InvalidResumeStateError, resume_agent_chat_turn, run_agent_chat_turn
from app.agents.sdk_runtime import AgentResumeError
from app.core.config import settings
from app.model_providers.llm_client import summarize_provider_error
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.review import (
    ReviewConversationSession,
    ReviewRequest,
    ReviewResponse,
    ReviewSessionCreateRequest,
    ReviewSessionSendRequest,
)
from app.services.audit_log import AuditLogger
from app.services.playbook_loader import PlaybookLoader
from app.services.review_session_runs import (
    ReviewSessionAlreadyRunningError,
    review_session_runs,
)
from app.services.review_sessions import ReviewSessionStore
from app.services.storage import JsonStorage, StorageError

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse)
def create_review(request: ReviewRequest) -> ReviewResponse:
    storage = JsonStorage(settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    try:
        playbook = playbook_loader.load(request.playbook_id)
    except (FileNotFoundError, StorageError) as error:
        _log_review_event(request, success=False, error_message="playbook not found")
        raise HTTPException(status_code=404, detail="playbook not found") from error

    provider = _load_provider(request.model_provider_id) if request.model_provider_id else None
    try:
        response = asyncio.run(
            run_review(
                request,
                playbook.metadata,
                playbook.rules,
                playbook.evidence,
                provider_config=provider,
            )
        )
    except Exception as error:
        if provider is None:
            raise
        response = asyncio.run(
            run_review(
                request,
                playbook.metadata,
                playbook.rules,
                playbook.evidence,
            )
        )
        response.execution_note = f"LLM review failed and fell back to deterministic mode: {summarize_provider_error(error)}"
    storage.save_json("reviews", response.id, response.model_dump(mode="json"))
    _log_review_event(request, success=True, response=response)
    return response


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str) -> ReviewResponse:
    storage = JsonStorage(settings.data_dir)
    try:
        record = storage.load_json("reviews", review_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review not found") from error
    return ReviewResponse.model_validate(record)


@router.post("/sessions", response_model=ReviewConversationSession)
def create_review_session(request: ReviewSessionCreateRequest) -> ReviewConversationSession:
    storage = JsonStorage(settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    try:
        playbook_loader.load(request.playbook_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="playbook not found") from error

    state = session_store.create(
        playbook_id=request.playbook_id,
        project_id=request.project_id,
        mode=request.mode,
        model_provider_id=request.model_provider_id,
        opening_message=request.opening_message,
    )
    return state.session


@router.get("/sessions/{session_id}", response_model=ReviewConversationSession)
def get_review_session(session_id: str) -> ReviewConversationSession:
    storage = JsonStorage(settings.data_dir)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    try:
        state = session_store.load(session_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session not found") from error
    return state.session


@router.post("/sessions/{session_id}/messages", response_model=ReviewConversationSession)
async def send_review_message(session_id: str, request: ReviewSessionSendRequest) -> ReviewConversationSession:
    storage = JsonStorage(settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    try:
        state = session_store.load(session_id)
        playbook = playbook_loader.load(state.session.playbook_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session or playbook not found") from error
    if review_session_runs.is_running(session_id):
        raise HTTPException(status_code=409, detail="review session is already running")

    provider: ModelProviderConfig | None = None
    if state.session.resolved_provider_id:
        try:
            provider = _load_provider(state.session.resolved_provider_id)
        except HTTPException as error:
            if error.status_code != 404:
                raise
    session_store.append_message(session_id, role="user", content=request.message)
    session_store.update_status(session_id, status="running", execution_note="agent run in progress")

    async def _run_turn():
        try:
            return await run_agent_chat_turn(
                session_store=session_store,
                session_id=session_id,
                playbook=playbook,
                provider_config=provider,
                user_message=request.message,
            )
        except Exception as error:
            if provider is None:
                raise
            turn_result = await run_agent_chat_turn(
                session_store=session_store,
                session_id=session_id,
                playbook=playbook,
                provider_config=None,
                user_message=request.message,
            )
            return turn_result.__class__(
                assistant_text=turn_result.assistant_text,
                review=turn_result.review,
                execution_mode="deterministic",
                resolved_provider_id=None,
                execution_note=f"LLM agent review failed and fell back to deterministic mode: {summarize_provider_error(error)}",
            )

    task = asyncio.create_task(_run_turn())
    try:
        review_session_runs.start(session_id, task)
    except ReviewSessionAlreadyRunningError as error:
        task.cancel()
        raise HTTPException(status_code=409, detail="review session is already running") from error

    try:
        turn_result = await task
    except InvalidResumeStateError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note=str(error),
        )
        session_store.append_message(
            session_id,
            role="assistant",
            content="断点已失效，无法继续恢复。请重新发送任务。",
        )
        raise HTTPException(status_code=409, detail=str(error)) from error
    except AgentResumeError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note=f"agent run interrupted, checkpoint saved: {summarize_provider_error(error)}",
        )
        if error.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=error.resume_state_json,
                resume_reason="error",
            )
        session_store.append_message(
            session_id,
            role="assistant",
            content="本轮任务执行中断，已保存断点。你可以点击继续执行，从中断处恢复。",
        )
        return session_store.load(session_id).session
    except asyncio.CancelledError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note="agent run cancelled by user",
        )
        session_store.mark_resume_available(
            session_id,
            resume_reason="cancelled",
            execution_note="agent run cancelled by user",
        )
        raise HTTPException(status_code=409, detail="review session cancelled") from error
    finally:
        review_session_runs.finish(session_id, task)

    session_store.append_message(session_id, role="assistant", content=turn_result.assistant_text)
    return session_store.attach_review_result(
        session_id,
        summary=turn_result.assistant_text,
        review=turn_result.review,
        execution_mode=turn_result.execution_mode,
        resolved_provider_id=turn_result.resolved_provider_id,
        execution_note=turn_result.execution_note,
    )


@router.post("/sessions/{session_id}/resume", response_model=ReviewConversationSession)
async def resume_review_message(session_id: str) -> ReviewConversationSession:
    storage = JsonStorage(settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    try:
        state = session_store.load(session_id)
        playbook = playbook_loader.load(state.session.playbook_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session or playbook not found") from error

    if not state.session.resume_available:
        raise HTTPException(status_code=409, detail="review session has no resumable checkpoint")
    if review_session_runs.is_running(session_id):
        raise HTTPException(status_code=409, detail="review session is already running")

    provider: ModelProviderConfig | None = None
    if state.session.resolved_provider_id:
        try:
            provider = _load_provider(state.session.resolved_provider_id)
        except HTTPException as error:
            if error.status_code != 404:
                raise

    session_store.update_status(session_id, status="running", execution_note="agent resume in progress")

    async def _resume_turn():
        return await resume_agent_chat_turn(
            session_store=session_store,
            session_id=session_id,
            playbook=playbook,
            provider_config=provider,
        )

    task = asyncio.create_task(_resume_turn())
    try:
        review_session_runs.start(session_id, task)
    except ReviewSessionAlreadyRunningError as error:
        task.cancel()
        raise HTTPException(status_code=409, detail="review session is already running") from error

    try:
        turn_result = await task
    except InvalidResumeStateError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note=str(error),
        )
        session_store.append_message(
            session_id,
            role="assistant",
            content="断点已失效，无法继续恢复。请重新发送任务。",
        )
        raise HTTPException(status_code=409, detail=str(error)) from error
    except AgentResumeError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note=f"agent resume interrupted, checkpoint saved: {summarize_provider_error(error)}",
        )
        if error.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=error.resume_state_json,
                resume_reason="error",
            )
        session_store.append_message(
            session_id,
            role="assistant",
            content="继续执行过程中再次中断，已更新断点。可以再次点击继续执行。",
        )
        return session_store.load(session_id).session
    except asyncio.CancelledError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note="agent resume cancelled by user",
        )
        session_store.mark_resume_available(
            session_id,
            resume_reason="cancelled",
            execution_note="agent resume cancelled by user",
        )
        raise HTTPException(status_code=409, detail="review session cancelled") from error
    finally:
        review_session_runs.finish(session_id, task)

    session_store.append_message(session_id, role="assistant", content=turn_result.assistant_text)
    return session_store.attach_review_result(
        session_id,
        summary=turn_result.assistant_text,
        review=turn_result.review,
        execution_mode=turn_result.execution_mode,
        resolved_provider_id=turn_result.resolved_provider_id,
        execution_note=turn_result.execution_note,
    )


@router.post("/sessions/{session_id}/stop", response_model=ReviewConversationSession)
def stop_review_session(session_id: str) -> ReviewConversationSession:
    storage = JsonStorage(settings.data_dir)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    try:
        state = session_store.load(session_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session not found") from error

    if not review_session_runs.cancel(session_id):
        return session_store.update_status(
            session_id,
            status="idle",
            execution_note=state.session.execution_note,
        )
    return session_store.update_status(
        session_id,
        status="idle",
        execution_note="agent run cancelled by user",
    )


def _load_provider(provider_id: str) -> ModelProviderConfig:
    storage = JsonStorage(settings.data_dir)
    try:
        record = storage.load_json("model-providers", provider_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="model provider not found") from error
    return ModelProviderConfig.model_validate(record)


def _log_review_event(
    request: ReviewRequest,
    *,
    success: bool,
    response: ReviewResponse | None = None,
    error_message: str | None = None,
) -> None:
    audit_logger = AuditLogger(settings.data_dir / "audit")
    audit_logger.log_event(
        {
            "workflow": "technical_review",
            "playbook_id": request.playbook_id,
            "provider_id": request.model_provider_id,
            "mode": request.mode,
            "success": success,
            "review_id": response.id if response else None,
            "artifact_paths": [f"reviews/{response.id}.json"] if response else [],
            "error": error_message,
            "proposal_excerpt": request.proposal,
        }
    )
