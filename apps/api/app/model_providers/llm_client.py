from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.model_provider import ModelProviderConfig
from app.services.audit_log import AuditLogger

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[2]
import sys

VENDOR_SITE = REPO_ROOT / ".vendor" / "py312"
if str(VENDOR_SITE) not in sys.path and VENDOR_SITE.exists():
    sys.path.insert(0, str(VENDOR_SITE))

from openai import AsyncOpenAI


class LLMClientError(RuntimeError):
    """Raised when model output cannot be parsed into the expected shape."""


logger = logging.getLogger(__name__)
MIN_PROVIDER_TIMEOUT_SECONDS = 150


class LLMClient:
    def __init__(self) -> None:
        self._distillation_prompt = self._load_prompt("distillation.md")
        self._review_prompt = self._load_prompt("review.md")
        self._audit_logger = AuditLogger(Path(__file__).resolve().parents[3] / "data" / "audit")

    @property
    def distillation_prompt(self) -> str:
        return self._distillation_prompt

    @property
    def review_prompt(self) -> str:
        return self._review_prompt

    async def distill_playbook(self, config: ModelProviderConfig, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = self._distillation_prompt
        user_content = json.dumps(payload, ensure_ascii=False, indent=2)
        return await self._request_json(config, prompt, user_content)

    async def review_proposal(self, config: ModelProviderConfig, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = self._review_prompt
        user_content = json.dumps(payload, ensure_ascii=False, indent=2)
        return await self._request_json(config, prompt, user_content)

    async def test_connection(self, config: ModelProviderConfig) -> str:
        client = AsyncOpenAI(
            api_key=config.api_key.get_secret_value() if config.api_key else None,
            base_url=config.base_url,
            timeout=float(max(config.timeout_seconds, MIN_PROVIDER_TIMEOUT_SECONDS)),
            max_retries=config.max_retries,
        )

        system_prompt = "Return a short plain-text confirmation that the model API is reachable."
        user_content = "Reply with: connection ok"

        if config.api_shape == "responses":
            response = await client.responses.create(
                model=config.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            text = getattr(response, "output_text", None)
            if not text:
                raise LLMClientError("responses API did not return output_text")
            return text.strip()

        completion = await client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        message = completion.choices[0].message.content if completion.choices else None
        if not message:
            raise LLMClientError("chat completions API returned empty content")
        return message.strip()

    async def _request_json(
        self,
        config: ModelProviderConfig,
        system_prompt: str,
        user_content: str,
    ) -> dict[str, Any]:
        request_log = self._audit_logger.sanitize(
            {
                "provider_id": config.id,
                "provider_type": config.provider_type,
                "api_shape": config.api_shape,
                "base_url": config.base_url,
                "model": config.model,
                "system_prompt": system_prompt,
                "user_content": user_content,
            }
        )
        logger.info("LLM request: %s", json.dumps(request_log, ensure_ascii=False))

        client = AsyncOpenAI(
            api_key=config.api_key.get_secret_value() if config.api_key else None,
            base_url=config.base_url,
            timeout=float(max(config.timeout_seconds, MIN_PROVIDER_TIMEOUT_SECONDS)),
            max_retries=config.max_retries,
        )

        if config.api_shape == "responses":
            response = await client.responses.create(
                model=config.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
            )
            text = getattr(response, "output_text", None)
            if not text:
                raise LLMClientError("responses API did not return output_text")
            response_log = self._audit_logger.sanitize(
                {
                    "provider_id": config.id,
                    "api_shape": config.api_shape,
                    "model": config.model,
                    "response_text": text,
                }
            )
            logger.info("LLM response: %s", json.dumps(response_log, ensure_ascii=False))
            return self._parse_json(text)

        completion = await client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
        message = completion.choices[0].message.content if completion.choices else None
        if not message:
            raise LLMClientError("chat completions API returned empty content")
        response_log = self._audit_logger.sanitize(
            {
                "provider_id": config.id,
                "api_shape": config.api_shape,
                "model": config.model,
                "response_text": message,
            }
        )
        logger.info("LLM response: %s", json.dumps(response_log, ensure_ascii=False))
        return self._parse_json(message)

    def _parse_json(self, text: str) -> dict[str, Any]:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            raise LLMClientError("model response was not valid JSON") from error
        if not isinstance(parsed, dict):
            raise LLMClientError("model response must be a JSON object")
        return parsed

    def _load_prompt(self, name: str) -> str:
        path = Path(__file__).resolve().parents[1] / "agents" / "prompts" / name
        return path.read_text(encoding="utf-8")


def summarize_provider_error(error: Exception) -> str:
    message = str(error).strip()
    if "Example Domain" in message:
        return "Provider base_url points to a placeholder page instead of an OpenAI-compatible API endpoint."
    normalized = message.lower()
    if "524" in normalized:
        return "上游网关超时（524），模型服务长时间未返回结果。"
    if "502" in normalized or "bad gateway" in normalized:
        return "上游网关不可用（502 Bad Gateway），模型服务或中转网关当前异常。"
    if not message:
        return error.__class__.__name__
    if len(message) > 280:
        return message[:280] + "..."
    return message
