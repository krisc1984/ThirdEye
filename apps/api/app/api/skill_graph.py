from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.model_providers.llm_client import LLMClient, summarize_provider_error
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.skill_graph import (
    CapabilityDraftRequest,
    CapabilityDraftResponse,
    CapabilityDefinition,
    CapabilitySourceDescriptor,
    CapabilitySourceReference,
    CompositeDefinition,
    GraphCompileResult,
    GraphPlaybookDefinition,
    GraphRun,
)
from app.services.business_agents import BusinessAgentService
from app.services.skill_graph_compiler import SkillGraphCompiler
from app.services.skill_graph_registry import SkillGraphRegistryService
from app.services.skill_graph_run_events import SkillGraphRunEventService, skill_graph_run_events
from app.services.skill_graph_runner import SkillGraphRunner
from app.services.skill_registry import SkillRegistryService
from app.services.storage import JsonStorage

router = APIRouter(prefix="/graph", tags=["skill-graph"])
API_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = API_ROOT / "skills"


class GraphRunStartRequest(BaseModel):
    input_payload: dict[str, Any] = Field(default_factory=dict)


class GraphApprovalRequest(BaseModel):
    approved: bool
    decided_by: str
    comment: str | None = None


def _encode_sse_event(event: dict[str, Any]) -> str:
    return f"event: {event['event_type']}\ndata: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _get_storage() -> JsonStorage:
    return JsonStorage(settings.data_dir)


def _get_skill_registry(storage: JsonStorage) -> SkillRegistryService:
    return SkillRegistryService(storage, SKILLS_ROOT)


def _get_registry(storage: JsonStorage) -> SkillGraphRegistryService:
    return SkillGraphRegistryService(storage, _get_skill_registry(storage))


def _get_runner(storage: JsonStorage) -> SkillGraphRunner:
    return SkillGraphRunner(
        storage=storage,
        registry=_get_registry(storage),
        action_handlers={
            "fetch": lambda _ctx, payload: {"page": payload.get("url", "")},
            "render": lambda ctx, _payload: {"report": f"report:{ctx['state'].get('page', '')}"},
            "fetch_competitor_homepage": lambda _ctx, payload: {
                "homepage_html": f"<html>{payload.get('competitor', 'unknown')}</html>"
            },
            "summarize_page_changes": lambda ctx, _payload: {
                "summary": f"summary:{ctx['state'].get('homepage_html', '')}"
            },
            "render_weekly_report": lambda ctx, payload: {
                "published": True,
                "report": f"weekly-report:{payload.get('topic', ctx['state'].get('summary', 'ready'))}",
            },
        },
    )


def _get_events(storage: JsonStorage) -> SkillGraphRunEventService:
    return SkillGraphRunEventService(storage)


@router.get("/capabilities", response_model=list[CapabilityDefinition])
def list_capabilities() -> list[CapabilityDefinition]:
    return _get_registry(_get_storage()).list_capabilities()


@router.get("/capability-sources", response_model=list[CapabilitySourceDescriptor])
def list_capability_sources() -> list[CapabilitySourceDescriptor]:
    storage = _get_storage()
    skill_registry = _get_skill_registry(storage)
    sources: list[CapabilitySourceDescriptor] = []

    for skill in skill_registry.list_skills():
        sources.append(
            CapabilitySourceDescriptor(
                source_type="skill",
                source_id=skill.name,
                name=skill.name,
                description=skill.description,
                suggested_kind="skill",
                metadata={
                    "enabled": skill.enabled,
                    "path": skill.path,
                    "source": skill.source,
                },
            )
        )

    for agent in BusinessAgentService(storage).list_agents():
        sources.append(
            CapabilitySourceDescriptor(
                source_type="agent",
                source_id=agent.id,
                name=agent.name,
                description=agent.description,
                suggested_kind="agent",
                metadata={
                    "category": agent.category,
                    "status": agent.status,
                    "is_default": agent.is_default,
                },
            )
        )

    sources.extend(_list_builtin_tool_sources())
    sources.extend(_list_mcp_server_sources(storage))
    return sorted(sources, key=lambda item: (item.source_type, item.name.lower()))


