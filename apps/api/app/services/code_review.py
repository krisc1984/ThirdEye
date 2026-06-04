from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.playbook import EvidenceItem, PlaybookMetadata, PlaybookRule
from app.schemas.review import (
    CodeReviewFileDiffResponse,
    CodeReviewChangedFile,
    CodeReviewFileFinding,
    CodeReviewProjectFile,
    CodeReviewRequest,
    CodeReviewResponse,
    ReviewFinding,
    ReviewResponse,
)
from app.services.ignore_rules import DEFAULT_IGNORE_PATTERNS, load_gitignore_patterns, should_ignore

CODE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".php",
    ".rb",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".css": "css",
    ".scss": "scss",
    ".html": "html",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
}

MAX_FILE_CONTENT_CHARS = 200_000


def collect_git_changed_files(
    *,
    project_root: Path,
    base_ref: str | None = None,
    head_ref: str | None = None,
    paths: list[str] | None = None,
    include_patch: bool = True,
) -> list[CodeReviewChangedFile]:
    root = project_root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")
    if not (root / ".git").exists():
        raise ValueError(f"project root is not a git repository: {root}")

    range_args = _build_git_range_args(base_ref, head_ref)
    path_args = ["--", *(paths or [])] if paths else []
    numstat = _run_git(root, ["diff", "--no-ext-diff", "--numstat", *range_args, *path_args])

    changes: list[CodeReviewChangedFile] = []
    for line in numstat.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        additions_raw, deletions_raw, raw_path = parts
        path = _normalize_git_diff_path(raw_path)
        patch = ""
        if include_patch:
            patch = _run_git(root, ["diff", "--no-ext-diff", *range_args, "--", path])
        changes.append(
            CodeReviewChangedFile(
                path=path,
                status=_infer_status_from_patch(patch),
                additions=_safe_int(additions_raw),
                deletions=_safe_int(deletions_raw),
                patch=patch,
                language=_detect_language(path),
            )
        )

    return changes


def list_git_branches(*, project_root: Path) -> tuple[str | None, list[str]]:
    root = _ensure_git_repository(project_root)
    branch_output = _run_git(root, ["branch", "--format=%(refname:short)"])
    branches = [line.strip() for line in branch_output.splitlines() if line.strip()]
    current_branch = _run_git(root, ["branch", "--show-current"]).strip() or None
    ordered = list(dict.fromkeys(branches))
    if current_branch and current_branch not in ordered:
        ordered.insert(0, current_branch)
    return current_branch, ordered


def list_project_files(
    *,
    project_root: Path,
    query: str | None = None,
    limit: int = 800,
) -> tuple[list[CodeReviewProjectFile], int, bool]:
    root = _ensure_project_directory(project_root)
    patterns = [*DEFAULT_IGNORE_PATTERNS, *load_gitignore_patterns(root)]
    normalized_query = (query or "").strip().lower()
    files: list[CodeReviewProjectFile] = []
    matched_count = 0

    for path in sorted(root.rglob("*"), key=lambda item: str(item).lower()):
        try:
            relative = path.relative_to(root)
            if should_ignore(relative, patterns) or not path.is_file():
                continue
            relative_text = relative.as_posix()
            if normalized_query and normalized_query not in relative_text.lower() and normalized_query not in path.name.lower():
                continue
            stat = path.stat()
        except OSError:
            continue

        matched_count += 1
        if len(files) >= limit:
            continue

        files.append(
            CodeReviewProjectFile(
                path=relative_text,
                name=path.name,
                directory=relative.parent.as_posix() if relative.parent.as_posix() != "." else "根目录",
                language=_detect_language(relative_text),
                size_bytes=max(stat.st_size, 0),
                updated_at=datetime.utcfromtimestamp(stat.st_mtime),
            )
        )

    return files, matched_count, matched_count > len(files)


