#!/usr/bin/env python3
"""
skill_agent.py - 使用 OpenAI Agent SDK 调用 skill 执行 agent 任务

基于 s05_skill_loading.py 的双层 skill 注入逻辑：
    Layer 1 (cheap): skill 名称和描述在 system prompt (~100 tokens/skill)
    Layer 2 (on demand): 完整 skill body 在 tool_result 中返回

核心思想："不要把所有内容都放在 system prompt 中，按需加载"
"""

import os
import re
import subprocess
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

SCRIPT_ROOT = Path(__file__).resolve().parent
API_ROOT = SCRIPT_ROOT.parent
PROJECT_ROOT = API_ROOT.parent.parent  # F:\codebaby\ThirdEye
WORKDIR = API_ROOT
SKILLS_DIR = API_ROOT / "skills"
logger = logging.getLogger("skill_agent")
MAX_TOOL_RESULT_CHARS = 1600
MAX_REQUEST_MESSAGES = 8
DEFAULT_READ_LIMIT = 200
MAX_READ_LIMIT = 400
MAX_WRITE_CONTENT_CHARS = 12000
REQUIRED_TOOL_ARGS: dict[str, tuple[str, ...]] = {
    "bash": ("command",),
    "read_file": ("path",),
    "write_file_chunk": ("path", "content"),
    "replace_in_file": ("path", "old_text", "new_text"),
    "load_skill": ("name",),
    "list_skills": (),
}

OSS_SKILL_PREFLIGHT_SCRIPT = PROJECT_ROOT / "scripts" / "run_oss_skill_with_preflight.py"

def _clip_text(value: Any, limit: int = 240) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "..."


def _clip_tool_result(value: Any, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "\n... [truncated]"


def _extract_oss_skill_target(query: str) -> Path | None:
    normalized = query.lower()
    if "oss-skill" not in normalized and "蒸馏" not in query:
        return None
    matches = re.findall(r"[A-Za-z]:\\\\[^\n\r\"']+|[A-Za-z]:\\[^\n\r\"']+", query)
    for raw in matches:
        candidate = Path(raw)
        if candidate.is_absolute():
            return candidate
    return None


def _maybe_run_oss_skill_preflight(query: str) -> str | None:
    target = _extract_oss_skill_target(query)
    if target is None:
        return None
    if "oss-skill" not in query and "蒸馏" not in query:
        return None
    if not OSS_SKILL_PREFLIGHT_SCRIPT.exists():
        return None
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(OSS_SKILL_PREFLIGHT_SCRIPT),
                "--target-project",
                str(target),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=180,
        )
    except Exception as error:
        return f"oss-skill preflight failed before agent execution: {error}"

    report_path = PROJECT_ROOT / "data" / "test-reports" / "oss_skill_preflight_run_result.md"
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8", errors="ignore")
        if completed.returncode == 0:
            return report
        return report + f"\n\n[preflight-exit-code] {completed.returncode}"

    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode == 0:
        return output
    return output + f"\n\n[preflight-exit-code] {completed.returncode}"


def _summarize_message_payload(message: Any) -> dict[str, Any]:
    if not isinstance(message, dict):
        return {"type": type(message).__name__, "preview": _clip_text(message, 200)}

    summary: dict[str, Any] = {"role": message.get("role")}
    if "name" in message:
        summary["name"] = message.get("name")
    if "tool_call_id" in message:
        summary["tool_call_id"] = message.get("tool_call_id")
    if "content" in message:
        summary["content_preview"] = _clip_text(message.get("content", ""), 200)
    if "tool_calls" in message:
        summary["tool_calls"] = [
            {
                "id": tool_call.get("id"),
                "name": tool_call.get("function", {}).get("name"),
                "arguments_preview": _clip_text(tool_call.get("function", {}).get("arguments", ""), 200),
            }
            for tool_call in message.get("tool_calls", [])
            if isinstance(tool_call, dict)
        ]
    return summary


