from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.tavily_settings import TavilySettings, TavilySettingsUpdateRequest
from app.services.storage import JsonStorage
from app.services.tavily_settings import TavilySettingsService

router = APIRouter(prefix="/settings/tavily", tags=["tavily-settings"])


def get_service() -> TavilySettingsService:
    return TavilySettingsService(JsonStorage(settings.data_dir))


@router.get("", response_model=TavilySettings)
def get_tavily_settings() -> TavilySettings:
    return get_service().get_settings()


@router.put("", response_model=TavilySettings)
def update_tavily_settings(request: TavilySettingsUpdateRequest) -> TavilySettings:
    return get_service().save_settings(request)

