from __future__ import annotations

from dataclasses import dataclass
import inspect
from pathlib import Path
import sys
import types
from uuid import uuid4

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
VENDOR_SITE = REPO_ROOT / ".vendor" / "py312"

if str(VENDOR_SITE) not in sys.path and VENDOR_SITE.exists():
    sys.path.insert(0, str(VENDOR_SITE))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "griffe" not in sys.modules:
    griffe_stub = types.ModuleType("griffe")

    class _DocstringSectionKind:
        text = "text"
        parameters = "parameters"

    class _DocstringSection:
        def __init__(self, kind: str, value):
            self.kind = kind
            self.value = value

    class _Docstring:
        def __init__(self, text: str, lineno: int = 1, parser: str | None = None):
            self.text = text

        def parse(self):
            lines = self.text.splitlines()
            description_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if description_lines:
                        break
                    continue
                if stripped.startswith(("Args:", "Arguments:", "Parameters", ":param")):
                    break
                description_lines.append(stripped)
            description = " ".join(description_lines).strip()
            return [_DocstringSection(_DocstringSectionKind.text, description)] if description else []

    griffe_stub.Docstring = _Docstring
    griffe_stub.DocstringSectionKind = _DocstringSectionKind
    sys.modules["griffe"] = griffe_stub

from agents import ModelSettings
from agents import Agent, RunState

from app.agents.oss_skill_preflight import maybe_run_oss_skill_preflight as _maybe_run_oss_skill_preflight
from app.agents.sdk_runtime import (
    AgentResumeError,
    build_agent_model,
    build_log_context,
    build_run_config,
    build_sqlite_session,
    run_text_agent,
)
from app.agents.tool import build_agent_tools
from app.core.config import settings
from app.model_providers.llm_client import summarize_provider_error
from app.schemas.business_agent import BusinessAgentConfig
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.playbook import EvidenceItem, PlaybookRule
from app.schemas.review import ReviewResponse
from app.services.business_agents import BusinessAgentService
from app.services.knowledge_workspace import KnowledgeWorkspaceService
from app.services.playbook_loader import LoadedPlaybook
from app.services.review_sessions import ReviewSessionStore
from app.services.storage import JsonStorage, StorageError


def _persist_live_runtime_event(
    session_store: ReviewSessionStore,
    session_id: str,
    event: dict[str, object],
) -> None:
    kind = str(event.get("kind") or "").strip()
    phase = str(event.get("phase") or "").strip()
    if kind == "tool":
        tool_call_id = str(event.get("tool_call_id") or "").strip()
        if not tool_call_id:
            return
        tool_name = str(event.get("tool_name") or "").strip() or None
        if phase == "start":
            session_store.upsert_tool_message(
                session_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                content=f"{tool_name or 'tool'} 调用中",
                tool_arguments=str(event.get("tool_arguments") or "") or None,
                call_status="running",
            )
            return
        if phase == "end":
            ok = bool(event.get("ok", True))
            session_store.upsert_tool_message(
                session_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                content=f"{tool_name or 'tool'} {'调用完成' if ok else '调用失败'}",
                tool_result=str(event.get("result") or "") or None,
                call_status="success" if ok else "error",
            )
            return
    if kind == "llm":
        runtime_id = str(event.get("runtime_id") or "").strip()
        if not runtime_id:
            return
        provider_id = str(event.get("provider_id") or "").strip() or None
        model_name = str(event.get("model") or "").strip() or None
        if phase == "start":
            session_store.upsert_llm_message(
                session_id,
                runtime_id=runtime_id,
                content=f"LLM 调用中 · {provider_id or 'provider'} / {model_name or 'model'}",
                call_status="running",
                provider_id=provider_id,
                model_name=model_name,
                tool_arguments=str(event.get("tool_arguments") or "") or None,
            )
            return
        if phase == "end":
            ok = bool(event.get("ok", True))
            session_store.upsert_llm_message(
                session_id,
                runtime_id=runtime_id,
                content=f"LLM {'调用完成' if ok else '调用失败'} · {provider_id or 'provider'} / {model_name or 'model'}",
                call_status="success" if ok else "error",
                provider_id=provider_id,
                model_name=model_name,
                tool_result=str(event.get("tool_result") or event.get("result") or "") or None,
            )
            return


async def _run_text_agent_compat(**kwargs):
    signature = inspect.signature(run_text_agent)
    if "runtime_event_callback" not in signature.parameters:
        kwargs.pop("runtime_event_callback", None)
    return await run_text_agent(**kwargs)

