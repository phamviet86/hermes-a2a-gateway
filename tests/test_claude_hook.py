from __future__ import annotations

import asyncio
import json
import stat
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from test_client import service, snapshot

from hermes_a2a_gateway import client_mcp, host_hook
from hermes_a2a_gateway.client import create_client_app
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.host_hook import BindingError, Bindings, ClaudeBindings, claude_hook
from hermes_a2a_gateway.host_identity import select_provider
from hermes_a2a_gateway.native_delivery import NativeOrigin


@pytest.fixture
def registry(tmp_path, monkeypatch):
    path = tmp_path / "claude"
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLAUDE_BINDING_DIR", str(path))
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS", "claude")
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE", "claude-desktop")
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_IDENTITY", "hook:claude")
    return path


def payload(tool="gateway_get", args=None, session=None, call=None, **extra):
    return {
        "hook_event_name": "PreToolUse",
        "session_id": session or str(uuid4()),
        "tool_use_id": call or "toolu_" + uuid4().hex,
        "tool_name": "mcp__hermes-a2a-gateway__" + tool,
        "tool_input": {"operation_id": str(uuid4())} if args is None else args,
        "mcp_server": {"name": "hermes-a2a-gateway", "source": "project"},
        **extra,
    }


def context(call, **meta):
    return SimpleNamespace(request_context=SimpleNamespace(meta={"claudecode/toolUseId": call, **meta}))


def consume(p):
    return select_provider(client_mcp.harness_identity()).origin_meta(
        p["tool_name"].split("__")[-1], p["tool_input"], {"claudecode/toolUseId": p["tool_use_id"]}
    )


def test_live_shape_single_use_private_storage_and_no_plaintext(registry):
    p = payload("gateway_submit", {"prompt": "private-sentinel"})
    assert claude_hook(p) is None
    origin = consume(p)
    assert origin == {
        "x-hermes-turn-metadata": {
            "conversation_id": p["session_id"],
            "turn_id": p["tool_use_id"],
            "call_id": p["tool_use_id"],
        }
    }
    with pytest.raises(BindingError):
        consume(p)
    assert claude_hook(p)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert stat.S_IMODE(registry.stat().st_mode) == 0o700
    for path in registry.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert b"private-sentinel" not in path.read_bytes()


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", None),
        ("session_id", ""),
        ("session_id", "not-uuid"),
        ("tool_use_id", None),
        ("tool_use_id", " "),
        ("tool_use_id", "x" * 513),
        ("tool_use_id", "x\n"),
        ("hook_event_name", "PostToolUse"),
        ("tool_input", []),
        ("tool_input", {"operation_id": "x", "request_key": str(uuid4())}),
        ("mcp_server", "hermes-a2a-gateway"),
        ("mcp_server", {"name": "other"}),
        ("mcp_server", {"name": "hermes-a2a-gateway", "source": []}),
        ("agent_id", []),
        ("agent_type", ""),
        ("tool_name", None),
        ("tool_name", "mcp__hermes-a2a-gateway__unknown"),
    ],
)
def test_malformed_gateway_fields_deny_without_binding(registry, field, value):
    p = payload()
    p[field] = value
    assert claude_hook(p)["hookSpecificOutput"]["permissionDecision"] == "deny"
    if (registry / "bindings.sqlite3").exists():
        b = ClaudeBindings()
        assert b.db.execute("SELECT count(*) FROM bindings").fetchone()[0] == 0
        b.close()


def test_other_tools_do_not_write_or_override_permissions(registry):
    assert claude_hook(payload(tool_name="mcp__other__gateway_get")) is None
    assert claude_hook(payload(tool_name="Read")) is None
    assert not registry.exists()


