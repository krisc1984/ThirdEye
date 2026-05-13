from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.business_agent import BusinessAgentActivateRequest, BusinessAgentConfig
from app.services.business_agents import BusinessAgentService
from app.services.storage import JsonStorage

router = APIRouter(prefix="/agent-configs", tags=["agent-configs"])


def get_service() -> BusinessAgentService:
    return BusinessAgentService(JsonStorage(settings.data_dir))


@router.get("", response_model=list[BusinessAgentConfig])
def list_agent_configs() -> list[BusinessAgentConfig]:
    return get_service().list_agents()


@router.get("/{agent_id}", response_model=BusinessAgentConfig)
def get_agent_config(agent_id: str) -> BusinessAgentConfig:
    try:
        return get_service().get_agent(agent_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="agent config not found") from error


@router.post("", response_model=BusinessAgentConfig)
def create_agent_config(config: BusinessAgentConfig) -> BusinessAgentConfig:
    return get_service().save_agent(config)


@router.put("/{agent_id}", response_model=BusinessAgentConfig)
def update_agent_config(agent_id: str, config: BusinessAgentConfig) -> BusinessAgentConfig:
    if agent_id != config.id:
        raise HTTPException(status_code=400, detail="agent id mismatch")
    return get_service().save_agent(config)


@router.post("/{agent_id}/activate", response_model=BusinessAgentConfig)
def activate_agent_config(agent_id: str, request: BusinessAgentActivateRequest | None = None) -> BusinessAgentConfig:
    if request is not None and request.id != agent_id:
        raise HTTPException(status_code=400, detail="agent id mismatch")
    try:
        return get_service().activate_agent(agent_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="agent config not found") from error
