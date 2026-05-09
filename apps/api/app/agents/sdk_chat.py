from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from agents import ModelSettings, function_tool
from agents import Agent, RunState

from app.agents.sdk_runtime import AgentResumeError, build_agent_model, build_run_config, build_sqlite_session, run_text_agent
from app.model_providers.llm_client import summarize_provider_error
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.playbook import EvidenceItem, PlaybookRule
from app.schemas.review import ReviewResponse
from app.services.playbook_loader import LoadedPlaybook
from app.services.review_sessions import ReviewSessionStore
from app.services.storage import StorageError
from scripts.skill_agent import (
    MAX_READ_LIMIT,
    MAX_WRITE_CONTENT_CHARS,
    SkillLoader,
    decode_text_arg,
    run_bash,
    run_edit,
    run_list_skills,
    run_read,
    run_write,
)

API_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AgentChatTurnResult:
    assistant_text: str
    review: ReviewResponse | None
    execution_mode: str
    resolved_provider_id: str | None
    execution_note: str | None


class InvalidResumeStateError(RuntimeError):
    pass


def _normalize_allowed_roots(project_root_path: str, knowledge_base_path: str) -> list[Path]:
    roots: list[Path] = []
    if project_root_path.strip():
        roots.append(Path(project_root_path).resolve())
    roots.append(Path(knowledge_base_path).resolve())
    deduped: list[Path] = []
    for root in roots:
        if root not in deduped:
            deduped.append(root)
    return deduped


def _resolve_allowed_path(value: str, *, allowed_roots: list[Path], default_root: Path) -> Path:
    raw = value.strip()
    target = Path(raw) if raw else default_root
    if not target.is_absolute():
        target = (default_root / target).resolve()
    else:
        target = target.resolve()
    if any(target == root or root in target.parents for root in allowed_roots):
        return target
    raise ValueError(
        "path is outside the allowed roots; only the configured project directory and knowledge base directory are accessible"
    )


def _read_allowed_file_payload(path: str, *, allowed_roots: list[Path], default_root: Path) -> str:
    target = _resolve_allowed_path(path, allowed_roots=allowed_roots, default_root=default_root)
    if not target.exists():
        return f"file not found: {target}"
    if not target.is_file():
        return f"path is not a file: {target}"
    content = target.read_text(encoding="utf-8", errors="ignore")
    clipped = content[:12000]
    return json.dumps(
        {
            "path": str(target),
            "truncated": len(content) > len(clipped),
            "content": clipped,
        },
        ensure_ascii=False,
    )


def _load_skill_loader() -> SkillLoader:
    skills_dir = API_ROOT / "skills"
    return SkillLoader(skills_dir)


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


def _build_agent_instructions(*, project_root_path: str, knowledge_base_path: str) -> str:
    return (
        "你是 ThirdEye 的多轮技术评审 Agent。\n"
        "你必须始终使用中文回复。\n"
        "你只能基于提供的项目空间目录、资料库目录、评审规则和对话上下文进行分析，禁止臆造仓库事实。\n"
        "当用户要求查看、总结、分析文件或目录内容时，你必须优先使用可用的 function tools 主动读取或检索信息，而不是要求用户手工粘贴文件内容。\n"
        "当用户提到技能、PDF、Word、Excel、Markdown、脚本或某类文件处理能力时，你必须先使用 list_skills 检查可用技能；如果存在相关技能，再使用 load_skill 加载技能详情后再回答。\n"
        "在没有先调用 list_skills 或 load_skill 之前，你禁止直接声称“没有某个技能”或“当前环境不支持某类能力”。\n"
        "当你调用 write_file 或 edit_file 且内容包含多行、大段 Markdown、代码、引号或反斜杠时，优先使用 base64 字段传参，避免 JSON 转义损坏：write_file 用 content_base64，edit_file 用 old_text_base64/new_text_base64。\n"
        "你在调用工具时，只允许访问以下目录：\n"
        f"1. 项目空间目录：{project_root_path or '(未提供)'}\n"
        f"2. 资料库目录：{knowledge_base_path}\n"
        "如果用户请求超出这两个目录，必须明确拒绝并说明原因。\n"
        "优先引用评审规则给出结构化、简洁、可执行的评审意见。"
    )


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
        "write_file",
        "edit_file",
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


