from __future__ import annotations

import json
from pathlib import Path
import sys
import types
from typing import Any

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

from agents import function_tool
from agents.run_context import RunContextWrapper

from app.agents.tool_registry import (
    ToolArgumentSpec,
    format_required_tool_arguments_error,
    validate_tool_json_arguments,
)
from app.core.config import settings
from app.services.tavily_client import TavilyClient
from app.services.skill_registry import SkillRegistryService
from app.services.storage import JsonStorage
from app.services.tavily_settings import TavilySettingsService
from scripts.skill_agent import (
    MAX_READ_LIMIT,
    MAX_WRITE_CONTENT_CHARS,
    SkillLoader,
    run_bash,
    run_edit,
    run_list_skills,
    run_read,
)


def replace_in_file_failure_error(ctx: RunContextWrapper[object], error: Exception) -> str:
    return format_required_tool_arguments_error(
        tool_name="replace_in_file",
        tool_arguments=getattr(ctx, "tool_arguments", ""),
        required_shape='"path", "old_text", and "new_text"',
        example_json='{"path":"...","old_text":"...","new_text":"..."}',
    )


def normalize_allowed_roots(project_root_path: str, knowledge_base_path: str) -> list[Path]:
    roots: list[Path] = []
    if project_root_path.strip():
        roots.append(Path(project_root_path).resolve())
    roots.append(Path(knowledge_base_path).resolve())
    roots.append((API_ROOT / "skills").resolve())
    deduped: list[Path] = []
    for root in roots:
        if root not in deduped:
            deduped.append(root)
    return deduped


def resolve_allowed_path(value: str, *, allowed_roots: list[Path], default_root: Path) -> Path:
    raw = value.strip()
    target = Path(raw) if raw else default_root
    if not target.is_absolute():
        target = (default_root / target).resolve()
    else:
        target = target.resolve()
    if any(target == root or root in target.parents for root in allowed_roots):
        return target
    raise ValueError(
        "path is outside the allowed roots; only the configured project directory, knowledge base directory, and apps/api/skills directory are accessible"
    )


def read_allowed_file_payload(path: str, *, allowed_roots: list[Path], default_root: Path) -> str:
    target = resolve_allowed_path(path, allowed_roots=allowed_roots, default_root=default_root)
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


def load_skill_loader() -> SkillLoader:
    skills_dir = API_ROOT / "skills"
    return SkillRegistryService(JsonStorage(settings.data_dir), skills_dir).enabled_skill_loader()


REPLACE_IN_FILE_SPEC = ToolArgumentSpec(
    required_fields=("path", "old_text", "new_text"),
    example_json='{"path":"...","old_text":"...","new_text":"..."}',
)

WRITE_FILE_CHUNK_SPEC = ToolArgumentSpec(
    required_fields=("path", "content"),
    example_json='{"path":"...","content":"<text chunk>","mode":"append"}',
)

TAVILY_WEB_SEARCH_SPEC = ToolArgumentSpec(
    required_fields=("query",),
    example_json='{"query":"latest OpenAI responses API changes","max_results":5}',
)


def _prevalidate_tool_call(
    ctx: RunContextWrapper[object],
    *,
    tool_name: str,
    spec: ToolArgumentSpec,
) -> str | None:
    _, error_message = validate_tool_json_arguments(
        tool_name=tool_name,
        tool_arguments=getattr(ctx, "tool_arguments", ""),
        spec=spec,
    )
    return error_message


def _run_tavily_search(query: str, max_results: int = 5) -> str:
    tavily_settings = TavilySettingsService(JsonStorage(settings.data_dir)).get_settings()
    if not tavily_settings.enabled:
        return "Error: Tavily web search is disabled in settings."
    if tavily_settings.api_key is None:
        return "Error: Tavily API key is not configured in settings."
    try:
        payload = __import__("asyncio").run(
            TavilyClient().search(
                api_key=tavily_settings.api_key.get_secret_value(),
                query=query,
                max_results=max(1, min(max_results, 10)),
            )
        )
    except Exception as error:
        return f"Error: Tavily search failed: {error}"
    results = payload.get("results", [])
    answer = payload.get("answer")
    return json.dumps(
        {
            "query": query,
            "answer": answer,
            "results": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content"),
                }
                for item in results[:10]
                if isinstance(item, dict)
            ],
        },
        ensure_ascii=False,
    )