def get_file_diff(
    *,
    project_id: str,
    project_root: Path,
    path: str,
    base_ref: str | None = None,
    head_ref: str | None = None,
    include_content: bool = True,
) -> CodeReviewFileDiffResponse:
    root = _ensure_project_directory(project_root)
    normalized_path = _normalize_project_relative_path(path)
    is_git_repository = (root / ".git").exists()
    if (base_ref or head_ref) and not is_git_repository:
        raise ValueError(f"project root is not a git repository: {root}")

    patch = ""
    additions = 0
    deletions = 0
    if is_git_repository:
        range_args = _build_git_range_args(base_ref, head_ref)
        patch = _run_git(root, ["diff", "--no-ext-diff", *range_args, "--", normalized_path])
        additions, deletions = _collect_single_file_numstat(root, normalized_path, range_args)

    content = ""
    content_truncated = False
    if include_content:
        content, content_truncated = _read_file_content_at_ref(root, normalized_path, head_ref=head_ref)

    return CodeReviewFileDiffResponse(
        project_id=project_id,
        root_path=str(root),
        path=normalized_path,
        base_ref=base_ref,
        head_ref=head_ref,
        status=_infer_status_from_patch(patch) if patch.strip() else "unknown",
        additions=additions,
        deletions=deletions,
        patch=patch,
        language=_detect_language(normalized_path),
        content=content,
        content_truncated=content_truncated,
    )


def changed_files_from_inline_diff(diff_text: str) -> list[CodeReviewChangedFile]:
    text = diff_text.strip()
    if not text:
        return []

    files: list[CodeReviewChangedFile] = []
    current_path = "inline.diff"
    current_status = "modified"
    current_patch: list[str] = []

    def flush_current() -> None:
        nonlocal current_patch, current_path, current_status
        if not current_patch:
            return
        patch = "\n".join(current_patch)
        files.append(
            CodeReviewChangedFile(
                path=current_path,
                status=current_status,  # type: ignore[arg-type]
                additions=sum(1 for line in current_patch if line.startswith("+") and not line.startswith("+++")),
                deletions=sum(1 for line in current_patch if line.startswith("-") and not line.startswith("---")),
                patch=patch,
                language=_detect_language(current_path),
            )
        )
        current_patch = []
        current_path = "inline.diff"
        current_status = "modified"

    for line in text.splitlines():
        if line.startswith("diff --git "):
            flush_current()
            parsed = re.match(r"diff --git a/(.+?) b/(.+)$", line)
            if parsed:
                current_path = parsed.group(2).strip()
            current_patch.append(line)
            continue
        if line.startswith("+++ b/"):
            current_path = line.removeprefix("+++ b/").strip()
        elif line.startswith("new file mode"):
            current_status = "added"
        elif line.startswith("deleted file mode"):
            current_status = "deleted"
        current_patch.append(line)

    flush_current()
    if files:
        return files

    return [
        CodeReviewChangedFile(
            path="inline.diff",
            status="modified",
            additions=sum(1 for line in text.splitlines() if line.startswith("+") and not line.startswith("+++")),
            deletions=sum(1 for line in text.splitlines() if line.startswith("-") and not line.startswith("---")),
            patch=text,
            language="diff",
        )
    ]


def build_code_review_proposal(request: CodeReviewRequest, files: list[CodeReviewChangedFile]) -> str:
    focus = "\n".join(f"- {item}" for item in request.focus if item.strip()) or "- 正确性\n- 安全\n- 测试覆盖\n- 可维护性"
    file_sections = "\n\n".join(
        [
            f"### {item.path} ({item.status}, +{item.additions}/-{item.deletions})\n"
            f"```diff\n{_truncate_text(item.patch or '(patch not provided)', 16_000)}\n```"
            for item in files[:20]
        ]
    )
    return "\n".join(
        [
            "请进行代码评审，优先指出会导致线上故障、行为回归、安全风险或测试缺口的问题。",
            "",
            "[评审重点]",
            focus,
            "",
            "[分支范围]",
            f"- base_ref: {request.base_ref or '(未提供)'}",
            f"- head_ref: {request.head_ref or '(未提供)'}",
            "",
            "[评审者补充]",
            request.reviewer_note or "(无)",
            "",
            "[代码变更]",
            file_sections or "(未提供文件级 patch)",
        ]
    )