@dataclass(frozen=True)
class AgentChatTurnResult:
    assistant_text: str
    review: ReviewResponse | None
    execution_mode: str
    resolved_provider_id: str | None
    execution_note: str | None
    tool_events: list[dict[str, object]] | None = None


class InvalidResumeStateError(RuntimeError):
    pass


def _resolve_provider_config(
    provider_config: ModelProviderConfig | None,
    *,
    session_store: ReviewSessionStore,
) -> ModelProviderConfig | None:
    if provider_config is not None:
        return provider_config

    try:
        record = session_store.storage.load_json("model-providers", "xunfei")
    except (FileNotFoundError, StorageError):
        return None
    return ModelProviderConfig.model_validate(record)


def _build_agent_query(
    *,
    project_root_path: str,
    knowledge_base_path: str,
    rules_text: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history[-10:])
    return f"""[项目空间目录地址]
{project_root_path}

[资料库目录地址]
{knowledge_base_path}

[评审规则]
{rules_text}

[历史对话]
{history_text or "(无历史对话)"}

[当前用户消息]
{user_message}
"""


def _build_rules_text(rules: list[PlaybookRule]) -> str:
    if not rules:
        return "(无规则，按资料库与项目上下文谨慎评审)"
    sections: list[str] = []
    for index, rule in enumerate(rules[:12], start=1):
        applicability = "、".join(rule.applicability[:3]) if rule.applicability else "通用"
        failure_modes = "；".join(rule.failure_modes[:2]) if rule.failure_modes else "无"
        prompts = "；".join(rule.review_prompts[:2]) if rule.review_prompts else "无"
        sections.append(
            f"{index}. [{rule.default_severity}] {rule.name} ({rule.category})\n"
            f"适用范围: {applicability}\n"
            f"规则说明: {rule.description}\n"
            f"典型失效模式: {failure_modes}\n"
            f"评审关注点: {prompts}"
        )
    return "\n\n".join(sections)


def _get_active_business_agent() -> BusinessAgentConfig:
    service = BusinessAgentService(JsonStorage(settings.data_dir))
    agents = service.list_agents()
    for agent in agents:
        if agent.is_default or agent.status == "active":
            return agent
    return agents[0]


def _build_agent_instructions(*, project_root_path: str, knowledge_base_path: str) -> str:
    skills_root_path = str((API_ROOT / "skills").resolve())
    try:
        active_agent = _get_active_business_agent()
        role_prompt = active_agent.system_prompt
        agent_name = active_agent.name
    except Exception:
        role_prompt = (
            "你是专业的代码评审智能体。优先识别高风险缺陷、行为回归、边界条件遗漏、测试缺口与设计偏差。"
            "输出保持结构化、直接，并给出可执行的修正建议。"
        )
        agent_name = "代码评审 Agent"
    return (
        f"你当前扮演 ThirdEye 的业务智能体：{agent_name}。\n"
        f"{role_prompt}\n"
        "你必须始终使用中文回复。\n"
        "你只能基于提供的项目空间目录、资料库目录、评审规则和对话上下文进行分析，禁止臆造仓库事实。\n"
        "当用户要求查看、总结、分析文件或目录内容时，你必须优先使用可用的 function tools 主动读取或检索信息，而不是要求用户手工粘贴文件内容。\n"
        "当用户提到技能、PDF、Word、Excel、Markdown、脚本或某类文件处理能力时，你必须先使用 list_skills 检查可用技能；如果存在相关技能，再使用 load_skill 加载技能详情后再回答。\n"
        "在没有先调用 list_skills 或 load_skill 之前，你禁止直接声称“没有某个技能”或“当前环境不支持某类能力”。\n"
        "当你需要写入或修改文件时，只能使用 write_file_chunk 或 replace_in_file。\n"
        "写入文件一律使用 write_file_chunk 分块写入：第一块用 mode='overwrite'，后续块用 mode='append'。\n"
        "调用 write_file_chunk 时，必须同时提供 path 和 content；可选 mode 只能是 overwrite 或 append。\n"
        "调用 replace_in_file 时，必须同时提供 path、old_text、new_text；缺少任一文本参数都是无效调用。\n"
        "在写文件前，先在脑中构造完整内容，再一次性发起合法工具调用，不要用缺参调用试探工具。\n"
        "你在调用工具时，只允许访问以下目录：\n"
        f"1. 项目空间目录：{project_root_path or '(未提供)'}\n"
        f"2. 资料库目录：{knowledge_base_path}\n"
        f"3. 技能目录：{skills_root_path}\n"
        "如果用户请求超出这三个目录，必须明确拒绝并说明原因。\n"
        "优先引用评审规则给出结构化、简洁、可执行的评审意见。"
    )


