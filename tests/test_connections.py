"""Connection defaults and isolation use only disposable configuration/state."""

import json
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from test_client import origin

from hermes_a2a_gateway.client import ClientService, create_client_app
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.connections import (
    broker_origin,
    config_path,
    connection_diagnostics,
    connection_name,
    server_name,
    state_path,
)
from hermes_a2a_gateway.host_hook import Bindings, ClaudeBindings
from hermes_a2a_gateway.host_profiles import AntigravityProfile, ClaudeProfile


def test_default_and_named_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_A2A_GATEWAY_CLIENT_CONNECTION", raising=False)
    assert state_path("client") == tmp_path / ".local/state/hermes-a2a-gateway/client"
    assert config_path() == tmp_path / ".config/hermes-a2a-gateway"
    assert server_name() == "hermes-a2a-gateway"
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_CONNECTION", "helen")
    assert server_name() == "hermes-a2a-helen"
    assert config_path().name == "helen"
    assert state_path("client").parts[-3:] == ("connections", "helen", "client")
    for cls, leaf in [(Bindings, "antigravity"), (ClaudeBindings, "claude")]:
        store = cls()
        assert store.directory == state_path(leaf)
        store.close()
    monkeypatch.setenv("HERMES_A2A_GATEWAY_MCP_SERVER_NAME", "explicit")
    assert server_name() == "explicit"
    monkeypatch.setenv("HERMES_A2A_GATEWAY_MCP_SERVER_NAME", "../bad")
    with pytest.raises(ValueError):
        server_name()


@pytest.mark.parametrize("name", ["", "A", "../escape", "a_", "a" * 33])
def test_invalid_connection_before_files(name, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_CONNECTION", name)
    with pytest.raises(ValueError):
        ClientSettings.from_env()
    with pytest.raises(ValueError):
        Bindings()
    assert not list(tmp_path.iterdir())


async def test_two_daemon_stores_and_commands_are_isolated(tmp_path):
    one = ClientSettings(
        broker_url="https://one.invalid",
        token="one",
        payload_key=Fernet.generate_key().decode(),
        connection="one",
        state_dir=tmp_path / "one",
    )
    two = replace(
        one, connection="two", token="two", payload_key=Fernet.generate_key().decode(), state_dir=tmp_path / "two"
    )
    services = [ClientService(s) for s in (one, two)]
    owner = origin()
    try:
        operation = services[0].store.create(owner, "private", [], 0)
        assert one.socket_path != two.socket_path
        # Both hold their own writer lock simultaneously; the same trusted origin
        # does not authorize reading an operation from another connection.
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_client_app(services[1], manage_lifecycle=False)),
            base_url="http://client",
        ) as client:
            from test_client import meta

            response = await client.post(
                "/command", json={"action": "get", "meta": meta(owner), "arguments": {"operation_id": operation}}
            )
            assert response.status_code == 404
        with pytest.raises(RuntimeError):
            ClientService(one)
    finally:
        for s in services:
            await s.close()


def test_hooks_follow_configured_server(monkeypatch):
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_CONNECTION", "second")
    antigravity = {
        "toolCall": {
            "name": "call_mcp_tool",
            "args": {"ServerName": "hermes-a2a-second", "ToolName": "gateway_get", "Arguments": {}},
        }
    }
    assert AntigravityProfile().parse(antigravity) is not None
    antigravity["toolCall"]["args"]["ServerName"] = "hermes-a2a-gateway"
    assert AntigravityProfile().parse(antigravity) is None
    claude = {
        "tool_name": "mcp__hermes-a2a-second__gateway_get",
        "hook_event_name": "PreToolUse",
        "session_id": str(uuid4()),
        "tool_use_id": "call-1",
        "tool_input": {},
    }
    assert ClaudeProfile().parse(claude)[2] == "gateway_get"
    claude["tool_name"] = "mcp__hermes-a2a-gateway__gateway_get"
    assert ClaudeProfile().parse(claude) is None


def test_doctor_reports_collisions_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    directory = config_path("other")
    directory.mkdir(parents=True)
    state = tmp_path / "shared"
    (directory / "client.json").write_text(
        json.dumps(
            {
                "HERMES_A2A_GATEWAY_CLIENT_STATE_DIR": str(state),
                "HERMES_A2A_GATEWAY_CLIENT_TOKEN": "do-not-report",
                "HERMES_A2A_GATEWAY_CLIENT_TRANSPORT_MODE": "ssh-tunnel",
                "HERMES_A2A_GATEWAY_CLIENT_SSH_LOCAL_PORT": 18790,
            }
        )
    )
    report = connection_diagnostics(connection_name(), state, 18790)
    assert report["configured_connections"] == ["other"]
    assert set(report["connection_warnings"]) == {"shared_state_directory", "shared_ssh_local_port"}
    assert "do-not-report" not in json.dumps(report)
    assert broker_origin("https://user:secret@example.test/path?secret") == "https://example.test:443"


async def test_real_daemons_bind_distinct_sockets():
    import asyncio
    import os
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix="hc-") as directory:
        processes = []
        try:
            for name in ("one", "two"):
                state = Path(directory) / name
                environment = {k: v for k, v in os.environ.items() if not k.startswith("HERMES_A2A_GATEWAY_")}
                environment.update(
                    {
                        "HERMES_A2A_GATEWAY_CLIENT_CONNECTION": name,
                        "HERMES_A2A_GATEWAY_CLIENT_STATE_DIR": str(state),
                        "HERMES_A2A_GATEWAY_CLIENT_BROKER_URL": "https://127.0.0.1:1",
                        "HERMES_A2A_GATEWAY_CLIENT_TOKEN": "disposable-" + name,
                        "HERMES_A2A_GATEWAY_CLIENT_PAYLOAD_KEY": Fernet.generate_key().decode(),
                        "HERMES_A2A_GATEWAY_CLIENT_NATIVE_DELIVERY": "false",
                    }
                )
                process = subprocess.Popen(
                    [sys.executable, "-m", "hermes_a2a_gateway.cli", "client"],
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                processes.append(process)
            for name in ("one", "two"):
                path = Path(directory) / name / "client.sock"
                for _ in range(100):
                    if path.exists():
                        break
                    assert all(p.poll() is None for p in processes)
                    await asyncio.sleep(0.05)
                async with httpx.AsyncClient(
                    transport=httpx.AsyncHTTPTransport(uds=str(path)), base_url="http://client"
                ) as client:
                    response = await client.get("/healthz")
                    assert response.json()["connection_name"] == name
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