def deterministic_code_review(
    *,
    request: CodeReviewRequest,
    metadata: PlaybookMetadata,
    rules: list[PlaybookRule],
    evidence: list[EvidenceItem],
    files: list[CodeReviewChangedFile],
) -> CodeReviewResponse:
    proposal = build_code_review_proposal(request, files)
    file_findings = _detect_file_findings(files)
    review_findings = [_to_review_finding(item) for item in file_findings]

    missing_information: list[str] = []
    if any(not item.patch.strip() for item in files):
        missing_information.append("部分文件缺少 patch 内容，只能基于文件名和变更规模做低置信评审。")
    if not files:
        missing_information.append("没有可评审的代码变更。")

    severity_order = {finding.severity for finding in file_findings}
    if "blocker" in severity_order:
        judgement = "不建议采用"
    elif "major" in severity_order:
        judgement = "建议修改后再评审"
    elif severity_order:
        judgement = "有条件通过"
    elif missing_information:
        judgement = "有条件通过"
    else:
        judgement = "通过"

    key_risks = [f"{item.file_path}: {item.title}" for item in file_findings[:8]]
    suggested_changes = list(dict.fromkeys(item.suggestion for item in file_findings[:8]))
    required_validation = _build_required_validation(files, file_findings)

    if not key_risks:
        key_risks.append(f"当前未发现与 {metadata.name} 直接冲突的高风险代码问题。")
    if not suggested_changes:
        suggested_changes.append("保持当前变更范围，并补充必要的回归验证记录。")

    review = ReviewResponse(
        id=f"rev_{uuid4().hex[:12]}",
        playbook_id=request.playbook_id,
        mode=request.mode,
        input=proposal,
        execution_mode="deterministic",
        resolved_provider_id=None,
        execution_note="Deterministic code review completed from diff/files.",
        overall_judgement=judgement,  # type: ignore[arg-type]
        key_risks=list(dict.fromkeys(key_risks)),
        playbook_conflicts=[],
        suggested_changes=suggested_changes,
        required_validation=required_validation,
        missing_information=missing_information,
        findings=review_findings,
        model_provider=request.model_provider_id,
    )
    return build_code_review_response(review=review, files=files, file_findings=file_findings)


def build_code_review_response(
    *,
    review: ReviewResponse,
    files: list[CodeReviewChangedFile],
    file_findings: list[CodeReviewFileFinding],
) -> CodeReviewResponse:
    total_additions = sum(item.additions for item in files)
    total_deletions = sum(item.deletions for item in files)
    return CodeReviewResponse(
        id=f"cr_{uuid4().hex[:12]}",
        review=review,
        changed_files=files,
        file_findings=file_findings,
        summary_markdown=_build_summary_markdown(review, files, file_findings),
        total_files=len(files),
        total_additions=total_additions,
        total_deletions=total_deletions,
    )


def _build_git_range_args(base_ref: str | None, head_ref: str | None) -> list[str]:
    if base_ref and head_ref:
        return [f"{base_ref}...{head_ref}"]
    if base_ref:
        return [base_ref]
    if head_ref:
        return [head_ref]
    return []


def _ensure_project_directory(project_root: Path) -> Path:
    root = project_root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")
    return root


def _ensure_git_repository(project_root: Path) -> Path:
    root = _ensure_project_directory(project_root)
    if not (root / ".git").exists():
        raise ValueError(f"project root is not a git repository: {root}")
    return root


def _run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=12,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "git command failed").strip()
        raise ValueError(detail[:500])
    return completed.stdout


def _collect_single_file_numstat(root: Path, path: str, range_args: list[str]) -> tuple[int, int]:
    numstat = _run_git(root, ["diff", "--no-ext-diff", "--numstat", *range_args, "--", path])
    for line in numstat.splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2:
            return _safe_int(parts[0]), _safe_int(parts[1])
    return 0, 0


def _normalize_project_relative_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("code review paths must be relative project paths")
    if not normalized:
        raise ValueError("code review path is required")
    return normalized


def _read_file_content_at_ref(root: Path, path: str, *, head_ref: str | None) -> tuple[str, bool]:
    text = ""
    if head_ref:
        try:
            text = _run_git(root, ["show", f"{head_ref}:{path}"])
        except ValueError:
            text = ""
    else:
        target = (root / path).resolve()
        if root not in target.parents and target != root:
            raise ValueError("code review path must stay inside project root")
        if target.exists() and target.is_file():
            text = target.read_text(encoding="utf-8", errors="replace")

    truncated = len(text) > MAX_FILE_CONTENT_CHARS
    if truncated:
        text = f"{text[:MAX_FILE_CONTENT_CHARS]}\n...<truncated {len(text) - MAX_FILE_CONTENT_CHARS} chars>"
    return text, truncated


def _normalize_git_diff_path(raw_path: str) -> str:
    path = raw_path.strip().replace("\\", "/")
    if " => " in path:
        right = path.split(" => ", 1)[1]
        path = right.replace("{", "").replace("}", "")
    return path