def load_model_config(config_path: Optional[Path] = None) -> Optional[dict]:
    """从 JSON 文件加载模型配置"""
    if config_path is None:
        # 默认尝试加载讯飞配置
        config_path = PROJECT_ROOT / "data" / "model-providers" / "xunfei.json"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Error] Failed to load model config: {e}")
        return None


# =============================================================================
# SkillLoader: 解析 skills/*.md 文件（带 YAML frontmatter）
# =============================================================================
class SkillLoader:
    """加载和管理 skill 文件"""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, dict] = {}
        self._load_all()

    def _load_all(self):
        """加载所有 skill 文件"""
        if not self.skills_dir.exists():
            print(f"[SkillLoader] Skills directory not found: {self.skills_dir}")
            return

        # 加载根目录的 *.md 文件
        for f in sorted(self.skills_dir.glob("*.md")):
            name = f.stem
            text = f.read_text(encoding="utf-8")
            meta, body = self._parse_frontmatter(text)
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}
            print(f"[SkillLoader] Loaded skill: {name}")

        # 加载子目录中的 SKILL.md 文件
        for d in sorted(self.skills_dir.iterdir()):
            if d.is_dir():
                skill_file = d / "SKILL.md"
                if skill_file.exists():
                    name = d.name
                    text = skill_file.read_text(encoding="utf-8")
                    meta, body = self._parse_frontmatter(text)
                    self.skills[name] = {"meta": meta, "body": body, "path": str(skill_file)}
                    print(f"[SkillLoader] Loaded skill: {name} (from {skill_file})")

    def _parse_frontmatter(self, text: str) -> tuple[dict, str]:
        """解析 YAML frontmatter（--- 分隔符之间的内容）"""
        import yaml

        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text

        try:
            meta = yaml.safe_load(match.group(1).strip())
            if meta is None:
                meta = {}
        except Exception:
            # 回退到简单解析器
            meta = {}
            for line in match.group(1).strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip()

        return meta, match.group(2).strip()

    def get_descriptions(self) -> str:
        """Layer 1: 简短描述，用于 system prompt"""
        if not self.skills:
            return "(no skills available)"

        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "No description")
            tags = skill["meta"].get("tags", "")
            line = f"  - {name}: {desc}"
            if tags:
                line += f" [{tags}]"
            lines.append(line)

        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """Layer 2: 完整 skill body，在 tool_result 中返回"""
        skill = self.skills.get(name)
        if not skill:
            available = ", ".join(self.skills.keys())
            return f"Error: Unknown skill '{name}'. Available: {available}"

        return f'<skill name="{name}">\n{skill["body"]}\n</skill>'

    def list_skills(self) -> list[str]:
        """返回所有可用的 skill 名称"""
        return list(self.skills.keys())


# =============================================================================
# 工具实现
# =============================================================================
def safe_path(p: str, workdir: Path, allowed_roots: Optional[list[Path]] = None) -> Path:
    """安全检查文件路径，防止路径遍历攻击，同时允许访问明确授权的根目录。"""
    candidate = Path(p)
    path = (candidate if candidate.is_absolute() else workdir / candidate).resolve()
    roots = [workdir.resolve(), *(root.resolve() for root in (allowed_roots or []))]
    if any(path == root or root in path.parents for root in roots):
        return path
    raise ValueError(f"Path escapes workspace: {p}")


