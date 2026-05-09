from __future__ import annotations

from dataclasses import dataclass

from app.agents.sdk_runtime import run_text_agent
from app.model_providers.llm_client import summarize_provider_error
from app.schemas.model_provider import ModelProviderConfig, ModelProviderTestResult


@dataclass(frozen=True)
class ProviderCapabilities:
    tool_calling: bool
    structured_output: bool
    streaming: bool
    usage_reporting: bool

    def as_dict(self) -> dict[str, bool]:
        return {
            "tool_calling": self.tool_calling,
            "structured_output": self.structured_output,
            "streaming": self.streaming,
            "usage_reporting": self.usage_reporting,
        }


class ModelProviderAdapter:
    def describe_capabilities(self, config: ModelProviderConfig) -> ProviderCapabilities:
        if config.provider_type == "openai" and config.api_shape == "responses":
            return ProviderCapabilities(
                tool_calling=True,
                structured_output=True,
                streaming=True,
                usage_reporting=True,
            )
        return ProviderCapabilities(
            tool_calling=False,
            structured_output=False,
            streaming=True,
            usage_reporting=False,
        )

    async def test_connection(self, config: ModelProviderConfig) -> ModelProviderTestResult:
        if config.provider_type == "openai_compatible" and not config.base_url:
            return ModelProviderTestResult(
                provider_id=config.id,
                ok=False,
                message="OpenAI-compatible provider requires base_url.",
                response_text=None,
                capabilities={},
            )
        capabilities = self.describe_capabilities(config).as_dict()
        try:
            response_text = await run_text_agent(
                name="ThirdEye Model Connectivity Test",
                instructions="Return a short plain-text confirmation that the model API is reachable.",
                user_input="Reply with: connection ok",
                provider_config=config,
            )
        except Exception as error:
            return ModelProviderTestResult(
                provider_id=config.id,
                ok=False,
                message=f"Model API test failed: {summarize_provider_error(error)}",
                response_text=None,
                capabilities=capabilities,
            )
        return ModelProviderTestResult(
            provider_id=config.id,
            ok=True,
            message="Model API responded to the test payload.",
            response_text=response_text,
            capabilities=capabilities,
        )
