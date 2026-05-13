from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from app.schemas.model_provider import ModelProviderConfig
from app.schemas.project import Project, ProjectScanSummary
from app.services.playbook_generator import PlaybookArtifacts

logger = logging.getLogger(__name__)
MIN_PROVIDER_TIMEOUT_SECONDS = 150

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
import sys

VENDOR_SITE = REPO_ROOT / ".vendor" / "py312"
if str(VENDOR_SITE) not in sys.path and VENDOR_SITE.exists():
    sys.path.insert(0, str(VENDOR_SITE))

from openai import AsyncOpenAI

OSS_SKILL_ROOT = Path(r"C:\Users\xiaoxuan\.agents\skills\oss-skill")
MAX_READ_CHARS = 12000
MAX_PROJECT_FILES = 24
MAX_CONTEXT_TOKENS = 256_000
TARGET_CONTEXT_TOKENS = 180_000
CHARS_PER_TOKEN_ESTIMATE = 4
ALLOWED_TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
}


def _run_preflight_command(command: str, *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=60,
    )
    return (completed.stdout + completed.stderr).strip()


def _build_preflight_context(project: Project) -> dict[str, object]:
    root = project.root_path.resolve()
    tree = _run_preflight_command(f'dir "{root}" /s /b', cwd=REPO_ROOT)
    java_files = _run_preflight_command(f'dir "{root}" /s /b *.java', cwd=REPO_ROOT)
    md_files = _run_preflight_command(f'dir "{root}" /s /b *.md', cwd=REPO_ROOT)
    pom_files = _run_preflight_command(f'dir "{root}" /s /b pom.xml', cwd=REPO_ROOT)
    return {
        "target_project": str(root),
        "top_tree_preview": tree.splitlines()[:80],
        "java_files_preview": java_files.splitlines()[:80],
        "markdown_files_preview": md_files.splitlines()[:40],
        "pom_files": pom_files.splitlines()[:20],
    }