def run_bash(command: str, workdir: Path) -> str:
    """执行 bash 命令"""
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"

    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=False,
            timeout=120,
        )

        def decode_output(raw: bytes | None) -> str:
            if not raw:
                return ""
            for encoding in ("utf-8", "gb18030", "gbk"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")

        stdout_text = decode_output(r.stdout)
        stderr_text = decode_output(r.stderr)
        out = (stdout_text + stderr_text).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, workdir: Path, limit: Optional[int] = None, allowed_roots: Optional[list[Path]] = None) -> str:
    """读取文件内容"""
    try:
        effective_limit = DEFAULT_READ_LIMIT if limit is None else max(1, min(limit, MAX_READ_LIMIT))
        lines = safe_path(path, workdir, allowed_roots).read_text(encoding="utf-8").splitlines()
        if effective_limit < len(lines):
            lines = lines[:effective_limit] + [f"... ({len(lines) - effective_limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(
    path: str,
    content: str,
    workdir: Path,
    allowed_roots: Optional[list[Path]] = None,
    *,
    overwrite: bool = True,
) -> str:
    """写入或追加文件内容"""
    try:
        if len(content) > MAX_WRITE_CONTENT_CHARS:
            return (
                f"Error: write_file_chunk content too large ({len(content)} chars). "
                f"Limit is {MAX_WRITE_CONTENT_CHARS}. Prefer replace_in_file for targeted updates."
            )
        fp = safe_path(path, workdir, allowed_roots)
        fp.parent.mkdir(parents=True, exist_ok=True)
        if overwrite:
            fp.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} bytes to {path}"
        with fp.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return f"Appended {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str, workdir: Path, allowed_roots: Optional[list[Path]] = None) -> str:
    """编辑文件内容（替换文本）"""
    try:
        fp = safe_path(path, workdir, allowed_roots)
        content = fp.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_list_skills(loader: SkillLoader) -> str:
    """列出所有可用的 skills"""
    skills = loader.list_skills()
    if not skills:
        return "No skills available"

    lines = [f"Available skills ({len(skills)}):"]
    for name in skills:
        skill = loader.skills.get(name, {})
        meta = skill.get("meta", {})
        desc = _clip_text(meta.get("description", "No description"), 120)
        lines.append(f"  - {name}: {desc}")

    lines.append("Use load_skill(name) to inspect one skill in detail.")
    return "\n".join(lines)


