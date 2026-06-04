from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr, field_serializer


class TavilySettings(BaseModel):
    api_key: SecretStr | None = Field(default=None)
    enabled: bool = False

    @field_serializer("api_key")
    def serialize_api_key(self, value: SecretStr | None) -> str | None:
        if value is None:
            return None
        return "********"


class TavilySettingsUpdateRequest(BaseModel):
    api_key: str | None = None
    enabled: bool = False

