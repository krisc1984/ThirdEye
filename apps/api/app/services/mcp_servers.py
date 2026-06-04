from __future__ import annotations

from datetime import datetime, UTC

from app.schemas.mcp_server import McpServerConfig, McpServerCreateRequest
from app.services.storage import JsonStorage

SETTINGS_NAMESPACE = "settings"
SETTINGS_RECORD_ID = "mcp-servers"


def _slugify(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    collapsed = "_".join(part for part in normalized.split("_") if part)
    return collapsed or "mcp_server"


class McpServerService:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def list_servers(self) -> list[McpServerConfig]:
        payload = self._load_payload()
        servers = [
            McpServerConfig.model_validate(item)
            for item in payload.get("servers", [])
            if isinstance(item, dict)
        ]
        return sorted(servers, key=lambda item: (item.scope, item.name.lower(), item.id))

    def get_server(self, server_id: str) -> McpServerConfig:
        for server in self.list_servers():
            if server.id == server_id:
                return server
        raise FileNotFoundError(server_id)

    def save_server(self, request: McpServerCreateRequest, server_id: str | None = None) -> McpServerConfig:
        existing_servers = self.list_servers()
        now = datetime.now(UTC)
        resolved_id = (server_id or request.id or f"mcp_{_slugify(request.name)}").strip()
        existing = next((item for item in existing_servers if item.id == resolved_id), None)
        created_at = existing.created_at if existing is not None else now
        status = "connected" if request.enabled else "idle"
        config = McpServerConfig(
            id=resolved_id,
            name=request.name,
            description=request.description,
            transport=request.transport,
            scope=request.scope,
            status=status,
            enabled=request.enabled,
            command=request.command,
            args=[item.strip() for item in request.args if item.strip()],
            endpoint=request.endpoint,
            env=request.env,
            created_at=created_at,
            updated_at=now,
        )
        next_servers = [item for item in existing_servers if item.id != resolved_id]
        next_servers.append(config)
        self._save_servers(next_servers)
        return config

    def toggle_server(self, server_id: str, enabled: bool) -> McpServerConfig:
        server = self.get_server(server_id)
        updated = server.model_copy(
            update={
                "enabled": enabled,
                "status": "connected" if enabled else ("attention" if server.status == "attention" else "idle"),
                "updated_at": datetime.now(UTC),
            }
        )
        next_servers = [item for item in self.list_servers() if item.id != server_id]
        next_servers.append(updated)
        self._save_servers(next_servers)
        return updated

    def _load_payload(self) -> dict:
        try:
            payload = self.storage.load_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID)
        except FileNotFoundError:
            payload = {"servers": []}
        if not isinstance(payload.get("servers"), list):
            payload["servers"] = []
        return payload

    def _save_servers(self, servers: list[McpServerConfig]) -> None:
        self.storage.save_json(
            SETTINGS_NAMESPACE,
            SETTINGS_RECORD_ID,
            {"servers": [item.model_dump(mode="json") for item in servers]},
        )