class NativeSkillAgent:
    """使用原生 OpenAI 客户端执行带工具的 skill agent。"""

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: Optional[str],
        model: str,
        workdir: Path,
        allowed_roots: Optional[list[Path]],
        loader: SkillLoader,
    ) -> None:
        from openai import OpenAI

        self.model = model
        self.loader = loader
        self.workdir = workdir.resolve()
        self.allowed_roots = [root.resolve() for root in (allowed_roots or [])]
        client_kwargs: dict[str, str] = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)
        self.tools = self._build_tools()
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        skill_descriptions = self.loader.get_descriptions()
        return f"""You are a coding agent at {self.workdir}.
You have access to specialized skills that contain expert knowledge for various tasks.
The execution environment is Windows, and shell commands run in PowerShell/cmd-style semantics.
Do not assume bash/Unix utilities like pwd, ls, cat, grep, or shell pipelines will work.
Prefer Windows-native commands such as dir, Get-ChildItem, Get-Content, Select-String, and explicit quoted paths.
When the user provides an absolute local path, treat it as real and inspect that path directly instead of probing the workspace first.
For repository inspection, avoid broad recursive shell listings when a targeted file read or a narrower directory listing will do.

Available skills (use load_skill to get full details):
{skill_descriptions}

When facing unfamiliar tasks:
1. First check if a relevant skill exists using list_skills
2. Load the skill using load_skill to get detailed instructions
3. Follow the skill's guidance to complete the task

Always use safe_file_path patterns when reading/writing files.
When calling tools, arguments must be strict JSON.
Escape all quotes and newlines correctly inside JSON strings.
Prefer smaller edits when possible; avoid sending oversized write payloads if replace_in_file can achieve the same goal.
For read_file, always prefer a small limit and inspect files incrementally.
When writing files, only use write_file_chunk. First chunk must use mode='overwrite', later chunks must use mode='append'.
Do not use write_file_chunk for very large single payloads; prefer replace_in_file for focused changes.
"""

    def _build_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Run a Windows PowerShell/cmd-style shell command and return output. Prefer dir, Get-ChildItem, Get-Content, Select-String, and quoted absolute paths.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to execute"}
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "limit": {"type": "integer", "description": "Optional max lines to read"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file_chunk",
                    "description": "Write one plain-text chunk into a file. Use mode='overwrite' for the first chunk and mode='append' for later chunks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "Plain text content chunk"},
                            "mode": {
                                "type": "string",
                                "description": "Write mode",
                                "enum": ["overwrite", "append"],
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "replace_in_file",
                    "description": "Replace the first occurrence of old_text with new_text in a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "old_text": {"type": "string", "description": "Original text to replace"},
                            "new_text": {"type": "string", "description": "Replacement text"},
                        },
                        "required": ["path", "old_text", "new_text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "load_skill",
                    "description": "Load a skill by name to get detailed instructions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Skill name"}
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_skills",
                    "description": "List all available skills",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
        ]

    def _execute_tool(self, name: str, args: dict[str, Any]) -> str:
        logger.info("[SkillAgent] Tool start: %s args=%s", name, _clip_text(json.dumps(args, ensure_ascii=False)))
        missing = [key for key in REQUIRED_TOOL_ARGS.get(name, ()) if key not in args or args[key] in (None, "")]
        if missing:
            result = f"Error: missing required arguments for {name}: {', '.join(missing)}"
            logger.warning("[SkillAgent] Tool args missing: %s missing=%s", name, ", ".join(missing))
            logger.info("[SkillAgent] Tool done: %s result=%s", name, _clip_text(result))
            return result

        if name == "bash":
            result = run_bash(args["command"], self.workdir)
        elif name == "read_file":
            result = run_read(args["path"], self.workdir, args.get("limit"), self.allowed_roots)
        elif name == "write_file_chunk":
            result = run_write(
                args["path"],
                args["content"],
                self.workdir,
                self.allowed_roots,
                overwrite=(args.get("mode") or "append") == "overwrite",
            )
        elif name == "replace_in_file":
            result = run_edit(args["path"], args["old_text"], args["new_text"], self.workdir, self.allowed_roots)
        elif name == "load_skill":
            result = self.loader.get_content(args["name"])
        elif name == "list_skills":
            result = run_list_skills(self.loader)
        else:
            result = f"Error: Unknown tool '{name}'"
        clipped = _clip_tool_result(result)
        logger.info("[SkillAgent] Tool done: %s result=%s", name, _clip_text(clipped))
        return clipped

    def _assistant_message_to_dict(self, assistant_message: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": "assistant",
        }
        if getattr(assistant_message, "content", None):
            payload["content"] = assistant_message.content
        else:
            payload["content"] = ""

        tool_calls = getattr(assistant_message, "tool_calls", None)
        if tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments or "{}",
                    },
                }
                for tool_call in tool_calls
            ]
        return payload

    def _parse_tool_args(self, tool_name: str, raw_args: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            parsed = json.loads(raw_args or "{}")
        except json.JSONDecodeError as error:
            logger.warning(
                "[SkillAgent] Tool args parse failed: tool=%s error=%s raw=%s",
                tool_name,
                error,
                _clip_text(raw_args, 800),
            )
            return None, (
                f"Error: tool arguments for {tool_name} were not valid JSON: {error}. "
                "Retry with strict JSON and properly escaped strings."
            )

        if not isinstance(parsed, dict):
            logger.warning(
                "[SkillAgent] Tool args must be object: tool=%s raw=%s",
                tool_name,
                _clip_text(raw_args, 800),
            )
            return None, f"Error: tool arguments for {tool_name} must decode to a JSON object."

        return parsed, None

    def _build_request_messages(self, messages: list[Any]) -> list[Any]:
        if len(messages) <= MAX_REQUEST_MESSAGES + 1:
            return messages

        trailing_block_start = len(messages) - 1
        for index in range(len(messages) - 1, 0, -1):
            message = messages[index]
            if isinstance(message, dict) and message.get("role") == "assistant" and message.get("tool_calls"):
                trailing_block_start = index
                break

        trailing_block = messages[trailing_block_start:]
        prefix_budget = max(0, MAX_REQUEST_MESSAGES - len(trailing_block))
        conversational_prefix = [
            message
            for message in messages[1:trailing_block_start]
            if not (isinstance(message, dict) and message.get("role") == "tool")
        ]
        trimmed = [messages[0], *conversational_prefix[-prefix_budget:], *trailing_block]
        logger.info(
            "[SkillAgent] Request message window trimmed original=%s kept=%s",
            len(messages),
            len(trimmed),
        )
        return trimmed

    def chat(self, message: str, max_turns: int = 100) -> str:
        messages: list[Any] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message},
        ]

        logger.info("[SkillAgent] Chat start model=%s max_turns=%s", self.model, max_turns)
        logger.info("[SkillAgent] User input=%s", _clip_text(message, 500))

        for turn_index in range(max_turns):
            logger.info("[SkillAgent] Turn %s request start", turn_index + 1)
            logger.info(
                "[SkillAgent] Turn %s payload summary=%s",
                turn_index + 1,
                json.dumps(
                    {
                        "message_count": len(messages),
                        "messages": [_summarize_message_payload(message) for message in messages[-6:]],
                        "tool_count": len(self.tools),
                        "tool_names": [tool.get("function", {}).get("name") for tool in self.tools],
                    },
                    ensure_ascii=False,
                ),
            )
            request_messages = self._build_request_messages(messages)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                tools=self.tools,
                tool_choice="auto",
            )
            choice = response.choices[0]
            assistant_message = choice.message

            if assistant_message.tool_calls:
                logger.info(
                    "[SkillAgent] Turn %s tool_calls=%s",
                    turn_index + 1,
                    ", ".join(tool_call.function.name for tool_call in assistant_message.tool_calls),
                )
                messages.append(self._assistant_message_to_dict(assistant_message))
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    raw_args = tool_call.function.arguments or "{}"
                    tool_args, parse_error = self._parse_tool_args(tool_name, raw_args)
                    tool_result = parse_error if parse_error else self._execute_tool(tool_name, tool_args or {})
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": tool_result,
                        }
                    )
                continue

            final_text = str(assistant_message.content or "")
            logger.info("[SkillAgent] Turn %s final response=%s", turn_index + 1, _clip_text(final_text, 500))
            logger.info("[SkillAgent] Chat completed turns=%s", turn_index + 1)
            return final_text

        logger.warning("[SkillAgent] Chat hit max turns=%s without final response", max_turns)
        return "Agent error: reached maximum tool-call turns without a final response"


