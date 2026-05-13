from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_serializer, model_validator

ProviderType = Literal["openai", "openai_compatible"]
ApiShape = Literal["responses", "chat_completions"]


class ModelProviderConfig(BaseModel):
    id: str
    name: str
    provider_type: ProviderType
    model: str
    api_key: SecretStr | None = None
    base_url: str | None = None
    api_shape: ApiShape = "responses"
    timeout_seconds: int = Field(default=150, ge=1, le=600)
    max_retries: int = Field(default=0, ge=0, le=10)
    tracing_enabled: bool = True

    @model_validator(mode="after")
    def validate_provider(self) -> "ModelProviderConfig":
        if self.provider_type == "openai_compatible" and not self.base_url:
            raise ValueError("openai_compatible providers require base_url")
        if self.provider_type == "openai_compatible" and self.api_shape == "responses":
            raise ValueError("openai_compatible providers must use chat_completions in MVP")
        return self

    @field_serializer("api_key")
    def serialize_api_key(self, value: SecretStr | None) -> str | None:
        if value is None:
            return None
        return "********"


class ModelProviderTestResult(BaseModel):
    provider_id: str
    ok: bool
    message: str
    response_text: str | None = None
    capabilities: dict[str, bool] = Field(default_factory=dict)