def _build_agent_tools(*, project_root_path: str, knowledge_base_path: str) -> list[object]:
    allowed_roots = _normalize_allowed_roots(project_root_path, knowledge_base_path)
    default_root = allowed_roots[0]
    workdir = default_root
    skill_loader = _load_skill_loader()

    @function_tool(name_override="bash")
    def bash(command: str) -> str:
        """Run a shell command inside the allowed workspace root and return stdout/stderr."""
        return run_bash(command, workdir)

    @function_tool(name_override="read_file")
    def read_file(path: str, limit: int = MAX_READ_LIMIT) -> str:
        """Read a text file from the allowed project or knowledge base directories."""
        return run_read(path, workdir, limit, allowed_roots)

    @function_tool(name_override="write_file")
    def write_file(path: str, content: str | None = None, content_base64: str | None = None) -> str:
        """Write text content to an allowed file. Use content_base64 for long or multi-line UTF-8 text."""
        try:
            resolved_content = decode_text_arg(
                plain_value=content,
                base64_value=content_base64,
                arg_name="content",
            )
        except ValueError as error:
            return f"Error: {error}"
        if len(resolved_content) > MAX_WRITE_CONTENT_CHARS:
            return (
                f"Error: write_file content too large ({len(resolved_content)} chars). "
                f"Limit is {MAX_WRITE_CONTENT_CHARS}. Prefer edit_file for targeted updates."
            )
        return run_write(path, resolved_content, workdir, allowed_roots)

    @function_tool(name_override="edit_file")
    def edit_file(
        path: str,
        old_text: str | None = None,
        new_text: str | None = None,
        old_text_base64: str | None = None,
        new_text_base64: str | None = None,
    ) -> str:
        """Replace the first occurrence of old_text with new_text in an allowed file. Use *_base64 for long or multi-line UTF-8 text."""
        try:
            resolved_old_text = decode_text_arg(
                plain_value=old_text,
                base64_value=old_text_base64,
                arg_name="old_text",
            )
            resolved_new_text = decode_text_arg(
                plain_value=new_text,
                base64_value=new_text_base64,
                arg_name="new_text",
            )
        except ValueError as error:
            return f"Error: {error}"
        return run_edit(path, resolved_old_text, resolved_new_text, workdir, allowed_roots)

    @function_tool(name_override="load_skill")
    def load_skill(name: str) -> str:
        """Load the full body of a named skill from the local skills directory."""
        return skill_loader.get_content(name)

    @function_tool(name_override="list_skills")
    def list_skills() -> str:
        """List all available local skills with descriptions."""
        return run_list_skills(skill_loader)

    return [bash, read_file, write_file, edit_file, load_skill, list_skills]


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
    knowledge_base_path = str(session_store.storage.root / "playbooks" / playbook.metadata.id)
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
        )
    instructions = _build_agent_instructions(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
    )
    tools = _build_agent_tools(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
    )
    tool_choice = _select_tool_choice(user_message)

    try:
        run_result = await run_text_agent(
            name="ThirdEye Review Conversation Agent",
            instructions=instructions,
            user_input=query,
            provider_config=effective_provider,
            session=sqlite_session,
            tools=tools,
            model_settings=ModelSettings(tool_choice=tool_choice),
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
        if error.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=error.resume_state_json,
                resume_reason="error",
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
        )

    session_project_id = state.project_id or playbook.metadata.project_id
    try:
        project_record = session_store.storage.load_json("projects", session_project_id)
        project_root_path = str(project_record.get("root_path", ""))
    except FileNotFoundError:
        project_root_path = ""
    knowledge_base_path = str(session_store.storage.root / "playbooks" / playbook.metadata.id)
    instructions = _build_agent_instructions(
        project_root_path=project_root_path,
        knowledge_base_path=knowledge_base_path,
    )
    tools = _build_agent_tools(
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
            context_override=None,
        )
    except Exception as error:
        session_store.clear_resume_state(session_id)
        raise InvalidResumeStateError("保存的断点无效或已过期，无法继续恢复，请重新发起任务。") from error

    try:
        run_result = await run_text_agent(
            name="ThirdEye Review Conversation Agent",
            instructions=instructions,
            user_input="",
            provider_config=effective_provider,
            session=sqlite_session,
            tools=tools,
            model_settings=ModelSettings(tool_choice=tool_choice),
            resume_state=resume_state,
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
        if error.resume_state_json is not None:
            session_store.save_resume_state(
                session_id,
                resume_state_json=error.resume_state_json,
                resume_reason="error",
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
    )
