"""Operator-owned connection names and paths; never request routing inputs."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PREFIX = "HERMES_A2A_GATEWAY_"


def connection_name(value: str | None = None) -> str:
    name = os.environ.get(PREFIX + "CLIENT_CONNECTION", "default") if value is None else value
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", name):
        raise ValueError("invalid client connection name")
    return name


def state_path(component: str, connection: str | None = None) -> Path:
    name = connection_name(connection)
    root = Path.home() / ".local/state/hermes-a2a-gateway"
    return (root if name == "default" else root / "connections" / name) / component


def config_path(connection: str | None = None) -> Path:
    name = connection_name(connection)
    root = Path.home() / ".config/hermes-a2a-gateway"
    return root if name == "default" else root / "connections" / name


def server_name() -> str:
    name = connection_name()
    value = os.environ.get(
        PREFIX + "MCP_SERVER_NAME", "hermes-a2a-gateway" if name == "default" else f"hermes-a2a-{name}"
    )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError("invalid MCP server name")
    return value


def broker_origin(url: str | None = None) -> str:
    parsed = urlsplit(os.environ.get(PREFIX + "CLIENT_BROKER_URL", "") if url is None else url)
    try:
        host, port = parsed.hostname, parsed.port
    except ValueError:
        return "unconfigured"
    if parsed.scheme not in {"https", "http"} or not host:
        return "unconfigured"
    host = f"[{host}]" if ":" in host else host
    return f"{parsed.scheme}://{host}:{port or (443 if parsed.scheme == 'https' else 80)}"


def connection_diagnostics(name: str, state: Path, port: int | None) -> dict[str, Any]:
    """Inspect supported launcher configs without returning values or secret-bearing errors."""
    root = config_path("default")
    candidates = [("default", root)]
    folder = root / "connections"
    if folder.is_dir() and not folder.is_symlink():
        candidates.extend((p.name, p) for p in sorted(folder.iterdir()) if p.is_dir() and not p.is_symlink())
    found, warnings = [], []
    states: dict[str, str] = {str(state.resolve()): name}
    ports: dict[int, str] = {} if port is None else {port: name}
    for other, directory in candidates:
        try:
            connection_name(other)
            file = directory / "client.json"
            if not file.is_file() or file.is_symlink():
                continue
            found.append(other)
            if other == name:
                continue
            # Configs contain credentials. Only allowlisted metadata is used below.
            if file.stat().st_size > 65536:
                warnings.append("unreadable_connection_configuration")
                continue
            values = json.loads(file.read_text())
            path = str(
                Path(values.get(PREFIX + "CLIENT_STATE_DIR", state_path("client", other))).expanduser().resolve()
            )
            if path in states:
                warnings.append("shared_state_directory")
            states[path] = other
            if values.get(PREFIX + "CLIENT_TRANSPORT_MODE") == "ssh-tunnel":
                local = int(values.get(PREFIX + "CLIENT_SSH_LOCAL_PORT", 18790))
                if local in ports:
                    warnings.append("shared_ssh_local_port")
                ports[local] = other
        except (ValueError, TypeError, AttributeError, OSError):
            warnings.append("unreadable_connection_configuration")
    return {"configured_connections": found, "connection_warnings": sorted(set(warnings))}
