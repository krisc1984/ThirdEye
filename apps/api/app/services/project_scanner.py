from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.schemas.project import ProjectScanSummary
from app.services.ignore_rules import (
    DEFAULT_IGNORE_PATTERNS,
    load_gitignore_patterns,
    should_ignore,
)
from app.services.secret_scanner import SecretScanner

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
    ".md": "markdown",
}

DOC_NAMES = {
    "readme.md",
    "contributing.md",
    "changelog.md",
    "architecture.md",
    "design.md",
}

CONFIG_NAMES = {
    "package.json",
    "tsconfig.json",
    "pyproject.toml",
    "requirements.txt",
    "dockerfile",
    "docker-compose.yml",
    ".eslintrc",
    ".prettierrc",
}

ENTRYPOINT_NAMES = {
    "main.py",
    "app.py",
    "index.ts",
    "index.tsx",
    "index.js",
    "main.ts",
    "main.go",
}

SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_dsa",
    "secrets.json",
}

MAX_FILE_SIZE_BYTES = 512 * 1024


class ProjectScanner:
    def __init__(self) -> None:
        self.secret_scanner = SecretScanner()

    def scan(
        self,
        root_path: Path | str,
        extra_ignore_patterns: list[str] | None = None,
    ) -> ProjectScanSummary:
        root = Path(root_path).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"project root does not exist or is not a directory: {root}")

        patterns = [
            *DEFAULT_IGNORE_PATTERNS,
            *load_gitignore_patterns(root),
            *(extra_ignore_patterns or []),
        ]

        total_files = 0
        scanned_files = 0
        skipped_files = 0
        languages: Counter[str] = Counter()
        docs: list[str] = []
        tests: list[str] = []
        config_files: list[str] = []
        entrypoint_candidates: list[str] = []
        sensitive_warnings: list[str] = []

        for path in root.rglob("*"):
            try:
                relative = path.relative_to(root)
                is_file = self._safe_is_file(path)
                if is_file is None:
                    sensitive_warnings.append(f"{path}: path could not be accessed and was skipped.")
                    skipped_files += 1
                    continue
                if should_ignore(relative, patterns):
                    if is_file:
                        skipped_files += 1
                    continue
                if not is_file:
                    continue
            except OSError:
                sensitive_warnings.append(f"{path}: path could not be accessed and was skipped.")
                skipped_files += 1
                continue

            total_files += 1
            relative_text = relative.as_posix()
            lower_name = path.name.lower()

            if lower_name in SENSITIVE_NAMES or "secret" in lower_name:
                sensitive_warnings.append(relative_text)
                skipped_files += 1
                continue

            try:
                file_size = path.stat().st_size
            except OSError:
                sensitive_warnings.append(f"{relative_text}: file metadata could not be accessed and was skipped.")
                skipped_files += 1
                continue

            if file_size > MAX_FILE_SIZE_BYTES:
                skipped_files += 1
                continue

            scanned_files += 1
            language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower())
            if language:
                languages[language] += 1

            if lower_name in DOC_NAMES or relative_text.startswith("docs/"):
                docs.append(relative_text)
            if self._is_test_file(relative):
                tests.append(relative_text)
            if lower_name in CONFIG_NAMES or lower_name.startswith(".github"):
                config_files.append(relative_text)
            if lower_name in ENTRYPOINT_NAMES:
                entrypoint_candidates.append(relative_text)

            for finding in self.secret_scanner.scan_path(root, relative_text):
                sensitive_warnings.append(f"{finding.path}: {finding.redacted_summary}")

        return ProjectScanSummary(
            root_path=root,
            total_files=total_files,
            scanned_files=scanned_files,
            skipped_files=skipped_files,
            languages=dict(sorted(languages.items())),
            docs=sorted(docs),
            tests=sorted(tests),
            config_files=sorted(config_files),
            entrypoint_candidates=sorted(entrypoint_candidates),
            sensitive_warnings=sorted(sensitive_warnings),
        )

    def _is_test_file(self, relative_path: Path) -> bool:
        path_text = relative_path.as_posix().lower()
        name = relative_path.name.lower()
        return (
            "/tests/" in f"/{path_text}"
            or name.startswith("test_")
            or name.endswith(".test.ts")
            or name.endswith(".spec.ts")
            or name.endswith("_test.go")
        )

    def _safe_is_file(self, path: Path) -> bool | None:
        try:
            return path.is_file()
        except OSError:
            return None
