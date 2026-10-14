"""Native hook envelope parsing, separate from durable attestation storage."""

from __future__ import annotations

import json
from typing import Any


class AntigravityProfile:
    """The established Antigravity wrapper and permission behavior."""

    def parse(self, payload: Any) -> tuple[Any, Any, Any, Any] | None:
        from .host_hook import SERVER

        call = payload.get("toolCall", {})
        wrapper = call.get("args", {})
        if call.get("name") != "call_mcp_tool" or wrapper.get("ServerName") != SERVER:
            return None
        arguments = wrapper.get("Arguments")
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        return payload.get("conversationId"), payload.get("stepIdx"), wrapper.get("ToolName"), arguments


class ClaudeProfile:
    """Observed Desktop Code PreToolUse shape; identity is host-owned."""

    def parse(self, payload: Any) -> tuple[str, str, str, dict[str, Any]] | None:
        import os
        import re
        from uuid import UUID

        from .host_hook import BindingError, valid_call_id

        server = os.environ.get("HERMES_A2A_GATEWAY_MCP_SERVER_NAME", "hermes-a2a-gateway")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", server):
            raise BindingError("invalid_hook_server_configuration")
        if not isinstance(payload, dict) or not isinstance(payload.get("tool_name"), str):
            raise BindingError("invalid_host_hook_input")
        prefix = f"mcp__{server}__"
        name = payload["tool_name"]
        if not name.startswith(prefix):
            return None
        if payload.get("hook_event_name") != "PreToolUse":
            raise BindingError("invalid_host_hook_input")
        if "mcp_server" in payload:
            value = payload["mcp_server"]
            if not isinstance(value, dict) or value.get("name") != server:
                raise BindingError("invalid_hook_server")
            if "source" in value and (
                not isinstance(value["source"], str) or not value["source"].strip() or len(value["source"]) > 128
            ):
                raise BindingError("invalid_hook_server")
        conversation = payload.get("session_id")
        try:
            if not isinstance(conversation, str) or str(UUID(conversation)) != conversation:
                raise ValueError
        except ValueError:
            raise BindingError("trusted_hook_identity_required") from None
        for key in ("agent_id", "agent_type"):
            if key in payload:
                valid_call_id(payload[key])  # Shape only: never a routing or sender field.
        call = valid_call_id(payload.get("tool_use_id"))
        arguments = payload.get("tool_input")
        if not isinstance(arguments, dict):
            raise BindingError("invalid_binding_request")
        return conversation, call, name[len(prefix) :], arguments
