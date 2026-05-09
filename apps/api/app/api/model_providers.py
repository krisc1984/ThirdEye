from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.model_providers.adapter import ModelProviderAdapter
from app.schemas.model_provider import ModelProviderConfig, ModelProviderTestResult
from app.services.storage import JsonStorage, StorageError

router = APIRouter(prefix="/model-providers", tags=["model-providers"])

adapter = ModelProviderAdapter()


def get_storage() -> JsonStorage:
    return JsonStorage(settings.data_dir)


@router.post("", response_model=ModelProviderConfig)
def create_model_provider(config: ModelProviderConfig) -> ModelProviderConfig:
    payload = config.model_dump(mode="python")
    if config.api_key is not None:
        payload["api_key"] = config.api_key.get_secret_value()
    get_storage().save_json("model-providers", config.id, payload)
    return config


@router.get("", response_model=list[ModelProviderConfig])
def list_model_providers() -> list[ModelProviderConfig]:
    return [ModelProviderConfig.model_validate(record) for record in get_storage().list_json("model-providers")]


@router.get("/{provider_id}", response_model=ModelProviderConfig)
def get_model_provider(provider_id: str) -> ModelProviderConfig:
    try:
        record = get_storage().load_json("model-providers", provider_id)
    except (FileNotFoundError, StorageError) as error:
        raise HTTPException(status_code=404, detail="model provider not found") from error
    return ModelProviderConfig.model_validate(record)


@router.post("/{provider_id}/test", response_model=ModelProviderTestResult)
async def test_model_provider(provider_id: str) -> ModelProviderTestResult:
    config = get_model_provider(provider_id)
    return await adapter.test_connection(config)