@router.post("/capabilities/draft", response_model=CapabilityDraftResponse)
def draft_capability(request: CapabilityDraftRequest) -> CapabilityDraftResponse:
    storage = _get_storage()
    registry = _get_registry(storage)
    source = _resolve_capability_source(storage, request.source_type, request.source_id)
    deterministic = _build_capability_template(registry, request, source)
    if not request.provider_id:
        return CapabilityDraftResponse(
            capability=deterministic,
            execution_mode="deterministic",
            execution_note="未选择模型，已按能力类型生成模板草稿。",
        )

    provider = _load_provider(request.provider_id)
    try:
        payload = asyncio.run(
            LLMClient().generate_capability_draft(
                provider,
                {
                    **request.model_dump(mode="json"),
                    "source": source.model_dump(mode="json") if source else None,
                },
            )
        )
        drafted = _merge_capability_draft(deterministic, payload)
        return CapabilityDraftResponse(
            capability=drafted,
            execution_mode="llm",
            resolved_provider_id=provider.id,
            execution_note="已结合模型补齐原子能力参数草稿。",
        )
    except Exception as error:
        return CapabilityDraftResponse(
            capability=deterministic,
            execution_mode="deterministic",
            execution_note=f"AI 填写失败，已回退到模板草稿：{summarize_provider_error(error)}",
        )


@router.post("/capabilities", response_model=CapabilityDefinition)
def save_capability(capability: CapabilityDefinition) -> CapabilityDefinition:
    return _get_registry(_get_storage()).save_capability(capability)


@router.get("/capabilities/{capability_id}", response_model=CapabilityDefinition)
def get_capability(capability_id: str) -> CapabilityDefinition:
    try:
        return _get_registry(_get_storage()).get_capability(capability_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="capability not found") from error


@router.put("/capabilities/{capability_id}", response_model=CapabilityDefinition)
def update_capability(capability_id: str, capability: CapabilityDefinition) -> CapabilityDefinition:
    if capability_id != capability.id:
        raise HTTPException(status_code=400, detail="capability id in path and body must match")
    return _get_registry(_get_storage()).save_capability(capability)


