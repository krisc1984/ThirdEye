from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

McpTransport = Literal["stdio", "streamable_http", "sse"]
McpServiceScope = Literal["global", "project"]
McpServiceStatus = Literal["connected", "idle", "attention"]


class McpEnvVar(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(default="")


class McpServerConfig(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    transport: McpTransport
    scope: McpServiceScope = "global"
    status: McpServiceStatus = "idle"
    enabled: bool = True
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    endpoint: str | None = None
    env: list[McpEnvVar] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_transport_payload(self) -> "McpServerConfig":
        if self.transport == "stdio":
            if not (self.command or "").strip():
                raise ValueError("stdio transport requires command")
        elif not (self.endpoint or "").strip():
            raise ValueError("http and sse transports require endpoint")
        return self


class McpServerCreateRequest(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    transport: McpTransport
    scope: McpServiceScope = "global"
    enabled: bool = True
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    endpoint: str | None = None
    env: list[McpEnvVar] = Field(default_factory=list)


class McpServerToggleRequest(BaseModel):
    enabled: bool