def _load_oss_skill_bundle() -> tuple[str, list[dict[str, object]]]:
    files = [
        OSS_SKILL_ROOT / "SKILL.md",
        OSS_SKILL_ROOT / "references" / "extraction-framework.md",
        OSS_SKILL_ROOT / "references" / "skill-template.md",
    ]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"oss-skill files not found: {', '.join(missing)}")

    parts: list[str] = []
    metadata: list[dict[str, object]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        parts.append(f"# Source: {path.name}")
        parts.append(text)
        parts.append("")
        metadata.append(
            {
                "path": str(path),
                "name": path.name,
                "size_chars": len(text),
            }
        )
    return "\n".join(parts), metadata


def _candidate_priority(relative_path: str, scan: ProjectScanSummary) -> tuple[int, str]:
    lower = relative_path.lower()
    if lower in {item.lower() for item in scan.docs}:
        return (0, relative_path)
    if lower in {item.lower() for item in scan.entrypoint_candidates}:
        return (1, relative_path)
    if lower in {item.lower() for item in scan.tests}:
        return (2, relative_path)
    if lower in {item.lower() for item in scan.config_files}:
        return (3, relative_path)
    if "src/" in lower or "/src/" in lower:
        return (4, relative_path)
    return (5, relative_path)


def _select_project_files(project: Project, scan: ProjectScanSummary) -> list[str]:
    root = project.root_path.resolve()
    selected: list[str] = []
    seen: set[str] = set()

    seeded = [
        *scan.docs,
        *scan.entrypoint_candidates,
        *scan.tests,
        *scan.config_files,
    ]
    for item in seeded:
        normalized = item.replace("\\", "/")
        if normalized not in seen:
            seen.add(normalized)
            selected.append(normalized)

    for path in sorted(root.rglob("*")):
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        if ".git" in path.parts or "__pycache__" in path.parts or "node_modules" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if relative in seen:
            continue
        if path.suffix.lower() not in ALLOWED_TEXT_SUFFIXES and path.name.lower() not in {
            "readme.md",
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "dockerfile",
            ".gitignore",
        }:
            continue
        seen.add(relative)
        selected.append(relative)

    ordered = sorted(selected, key=lambda item: _candidate_priority(item, scan))
    return ordered[:MAX_PROJECT_FILES]


def _read_project_files(project: Project, relative_paths: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    root = project.root_path.resolve()
    files_payload: list[dict[str, str]] = []
    files_read: list[str] = []
    for relative_path in relative_paths:
        candidate = (root / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            continue
        if not candidate.exists() or not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if len(text) > MAX_READ_CHARS:
            text = text[:MAX_READ_CHARS] + "\n...[truncated]"
        relative_text = candidate.relative_to(root).as_posix()
        files_payload.append({"path": relative_text, "content": text})
        files_read.append(relative_text)
    return files_payload, files_read


def _build_system_prompt() -> str:
    return (
        "You are the backend-orchestrated playbook distillation agent for ThirdEye.\n\n"
        "You will receive:\n"
        "1. The real local oss-skill files.\n"
        "2. Project scan metadata.\n"
        "3. Existing evidence.\n"
        "4. Directly read project file contents selected by the backend.\n\n"
        "5. Deterministic preflight scan results already gathered by the backend.\n\n"
        "Your task is to synthesize a project-specific reusable reviewer skill markdown file and grounded rules.\n"
        "Do not spend turns re-exploring the repository through shell-style discovery. Treat the provided preflight results as authoritative starting context.\n"
        "Do not output progress notes, next steps, or placeholders.\n"
        "Rules must use evidence_ids from the provided evidence list.\n"
        "Return only a JSON object with keys: rules, skill_sections, execution_note.\n"
        "skill_sections must be an object with these keys:\n"
        "- title\n"
        "- overview\n"
        "- activation_rules\n"
        "- heuristics\n"
        "- anti_patterns\n"
        "- review_workflow\n"
        "- validation_expectations\n"
        "- honesty_boundary\n"
        "Each section must use strings or arrays of strings only. Do not return one giant markdown string."
    )


def _render_skill_markdown_from_sections(sections: dict[str, Any]) -> str:
    title = str(sections.get("title") or "Project Reviewer Skill").strip()

    def list_section(name: str, values: Any) -> str:
        if isinstance(values, list):
            items = [f"- {str(item).strip()}" for item in values if str(item).strip()]
            return "\n".join(items) if items else "- None documented."
        if isinstance(values, str) and values.strip():
            return values.strip()
        return "- None documented."

    overview = str(sections.get("overview") or "").strip() or "Project-specific reviewer guidance distilled from repository evidence."
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Overview",
            overview,
            "",
            "## Activation Rules",
            list_section("activation_rules", sections.get("activation_rules")),
            "",
            "## Core Heuristics",
            list_section("heuristics", sections.get("heuristics")),
            "",
            "## Anti-Patterns",
            list_section("anti_patterns", sections.get("anti_patterns")),
            "",
            "## Review Workflow",
            list_section("review_workflow", sections.get("review_workflow")),
            "",
            "## Validation Expectations",
            list_section("validation_expectations", sections.get("validation_expectations")),
            "",
            "## Honesty Boundary",
            list_section("honesty_boundary", sections.get("honesty_boundary")),
        ]
    )


def _estimate_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def _chunk_project_file_payloads(project_files: list[dict[str, str]], token_budget: int) -> list[list[dict[str, str]]]:
    chunks: list[list[dict[str, str]]] = []
    current_chunk: list[dict[str, str]] = []
    current_tokens = 0

    for item in project_files:
        item_tokens = _estimate_tokens(item)
        if current_chunk and current_tokens + item_tokens > token_budget:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0
        current_chunk.append(item)
        current_tokens += item_tokens

    if current_chunk:
        chunks.append(current_chunk)
    return chunks


async def _request_orchestrated_distillation(
    provider_config: ModelProviderConfig,
    payload: dict[str, Any],
) -> dict[str, Any]:
    client = AsyncOpenAI(
        api_key=provider_config.api_key.get_secret_value() if provider_config.api_key else None,
        base_url=provider_config.base_url,
        timeout=float(max(provider_config.timeout_seconds, MIN_PROVIDER_TIMEOUT_SECONDS)),
        max_retries=provider_config.max_retries,
    )
    system_prompt = _build_system_prompt()
    user_content = json.dumps(payload, ensure_ascii=False, indent=2)

    if provider_config.api_shape == "responses":
        response = await client.responses.create(
            model=provider_config.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
        text = getattr(response, "output_text", None)
        if not text:
            raise ValueError("responses API did not return output_text")
    else:
        completion = await client.chat.completions.create(
            model=provider_config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
        text = completion.choices[0].message.content if completion.choices else None
        if not text:
            raise ValueError("chat completions API returned empty content")

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("orchestrated distillation response must be a JSON object")
    skill_sections = parsed.get("skill_sections")
    if isinstance(skill_sections, dict):
        parsed["skill_markdown"] = _render_skill_markdown_from_sections(skill_sections)
    return parsed


async def _request_chunk_distillation(
    provider_config: ModelProviderConfig,
    *,
    project: Project,
    scan: ProjectScanSummary,
    baseline: PlaybookArtifacts,
    evidence: list,
    oss_skill_bundle: str,
    project_files: list[dict[str, str]],
    chunk_index: int,
    chunk_count: int,
) -> dict[str, Any]:
    payload = {
        "phase": "chunk_distillation",
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
        "project": project.model_dump(mode="json"),
        "preflight": _build_preflight_context(project),
        "scan": scan.model_dump(mode="json"),
        "baseline_rules": [rule.model_dump(mode="json") for rule in baseline.rules],
        "baseline_skill_markdown": baseline.skill_markdown,
        "project_summary": baseline.project_summary,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "oss_skill_bundle": oss_skill_bundle,
        "project_files": project_files,
        "instructions": (
            "Distill only the project-specific evidence visible in this chunk. "
            "Return partial rules and partial skill_sections grounded in the provided evidence_ids. "
            "Do not mention that this is a partial result in the sections."
        ),
    }
    return await _request_orchestrated_distillation(provider_config, payload)


async def _request_merge_distillation(
    provider_config: ModelProviderConfig,
    *,
    project: Project,
    scan: ProjectScanSummary,
    baseline: PlaybookArtifacts,
    evidence: list,
    oss_skill_bundle: str,
    chunk_outputs: list[dict[str, Any]],
    selected_project_files: list[str],
) -> dict[str, Any]:
    payload = {
        "phase": "merge_distillation",
        "project": project.model_dump(mode="json"),
        "preflight": _build_preflight_context(project),
        "scan": scan.model_dump(mode="json"),
        "baseline_rules": [rule.model_dump(mode="json") for rule in baseline.rules],
        "baseline_skill_markdown": baseline.skill_markdown,
        "project_summary": baseline.project_summary,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "oss_skill_bundle": oss_skill_bundle,
        "selected_project_files": selected_project_files,
        "chunk_outputs": chunk_outputs,
        "instructions": (
            "Merge the chunk-level distillation results into one final project-specific skill. "
            "Deduplicate rules, preserve grounded evidence_ids, and produce polished final skill_sections."
        ),
    }
    return await _request_orchestrated_distillation(provider_config, payload)


async def run_agent_distillation(
    *,
    provider_config: ModelProviderConfig,
    project: Project,
    scan: ProjectScanSummary,
    evidence: list,
    baseline: PlaybookArtifacts,
) -> dict[str, object]:
    oss_skill_bundle, oss_skill_files = _load_oss_skill_bundle()
    preflight = _build_preflight_context(project)
    selected_project_files = _select_project_files(project, scan)
    project_file_payloads, files_read = _read_project_files(project, selected_project_files)

    logger.info(
        "Loaded local oss-skill bundle: %s",
        json.dumps(
            {
                "workflow": "orchestrated_distillation",
                "project_id": project.id,
                "playbook_id": baseline.metadata.id,
                "source_root": str(OSS_SKILL_ROOT),
                "files": oss_skill_files,
                "preflight": {
                    "tree_count": len(preflight["top_tree_preview"]),
                    "java_count": len(preflight["java_files_preview"]),
                    "md_count": len(preflight["markdown_files_preview"]),
                },
            },
            ensure_ascii=False,
        ),
    )
    logger.info(
        "Prepared project file context: %s",
        json.dumps(
            {
                "workflow": "orchestrated_distillation",
                "project_id": project.id,
                "playbook_id": baseline.metadata.id,
                "selected_files": selected_project_files,
                "files_read": files_read,
            },
            ensure_ascii=False,
        ),
    )

    payload = {
        "project": project.model_dump(mode="json"),
        "preflight": preflight,
        "scan": scan.model_dump(mode="json"),
        "baseline_rules": [rule.model_dump(mode="json") for rule in baseline.rules],
        "baseline_skill_markdown": baseline.skill_markdown,
        "project_summary": baseline.project_summary,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "oss_skill_bundle": oss_skill_bundle,
        "project_files": project_file_payloads,
        "selected_project_files": selected_project_files,
    }
    estimated_tokens = _estimate_tokens(payload)

    logger.info(
        "Orchestrated distillation request: %s",
        json.dumps(
            {
                "provider_id": provider_config.id,
                "provider_type": provider_config.provider_type,
                "api_shape": provider_config.api_shape,
                "base_url": provider_config.base_url,
                "model": provider_config.model,
                "workflow": "orchestrated_distillation",
                "project_id": project.id,
                "playbook_id": baseline.metadata.id,
                "project_file_count": len(project_file_payloads),
                "estimated_tokens": estimated_tokens,
            },
            ensure_ascii=False,
        ),
    )
    if estimated_tokens <= TARGET_CONTEXT_TOKENS:
        response = await _request_orchestrated_distillation(provider_config, payload)
    else:
        base_payload = {
            "project": project.model_dump(mode="json"),
            "scan": scan.model_dump(mode="json"),
            "baseline_rules": [rule.model_dump(mode="json") for rule in baseline.rules],
            "baseline_skill_markdown": baseline.skill_markdown,
            "project_summary": baseline.project_summary,
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "oss_skill_bundle": oss_skill_bundle,
            "selected_project_files": selected_project_files,
        }
        base_tokens = _estimate_tokens(base_payload)
        per_chunk_budget = max(10_000, TARGET_CONTEXT_TOKENS - base_tokens)
        chunks = _chunk_project_file_payloads(project_file_payloads, per_chunk_budget)
        logger.warning(
            "Orchestrated distillation context too large, chunking: %s",
            json.dumps(
                {
                    "workflow": "orchestrated_distillation",
                    "project_id": project.id,
                    "playbook_id": baseline.metadata.id,
                    "estimated_tokens": estimated_tokens,
                    "max_context_tokens": MAX_CONTEXT_TOKENS,
                    "target_context_tokens": TARGET_CONTEXT_TOKENS,
                    "chunk_count": len(chunks),
                    "per_chunk_budget": per_chunk_budget,
                },
                ensure_ascii=False,
            ),
        )
        chunk_outputs: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks, start=1):
            logger.info(
                "Orchestrated distillation chunk request: %s",
                json.dumps(
                    {
                        "workflow": "orchestrated_distillation",
                        "project_id": project.id,
                        "playbook_id": baseline.metadata.id,
                        "chunk_index": index,
                        "chunk_count": len(chunks),
                        "chunk_file_count": len(chunk),
                        "chunk_estimated_tokens": _estimate_tokens(chunk),
                    },
                    ensure_ascii=False,
                ),
            )
            chunk_outputs.append(
                await _request_chunk_distillation(
                    provider_config,
                    project=project,
                    scan=scan,
                    baseline=baseline,
                    evidence=evidence,
                    oss_skill_bundle=oss_skill_bundle,
                    project_files=chunk,
                    chunk_index=index,
                    chunk_count=len(chunks),
                )
            )
        response = await _request_merge_distillation(
            provider_config,
            project=project,
            scan=scan,
            baseline=baseline,
            evidence=evidence,
            oss_skill_bundle=oss_skill_bundle,
            chunk_outputs=chunk_outputs,
            selected_project_files=selected_project_files,
        )
    logger.info(
        "Orchestrated distillation response: %s",
        json.dumps(
            {
                "provider_id": provider_config.id,
                "workflow": "orchestrated_distillation",
                "playbook_id": baseline.metadata.id,
                "response_text": response,
            },
            ensure_ascii=False,
        ),
    )
    return response