@router.delete("/capabilities/{capability_id}")
def delete_capability(capability_id: str) -> dict[str, str]:
    try:
        _get_registry(_get_storage()).delete_capability(capability_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="capability not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"status": "deleted", "capability_id": capability_id}


@router.get("/composites", response_model=list[CompositeDefinition])
def list_composites() -> list[CompositeDefinition]:
    return _get_registry(_get_storage()).list_composites()


@router.post("/composites", response_model=CompositeDefinition)
def save_composite(composite: CompositeDefinition) -> CompositeDefinition:
    try:
        return _get_registry(_get_storage()).save_composite(composite)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/composites/{composite_id}", response_model=CompositeDefinition)
def get_composite(composite_id: str) -> CompositeDefinition:
    try:
        return _get_registry(_get_storage()).get_composite(composite_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="composite not found") from error


@router.put("/composites/{composite_id}", response_model=CompositeDefinition)
def update_composite(composite_id: str, composite: CompositeDefinition) -> CompositeDefinition:
    if composite_id != composite.id:
        raise HTTPException(status_code=400, detail="composite id in path and body must match")
    try:
        return _get_registry(_get_storage()).save_composite(composite)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete("/composites/{composite_id}")
def delete_composite(composite_id: str) -> dict[str, str]:
    try:
        _get_registry(_get_storage()).delete_composite(composite_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="composite not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"status": "deleted", "composite_id": composite_id}


@router.post("/composites/{composite_id}/compile", response_model=GraphCompileResult)
def compile_composite(composite_id: str) -> GraphCompileResult:
    storage = _get_storage()
    registry = _get_registry(storage)
    try:
        composite = registry.get_composite(composite_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="composite not found") from error
    return SkillGraphCompiler().compile_composite(composite)


@router.get("/playbooks", response_model=list[GraphPlaybookDefinition])
def list_graph_playbooks() -> list[GraphPlaybookDefinition]:
    return _get_registry(_get_storage()).list_graph_playbooks()


@router.post("/playbooks", response_model=GraphPlaybookDefinition)
def save_graph_playbook(graph: GraphPlaybookDefinition) -> GraphPlaybookDefinition:
    try:
        return _get_registry(_get_storage()).save_graph_playbook(graph)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/playbooks/{graph_id}", response_model=GraphPlaybookDefinition)
def get_graph_playbook(graph_id: str) -> GraphPlaybookDefinition:
    try:
        return _get_registry(_get_storage()).get_graph_playbook(graph_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="graph playbook not found") from error


@router.put("/playbooks/{graph_id}", response_model=GraphPlaybookDefinition)
def update_graph_playbook(graph_id: str, graph: GraphPlaybookDefinition) -> GraphPlaybookDefinition:
    if graph_id != graph.id:
        raise HTTPException(status_code=400, detail="graph playbook id in path and body must match")
    try:
        return _get_registry(_get_storage()).save_graph_playbook(graph)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete("/playbooks/{graph_id}")
def delete_graph_playbook(graph_id: str) -> dict[str, str]:
    try:
        _get_registry(_get_storage()).delete_graph_playbook(graph_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="graph playbook not found") from error
    return {"status": "deleted", "graph_playbook_id": graph_id}


@router.post("/playbooks/{graph_id}/compile", response_model=GraphCompileResult)
def compile_graph_playbook(graph_id: str) -> GraphCompileResult:
    storage = _get_storage()
    registry = _get_registry(storage)
    try:
        graph = registry.get_graph_playbook(graph_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="graph playbook not found") from error
    return SkillGraphCompiler().compile_graph_playbook(graph)


@router.post("/playbooks/{graph_id}/runs", response_model=GraphRun)
def start_graph_run(graph_id: str, request: GraphRunStartRequest) -> GraphRun:
    storage = _get_storage()
    try:
        run = _get_runner(storage).start_run(graph_id, request.input_payload)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="graph playbook not found") from error
    _get_events(storage).append_run_event(run, event_type="run_updated")
    return run


@router.get("/runs", response_model=list[GraphRun])
def list_graph_runs() -> list[GraphRun]:
    storage = _get_storage()
    return [
        GraphRun.model_validate(item)
        for item in storage.list_json("skill-graph/runs")
    ]


@router.get("/runs/{run_id}", response_model=GraphRun)
def get_graph_run(run_id: str) -> GraphRun:
    try:
        return _get_runner(_get_storage()).get_run(run_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="graph run not found") from error


@router.post("/runs/{run_id}/approvals/{approval_id}", response_model=GraphRun)
def record_graph_approval(run_id: str, approval_id: str, request: GraphApprovalRequest) -> GraphRun:
    storage = _get_storage()
    try:
        run = _get_runner(storage).record_approval(
            run_id,
            approval_id,
            approved=request.approved,
            decided_by=request.decided_by,
            comment=request.comment,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="graph run or approval not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    _get_events(storage).append_run_event(
        run,
        event_type="approval_recorded" if request.approved else "approval_rejected",
    )
    return run


@router.get("/runs/{run_id}/events")
async def stream_graph_run_events(run_id: str, replay_only: bool = False) -> StreamingResponse:
    storage = _get_storage()
    events = _get_events(storage)
    try:
        snapshot = events.replay_run_snapshot(run_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="graph run not found") from error
    recorded = events.list_run_events(run_id)
    queue = skill_graph_run_events.subscribe(run_id)

    async def event_stream():
        yield _encode_sse_event(snapshot)
        for event in recorded:
            yield _encode_sse_event(event)
        if replay_only:
            return
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield _encode_sse_event(event)
                except asyncio.TimeoutError:
                    heartbeat = {
                        "run_id": run_id,
                        "sequence": -1,
                        "event_type": "heartbeat",
                        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                        "payload": {"run_id": run_id},
                    }
                    yield _encode_sse_event(heartbeat)
        finally:
            skill_graph_run_events.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _slugify(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    collapsed = "_".join(part for part in normalized.split("_") if part)
    return collapsed or "capability"


def _build_capability_template(
    registry: SkillGraphRegistryService,
    request: CapabilityDraftRequest,
    source: CapabilitySourceDescriptor | None,
) -> CapabilityDefinition:
    source_name = source.name if source else request.name.strip()
    source_description = source.description if source else ""
    if (source and source.source_type == "skill") or request.kind == "skill":
        try:
            capability = registry.skill_registry.build_capability_definition(source_name)
            description = request.description.strip() or source_description
            if description:
                return capability.model_copy(
                    update={
                        "description": description,
                        "source": _build_capability_source_reference(source),
                    }
                )
            return capability
        except FileNotFoundError:
            pass

    base_name = source_name or request.name.strip()
    capability_id = f"cap_{request.kind}_{_slugify(base_name)}"
    action = f"{request.kind}.{_slugify(base_name)}"
    description = request.description.strip() or source_description or f"{request.kind} 类型原子能力：{base_name}"
    config: dict[str, Any] = {}
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "input": {
                "type": "string",
                "description": "调用该原子能力时需要的主要输入。",
            }
        },
        "required": ["input"],
    }
    output_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "result": {
                "type": "string",
                "description": "该原子能力执行后的核心输出。",
            }
        },
        "required": ["result"],
    }
    retry_policy = {"max_attempts": 1, "backoff_seconds": 0, "retry_on": []}

    if request.kind == "tool":
        config = {"transport": "local_function", "timeout_seconds": 30}
    elif request.kind == "skill":
        config = {"skill_name": base_name, "entry": "SKILL.md"}
    elif request.kind == "agent":
        config = {"mode": "single_turn", "temperature": 0.2}
        retry_policy = {"max_attempts": 2, "backoff_seconds": 3, "retry_on": ["timeout", "rate_limit"]}
    elif request.kind == "service":
        config = {"endpoint": "", "method": "POST", "timeout_seconds": 20}
        retry_policy = {"max_attempts": 2, "backoff_seconds": 2, "retry_on": ["timeout", "5xx"]}

    if source:
        if source.source_type == "tool":
            config = {
                **config,
                "tool_name": source.source_id,
                "transport": "local_function",
            }
            action = source.source_id
        elif source.source_type == "agent":
            config = {
                **config,
                "agent_id": source.source_id,
                "agent_category": source.metadata.get("category", ""),
            }
            action = f"agent.{_slugify(source.source_id)}"
        elif source.source_type == "mcp_server":
            config = {
                **config,
                "mcp_server_id": source.source_id,
                "transport": str(source.metadata.get("transport", "")),
            }
            action = f"mcp.{_slugify(source.source_id)}"

    return CapabilityDefinition(
        id=capability_id,
        name=base_name,
        kind=request.kind,
        action=action,
        description=description,
        config=config,
        input_schema=input_schema,
        output_schema=output_schema,
        retry_policy=retry_policy,
        source=_build_capability_source_reference(source),
    )


