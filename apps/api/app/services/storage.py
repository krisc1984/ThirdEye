from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class StorageError(ValueError):
    """Raised when a storage key or namespace is invalid."""


class JsonStorage:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_json(self, namespace: str, record_id: str, payload: dict[str, Any]) -> Path:
        path = self._record_path(namespace, record_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def load_json(self, namespace: str, record_id: str) -> dict[str, Any]:
        path = self._record_path(namespace, record_id)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise StorageError("stored JSON record must be an object")
        return data

    def list_json(self, namespace: str) -> list[dict[str, Any]]:
        directory = self._namespace_path(namespace)
        if not directory.exists():
            return []

        records: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                records.append(data)
        return records

    def save_playbook_artifact(
        self,
        playbook_id: str,
        artifact_name: str,
        content: str,
    ) -> Path:
        playbook_dir = self._playbook_dir(playbook_id)
        artifact_path = self._safe_child(playbook_dir, artifact_name)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
        return artifact_path

    def load_playbook_artifact(self, playbook_id: str, artifact_name: str) -> str:
        playbook_dir = self._playbook_dir(playbook_id)
        artifact_path = self._safe_child(playbook_dir, artifact_name)
        return artifact_path.read_text(encoding="utf-8")

    def _record_path(self, namespace: str, record_id: str) -> Path:
        directory = self._namespace_path(namespace)
        self._validate_id(record_id, "record id")
        return self._safe_child(directory, f"{record_id}.json")

    def _namespace_path(self, namespace: str) -> Path:
        self._validate_id(namespace, "namespace")
        return self._safe_child(self.root, namespace)

    def _playbook_dir(self, playbook_id: str) -> Path:
        self._validate_id(playbook_id, "playbook id")
        return self._safe_child(self.root / "playbooks", playbook_id)

    def _safe_child(self, parent: Path, child: str) -> Path:
        if Path(child).is_absolute():
            raise StorageError("absolute paths are not allowed")
        candidate = (parent / child).resolve()
        parent_resolved = parent.resolve()
        if candidate != parent_resolved and parent_resolved not in candidate.parents:
            raise StorageError("path escapes storage root")
        return candidate

    def _validate_id(self, value: str, label: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
            raise StorageError(f"invalid {label}: {value!r}")

