from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: dict[str, Any], at: datetime | None = None) -> Path:
        timestamp = at or datetime.utcnow()
        path = self.root / f"{timestamp.date().isoformat()}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        sanitized = self._sanitize(event)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sanitized, ensure_ascii=False))
            handle.write("\n")
        return path

    def sanitize(self, value: Any, key: str | None = None) -> Any:
        return self._sanitize(value, key)

    def _sanitize(self, value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for sub_key, sub_value in value.items():
                key_lower = sub_key.lower()
                if "file_content" in key_lower or "raw_content" in key_lower:
                    continue
                sanitized[sub_key] = self._sanitize(sub_value, sub_key)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize(item, key) for item in value]
        if key and any(token in key.lower() for token in ("api_key", "token", "secret", "authorization")):
            return "********"
        if isinstance(value, str) and self._looks_like_secret(value):
            return "********"
        if isinstance(value, str) and key and any(token in key.lower() for token in ("content", "prompt", "proposal", "input")):
            if len(value) > 240:
                return value[:240] + "..."
            return value
        return value

    def _looks_like_secret(self, value: str) -> bool:
        return (
            "OPENAI_API_KEY=" in value
            or "BEGIN PRIVATE KEY" in value
            or "password=" in value.lower()
            or "sk-" in value
        )
