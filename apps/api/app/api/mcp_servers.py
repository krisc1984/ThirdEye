from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.mcp_server import McpServerConfig, McpServerCreateRequest, McpServerToggleRequest
from app.services.mcp_servers import McpServerService
from app.services.storage import JsonStorage

router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])


def get_service() -> McpServerService:
    return McpServerService(JsonStorage(settings.data_dir))


@router.get("", response_model=list[McpServerConfig])
def list_mcp_servers() -> list[McpServerConfig]:
    return get_service().list_servers()


@router.get("/{server_id}", response_model=McpServerConfig)
def get_mcp_server(server_id: str) -> McpServerConfig:
    try:
        return get_service().get_server(server_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="mcp server not found") from error


@router.post("", response_model=McpServerConfig)
def create_mcp_server(request: McpServerCreateRequest) -> McpServerConfig:
    return get_service().save_server(request)


@router.put("/{server_id}", response_model=McpServerConfig)
def update_mcp_server(server_id: str, request: McpServerCreateRequest) -> McpServerConfig:
    if request.id is not None and request.id != server_id:
        raise HTTPException(status_code=400, detail="mcp server id mismatch")
    return get_service().save_server(request, server_id=server_id)


@router.post("/{server_id}/toggle", response_model=McpServerConfig)
def toggle_mcp_server(server_id: str, request: McpServerToggleRequest) -> McpServerConfig:
    try:
        return get_service().toggle_server(server_id, request.enabled)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="mcp server not found") from error