def _resolve_knowledge_base_path(
    *,
    session_store: ReviewSessionStore,
    session_project_id: str,
    playbook_id: str,
) -> str:
    service = KnowledgeWorkspaceService(session_store.storage)
    try:
        binding = service.get_project_binding(session_project_id)
    except Exception:
        binding = None
    if binding is not None and binding.effective_root_path is not None:
        return str(binding.effective_root_path)
    return str(session_store.storage.root / "playbooks" / playbook_id)


def _select_tool_choice(user_message: str) -> str:
    normalized = user_message.lower()
    file_read_signals = [
        "read_file",
        "查看文件",
        "读取文件",
        "打开文件",
        "看下文件",
        "分析文件",
        ".md",
        ".json",
        ".py",
        "project-summary",
        "rules.json",
    ]
    file_write_signals = [
        "write_file_chunk",
        "replace_in_file",
        "修改文件",
        "写入文件",
        "编辑文件",
        "替换",
        "删除这行",
        "删除这一行",
        "新增一行",
        "更新文件",
    ]
    skill_signals = [
        "load_skill",
        "list_skills",
        "skill",
        "技能",
        "列出技能",
        "加载技能",
        "pdf",
        "word",
        "excel",
        "docx",
        "xlsx",
        "pptx",
        "markdown",
        "md",
    ]
    bash_signals = [
        "bash",
        "命令",
        "shell",
        "powershell",
        "终端",
        "执行命令",
    ]
    if any(token in normalized for token in [*file_read_signals, *file_write_signals, *skill_signals, *bash_signals]):
        return "required"
    return "auto"


def _build_conversation_agent(
    *,
    provider_config: ModelProviderConfig,
    instructions: str,
    tools: list[object],
    tool_choice: str,
) -> Agent[object]:
    return Agent(
        name="ThirdEye Review Conversation Agent",
        instructions=instructions,
        model=build_agent_model(provider_config),
        tools=tools,
        model_settings=ModelSettings(tool_choice=tool_choice),
    )


def _build_review_response(
    *,
    playbook_id: str,
    proposal: str,
    assistant_text: str,
    provider_id: str | None,
    evidence: list[EvidenceItem],
) -> ReviewResponse:
    evidence_ids = [item.id for item in evidence[:5]]
    return ReviewResponse(
        id=f"rev_{uuid4().hex[:12]}",
        playbook_id=playbook_id,
        mode="standard",
        input=proposal,
        execution_mode="llm" if provider_id else "deterministic",
        resolved_provider_id=provider_id,
        execution_note="Generated through skill_agent multi-turn workflow.",
        overall_judgement="有条件通过",
        key_risks=[assistant_text[:160]] if assistant_text.strip() else [],
        playbook_conflicts=[],
        suggested_changes=[],
        required_validation=[],
        missing_information=[],
        findings=[],
        model_provider=provider_id,
    ).model_copy(
        update={
            "findings": [],
            "key_risks": [assistant_text[:160]] if assistant_text.strip() else [],
            "required_validation": ["结合项目技能包继续补充验证步骤。"] if assistant_text.strip() else [],
        }
    )


