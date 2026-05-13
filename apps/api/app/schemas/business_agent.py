from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

BusinessAgentStatus = Literal["active", "draft"]


class BusinessAgentConfig(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="review", min_length=1, max_length=60)
    system_prompt: str = Field(default="", min_length=1)
    status: BusinessAgentStatus = "draft"
    is_default: bool = False

    @field_validator("id", "name", "description", "category", "system_prompt", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class BusinessAgentActivateRequest(BaseModel):
    id: str

