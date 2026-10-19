from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_a2a_gateway import client_mcp
from hermes_a2a_gateway.host_identity import IdentityError, select_provider


@pytest.mark.parametrize(
    "harness,expected", [("codex", "codex-meta"), ("antigravity", "hermes-meta"), ("claude", "hermes-meta")]
)
def test_defaults_preserve_existing_metadata_contract(monkeypatch, harness, expected):
    monkeypatch.delenv("HERMES_A2A_GATEWAY_CLIENT_IDENTITY", raising=False)
    assert select_provider({"harness": harness, "instance": "default"}).name == expected


@pytest.mark.parametrize(
    "harness,name",
    [
        ("codex", "hermes-meta"),
        ("antigravity", "codex-meta"),
        ("codex", "hook:antigravity"),
        ("claude", "hook:antigravity"),
        ("codex", "hook:claude"),
        ("claude", "single-conversation"),
        ("codex", ""),
        ("codex", "unknown"),
    ],
)
def test_unsupported_provider_pair_fails_closed(harness, name):
    with pytest.raises(IdentityError):
        select_provider({"harness": harness, "instance": "default"}, name)


async def test_full_v010_schema_and_instruction_snapshots():
    snapshot = json.loads((Path(__file__).parent / "fixtures/mcp-v010.json").read_text())
    for name, server in [("codex", client_mcp.mcp), ("antigravity", client_mcp.antigravity_server)]:
        assert server.instructions.startswith("Connection: default; broker origin: unconfigured. ")
        assert server.instructions.endswith(snapshot[name]["instructions"])
        assert [t.model_dump(mode="json") for t in await server.list_tools()] == snapshot[name]["tools"]


def test_unified_entrypoint_selects_hook_schema(monkeypatch):
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS", "antigravity")
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_IDENTITY", "hook:antigravity")
    assert client_mcp.configured_server() is client_mcp.antigravity_server


def test_startup_invalid_configuration_has_no_protocol_or_secret_output():
    env = {**os.environ, "HERMES_A2A_GATEWAY_CLIENT_IDENTITY": "invalid-secret-sentinel"}
    result = subprocess.run(
        [sys.executable, "-m", "hermes_a2a_gateway.client_mcp"],
        input="",
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "invalid-secret-sentinel" not in result.stderr


def test_hook_alias_keeps_module_and_registry_constants():
    from hermes_a2a_gateway import antigravity_binding, host_hook

    assert antigravity_binding is host_hook


def test_shared_and_legacy_hook_entrypoints_preserve_permission_flow():
    for module, args in [("host_hook", ["--profile", "antigravity"]), ("antigravity_binding", [])]:
        result = subprocess.run(
            [sys.executable, "-m", "hermes_a2a_gateway." + module, *args],
            input="{}",
            text=True,
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert json.loads(result.stdout) == {"decision": "ask"}
        assert result.stderr == ""


@pytest.mark.parametrize(
    "identity",
    [{"harness": "bad space", "instance": "default"}, {"harness": "codex", "instance": ""}, {"harness": "codex"}],
)
def test_startup_rejects_invalid_namespace(identity):
    with pytest.raises(IdentityError):
        select_provider(identity)


def test_existing_v010_registry_no_schema_migration(tmp_path):
    import sqlite3
    from uuid import uuid4

    from hermes_a2a_gateway.host_hook import Bindings

    directory = tmp_path / "old-registry"
    directory.mkdir(mode=0o700)
    key = directory / "attestation.key"
    key.write_bytes(b"k" * 32)
    key.chmod(0o600)
    path = directory / "bindings.sqlite3"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE bindings (request_key TEXT PRIMARY KEY, conversation TEXT NOT NULL, "
        "tool TEXT NOT NULL, digest TEXT NOT NULL, step INTEGER NOT NULL, expires REAL NOT NULL)"
    )
    before = db.execute("SELECT sql FROM sqlite_master").fetchall()
    db.close()
    path.chmod(0o600)
    bindings = Bindings(directory)
    args = {"request_key": str(uuid4()), "operation_id": str(uuid4())}
    owner = str(uuid4())
    bindings.attest(owner, 1, "gateway_get", args)
    assert bindings.origin("gateway_get", args)["x-hermes-turn-metadata"]["conversation_id"] == owner
    assert bindings.db.execute("SELECT sql FROM sqlite_master").fetchall() == before
    bindings.close()
    assert key.read_bytes() == b"k" * 32