async def run_agent_chat_turn(
    *,
    session_store: ReviewSessionStore,
    session_id: str,
    playbook: LoadedPlaybook,
    provider_config: ModelProviderConfig | None,
    user_message: str,
) -> AgentChatTurnResult:
    state = session_store.load(session_id).session
    preflight_result = _maybe_run_oss_skill_preflight(user_message)
    if preflight_result is not None:
        review = _build_review_response(
            playbook_id=playbook.metadata.id,
            proposal=user_message,
            assistant_text=preflight_result,
            provider_id=None,
            evidence=playbook.evidence,
        )
        return AgentChatTurnResult(
            assistant_text=preflight_result,
            review=review,
            execution_mode="deterministic",
            resolved_provider_id=None,
            execution_note="Handled by deterministic oss-skill preflight shortcut.",
            tool_events=None,
        )

    history = [
        {"role": message.role, "content": message.content}
        for message in state.messages
        if message.role in {"user", "assistant"}
    ]
    session_project_id = state.project_id or playbook.metadata.project_id
    try:
        project_record = session_store.storage.load_json("projects", session_project_id)
        project_root_path = str(project_record.get("root_path", ""))
    except FileNotFoundError:
        project_root_path = ""
    knowledge_base_path = _resolve_knowledge_base_path(
        session_store=session_store,
        session_project_id=session_project_id,
        playbook_id=playbook.metadata.id,
    )
    rules_text = _build_rules_text(playbook.rules)
    query = _build_agent_query(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
        rules_text=rules_text,
        history=history,
        user_message=user_message,
    )
    sqlite_session = build_sqlite_session(session_id, session_store.sqlite_db_path)
    effective_provider = _resolve_provider_config(provider_config, session_store=session_store)
    if effective_provider is None:
        assistant_text = (
            "当前会话没有可用的大模型配置，无法继续调用智能体工具或执行多轮推理。"
            "请先在设置页配置可用模型，或为本会话选择一个 provider 后重试。"
        )
        review = _build_review_response(
            playbook_id=playbook.metadata.id,
            proposal=user_message,
            assistant_text=assistant_text,
            provider_id=None,
            evidence=playbook.evidence,
        )
        return AgentChatTurnResult(
            assistant_text=assistant_text,
            review=review,
            execution_mode="deterministic",
            resolved_provider_id=None,
            execution_note="No available model provider for multi-turn agent session.",
            tool_events=None,
        )
    instructions = _build_agent_instructions(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
    )
    tools = build_agent_tools(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
    )
    tool_choice = _select_tool_choice(user_message)

    try:
        run_result = await _run_text_agent_compat(
            name="ThirdEye Review Conversation Agent",
            instructions=instructions,
            user_input=query,
            provider_config=effective_provider,
            session=sqlite_session,
            tools=tools,
            model_settings=ModelSettings(tool_choice=tool_choice),
            runtime_event_callback=lambda event: _persist_live_runtime_event(session_store, session_id, event),
        )
        assistant_text = run_result.output_text.strip()
        execution_mode = "llm" if effective_provider is not None else "deterministic"
        resolved_provider_id = effective_provider.id if effective_provider is not None else None
        execution_note = "OpenAI Agents SDK session run completed from local src/agents runtime."
        if run_result.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=run_result.resume_state_json,
                resume_reason=run_result.interrupted_reason or "interruption",
            )
    except ModuleNotFoundError as error:
        assistant_text = (
            "agents sdk 运行环境未就绪，缺少 openai-agents 依赖。"
            "当前已保留本轮消息，请安装依赖后重试。"
        )
        execution_mode = "deterministic"
        resolved_provider_id = None
        execution_note = f"agents sdk dependency missing: {error}"
    except AgentResumeError as error:
        if not error.resumable:
            provider_label = (
                effective_provider.name
                if effective_provider is not None and effective_provider.name
                else effective_provider.id
                if effective_provider is not None
                else "当前模型服务"
            )
            assistant_text = (
                f"{provider_label} 当前不可用，本轮已停止调用大模型。\n\n"
                "请稍后重试，或切换到其他模型配置后继续会话。"
            )
            execution_mode = "deterministic"
            resolved_provider_id = None
            execution_note = f"LLM agent run failed: {summarize_provider_error(error)}"
            review = _build_review_response(
                playbook_id=playbook.metadata.id,
                proposal=user_message,
                assistant_text=assistant_text,
                provider_id=resolved_provider_id,
                evidence=playbook.evidence,
            )
            return AgentChatTurnResult(
                assistant_text=assistant_text,
                review=review,
                execution_mode=execution_mode,
                resolved_provider_id=resolved_provider_id,
                execution_note=execution_note,
                tool_events=None,
            )
        if error.resumable and error.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=error.resume_state_json,
                resume_reason="interruption",
            )
        raise
    except Exception as error:
        provider_label = (
            effective_provider.name
            if effective_provider is not None and effective_provider.name
            else effective_provider.id
            if effective_provider is not None
            else "当前模型服务"
        )
        assistant_text = (
            f"{provider_label} 当前不可用，本轮已停止调用大模型。\n\n"
            "请稍后重试，或切换到其他模型配置后继续会话。"
        )
        execution_mode = "deterministic"
        resolved_provider_id = None
        execution_note = f"LLM agent run failed: {summarize_provider_error(error)}"

    review = _build_review_response(
        playbook_id=playbook.metadata.id,
        proposal=user_message,
        assistant_text=assistant_text,
        provider_id=resolved_provider_id,
        evidence=playbook.evidence,
    )
    return AgentChatTurnResult(
        assistant_text=assistant_text,
        review=review,
        execution_mode=execution_mode,
        resolved_provider_id=resolved_provider_id,
        execution_note=execution_note,
        tool_events=run_result.tool_events if 'run_result' in locals() else None,
    )


