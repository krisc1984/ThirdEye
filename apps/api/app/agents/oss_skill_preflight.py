from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
DEFAULT_REPORT_DIR = REPO_ROOT / "data" / "test-reports"
DEFAULT_LOG_PATH = DEFAULT_REPORT_DIR / "oss_skill_preflight_run.log"
DEFAULT_REPORT_PATH = DEFAULT_REPORT_DIR / "oss_skill_preflight_run_result.md"


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def _iter_preview(root: Path, pattern: str, limit: int) -> list[str]:
    try:
        return [str(path) for path in root.rglob(pattern)][:limit]
    except Exception:
        return []


def _build_preflight(target_project: Path) -> dict[str, object]:
    tree_preview: list[str] = []
    if target_project.exists():
        try:
            tree_preview = [str(path) for path in target_project.rglob("*")][:80]
        except Exception:
            tree_preview = []

    return {
        "target_project": str(target_project),
        "exists": target_project.exists(),
        "is_dir": target_project.is_dir(),
        "top_tree_preview": tree_preview,
        "java_files_preview": _iter_preview(target_project, "*.java", 80) if target_project.exists() else [],
        "markdown_files_preview": _iter_preview(target_project, "*.md", 40) if target_project.exists() else [],
        "pom_files": _iter_preview(target_project, "pom.xml", 20) if target_project.exists() else [],
        "python_files_preview": _iter_preview(target_project, "*.py", 40) if target_project.exists() else [],
        "readme_candidates": [
            str(path)
            for path in (
                target_project / "README.md",
                target_project / "README.MD",
                target_project / "readme.md",
                target_project / "pyproject.toml",
                target_project / "package.json",
                target_project / "pom.xml",
            )
            if path.exists()
        ][:10],
    }


def _recommend_files(preflight: dict[str, object]) -> list[str]:
    ordered_candidates: list[str] = []
    for key in ("readme_candidates", "pom_files", "python_files_preview", "markdown_files_preview", "top_tree_preview"):
        for item in preflight.get(key, []):
            if isinstance(item, str) and item not in ordered_candidates and Path(item).is_file():
                ordered_candidates.append(item)
            if len(ordered_candidates) >= 5:
                return ordered_candidates
    return ordered_candidates[:5]


def _build_report(target_project: Path, preflight: dict[str, object]) -> str:
    exists = bool(preflight["exists"])
    next_files = _recommend_files(preflight)
    if not exists:
        verdict = "目标路径不存在，agent 不应继续发起 bash/write_file_chunk 工具调用。"
    else:
        verdict = "本地预检已完成，适合先基于预检结果收敛分析范围，再决定是否进入更细粒度文件读取。"

    lines = [
        "# OSS Skill Preflight Run Result",
        "",
        f"- Time: `{_ts()}`",
        f"- Target project: `{target_project}`",
        f"- Status: `{'PASS' if exists else 'FAIL'}`",
        "",
        "## Preflight",
        "",
        "```json",
        json.dumps(preflight, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Deterministic Assessment",
        "",
        "1. Phase 0A/0.5 判断",
        f"   - {verdict}",
        "2. 下一步最值得读取的 5 个文件",
    ]
    if next_files:
        lines.extend([f"   - `{path}`" for path in next_files])
    else:
        lines.append("   - 暂无可读取候选，先确认目标路径和项目内容。")
    lines.extend(
        [
            "3. 对 agent 调用复杂 skill 可用性的验证结论",
            "   - 当前请求已通过后端 deterministic preflight 处理，绕过了不稳定的模型工具参数生成。",
            "   - 如果后续仍需进入 LLM 阶段，应优先使用受限的小步 read_file，而不是直接让模型构造大段写文件参数。",
        ]
    )
    return "\n".join(lines) + "\n"


def maybe_run_oss_skill_preflight(query: str) -> str | None:
    target = _extract_oss_skill_target(query)
    if target is None:
        return None
    if "oss-skill" not in query.lower() and "蒸馏" not in query:
        return None

    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    logs = [f"[{_ts()}] Start oss-skill deterministic preflight", f"[{_ts()}] Target={target}"]
    preflight = _build_preflight(target)
    logs.append(
        f"[{_ts()}] Gathered tree={len(preflight['top_tree_preview'])} "
        f"java={len(preflight['java_files_preview'])} md={len(preflight['markdown_files_preview'])}"
    )
    report = _build_report(target, preflight)
    DEFAULT_LOG_PATH.write_text("\n".join(logs) + "\n", encoding="utf-8")
    DEFAULT_REPORT_PATH.write_text(report, encoding="utf-8")
    return report
