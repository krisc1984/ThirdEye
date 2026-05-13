from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolArgumentSpec:
    required_fields: tuple[str, ...]
    example_json: str


def format_required_tool_arguments_error(
    *,
    tool_name: str,
    tool_arguments: str,
    required_shape: str,
    example_json: str,
) -> str:
    raw_arguments = (tool_arguments or "").strip()
    if not raw_arguments:
        return (
            f"Error: {tool_name} was called with empty arguments. "
            f"You must send a complete JSON object with {required_shape}. "
            f"Example: {example_json}"
        )
    return (
        f"Error: {tool_name} arguments are invalid. "
        f"You must send a complete JSON object with {required_shape}. "
        f"Received: {raw_arguments[:400]}. "
        f"Example: {example_json}"
    )


def validate_tool_json_arguments(
    *,
    tool_name: str,
    tool_arguments: str,
    spec: ToolArgumentSpec,
) -> tuple[dict[str, Any] | None, str | None]:
    raw_arguments = (tool_arguments or "").strip()
    required_shape = ", ".join(f'"{field}"' for field in spec.required_fields)
    if not raw_arguments:
        return None, format_required_tool_arguments_error(
            tool_name=tool_name,
            tool_arguments=raw_arguments,
            required_shape=required_shape,
            example_json=spec.example_json,
        )

    try:
        payload = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return None, format_required_tool_arguments_error(
            tool_name=tool_name,
            tool_arguments=raw_arguments,
            required_shape=required_shape,
            example_json=spec.example_json,
        )

    if not isinstance(payload, dict):
        return None, format_required_tool_arguments_error(
            tool_name=tool_name,
            tool_arguments=raw_arguments,
            required_shape=required_shape,
            example_json=spec.example_json,
        )

    missing = [field for field in spec.required_fields if payload.get(field) in (None, "")]
    if missing:
        return None, format_required_tool_arguments_error(
            tool_name=tool_name,
            tool_arguments=raw_arguments,
            required_shape=required_shape,
            example_json=spec.example_json,
        )

    return payload, None
