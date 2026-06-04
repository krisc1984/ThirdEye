from __future__ import annotations

from app.schemas.tavily_settings import TavilySettings, TavilySettingsUpdateRequest
from app.services.storage import JsonStorage

SETTINGS_NAMESPACE = "settings"
SETTINGS_RECORD_ID = "tavily"


class TavilySettingsService:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def get_settings(self) -> TavilySettings:
        try:
            payload = self.storage.load_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID)
        except FileNotFoundError:
            return TavilySettings()
        return TavilySettings.model_validate(payload)

    def save_settings(self, request: TavilySettingsUpdateRequest) -> TavilySettings:
        current = self.get_settings()
        raw_api_key = request.api_key.strip() if isinstance(request.api_key, str) else None
        next_api_key = current.api_key
        if raw_api_key is not None:
            next_api_key = raw_api_key or None
        settings = TavilySettings(api_key=next_api_key, enabled=request.enabled)
        payload = {"enabled": settings.enabled}
        if settings.api_key is not None:
            payload["api_key"] = settings.api_key.get_secret_value()
        self.storage.save_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID, payload)
        return settings