async def resume_agent_chat_turn(
    *,
    session_store: ReviewSessionStore,
    session_id: str,
    playbook: LoadedPlaybook,
    provider_config: ModelProviderConfig | None,
) -> AgentChatTurnResult:
    state = session_store.load(session_id).session
    effective_provider = _resolve_provider_config(provider_config, session_store=session_store)
    if effective_provider is None:
        assistant_text = "当前会话没有可用的大模型配置，无法从断点恢复执行。请先配置或选择可用 provider。"
        review = _build_review_response(
            playbook_id=playbook.metadata.id,
            proposal="resume",
            assistant_text=assistant_text,
            provider_id=None,
            evidence=playbook.evidence,
        )
        return AgentChatTurnResult(
            assistant_text=assistant_text,
            review=review,
            execution_mode="deterministic",
            resolved_provider_id=None,
            execution_note="No available model provider for resume.",
            tool_events=None,
        )

    session_project_id = state.project_id or playbook.metadata.project_id
    try:
        project_record = session_store.storage.load_json("projects", session_project_id)
        project_root_path = str(project_record.get("root_path", ""))
    except FileNotFoundError:
        project_root_path = ""
    knowledge_base_path = _resolve_knowledge_base_path(
        session_store=session_store,
        session_project_id=session_project_id,
        playbook_id=playbook.metadata.id,
    )
    instructions = _build_agent_instructions(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
    )
    tools = build_agent_tools(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
    )
    tool_choice = "auto"
    sqlite_session = build_sqlite_session(session_id, session_store.sqlite_db_path)
    resume_state_json = session_store.load_resume_state(session_id)
    try:
        resume_state = await RunState.from_json(
            _build_conversation_agent(
                provider_config=effective_provider,
                instructions=instructions,
                tools=tools,
                tool_choice=tool_choice,
            ),
            resume_state_json,
            context_override=build_log_context(name="ThirdEye Review Conversation Agent", provider_config=effective_provider),
        )
    except Exception as error:
        session_store.clear_resume_state(session_id)
        raise InvalidResumeStateError("保存的断点无效或已过期，无法继续恢复，请重新发起任务。") from error

    try:
        run_result = await _run_text_agent_compat(
            name="ThirdEye Review Conversation Agent",
            instructions=instructions,
            user_input="",
            provider_config=effective_provider,
            session=sqlite_session,
            tools=tools,
            model_settings=ModelSettings(tool_choice=tool_choice),
            resume_state=resume_state,
            runtime_event_callback=lambda event: _persist_live_runtime_event(session_store, session_id, event),
        )
        assistant_text = run_result.output_text.strip()
        if run_result.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=run_result.resume_state_json,
                resume_reason=run_result.interrupted_reason or "interruption",
            )
        else:
            session_store.clear_resume_state(session_id)
        execution_mode = "llm"
        resolved_provider_id = effective_provider.id
        execution_note = "OpenAI Agents SDK session resumed from persisted RunState."
    except AgentResumeError as error:
        if not error.resumable:
            session_store.clear_resume_state(session_id)
            provider_label = (
                effective_provider.name
                if effective_provider.name
                else effective_provider.id
            )
            assistant_text = (
                f"{provider_label} 在继续执行时返回了不可恢复错误，当前断点已清除。\n\n"
                "请重新发送任务，或切换到其他模型配置后再试。"
            )
            review = _build_review_response(
                playbook_id=playbook.metadata.id,
                proposal="resume",
                assistant_text=assistant_text,
                provider_id=None,
                evidence=playbook.evidence,
            )
            return AgentChatTurnResult(
                assistant_text=assistant_text,
                review=review,
                execution_mode="deterministic",
                resolved_provider_id=None,
                execution_note=f"LLM resume failed: {summarize_provider_error(error)}",
                tool_events=None,
            )
        if error.resumable and error.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=error.resume_state_json,
                resume_reason="interruption",
            )
        raise

    review = _build_review_response(
        playbook_id=playbook.metadata.id,
        proposal="resume",
        assistant_text=assistant_text,
        provider_id=resolved_provider_id,
        evidence=playbook.evidence,
    )
    return AgentChatTurnResult(
        assistant_text=assistant_text,
        review=review,
        execution_mode=execution_mode,
        resolved_provider_id=resolved_provider_id,
        execution_note=execution_note,
        tool_events=run_result.tool_events if 'run_result' in locals() else None,
    )