def _merge_capability_draft(
    deterministic: CapabilityDefinition,
    payload: dict[str, Any],
) -> CapabilityDefinition:
    merged = deterministic.model_dump(mode="json")
    for key in ("id", "name", "kind", "action", "description", "config", "input_schema", "output_schema", "retry_policy", "enabled", "source"):
        value = payload.get(key)
        if value is not None:
            merged[key] = value
    merged["id"] = str(merged["id"])
    merged["name"] = str(merged["name"])
    merged["kind"] = deterministic.kind
    merged["action"] = str(merged["action"])
    merged["description"] = str(merged.get("description", ""))
    if not isinstance(merged.get("config"), dict):
        merged["config"] = deterministic.config
    if not isinstance(merged.get("input_schema"), dict):
        merged["input_schema"] = deterministic.input_schema
    if not isinstance(merged.get("output_schema"), dict):
        merged["output_schema"] = deterministic.output_schema
    if not isinstance(merged.get("retry_policy"), dict):
        merged["retry_policy"] = deterministic.retry_policy.model_dump(mode="json")
    if merged.get("source") is None and deterministic.source is not None:
        merged["source"] = deterministic.source.model_dump(mode="json")
    return CapabilityDefinition.model_validate(merged)


def _load_provider(provider_id: str) -> ModelProviderConfig:
    try:
        record = _get_storage().load_json("model-providers", provider_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="model provider not found") from error
    return ModelProviderConfig.model_validate(record)


