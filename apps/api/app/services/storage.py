from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

GRAPH_ROOT_NAMESPACE = "skill-graph"
GRAPH_CAPABILITIES_NAMESPACE = f"{GRAPH_ROOT_NAMESPACE}/capabilities"
GRAPH_COMPOSITES_NAMESPACE = f"{GRAPH_ROOT_NAMESPACE}/composites"
GRAPH_PLAYBOOKS_NAMESPACE = f"{GRAPH_ROOT_NAMESPACE}/graph-playbooks"
GRAPH_RUNS_NAMESPACE = f"{GRAPH_ROOT_NAMESPACE}/runs"
GRAPH_ASSETS_NAMESPACE = f"{GRAPH_ROOT_NAMESPACE}/assets"


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

    def delete_json(self, namespace: str, record_id: str) -> None:
        path = self._record_path(namespace, record_id)
        if not path.exists():
            raise FileNotFoundError(path)
        path.unlink()

    def save_graph_run_snapshot(
        self,
        run_id: str,
        snapshot_name: str,
        payload: dict[str, Any],
    ) -> Path:
        run_dir = self._graph_run_dir(run_id)
        snapshot_path = self._relative_json_path(run_dir, snapshot_name)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return snapshot_path

    def load_graph_run_snapshot(self, run_id: str, snapshot_name: str) -> dict[str, Any]:
        snapshot_path = self._relative_json_path(self._graph_run_dir(run_id), snapshot_name)
        with snapshot_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise StorageError("stored JSON record must be an object")
        return data

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

    def list_playbook_artifacts(self, playbook_id: str) -> list[str]:
        playbook_dir = self._playbook_dir(playbook_id)
        if not playbook_dir.exists():
            return []
        return sorted(
            str(path.relative_to(playbook_dir)).replace("\\", "/")
            for path in playbook_dir.rglob("*")
            if path.is_file()
        )

    def _record_path(self, namespace: str, record_id: str) -> Path:
        directory = self._namespace_path(namespace)
        self._validate_id(record_id, "record id")
        return self._safe_child(directory, f"{record_id}.json")

    def _namespace_path(self, namespace: str) -> Path:
        self._validate_namespace(namespace)
        current = self.root
        for segment in namespace.split("/"):
            current = self._safe_child(current, segment)
        return current

    def _playbook_dir(self, playbook_id: str) -> Path:
        self._validate_id(playbook_id, "playbook id")
        return self._safe_child(self.root / "playbooks", playbook_id)

    def _graph_run_dir(self, run_id: str) -> Path:
        self._validate_id(run_id, "run id")
        return self._safe_child(self._namespace_path(GRAPH_RUNS_NAMESPACE), run_id)

    def _relative_json_path(self, parent: Path, value: str) -> Path:
        self._validate_relative_path(value, "snapshot name")
        return self._safe_child(parent, f"{value}.json")

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

    def _validate_namespace(self, value: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*(/[A-Za-z0-9][A-Za-z0-9_.-]*)*", value):
            raise StorageError(f"invalid namespace: {value!r}")

    def _validate_relative_path(self, value: str, label: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*(/[A-Za-z0-9][A-Za-z0-9_.-]*)*", value):
            raise StorageError(f"invalid {label}: {value!r}")
