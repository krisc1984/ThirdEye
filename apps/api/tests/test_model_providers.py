import pytest
from fastapi.testclient import TestClient
from openai import Omit
from pydantic import ValidationError

from app.main import app
from app.core.config import settings
from app.agents.sdk_runtime import TextAgentRunResult
from app.model_providers.adapter import ModelProviderAdapter
from app.model_providers.llm_client import LLMClient, summarize_provider_error
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
    assert config.max_retries == 0


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


def test_openai_model_header_merge_tolerates_omit_sentinel():
    from agents import ModelSettings, OpenAIChatCompletionsModel, OpenAIResponsesModel

    class _DummyClient:
        pass

    settings = ModelSettings(extra_headers=Omit())

    responses_model = OpenAIResponsesModel(model="gpt-5.4", openai_client=_DummyClient())
    chat_model = OpenAIChatCompletionsModel(model="gpt-5.4", openai_client=_DummyClient())

    assert responses_model._merge_headers(settings)["User-Agent"]
    assert chat_model._merge_headers(settings)["User-Agent"]


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

    async def fake_test_connection(
        *, name, instructions, user_input, provider_config, session=None
    ) -> TextAgentRunResult:
        return TextAgentRunResult(output_text="connection ok")

    monkeypatch.setattr("app.model_providers.adapter.run_text_agent", fake_test_connection)

    result = await ModelProviderAdapter().test_connection(config)

    assert result.ok is True
    assert result.response_text == "connection ok"
    assert result.capabilities["streaming"] is True


@pytest.mark.asyncio
async def test_chat_completions_text_agent_uses_non_streaming_runner(monkeypatch):
    config = ModelProviderConfig(
        id="router",
        name="Router",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="provider/model",
        api_shape="chat_completions",
        api_key="secret",
        tracing_enabled=False,
    )

    called: dict[str, int] = {"run": 0, "run_streamed": 0}

    from agents.models.interface import Model

    class _FakeModel(Model):
        async def get_response(self, *args, **kwargs):
            raise AssertionError("model should not be invoked in this unit test")

        async def stream_response(self, *args, **kwargs):
            raise AssertionError("stream_response should not be invoked in this unit test")

    class _FakeResult:
        final_output = "connection ok"
        interruptions: list[object] = []

    async def fake_run(*args, **kwargs):
        called["run"] += 1
        return _FakeResult()

    def fake_run_streamed(*args, **kwargs):
        called["run_streamed"] += 1
        raise AssertionError("chat_completions provider should not use run_streamed")

    monkeypatch.setattr(
        "app.agents.sdk_runtime.build_agent_model",
        lambda provider_config: _FakeModel(),
    )
    monkeypatch.setattr("app.agents.sdk_runtime.Runner.run", fake_run)
    monkeypatch.setattr("app.agents.sdk_runtime.Runner.run_streamed", fake_run_streamed)

    result = await __import__("app.agents.sdk_runtime", fromlist=["run_text_agent"]).run_text_agent(
        name="Test Agent",
        instructions="Say ok",
        user_input="ping",
        provider_config=config,
    )

    assert result.output_text == "connection ok"
    assert called["run"] == 1
    assert called["run_streamed"] == 0


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

    async def fake_test_connection(
        *, name, instructions, user_input, provider_config, session=None
    ) -> TextAgentRunResult:
        return TextAgentRunResult(output_text="connection ok")

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


def test_summarize_provider_error_maps_502_and_524():
    assert "上游网关超时" in summarize_provider_error(RuntimeError("HTTP 524"))
    assert "上游网关不可用" in summarize_provider_error(RuntimeError("502 Bad Gateway"))