def _resolve_capability_source(
    storage: JsonStorage,
    source_type: str | None,
    source_id: str | None,
) -> CapabilitySourceDescriptor | None:
    if not source_type or not source_id:
        return None
    for source in list_capability_sources():
        if source.source_type == source_type and source.source_id == source_id:
            return source
    return None


def _build_capability_source_reference(
    source: CapabilitySourceDescriptor | None,
) -> CapabilitySourceReference | None:
    if source is None:
        return None
    return CapabilitySourceReference(
        source_type=source.source_type,
        source_id=source.source_id,
        source_name=source.name,
        metadata=source.metadata,
    )


def _list_builtin_tool_sources() -> list[CapabilitySourceDescriptor]:
    return [
        CapabilitySourceDescriptor(
            source_type="tool",
            source_id="bash",
            name="bash",
            description="在允许的工作区根目录内执行 shell 命令。",
            suggested_kind="tool",
            metadata={"transport": "local_function"},
        ),
        CapabilitySourceDescriptor(
            source_type="tool",
            source_id="read_file",
            name="read_file",
            description="读取允许目录内的文本文件。",
            suggested_kind="tool",
            metadata={"transport": "local_function"},
        ),
        CapabilitySourceDescriptor(
            source_type="tool",
            source_id="write_file_chunk",
            name="write_file_chunk",
            description="向允许目录内的文件追加或覆盖文本片段。",
            suggested_kind="tool",
            metadata={"transport": "local_function"},
        ),
        CapabilitySourceDescriptor(
            source_type="tool",
            source_id="replace_in_file",
            name="replace_in_file",
            description="替换允许文件中的指定文本片段。",
            suggested_kind="tool",
            metadata={"transport": "local_function"},
        ),
        CapabilitySourceDescriptor(
            source_type="tool",
            source_id="load_skill",
            name="load_skill",
            description="读取本地技能目录中的完整技能内容。",
            suggested_kind="tool",
            metadata={"transport": "local_function"},
        ),
        CapabilitySourceDescriptor(
            source_type="tool",
            source_id="list_skills",
            name="list_skills",
            description="列出当前应用可用的技能及描述。",
            suggested_kind="tool",
            metadata={"transport": "local_function"},
        ),
        CapabilitySourceDescriptor(
            source_type="tool",
            source_id="tavily_web_search",
            name="tavily_web_search",
            description="通过 Tavily 执行联网网页搜索并返回结构化结果。",
            suggested_kind="tool",
            metadata={"transport": "local_function", "provider": "tavily"},
        ),
    ]


def _list_mcp_server_sources(storage: JsonStorage) -> list[CapabilitySourceDescriptor]:
    try:
        payload = storage.load_json("settings", "mcp-servers")
    except FileNotFoundError:
        return []
    raw_servers = payload.get("servers", [])
    if not isinstance(raw_servers, list):
        return []
    servers: list[CapabilitySourceDescriptor] = []
    for item in raw_servers:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip() or source_id
        if not source_id:
            continue
        servers.append(
            CapabilitySourceDescriptor(
                source_type="mcp_server",
                source_id=source_id,
                name=name,
                description=str(item.get("description", "")).strip(),
                suggested_kind="service",
                metadata={
                    "transport": str(item.get("transport", "")).strip(),
                    "url": str(item.get("url", "")).strip(),
                    "command": str(item.get("command", "")).strip(),
                },
            )
        )
    return servers