# =============================================================================
# OpenAI Skill Agent 工厂
# =============================================================================
def create_openai_agent_with_skills(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o",
    skills_dir: Optional[Path] = None,
    config_path: Optional[Path] = None,
    workdir: Optional[Path] = None,
    allowed_roots: Optional[list[Path]] = None,
) -> tuple:
    config = load_model_config(config_path)
    if config:
        print(f"[Config] Loaded model config from {config_path or 'default path'}")
        api_key = api_key or config.get("api_key")
        base_url = base_url or config.get("base_url")
        model = model or config.get("model", model)

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url

    loader = SkillLoader(skills_dir or SKILLS_DIR)
    agent = NativeSkillAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        workdir=workdir or PROJECT_ROOT,
        allowed_roots=allowed_roots,
        loader=loader,
    )
    return agent, loader, agent.tools


async def run_skill_agent(
    query: str,
    agent=None,
    loader: Optional[SkillLoader] = None,
    workdir: Optional[Path] = None,
    max_turns: int = 100,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    tracing_disabled: bool = True,
) -> str:
    """
    运行 skill agent 处理用户查询

    Args:
        query: 用户查询
        agent: Agent 实例（可选，会创建默认的）
        loader: SkillLoader 实例
        workdir: 工作目录
        max_turns: 最大回合数
        api_key: API key（可选）
        base_url: API base URL（可选）

    Returns:
        agent 响应文本
    """
    workdir = workdir or WORKDIR

    if agent is None:
        agent, loader, _ = create_openai_agent_with_skills()

    print(f"\n[Agent] Processing: {query}")
    print("-" * 50)
    logger.info("[SkillAgent] Processing new query")

    preflight_result = _maybe_run_oss_skill_preflight(query)
    if preflight_result is not None:
        logger.info("[SkillAgent] Routed oss-skill request through deterministic preflight")
        return preflight_result

    try:
        result = await asyncio.to_thread(agent.chat, query, max_turns)
        logger.info("[SkillAgent] Query finished result=%s", _clip_text(result, 500))
        return result
    except Exception as e:
        print(f"[Agent] Error: {e}")
        logger.exception("[SkillAgent] Query failed")
        return f"Agent error: {e}"


