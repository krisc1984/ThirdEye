import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.core.config import settings
from app.model_providers.adapter import ModelProviderAdapter
from app.model_providers.llm_client import LLMClient
from app.agents.sdk_runtime import run_text_agent
from app.schemas.model_provider import ModelProviderConfig


def test_openai_provider_config_validates_without_base_url():
    config = ModelProviderConfig(
        id="openai-default",
        name="OpenAI",
        provider_type="openai",
        model="gpt-5.4",
        api_shape="responses",
    )

    assert config.base_url is None


def test_openai_compatible_provider_requires_base_url():
    with pytest.raises(ValidationError):
        ModelProviderConfig(
            id="router",
            name="Router",
            provider_type="openai_compatible",
            model="provider/model",
            api_shape="chat_completions",
        )


def test_api_key_is_masked_in_serialized_response():
    config = ModelProviderConfig(
        id="openai-default",
        name="OpenAI",
        provider_type="openai",
        model="gpt-5.4",
        api_key="secret",
    )

    assert config.model_dump(mode="json")["api_key"] == "********"


def test_unsupported_api_shape_fails_validation():
    with pytest.raises(ValidationError):
        ModelProviderConfig(
            id="bad",
            name="Bad",
            provider_type="openai",
            model="x",
            api_shape="completion",
        )


@pytest.mark.asyncio
async def test_connection_test_can_be_mocked(monkeypatch):
    config = ModelProviderConfig(
        id="router",
        name="Router",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="provider/model",
        api_shape="chat_completions",
        tracing_enabled=False,
    )

    async def fake_test_connection(*, name, instructions, user_input, provider_config, session=None) -> str:
        return "connection ok"

    monkeypatch.setattr("app.model_providers.adapter.run_text_agent", fake_test_connection)

    result = await ModelProviderAdapter().test_connection(config)

    assert result.ok is True
    assert result.response_text == "connection ok"
    assert result.capabilities["streaming"] is True


def test_model_provider_api_create_list_get_and_test():
    from unittest.mock import patch

    client = TestClient(app)

    create = client.post(
        "/model-providers",
        json={
            "id": "router-api",
            "name": "Router",
            "provider_type": "openai_compatible",
            "base_url": "https://example.com/v1",
            "model": "provider/model",
            "api_shape": "chat_completions",
            "api_key": "secret",
            "tracing_enabled": False,
        },
    )

    assert create.status_code == 200
    assert create.json()["api_key"] == "********"

    listed = client.get("/model-providers")
    assert listed.status_code == 200
    assert any(item["id"] == "router-api" for item in listed.json())

    fetched = client.get("/model-providers/router-api")
    assert fetched.status_code == 200
    assert fetched.json()["api_key"] == "********"

    async def fake_test_connection(*, name, instructions, user_input, provider_config, session=None) -> str:
        return "connection ok"

    with patch("app.model_providers.adapter.run_text_agent", fake_test_connection):
        tested = client.post("/model-providers/router-api/test")
    assert tested.status_code == 200
    assert tested.json()["ok"] is True
    assert tested.json()["response_text"] == "connection ok"


def test_model_provider_persists_real_api_key_but_returns_masked():
    client = TestClient(app)

    response = client.post(
        "/model-providers",
        json={
            "id": "router-real",
            "name": "Router Real",
            "provider_type": "openai_compatible",
            "base_url": "https://llm.example.org/v1",
            "model": "provider/model",
            "api_shape": "chat_completions",
            "api_key": "real-secret-key",
        },
    )

    assert response.status_code == 200
    assert response.json()["api_key"] == "********"

    stored = (settings.data_dir / "model-providers" / "router-real.json").read_text(encoding="utf-8")
    assert '"api_key": "real-secret-key"' in stored
    assert '"base_url": "https://llm.example.org/v1"' in stored


@pytest.mark.asyncio
async def test_llm_client_logs_sanitized_request_and_response(caplog, monkeypatch):
    config = ModelProviderConfig(
        id="openai-default",
        name="OpenAI",
        provider_type="openai",
        model="gpt-5.4",
        api_key="sk-secret",
        api_shape="responses",
    )

    class FakeResponses:
        async def create(self, **_kwargs):
            class FakeResponse:
                output_text = '{"ok": true, "note": "OPENAI_API_KEY=sk-secret"}'

            return FakeResponse()

    class FakeClient:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr("app.model_providers.llm_client.AsyncOpenAI", FakeClient)

    caplog.set_level("INFO")
    result = await LLMClient().distill_playbook(config, {"proposal": "OPENAI_API_KEY=sk-secret"})

    assert result["ok"] is True
    messages = [record.getMessage() for record in caplog.records]
    assert any("LLM request:" in message for message in messages)
    assert any("LLM response:" in message for message in messages)
    assert all("sk-secret" not in message for message in messages)
