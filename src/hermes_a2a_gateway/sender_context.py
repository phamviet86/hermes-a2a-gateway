"""Descriptive sender labels. Never routing identity, authentication or capability claims."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SenderContext(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    harness: str = Field(min_length=1, max_length=64)
    model: str | None = Field(default=None, min_length=1, max_length=256)
    connection: Literal["a2a"] = "a2a"

    @field_validator("harness", "model")
    @classmethod
    def label(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or any(ord(c) < 32 for c in value)):
            raise ValueError("invalid descriptive label")
        return value


def sender_context(harness: str, model: str | None = None) -> dict[str, str | None]:
    # Family labels only. There is deliberately no model capability table.
    defaults = {
        "codex": ("Codex", "Codex model"),
        "antigravity": ("Antigravity", "Gemini model"),
        "claude": ("Claude", "Claude model"),
        "gemini": ("Gemini", "Gemini model"),
    }
    label, fallback = defaults.get(harness, (harness, None))
    return SenderContext(harness=label, model=model if model is not None else fallback).model_dump()