# =============================================================================
# 同步版本（用于简单脚本）
# =============================================================================
def run_skill_agent_sync(
    query: str,
    skills_dir: Optional[Path] = None,
    model: str = None,  # 默认为 None，从配置文件加载
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    config_path: Optional[Path] = None,
    max_turns: int = 100,
) -> str:
    """
    同步运行 skill agent（使用 threading 包装异步调用）

    Args:
        query: 用户查询
        skills_dir: skill 目录
        model: 模型名称（可选，默认从配置文件加载）
        api_key: API key（可选，优先从配置文件加载）
        base_url: API base URL（可选，优先从配置文件加载）
        config_path: 模型配置文件路径（可选）
        max_turns: 最大回合数

    Returns:
        agent 响应文本
    """
    # 创建 agent
    agent, loader, _ = create_openai_agent_with_skills(
        api_key=api_key,
        base_url=base_url,
        model=model,
        skills_dir=skills_dir,
        config_path=config_path,
    )

    # 运行异步代码
    return asyncio.run(run_skill_agent(query, agent, loader, max_turns=max_turns))


# =============================================================================
# CLI 入口
# =============================================================================
if __name__ == "__main__":
    import sys
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Skill Agent - 使用 OpenAI Agent SDK 调用 skill")
    parser.add_argument("query", nargs="*", help="用户查询（可选，进入交互模式如果未提供）")
    parser.add_argument("--config", "-c", type=Path, default=None, help="模型配置文件路径")
    parser.add_argument("--skills-dir", type=Path, default=None, help="Skill 目录路径")
    parser.add_argument("--list", action="store_true", help="列出所有可用 skills")

    args = parser.parse_args()

    # 显示可用 skills
    loader = SkillLoader(args.skills_dir or SKILLS_DIR)
    print("\n=== Available Skills ===")
    print(loader.get_descriptions())
    print()

    # 如果指定 --list，只列出 skills
    if args.list:
        sys.exit(0)

    # 检查命令行参数
    if args.query:
        # 直接执行命令行查询
        query = " ".join(args.query)
        print(f"Query: {query}")
        result = run_skill_agent_sync(query, config_path=args.config, skills_dir=args.skills_dir)
        print(f"\n[Agent] {result}")
    else:
        # 交互模式
        print("Entering interactive mode. Type 'quit' to exit.\n")

        history = []
        while True:
            try:
                query = input("\033[36mskill-agent >> \033[0m")
            except (EOFError, KeyboardInterrupt):
                break

            if query.strip().lower() in ("q", "quit", "exit"):
                break

            if not query.strip():
                continue

            history.append(query)
            result = run_skill_agent_sync("\n".join(history), config_path=args.config)
            print(f"\n[Agent] {result}")
            print()
