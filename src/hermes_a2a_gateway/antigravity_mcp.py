"""Compatible Antigravity module entrypoint for the unified MCP facade."""

from __future__ import annotations

import os

from . import client_mcp
from .client_mcp import (
    binding_context as binding_context,
)
from .client_mcp import (
    execute as execute,
)
from .client_mcp import (
    run_client_mcp,
)
from .client_settings import PREFIX

mcp = client_mcp.antigravity_server
gateway_submit = client_mcp.antigravity_gateway_submit
gateway_get = client_mcp.antigravity_gateway_get
gateway_wait = client_mcp.antigravity_gateway_wait
gateway_cancel = client_mcp.antigravity_gateway_cancel
gateway_upload_artifact = client_mcp.antigravity_gateway_upload_artifact


def main() -> None:
    import sys

    os.umask(0o077)
    configured = os.environ.get(PREFIX + "IDENTITY", "hook:antigravity")
    if configured != "hook:antigravity":
        print("Antigravity entrypoint requires hook:antigravity identity.", file=sys.stderr)
        raise SystemExit(2)
    os.environ[PREFIX + "IDENTITY"] = configured
    run_client_mcp()


if __name__ == "__main__":
    main()
