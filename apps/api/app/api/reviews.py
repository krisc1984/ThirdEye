from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agents.sandbox.capabilities.compaction import CompactionModelInfo
from agents.sandbox.util import approx_token_count
from app.agents.report_writer import generate_review_report_reply
from app.agents.review import run_review
from app.agents.sdk_chat import InvalidResumeStateError, resume_agent_chat_turn, run_agent_chat_turn
from app.agents.sdk_runtime import AgentResumeError
from app.core.config import settings
from app.model_providers.llm_client import summarize_provider_error
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.review import (
    ReviewConversationSession,
    ReviewSessionContextUsage,
    ReviewSessionContextUsageBreakdown,
    ReviewReportAssistantRequest,
    ReviewReportAssistantResponse,
    ReviewRequest,
    ReviewResponse,
    ReviewSessionCreateRequest,
    ReviewSessionSendRequest,
)
from app.services.audit_log import AuditLogger
from app.services.business_agents import BusinessAgentService
from app.services.playbook_loader import PlaybookLoader
from app.services.review_session_runs import (
    ReviewSessionAlreadyRunningError,
    review_session_runs,
)
from app.services.review_session_events import encode_sse_event, review_session_events
from app.services.review_sessions import ReviewSessionStore
from app.services.storage import JsonStorage, StorageError

router = APIRouter(prefix="/reviews", tags=["reviews"])

_SYSTEM_PROMPT_GUARDRAILS = (
    "你必须始终使用中文回复。"
    "你只能基于提供的项目空间目录、资料库目录、评审规则和对话上下文进行分析，禁止臆造仓库事实。"
    "当用户要求查看、总结、分析文件或目录内容时，你必须优先使用可用的 function tools 主动读取或检索信息。"
    "优先引用评审规则给出结构化、简洁、可执行的评审意见。"
)


def _resolve_active_agent_prompt(storage: JsonStorage) -> tuple[str, str]:
    try:
        agents = BusinessAgentService(storage).list_agents()
    except Exception:
        agents = []
    for agent in agents:
        if agent.is_default or agent.status == "active":
            return agent.name, agent.system_prompt
    return (
        "代码评审 Agent",
        "你是专业的代码评审智能体。优先识别高风险缺陷、行为回归、边界条件遗漏、测试缺口与设计偏差。"
        "输出保持结构化、直接，并给出可执行的修正建议。",
    )


def _resolve_context_window(model_name: str | None) -> int:
    if not model_name:
        return 0
    model_info = CompactionModelInfo.maybe_for_model(model_name)
    if model_info is not None:
        return model_info.context_window
    return 200_000


def _estimate_session_context_usage(
    session: ReviewConversationSession,
    *,
    storage: JsonStorage,
    playbook_loader: PlaybookLoader,
) -> ReviewSessionContextUsage | None:
    provider_name: str | None = None
    model_name: str | None = None
    if session.resolved_provider_id:
        try:
            provider = _load_provider(session.resolved_provider_id)
        except HTTPException:
            provider = None
        if provider is not None:
            provider_name = provider.name
            model_name = provider.model

    context_window = _resolve_context_window(model_name)
    if context_window <= 0:
        return None

    message_parts: list[str] = []
    for message in session.messages:
        message_parts.append(message.content or "")
        if message.tool_arguments:
            message_parts.append(message.tool_arguments)
        if message.tool_result:
            message_parts.append(message.tool_result)
    messages_tokens = approx_token_count("\n".join(message_parts))

    agent_name, agent_prompt = _resolve_active_agent_prompt(storage)
    system_prompt_tokens = approx_token_count(
        f"你当前扮演 ThirdEye 的业务智能体：{agent_name}。\n{agent_prompt}\n{_SYSTEM_PROMPT_GUARDRAILS}"
    )

    playbook_tokens = 0
    try:
        playbook = playbook_loader.load(session.playbook_id)
    except (FileNotFoundError, StorageError):
        playbook = None
    if playbook is not None:
        playbook_text = "\n".join(
            [
                playbook.project_summary or "",
                playbook.skill_markdown or "",
                "\n".join(
                    f"{rule.name}\n{rule.description}\n{' '.join(rule.review_prompts)}"
                    for rule in playbook.rules
                ),
            ]
        )
        playbook_tokens = approx_token_count(playbook_text)

    used_tokens = messages_tokens + system_prompt_tokens + playbook_tokens
    remaining_tokens = max(context_window - used_tokens, 0)
    usage_percent = min(100, round((used_tokens / context_window) * 100)) if context_window else 0
    return ReviewSessionContextUsage(
        model_name=model_name,
        provider_name=provider_name,
        context_window=context_window,
        used_tokens=used_tokens,
        remaining_tokens=remaining_tokens,
        usage_percent=usage_percent,
        breakdown=ReviewSessionContextUsageBreakdown(
            messages_tokens=messages_tokens,
            system_prompt_tokens=system_prompt_tokens,
            playbook_tokens=playbook_tokens,
        ),
        updated_at=datetime.utcnow(),
    )