def test_custom_server_and_optional_server_field(registry, monkeypatch):
    monkeypatch.setenv("HERMES_A2A_GATEWAY_MCP_SERVER_NAME", "gateway-test")
    p = payload(tool_name="mcp__gateway-test__gateway_get", mcp_server={"name": "gateway-test", "source": "local"})
    assert claude_hook(p) is None
    consume(p)
    p = payload(tool_name="mcp__gateway-test__gateway_get")
    del p["mcp_server"]
    assert claude_hook(p) is None
    consume(p)
    monkeypatch.setenv("HERMES_A2A_GATEWAY_MCP_SERVER_NAME", "bad name")
    assert claude_hook(payload())["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_defaults_and_numeric_normalization_before_wire_transforms(registry):
    p = payload("gateway_submit", {"prompt": "fixture", "wait_seconds": 30})
    assert claude_hook(p) is None
    p["tool_input"] = {"prompt": "fixture", "artifact_ids": None, "wait_seconds": 30.0, "model": None}
    consume(p)
    p = payload("gateway_wait", {"operation_id": "fixture"})
    assert claude_hook(p) is None
    p["tool_input"]["timeout"] = 30
    consume(p)


def test_content_tool_and_expiry_fail_without_consumption(registry, monkeypatch):
    p = payload()
    monkeypatch.setattr(host_hook.time, "time", lambda: 1000)
    assert claude_hook(p) is None
    b = ClaudeBindings()
    for tool, args in [("gateway_cancel", p["tool_input"]), ("gateway_get", {"operation_id": "other"})]:
        with pytest.raises(BindingError):
            b.consume(p["tool_use_id"], tool, args)
    assert b.db.execute("SELECT consumed FROM bindings").fetchone()[0] is None
    assert b.db.execute("SELECT expires FROM bindings").fetchone()[0] == 1300
    monkeypatch.setattr(host_hook.time, "time", lambda: 1300)
    with pytest.raises(BindingError):
        b.consume(p["tool_use_id"], "gateway_get", p["tool_input"])
    b.close()


async def test_conflicting_hooks_and_consume_are_atomic(registry):
    b = ClaudeBindings()
    b.close()
    p = payload()
    results = await asyncio.gather(
        *(asyncio.to_thread(claude_hook, {**p, "session_id": str(uuid4())}) for _ in range(2))
    )
    assert sum(result is None for result in results) == 1

    def read():
        try:
            return consume(p)
        except BindingError:
            return None

    results = await asyncio.gather(*(asyncio.to_thread(read) for _ in range(2)))
    assert sum(result is not None for result in results) == 1


def test_profile_registry_isolation_and_additive_consumed_column(registry, tmp_path):
    b = ClaudeBindings()
    before = {r[1] for r in b.db.execute("PRAGMA table_info(bindings)")}
    assert "consumed" in before
    b.close()
    with pytest.raises(BindingError, match="profile"):
        Bindings(registry)
    old = tmp_path / "antigravity"
    b = Bindings(old)
    schema = b.db.execute("SELECT sql FROM sqlite_master").fetchall()
    b.close()
    with pytest.raises(BindingError, match="profile"):
        ClaudeBindings(old)
    b = Bindings(old)
    assert b.db.execute("SELECT sql FROM sqlite_master").fetchall() == schema
    b.close()


def test_pruning_only_old_expired_or_consumed_rows(registry, monkeypatch):
    monkeypatch.setattr(host_hook.time, "time", lambda: 100000)
    p, q, r = payload(), payload(), payload()
    for x in (p, q, r):
        assert claude_hook(x) is None
    b = ClaudeBindings()
    b.db.execute("UPDATE bindings SET expires=0 WHERE request_key=?", (p["tool_use_id"],))
    b.db.execute("UPDATE bindings SET consumed=0 WHERE request_key=?", (q["tool_use_id"],))
    b.close()
    assert claude_hook(payload()) is None
    b = ClaudeBindings()
    assert b.db.execute("SELECT count(*) FROM bindings").fetchone()[0] == 2
    assert b.db.execute("SELECT 1 FROM bindings WHERE request_key=?", (r["tool_use_id"],)).fetchone()
    b.close()


@pytest.mark.parametrize(
    "raw", ["{", "[]", "x" * (1024 * 1024 + 1), "[" * 2000], ids=["json", "list", "oversized", "nested"]
)
def test_invalid_stdin_denies_with_fixed_safe_json(registry, raw):
    result = subprocess.run(
        [sys.executable, "-m", "hermes_a2a_gateway.host_hook", "--profile", "claude"],
        input=raw,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert result.stderr == ""


def test_valid_hook_stdout_is_empty(registry):
    result = subprocess.run(
        [sys.executable, "-m", "hermes_a2a_gateway.host_hook", "--profile", "claude"],
        input=json.dumps(payload()),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""


async def test_missing_provenance_and_forged_meta_never_reach_transport_or_upload(registry, monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("unattested request touched transport/file")

    monkeypatch.setattr(client_mcp.httpx, "AsyncHTTPTransport", fail)
    forged = {"x-hermes-turn-metadata": {"conversation_id": str(uuid4()), "turn_id": "x", "call_id": "x"}}
    result = await client_mcp.gateway_get("x", context("unknown", **forged))
    assert result.structured_content["error"]["code"] == "host_hook_binding_required"
    monkeypatch.setattr(client_mcp.os, "open", fail)
    result = await client_mcp.gateway_upload_artifact(
        "/never/open", SimpleNamespace(request_context=SimpleNamespace(meta={}))
    )
    assert result.structured_content["error"]["code"] == "host_hook_binding_required"


async def test_lost_ack_uses_same_consumed_origin_and_model_defaults(registry, monkeypatch):
    p = payload("gateway_submit", {"prompt": "fixture"})
    assert claude_hook(p) is None
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_MODEL", "operator-label")
    commands = []

    def handler(request):
        if request.url.path == "/healthz":
            return httpx.Response(200, json={"harness_identity_version": 1, "sender_context_version": 1})
        command = json.loads(request.content)
        commands.append(command)
        if command["action"] == "harness_v1/submit":
            raise httpx.ReadError("private error sentinel")
        return httpx.Response(200, json={"operation_id": "saved-operation"})

    monkeypatch.setattr(client_mcp.httpx, "AsyncHTTPTransport", lambda **kw: httpx.MockTransport(handler))
    result = await client_mcp.gateway_submit(
        "fixture", context(p["tool_use_id"], **{"x-hermes-turn-metadata": {"forged": True}})
    )
    assert not result.is_error and result.structured_content["local_ack_recovered"]
    assert len(commands) == 2
    assert commands[0]["meta"] == commands[1]["meta"]
    assert commands[0]["meta"]["x-hermes-turn-metadata"]["conversation_id"] == p["session_id"]
    assert commands[0]["arguments"]["model"] == "operator-label"
    assert commands[0]["arguments"]["artifact_ids"] == []
    assert commands[1]["arguments"] == {}
    assert "private error sentinel" not in str(result)
    with pytest.raises(BindingError):
        consume(p)


async def test_upload_consumes_before_file_and_preserves_origin(registry, tmp_path, monkeypatch):
    path = tmp_path / "file.txt"
    path.write_text("fixture")
    p = payload("gateway_upload_artifact", {"path": str(path)})
    assert claude_hook(p) is None
    captured = []

    async def invoke(ctx, action, arguments):
        captured.append((client_mcp.request_meta(ctx), action, arguments))
        return "ok"

    monkeypatch.setattr(client_mcp, "invoke", invoke)
    assert await client_mcp.gateway_upload_artifact(str(path), context(p["tool_use_id"])) == "ok"
    assert captured[0][0]["x-hermes-turn-metadata"]["call_id"] == p["tool_use_id"]
    assert "path" not in captured[0][2]
    assert (await client_mcp.gateway_upload_artifact(str(path), context(p["tool_use_id"]))).is_error
    assert len(captured) == 1


async def test_claude_schema_matches_codex_and_selects_explicit_pull(registry):
    assert client_mcp.configured_server() is client_mcp.claude_server
    assert [x.model_dump() for x in await client_mcp.claude_server.list_tools()] == [
        x.model_dump() for x in await client_mcp.mcp.list_tools()
    ]
    assert "no native push" in client_mcp.claude_server.instructions


async def test_session_and_harness_ownership_and_parent_subagent_reads(registry, tmp_path):
    settings = ClientSettings(
        broker_url="https://broker.invalid",
        token="fixture",
        payload_key=Fernet.generate_key().decode(),
        state_dir=tmp_path / "inbox",
    )
    requests = []
    client = service(settings, handler=lambda r: requests.append(r) or httpx.Response(500))
    parent = str(uuid4())
    p = payload("gateway_submit", {"prompt": "same"}, session=parent, agent_id="child", agent_type="general-purpose")
    assert claude_hook(p) is None
    origin = NativeOrigin.from_meta(consume(p), client_mcp.harness_identity())
    op = client.store.create(origin, "same", [], 0)
    client.store.accept_snapshot(snapshot(client.store, op))
    other = replace(origin, thread_id=str(uuid4()), call_id="other")
    ag = replace(origin, harness="antigravity")
    assert len({client.store.row(client.store.create(o, "same", [], 0))["flow_id"] for o in (origin, other, ag)}) == 3
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_client_app(client, manage_lifecycle=False)), base_url="http://client"
    ) as transport:
        for actor in (other, ag):
            for action in ("get", "wait", "cancel"):
                response = await transport.post(
                    "/command",
                    json={
                        "action": "harness_v1/" + action,
                        "identity": {"harness": actor.harness, "instance": actor.instance},
                        "meta": {
                            "x-hermes-turn-metadata": {
                                "conversation_id": actor.thread_id,
                                "turn_id": actor.turn_id,
                                "call_id": actor.call_id,
                            }
                        },
                        "arguments": {"operation_id": op, "timeout": 0},
                    },
                )
                assert response.status_code == 404
        assert requests == []
        q = payload(args={"operation_id": op}, session=parent)
        assert claude_hook(q) is None
        response = await transport.post(
            "/command",
            json={
                "action": "harness_v1/get",
                "identity": client_mcp.harness_identity(),
                "meta": consume(q),
                "arguments": q["tool_input"],
            },
        )
        assert response.status_code == 200
    await client.close()


@pytest.mark.parametrize(
    "args",
    [
        {"prompt": 42},
        {"prompt": ""},
        {"prompt": "x", "wait_seconds": True},
        {"prompt": "x", "wait_seconds": float("nan")},
        {"prompt": "x", "wait_seconds": 61},
        {"prompt": "x", "artifact_ids": "not-list"},
        {"prompt": "x", "artifact_ids": [42]},
        {"prompt": "x", "model": {}},
        {"prompt": "x", "model": ""},
    ],
)
def test_malformed_arguments_never_attest(registry, args):
    assert claude_hook(payload("gateway_submit", args))["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_claude_rejects_unsafe_storage(registry, tmp_path):
    registry.mkdir(mode=0o755)
    assert claude_hook(payload())["hookSpecificOutput"]["permissionDecision"] == "deny"
    registry.chmod(0o700)
    outside = tmp_path / "outside"
    outside.write_bytes(b"k" * 32)
    outside.chmod(0o600)
    (registry / "attestation.key").symlink_to(outside)
    assert claude_hook(payload())["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert outside.read_bytes() == b"k" * 32


def test_quota_and_same_call_reissue_do_not_renew(registry, monkeypatch):
    monkeypatch.setattr(host_hook, "MAX_BINDINGS", 1)
    p = payload()
    assert claude_hook(p) is None
    b = ClaudeBindings()
    before = b.db.execute("SELECT expires FROM bindings").fetchone()
    b.close()
    assert claude_hook(p)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert claude_hook(payload())["hookSpecificOutput"]["permissionDecision"] == "deny"
    b = ClaudeBindings()
    assert b.db.execute("SELECT expires FROM bindings").fetchone() == before
    b.close()
