"""Antigravity MCP facade authenticated by its native PreToolUse hook."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from types import SimpleNamespace
from typing import Annotated, Any, cast

from mcp import types
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import Field

from . import __version__, client_mcp
from .antigravity_binding import BindingError, Bindings

mcp = MCPServer[Any](
    "hermes-a2a-gateway",
    version=__version__,
    log_level="WARNING",
    instructions=(
        "Antigravity host-hook integration. Each tool call MUST have request_key: a new random UUID "
        "for a new action. Preserve that key AND exact arguments on a submit/read retry. "
        "Never retry an ambiguous submit with a new key: use get/wait on the saved operation_id. "
        "The native hook supplies conversation identity; do not pass or invent conversation IDs. "
        "Different conversations must never reuse keys. Keep operation IDs within their originating "
        "conversation. Reopened chats retain their host identity and flow. Model label changes do "
        "not create a new flow. Default sender labels are Antigravity / Gemini model / a2a; model "
        "is an optional user-selected descriptive override. Only explicit pull is supported. "
        "Cancellation is best effort. Upload only when explicitly requested. Never blindly retry "
        "an upload or cancel whose acknowledgement is uncertain."
    ),
)
Key = Annotated[str, Field(description="Unique UUID for a new action; retain exact key/arguments on retry.")]


def binding_context(tool: str, args: dict[str, Any]) -> Context[Any, Any]:
    if client_mcp.harness_identity()["harness"] != "antigravity":
        raise BindingError("antigravity_process_configuration_required")
    bindings = Bindings()
    try:
        meta = bindings.origin(tool, args)
    finally:
        bindings.close()
    return cast(Context[Any, Any], SimpleNamespace(request_context=SimpleNamespace(meta=meta)))


async def execute(tool: str, args: dict[str, Any]) -> types.CallToolResult:
    try:
        ctx = await asyncio.to_thread(binding_context, tool, args)
    except (BindingError, OSError, sqlite3.Error):
        payload = {
            "error": {
                "code": "host_hook_binding_required",
                "message": "Fresh host attestation of this exact request required.",
            }
        }
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(payload))],
            structured_content=payload,
            is_error=True,
        )
    values = {k: v for k, v in args.items() if k != "request_key"}
    result: types.CallToolResult = await getattr(client_mcp, tool)(ctx=ctx, **values)
    return result


@mcp.tool(annotations=client_mcp.WRITE, structured_output=True)
async def gateway_submit(
    prompt: Annotated[str, Field(min_length=1, max_length=262144)],
    request_key: Key,
    artifact_ids: Annotated[list[str] | None, Field(max_length=16)] = None,
    wait_seconds: Annotated[float | None, Field(ge=0, le=60, allow_inf_nan=False)] = None,
    model: Annotated[str | None, Field(min_length=1, max_length=256)] = None,
) -> types.CallToolResult:
    """Submit once in this host conversation. Save operation_id; new key means new work."""
    return await execute(
        "gateway_submit",
        {
            "prompt": prompt,
            "request_key": request_key,
            "artifact_ids": artifact_ids,
            "wait_seconds": wait_seconds,
            "model": model,
        },
    )


@mcp.tool(annotations=client_mcp.READ, structured_output=True)
async def gateway_get(operation_id: str, request_key: Key) -> types.CallToolResult:
    """Read an operation owned by this host conversation; never resubmit unknown work."""
    return await execute("gateway_get", {"operation_id": operation_id, "request_key": request_key})


@mcp.tool(annotations=client_mcp.READ, structured_output=True)
async def gateway_wait(
    operation_id: str,
    request_key: Key,
    timeout: Annotated[float, Field(ge=0, le=60)] = 30,
) -> types.CallToolResult:
    """Wait boundedly for this conversation's known operation. Preserve key on retry."""
    return await execute("gateway_wait", {"operation_id": operation_id, "request_key": request_key, "timeout": timeout})


@mcp.tool(annotations=client_mcp.WRITE, structured_output=True)
async def gateway_cancel(operation_id: str, request_key: Key) -> types.CallToolResult:
    """Request best-effort cancellation of this conversation's operation only."""
    return await execute("gateway_cancel", {"operation_id": operation_id, "request_key": request_key})


@mcp.tool(annotations=client_mcp.WRITE, structured_output=True)
async def gateway_upload_artifact(
    path: str,
    request_key: Key,
    content_type: str = "application/octet-stream",
) -> types.CallToolResult:
    """Upload one explicitly requested bounded file after host provenance verification."""
    return await execute(
        "gateway_upload_artifact", {"path": path, "request_key": request_key, "content_type": content_type}
    )


def main() -> None:
    os.umask(0o077)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
