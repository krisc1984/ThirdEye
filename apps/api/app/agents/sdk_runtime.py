from __future__ import annotations

import json
import logging
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

import openai.types.responses as openai_responses_types

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Provide a tiny fallback for optional vendored SDK dependencies that are not
# installed in the current backend environment.
if "griffe" not in sys.modules:
    griffe_stub = types.ModuleType("griffe")

    class _DocstringSectionKind:
        text = "text"
        parameters = "parameters"

    class _DocstringSection:
        def __init__(self, kind: str, value: Any):
            self.kind = kind
            self.value = value

    class _Docstring:
        def __init__(self, text: str, lineno: int = 1, parser: str | None = None):
            self.text = text

        def parse(self) -> list[_DocstringSection]:
            lines = self.text.splitlines()
            description_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if description_lines:
                        break
                    continue
                if stripped.startswith(("Args:", "Arguments:", "Parameters", ":param")):
                    break
                description_lines.append(stripped)
            description = " ".join(description_lines).strip()
            return [_DocstringSection(_DocstringSectionKind.text, description)] if description else []

    griffe_stub.Docstring = _Docstring
    griffe_stub.DocstringSectionKind = _DocstringSectionKind
    sys.modules["griffe"] = griffe_stub

# The local src/agents tree may be newer than the installed openai package.
# Patch missing response item aliases so the vendored SDK can import.
if not hasattr(openai_responses_types, "ResponseToolSearchCall"):
    fallback = getattr(openai_responses_types, "ResponseFileSearchToolCall", dict[str, Any])
    setattr(openai_responses_types, "ResponseToolSearchCall", fallback)
if not hasattr(openai_responses_types, "ResponseToolSearchOutputItem"):
    fallback = getattr(openai_responses_types, "ResponseOutputItem", dict[str, Any])
    setattr(openai_responses_types, "ResponseToolSearchOutputItem", fallback)

from agents import (
    Agent,
    ModelSettings,
    OpenAIChatCompletionsModel,
    OpenAIResponsesModel,
    RunConfig,
    RunHooks,
    Runner,
    RunState,
    SQLiteSession,
    set_tracing_disabled,
)

from app.schemas.model_provider import ModelProviderConfig

logger = logging.getLogger(__name__)
SESSION_AGENT_MAX_TURNS = 100


@dataclass
class SDKRunLogContext:
    workflow_name: str
    provider_id: str
    model: str
    llm_turn: int = 0


@dataclass
class TextAgentRunResult:
    output_text: str
    resume_state_json: dict[str, Any] | None = None
    interrupted: bool = False
    interrupted_reason: str | None = None


class AgentResumeError(RuntimeError):
    def __init__(self, message: str, *, resume_state_json: dict[str, Any] | None = None):
        super().__init__(message)
        self.resume_state_json = resume_state_json


class AgentRunLogger(RunHooks[SDKRunLogContext]):
    async def on_agent_start(self, context, agent) -> None:
        run = context.context
        logger.info(
            "Agents SDK agent start: %s",
            json.dumps(
                {
                    "workflow": run.workflow_name,
                    "provider_id": run.provider_id,
                    "model": run.model,
                    "agent": agent.name,
                },
                ensure_ascii=False,
            ),
        )

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        run = context.context
        run.llm_turn += 1
        logger.info(
            "Agents SDK llm turn start: %s",
            json.dumps(
                {
                    "workflow": run.workflow_name,
                    "provider_id": run.provider_id,
                    "model": run.model,
                    "agent": agent.name,
                    "turn": run.llm_turn,
                    "input_items": len(input_items),
                },
                ensure_ascii=False,
            ),
        )

    async def on_tool_start(self, context, agent, tool) -> None:
        run = context.context
        logger.info(
            "Agents SDK tool start: %s",
            json.dumps(
                {
                    "workflow": run.workflow_name,
                    "provider_id": run.provider_id,
                    "model": run.model,
                    "agent": agent.name,
                    "turn": run.llm_turn,
                    "tool_name": getattr(tool, "name", tool.__class__.__name__),
                    "tool_call_id": getattr(context, "tool_call_id", None),
                    "tool_arguments": _clip_value(getattr(context, "tool_arguments", None), 600),
                },
                ensure_ascii=False,
            ),
        )

    async def on_tool_end(self, context, agent, tool, result) -> None:
        run = context.context
        logger.info(
            "Agents SDK tool end: %s",
            json.dumps(
                {
                    "workflow": run.workflow_name,
                    "provider_id": run.provider_id,
                    "model": run.model,
                    "agent": agent.name,
                    "turn": run.llm_turn,
                    "tool_name": getattr(tool, "name", tool.__class__.__name__),
                    "tool_call_id": getattr(context, "tool_call_id", None),
                    "result": _clip_value(result, 1200),
                },
                ensure_ascii=False,
            ),
        )

    async def on_llm_end(self, context, agent, response) -> None:
        run = context.context
        logger.info(
            "Agents SDK llm turn end: %s",
            json.dumps(
                {
                    "workflow": run.workflow_name,
                    "provider_id": run.provider_id,
                    "model": run.model,
                    "agent": agent.name,
                    "turn": run.llm_turn,
                    "output_items": len(getattr(response, "output", []) or []),
                    "response_id": getattr(response, "response_id", None),
                    "usage": getattr(getattr(response, "usage", None), "model_dump", lambda: None)(),
                },
                ensure_ascii=False,
            ),
        )

    async def on_agent_end(self, context, agent, output) -> None:
        run = context.context
        logger.info(
            "Agents SDK agent end: %s",
            json.dumps(
                {
                    "workflow": run.workflow_name,
                    "provider_id": run.provider_id,
                    "model": run.model,
                    "agent": agent.name,
                    "turns": run.llm_turn,
                    "output": _clip_value(output, 1200),
                },
                ensure_ascii=False,
            ),
        )