def _infer_status_from_patch(patch: str) -> str:
    if "new file mode" in patch:
        return "added"
    if "deleted file mode" in patch:
        return "deleted"
    if "rename from" in patch and "rename to" in patch:
        return "renamed"
    return "modified"


def _safe_int(value: str) -> int:
    try:
        return max(int(value), 0)
    except ValueError:
        return 0


def _detect_language(path: str) -> str | None:
    return LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower())


def _detect_file_findings(files: list[CodeReviewChangedFile]) -> list[CodeReviewFileFinding]:
    findings: list[CodeReviewFileFinding] = []
    code_files = [item for item in files if _is_code_file(item.path)]
    tests_changed = any(_is_test_path(item.path) for item in files)
    package_changed = any(Path(item.path).name == "package.json" for item in files)
    lock_changed = any(Path(item.path).name in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"} for item in files)

    for item in files:
        added_lines = list(_iter_added_lines(item.patch))
        if item.additions + item.deletions >= 400:
            findings.append(
                _finding(
                    item.path,
                    "minor",
                    "maintainability",
                    "单文件变更规模较大",
                    f"{item.path} 当前变更 +{item.additions}/-{item.deletions}，评审和回滚成本较高。",
                    "拆分提交或在评审说明中明确每一组变更的目的、影响范围和回滚方式。",
                )
            )

        for line_number, line in added_lines:
            normalized = line.lower()
            if any(token in normalized for token in ["eval(", "dangerouslysetinnerhtml", ".innerhtml"]):
                findings.append(
                    _finding(
                        item.path,
                        "blocker",
                        "security",
                        "新增动态代码执行或直接 HTML 注入入口",
                        "新增代码包含高风险执行/渲染模式，可能引入 XSS 或任意代码执行风险。",
                        "移除动态执行路径，使用白名单解析、框架安全 API 或安全模板渲染。",
                        line_number,
                        0.9,
                    )
                )
            if "shell=true" in normalized or "os.system(" in normalized:
                findings.append(
                    _finding(
                        item.path,
                        "blocker",
                        "security",
                        "新增 shell 拼接执行风险",
                        "shell=True 或 os.system 容易把用户输入扩展为命令注入面。",
                        "改用参数数组形式执行命令，并对输入做白名单校验。",
                        line_number,
                        0.88,
                    )
                )
            if any(token in normalized for token in ["api_key", "secret", "password"]) and "hash" not in normalized:
                findings.append(
                    _finding(
                        item.path,
                        "major",
                        "security",
                        "疑似敏感字段进入代码变更",
                        "新增代码包含敏感字段名，需确认没有硬编码密钥、明文密码或日志泄露。",
                        "改用环境变量/密钥管理，并检查日志与错误响应是否会输出敏感值。",
                        line_number,
                        0.7,
                    )
                )
            if re.search(r"\b(as any|: any)\b", line):
                findings.append(
                    _finding(
                        item.path,
                        "minor",
                        "maintainability",
                        "新增 any 降低类型约束",
                        "any 会绕过 TypeScript 编译期保护，可能掩盖接口结构变化。",
                        "替换为精确类型、泛型约束或显式 unknown 后再收窄。",
                        line_number,
                        0.72,
                    )
                )
            if "console.log(" in normalized:
                findings.append(
                    _finding(
                        item.path,
                        "nit",
                        "observability",
                        "新增临时日志输出",
                        "console.log 可能污染生产日志，且缺少结构化上下文。",
                        "移除临时日志，或改用项目统一 logger 并设置合适级别。",
                        line_number,
                        0.68,
                    )
                )
            if "todo" in normalized or "fixme" in normalized:
                findings.append(
                    _finding(
                        item.path,
                        "minor",
                        "maintainability",
                        "新增未关闭的 TODO/FIXME",
                        "评审合入后 TODO 往往缺少跟踪，容易形成隐性技术债。",
                        "在当前变更内处理，或关联明确 issue/负责人和验收条件。",
                        line_number,
                        0.66,
                    )
                )

    if code_files and not tests_changed:
        findings.append(
            _finding(
                "(测试覆盖)",
                "major",
                "testing",
                "代码变更缺少对应测试文件",
                "本次包含代码文件变更，但没有检测到测试文件同步修改，回归风险无法被自动验证。",
                "补充单元测试或集成测试；如果无需新增测试，在评审说明中列出已执行的现有测试命令。",
                confidence=0.82,
            )
        )

    if package_changed and not lock_changed:
        findings.append(
            _finding(
                "package.json",
                "major",
                "correctness",
                "依赖声明变更缺少锁文件同步",
                "package.json 发生变化但未检测到锁文件变更，安装结果可能在不同环境不一致。",
                "同步提交 package-lock/pnpm-lock/yarn.lock，或说明该变更不影响依赖解析。",
                confidence=0.78,
            )
        )

    return findings


def _iter_added_lines(patch: str):
    new_line: int | None = None
    for raw_line in patch.splitlines():
        hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw_line)
        if hunk:
            new_line = int(hunk.group(1))
            continue
        if raw_line.startswith("+++") or raw_line.startswith("---"):
            continue
        if raw_line.startswith("+"):
            yield new_line, raw_line[1:]
            if new_line is not None:
                new_line += 1
            continue
        if raw_line.startswith("-"):
            continue
        if new_line is not None:
            new_line += 1