def _enrich_session(
    session: ReviewConversationSession,
    *,
    storage: JsonStorage,
    playbook_loader: PlaybookLoader,
) -> ReviewConversationSession:
    context_usage = _estimate_session_context_usage(session, storage=storage, playbook_loader=playbook_loader)
    return session.model_copy(update={"context_usage": context_usage})


def _append_tool_messages(
    session_store: ReviewSessionStore,
    session_id: str,
    tool_events: list[dict[str, object]] | None,
) -> None:
    if not tool_events:
        return

    merged: dict[str, dict[str, str]] = {}
    existing_session = session_store.load(session_id).session
    existing_tool_call_ids = {
        message.tool_call_id
        for message in existing_session.messages
        if message.role == "tool" and message.tool_call_id
    }
    for event in tool_events:
        tool_call_id = str(event.get("tool_call_id") or "")
        if not tool_call_id:
            continue
        bucket = merged.setdefault(
            tool_call_id,
            {"tool_name": "", "tool_arguments": "", "tool_result": ""},
        )
        if event.get("tool_name"):
            bucket["tool_name"] = str(event["tool_name"])
        if event.get("phase") == "start" and event.get("tool_arguments"):
            bucket["tool_arguments"] = str(event["tool_arguments"])
        if event.get("phase") == "end" and event.get("result"):
            bucket["tool_result"] = str(event["result"])

    for tool_call_id, event in merged.items():
        if tool_call_id in existing_tool_call_ids:
            continue
        session_store.append_message(
            session_id,
            role="tool",
            content=f"{event['tool_name'] or 'tool'} 调用完成",
            tool_name=event["tool_name"] or None,
            tool_call_id=tool_call_id,
            tool_arguments=event["tool_arguments"] or None,
            tool_result=event["tool_result"] or None,
        )


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
    return _enrich_session(state.session, storage=storage, playbook_loader=playbook_loader)