def _clip_value(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "..."


def build_openai_client(config: ModelProviderConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=config.api_key.get_secret_value() if config.api_key else None,
        base_url=config.base_url,
        timeout=float(config.timeout_seconds),
        max_retries=config.max_retries,
    )


def build_agent_model(config: ModelProviderConfig):
    client = build_openai_client(config)
    if config.api_shape == "chat_completions":
        return OpenAIChatCompletionsModel(model=config.model, openai_client=client)
    return OpenAIResponsesModel(model=config.model, openai_client=client)


def build_run_config(config: ModelProviderConfig | None) -> RunConfig | None:
    if config is None:
        return None
    set_tracing_disabled(disabled=not config.tracing_enabled)
    return RunConfig(
        tracing_disabled=not config.tracing_enabled,
        workflow_name=f"ThirdEye::{config.id}",
        trace_metadata={"provider_id": config.id, "model": config.model},
    )


def build_sqlite_session(session_id: str, db_path: Path) -> SQLiteSession:
    return SQLiteSession(session_id=session_id, db_path=db_path)


async def run_text_agent(
    *,
    name: str,
    instructions: str,
    user_input: str,
    provider_config: ModelProviderConfig,
    session: SQLiteSession | None = None,
    tools: list[Any] | None = None,
    model_settings: ModelSettings | None = None,
    resume_state: RunState[Any] | None = None,
) -> TextAgentRunResult:
    log_context = SDKRunLogContext(
        workflow_name=name,
        provider_id=provider_config.id,
        model=provider_config.model,
    )
    agent = Agent(
        name=name,
        instructions=instructions,
        model=build_agent_model(provider_config),
        tools=tools or [],
        model_settings=model_settings or ModelSettings(),
    )
    streamed = Runner.run_streamed(
        agent,
        resume_state if resume_state is not None else user_input,
        context=log_context,
        max_turns=SESSION_AGENT_MAX_TURNS,
        hooks=AgentRunLogger(),
        run_config=build_run_config(provider_config),
        session=session,
    )
    try:
        async for _event in streamed.stream_events():
            pass
    except Exception as error:
        raise AgentResumeError(
            str(error),
            resume_state_json=streamed.to_state().to_json(),
        ) from error

    final_output = streamed.final_output
    output_text = final_output if isinstance(final_output, str) else json.dumps(final_output, ensure_ascii=False)
    if streamed.interruptions:
        return TextAgentRunResult(
            output_text=output_text,
            resume_state_json=streamed.to_state().to_json(),
            interrupted=True,
            interrupted_reason="interruption",
        )
    return TextAgentRunResult(output_text=output_text)


async def run_structured_agent(
    *,
    name: str,
    instructions: str,
    user_input: str,
    provider_config: ModelProviderConfig,
    output_type: type[BaseModel],
    session: SQLiteSession | None = None,
) -> BaseModel:
    log_context = SDKRunLogContext(
        workflow_name=name,
        provider_id=provider_config.id,
        model=provider_config.model,
    )
    agent = Agent(
        name=name,
        instructions=instructions,
        model=build_agent_model(provider_config),
        output_type=output_type,
    )
    result = await Runner.run(
        agent,
        user_input,
        context=log_context,
        max_turns=SESSION_AGENT_MAX_TURNS,
        hooks=AgentRunLogger(),
        run_config=build_run_config(provider_config),
        session=session,
    )
    output = result.final_output
    if isinstance(output, output_type):
        return output
    if isinstance(output, dict):
        return output_type.model_validate(output)
    if isinstance(output, str):
        return output_type.model_validate_json(output)
    raise TypeError(f"Unsupported structured agent output type: {type(output).__name__}")


def build_json_prompt(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
