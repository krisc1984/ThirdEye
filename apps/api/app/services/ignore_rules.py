from __future__ import annotations

from pathlib import Path
from fnmatch import fnmatch

DEFAULT_IGNORE_PATTERNS = [
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".venv",
    "__pycache__",
    "*.log",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.pdf",
    "*.zip",
]


def load_gitignore_patterns(root_path: Path) -> list[str]:
    gitignore = root_path / ".gitignore"
    if not gitignore.exists():
        return []

    patterns: list[str] = []
    for raw_line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def should_ignore(relative_path: Path, patterns: list[str]) -> bool:
    path_text = relative_path.as_posix()
    name = relative_path.name
    parts = relative_path.parts

    for pattern in patterns:
        normalized = pattern.strip().rstrip("/")
        if not normalized:
            continue
        if normalized in parts:
            return True
        if fnmatch(name, normalized) or fnmatch(path_text, normalized):
            return True
        if "/" not in normalized and any(fnmatch(part, normalized) for part in parts):
            return True
    return False