@router.get("/sessions/{session_id}", response_model=ReviewConversationSession)
def get_review_session(session_id: str) -> ReviewConversationSession:
    storage = JsonStorage(settings.data_dir)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    try:
        state = session_store.load(session_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session not found") from error
    return _enrich_session(state.session, storage=storage, playbook_loader=playbook_loader)


@router.get("/sessions/{session_id}/events")
async def stream_review_session_events(session_id: str) -> StreamingResponse:
    storage = JsonStorage(settings.data_dir)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    try:
        state = session_store.load(session_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session not found") from error

    queue = review_session_events.subscribe(session_id)

    async def event_stream():
        snapshot_event = {
            "session_id": session_id,
            "sequence": 0,
            "event_type": "session.snapshot",
            "timestamp": state.session.updated_at.isoformat(),
            "payload": _enrich_session(state.session, storage=storage, playbook_loader=playbook_loader).model_dump(mode="json"),
        }
        yield encode_sse_event(snapshot_event)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield encode_sse_event(event)
                except asyncio.TimeoutError:
                    heartbeat = {
                        "session_id": session_id,
                        "sequence": -1,
                        "event_type": "heartbeat",
                        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                        "payload": {"session_id": session_id},
                    }
                    yield encode_sse_event(heartbeat)
        finally:
            review_session_events.unsubscribe(session_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
                resume_reason="runtime_error",
            )
        session_store.append_message(
            session_id,
            role="assistant",
            content="本轮任务执行中断，已保存断点。你可以点击继续执行，从中断处恢复。",
        )
        return _enrich_session(session_store.load(session_id).session, storage=storage, playbook_loader=playbook_loader)
    except asyncio.CancelledError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note="agent run cancelled by user",
        )
        session_store.mark_resume_available(
            session_id,
            resume_reason="cancelled_by_user",
            execution_note="agent run cancelled by user",
        )
        raise HTTPException(status_code=409, detail="review session cancelled") from error
    finally:
        review_session_runs.finish(session_id, task)

    _append_tool_messages(session_store, session_id, getattr(turn_result, "tool_events", None))
    session_store.append_message(session_id, role="assistant", content=turn_result.assistant_text)
    session = session_store.attach_review_result(
        session_id,
        summary=turn_result.assistant_text,
        review=turn_result.review,
        execution_mode=turn_result.execution_mode,
        resolved_provider_id=turn_result.resolved_provider_id,
        execution_note=turn_result.execution_note,
    )
    return _enrich_session(session, storage=storage, playbook_loader=playbook_loader)


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
                resume_reason="runtime_error",
            )
        session_store.append_message(
            session_id,
            role="assistant",
            content="继续执行过程中再次中断，已更新断点。可以再次点击继续执行。",
        )
        return _enrich_session(session_store.load(session_id).session, storage=storage, playbook_loader=playbook_loader)
    except asyncio.CancelledError as error:
        session_store.update_status(
            session_id,
            status="idle",
            execution_note="agent resume cancelled by user",
        )
        session_store.mark_resume_available(
            session_id,
            resume_reason="cancelled_by_user",
            execution_note="agent resume cancelled by user",
        )
        raise HTTPException(status_code=409, detail="review session cancelled") from error
    finally:
        review_session_runs.finish(session_id, task)

    _append_tool_messages(session_store, session_id, getattr(turn_result, "tool_events", None))
    session_store.append_message(session_id, role="assistant", content=turn_result.assistant_text)
    session = session_store.attach_review_result(
        session_id,
        summary=turn_result.assistant_text,
        review=turn_result.review,
        execution_mode=turn_result.execution_mode,
        resolved_provider_id=turn_result.resolved_provider_id,
        execution_note=turn_result.execution_note,
    )
    return _enrich_session(session, storage=storage, playbook_loader=playbook_loader)


@router.post("/sessions/{session_id}/stop", response_model=ReviewConversationSession)
def stop_review_session(session_id: str) -> ReviewConversationSession:
    storage = JsonStorage(settings.data_dir)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    try:
        state = session_store.load(session_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session not found") from error

    if not review_session_runs.cancel(session_id):
        session = session_store.update_status(
            session_id,
            status="idle",
            execution_note=state.session.execution_note,
        )
        return _enrich_session(session, storage=storage, playbook_loader=playbook_loader)
    session = session_store.update_status(
        session_id,
        status="idle",
        execution_note="agent run cancelled by user",
    )
    return _enrich_session(session, storage=storage, playbook_loader=playbook_loader)


@router.post("/report-assistant", response_model=ReviewReportAssistantResponse)
async def review_report_assistant(request: ReviewReportAssistantRequest) -> ReviewReportAssistantResponse:
    storage = JsonStorage(settings.data_dir)
    playbook_loader = PlaybookLoader(storage)
    session_store = ReviewSessionStore(storage, settings.data_dir)
    try:
        state = session_store.load(request.session_id)
        playbook = playbook_loader.load(request.playbook_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="review session or playbook not found") from error

    provider: ModelProviderConfig | None = None
    if state.session.resolved_provider_id:
        try:
            provider = _load_provider(state.session.resolved_provider_id)
        except HTTPException as error:
            if error.status_code != 404:
                raise

    return await generate_review_report_reply(
        session=state.session,
        playbook=playbook,
        markdown=request.markdown,
        instruction=request.instruction,
        provider_config=provider,
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