def _finding(
    file_path: str,
    severity: str,
    category: str,
    title: str,
    detail: str,
    suggestion: str,
    line: int | None = None,
    confidence: float = 0.74,
) -> CodeReviewFileFinding:
    return CodeReviewFileFinding(
        file_path=file_path,
        severity=severity,  # type: ignore[arg-type]
        category=category,  # type: ignore[arg-type]
        title=title,
        detail=detail,
        suggestion=suggestion,
        line=line,
        confidence=confidence,
    )


def _to_review_finding(item: CodeReviewFileFinding) -> ReviewFinding:
    return ReviewFinding(
        severity=item.severity,
        confidence=item.confidence,
        evidence_level="inferred",
        rule_id=None,
        problem=f"{item.file_path}: {item.title}",
        impact=item.detail,
        suggested_change=item.suggestion,
        required_validation=[item.suggestion] if item.category == "testing" else [],
        evidence_ids=[],
    )


def _build_required_validation(
    files: list[CodeReviewChangedFile],
    findings: list[CodeReviewFileFinding],
) -> list[str]:
    validations: list[str] = []
    if any(_is_code_file(item.path) for item in files):
        validations.append("运行与变更模块相关的单元测试/集成测试，并在评审记录中附上命令和结果。")
    if any(item.category == "security" for item in findings):
        validations.append("对新增输入、命令执行、HTML 渲染或敏感字段路径做安全回归验证。")
    if any(item.category == "observability" for item in findings):
        validations.append("确认日志、指标和错误处理符合项目统一可观测性规范。")
    if not validations:
        validations.append("执行现有回归测试，并确认变更路径可回滚。")
    return list(dict.fromkeys(validations))


def _build_summary_markdown(
    review: ReviewResponse,
    files: list[CodeReviewChangedFile],
    findings: list[CodeReviewFileFinding],
) -> str:
    severity_counts = {
        severity: sum(1 for item in findings if item.severity == severity)
        for severity in ["blocker", "major", "minor", "nit"]
    }
    finding_lines = [
        f"- [{item.severity}] {item.file_path}{f':{item.line}' if item.line else ''} - {item.title}"
        for item in findings[:12]
    ]
    return "\n".join(
        [
            "# 代码评审结果",
            "",
            f"- 结论：{review.overall_judgement}",
            f"- 文件数：{len(files)}",
            f"- 风险计数：blocker {severity_counts['blocker']} / major {severity_counts['major']} / minor {severity_counts['minor']} / nit {severity_counts['nit']}",
            "",
            "## 主要发现",
            *(finding_lines or ["- 未发现明确的高风险代码问题。"]),
            "",
            "## 建议验证",
            *[f"- {item}" for item in review.required_validation],
        ]
    )


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n...<truncated {len(value) - limit} chars>"


def _is_code_file(path: str) -> bool:
    return Path(path).suffix.lower() in CODE_SUFFIXES


def _is_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    name = Path(normalized).name
    return (
        "/test/" in f"/{normalized}"
        or "/tests/" in f"/{normalized}"
        or name.startswith("test_")
        or name.endswith(".test.ts")
        or name.endswith(".spec.ts")
        or name.endswith("_test.go")
        or name.endswith("_test.py")
    )
