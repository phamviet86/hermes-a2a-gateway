"""Operator-selected host provenance providers; never model-selected identity."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Protocol

from .client_settings import PREFIX
from .native_delivery import NativeOrigin


class IdentityError(ValueError):
    """Safe identity configuration/provenance failure, without request content."""


class IdentityProvider(Protocol):
    name: str
    requires_request_key: bool

    def origin_meta(self, tool: str, arguments: dict[str, Any], request_meta: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class MetadataProvider:
    name: str
    identity: dict[str, str]
    requires_request_key: bool = False

    def origin_meta(self, tool: str, arguments: dict[str, Any], request_meta: dict[str, Any]) -> dict[str, Any]:
        NativeOrigin.from_meta(request_meta, self.identity)
        return dict(request_meta)


@dataclass
class AntigravityProvider:
    name: str = "hook:antigravity"
    requires_request_key: bool = True

    def origin_meta(self, tool: str, arguments: dict[str, Any], request_meta: dict[str, Any]) -> dict[str, Any]:
        from .host_hook import Bindings

        bindings = Bindings()
        try:
            return bindings.origin(tool, arguments)
        finally:
            bindings.close()


@dataclass
class ClaudeProvider:
    name: str = "hook:claude"
    requires_request_key: bool = False

    def origin_meta(self, tool: str, arguments: dict[str, Any], request_meta: dict[str, Any]) -> dict[str, Any]:
        from .host_hook import ClaudeBindings, valid_call_id

        call = valid_call_id(request_meta.get("claudecode/toolUseId"))
        bindings = ClaudeBindings()
        try:
            # Replace host metadata; forged x-hermes-turn-metadata is never forwarded.
            return bindings.consume(call, tool, arguments)
        finally:
            bindings.close()


def select_provider(identity: dict[str, str], name: str | None = None) -> IdentityProvider:
    if set(identity) != {"harness", "instance"} or any(
        not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,63}", value)
        for value in identity.values()
    ):
        raise IdentityError("invalid_identity_provider_configuration")
    harness = identity["harness"]
    chosen = name if name is not None else os.environ.get(PREFIX + "IDENTITY")
    if chosen is None:
        chosen = "codex-meta" if harness == "codex" else "hermes-meta"
    if chosen == "codex-meta" and harness == "codex" or chosen == "hermes-meta" and harness != "codex":
        return MetadataProvider(chosen, identity)
    if chosen == "hook:antigravity" and harness == "antigravity":
        return AntigravityProvider()
    if chosen == "hook:claude" and harness == "claude":
        return ClaudeProvider()
    raise IdentityError("invalid_identity_provider_configuration")