def append_text_file(
    path: str,
    content: str,
    workdir: Path,
    allowed_roots: list[Path],
    *,
    overwrite: bool = False,
) -> str:
    try:
        if len(content) > MAX_WRITE_CONTENT_CHARS:
            return (
                f"Error: write_file_chunk content too large ({len(content)} chars). "
                f"Limit is {MAX_WRITE_CONTENT_CHARS}."
            )
        fp = resolve_allowed_path(path, allowed_roots=allowed_roots, default_root=workdir)
        fp.parent.mkdir(parents=True, exist_ok=True)
        if overwrite:
            fp.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} bytes to {fp}"
        with fp.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return f"Appended {len(content)} bytes to {fp}"
    except Exception as error:
        return f"Error: {error}"


def build_agent_tools(*, project_root_path: str, knowledge_base_path: str) -> list[object]:
    allowed_roots = normalize_allowed_roots(project_root_path, knowledge_base_path)
    default_root = allowed_roots[0]
    workdir = default_root
    skill_loader = load_skill_loader()

    @function_tool(name_override="bash")
    def bash(command: str) -> str:
        """Run a shell command inside the allowed workspace root and return stdout/stderr."""
        return run_bash(command, workdir)

    @function_tool(name_override="read_file")
    def read_file(path: str, limit: int = MAX_READ_LIMIT) -> str:
        """Read a text file from the allowed project or knowledge base directories."""
        return run_read(path, workdir, limit, allowed_roots)

    @function_tool(name_override="write_file_chunk")
    def write_file_chunk(
        ctx: RunContextWrapper[object],
        path: str,
        content: str,
        mode: str = "append",
    ) -> str:
        """Append or overwrite a text chunk into an allowed file. Use mode='overwrite' for the first chunk, then 'append'."""
        prevalidation_error = _prevalidate_tool_call(
            ctx,
            tool_name="write_file_chunk",
            spec=WRITE_FILE_CHUNK_SPEC,
        )
        if prevalidation_error is not None:
            return prevalidation_error
        normalized_mode = (mode or "append").strip().lower()
        if normalized_mode not in {"append", "overwrite"}:
            return "Error: write_file_chunk mode must be either 'append' or 'overwrite'."
        return append_text_file(
            path,
            content,
            workdir,
            allowed_roots,
            overwrite=normalized_mode == "overwrite",
        )

    @function_tool(
        name_override="replace_in_file",
        failure_error_function=replace_in_file_failure_error,
    )
    def replace_in_file(
        ctx: RunContextWrapper[object],
        path: str,
        old_text: str,
        new_text: str,
    ) -> str:
        """Replace the first occurrence of old_text with new_text in an allowed file."""
        prevalidation_error = _prevalidate_tool_call(
            ctx,
            tool_name="replace_in_file",
            spec=REPLACE_IN_FILE_SPEC,
        )
        if prevalidation_error is not None:
            return prevalidation_error
        return run_edit(path, old_text, new_text, workdir, allowed_roots)

    @function_tool(name_override="load_skill")
    def load_skill(name: str) -> str:
        """Load the full body of a named skill from the local skills directory."""
        return skill_loader.get_content(name)

    @function_tool(name_override="list_skills")
    def list_skills() -> str:
        """List all available local skills with descriptions."""
        return run_list_skills(skill_loader)

    @function_tool(name_override="tavily_web_search")
    def tavily_web_search(
        ctx: RunContextWrapper[object],
        query: str,
        max_results: int = 5,
    ) -> str:
        """Search the public web through Tavily and return concise result records."""
        prevalidation_error = _prevalidate_tool_call(
            ctx,
            tool_name="tavily_web_search",
            spec=TAVILY_WEB_SEARCH_SPEC,
        )
        if prevalidation_error is not None:
            return prevalidation_error
        return _run_tavily_search(query=query, max_results=max_results)

    return [bash, read_file, write_file_chunk, replace_in_file, load_skill, list_skills, tavily_web_search]
