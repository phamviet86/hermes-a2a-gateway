from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest

from hermes_a2a_gateway import antigravity_mcp, client_mcp
from hermes_a2a_gateway.antigravity_binding import ENV, BindingError, Bindings, hook, normalized


def request(tool="gateway_get", **values):
    return {
        "request_key": str(uuid4()),
        **({"operation_id": str(uuid4())} if tool != "gateway_submit" else {"prompt": "harmless"}),
        **values,
    }


def payload(conversation, args, tool="gateway_get", step=3):
    return {
        "conversationId": conversation,
        "stepIdx": step,
        "toolCall": {
            "name": "call_mcp_tool",
            "args": {"ServerName": "hermes-a2a-gateway", "ToolName": tool, "Arguments": json.dumps(args)},
        },
    }


@pytest.fixture
def binding_dir(tmp_path, monkeypatch):
    p = tmp_path / "binding"
    monkeypatch.setenv(ENV, str(p))
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS", "antigravity")
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE", "ag-desktop")
    return p


def test_actual_host_wrapper_binds_identity_and_normalizes_defaults(binding_dir):
    conversation = str(uuid4())
    args = request("gateway_submit")
    assert hook(payload(conversation, args, "gateway_submit")) == {"decision": "ask"}
    b = Bindings()
    meta = b.origin("gateway_submit", {**args, "artifact_ids": None, "wait_seconds": None, "model": None})
    b.close()
    assert meta == {
        "x-hermes-turn-metadata": {
            "conversation_id": conversation,
            "turn_id": args["request_key"],
            "call_id": args["request_key"],
        }
    }
    assert "harmless" not in (binding_dir / "bindings.sqlite3").read_bytes().decode(errors="ignore")


def test_persistent_ownership_after_restart_and_expiry(binding_dir):
    a, b = str(uuid4()), str(uuid4())
    args = request()
    s = Bindings()
    s.attest(a, 1, "gateway_get", args)
    s.db.execute("update bindings set expires=0")
    s.close()
    s = Bindings()
    with pytest.raises(BindingError, match="fresh_host"):
        s.origin("gateway_get", args)
    with pytest.raises(BindingError, match="owner_or_content"):
        s.attest(b, 2, "gateway_get", args)
    s.attest(a, 9, "gateway_get", args)
    assert s.origin("gateway_get", args)["x-hermes-turn-metadata"]["conversation_id"] == a
    s.close()


def test_retry_exact_key_and_arguments_keeps_original_origin(binding_dir):
    a = str(uuid4())
    args = request("gateway_submit")
    s = Bindings()
    s.attest(a, 3, "gateway_submit", args)
    before = s.origin("gateway_submit", args)
    s.attest(a, 99, "gateway_submit", args)
    assert s.origin("gateway_submit", args) == before
    assert s.db.execute("select count(*) from bindings").fetchone()[0] == 1
    with pytest.raises(BindingError):
        s.attest(a, 100, "gateway_submit", {**args, "prompt": "changed"})
    with pytest.raises(BindingError):
        s.origin("gateway_submit", {**args, "model": "Claude model"})
    s.close()


def test_wrong_session_key_and_missing_host_fields_denied(binding_dir):
    args = request()
    assert hook(payload(str(uuid4()), args))["decision"] == "ask"
    assert hook(payload(str(uuid4()), args))["decision"] == "deny"
    p = payload(str(uuid4()), request())
    del p["conversationId"]
    assert hook(p)["decision"] == "deny"
    p = payload(str(uuid4()), request())
    p["stepIdx"] = True
    assert hook(p)["decision"] == "deny"
    p = payload(str(uuid4()), {"operation_id": str(uuid4())})
    assert hook(p)["decision"] == "deny"


def test_non_gateway_never_auto_allowed_or_attested(binding_dir):
    p = payload(str(uuid4()), request())
    p["toolCall"]["args"]["ServerName"] = "unrelated"
    assert hook(p) == {"decision": "ask"}
    assert not binding_dir.exists()


@pytest.mark.parametrize(
    "tool,extra",
    [
        ("gateway_get", {"meta": {"conversationId": "invented"}}),
        ("gateway_get", {"request_key": "global"}),
        ("gateway_wait", {"timeout": True}),
        ("invented", {}),
    ],
)
def test_invalid_request_fail_closed(tool, extra):
    with pytest.raises(BindingError):
        normalized(tool, request(**extra))


def test_storage_modes_and_symlink_fail_closed(tmp_path):
    p = tmp_path / "unsafe"
    p.mkdir(mode=0o755)
    with pytest.raises(BindingError):
        Bindings(p)
    p.chmod(0o700)
    outside = tmp_path / "outside"
    outside.write_bytes(b"x" * 32)
    outside.chmod(0o600)
    (p / "attestation.key").symlink_to(outside)
    with pytest.raises(BindingError):
        Bindings(p)
    assert outside.read_bytes() == b"x" * 32


async def test_concurrent_conversations_cannot_claim_same_key(binding_dir):
    args = request()
    owners = [str(uuid4()), str(uuid4())]

    def claim(owner):
        s = Bindings()
        try:
            s.attest(owner, 1, "gateway_get", args)
            return owner
        except BindingError:
            return None
        finally:
            s.close()

    # Initialize schema/key before racing ownership transactions.
    s = Bindings()
    s.close()
    results = await asyncio.gather(*(asyncio.to_thread(claim, x) for x in owners))
    assert len([x for x in results if x]) == 1


async def test_facade_requires_host_attestation_before_transport(binding_dir, monkeypatch):
    async def no_call(**kwargs):
        pytest.fail("unattested request reached daemon")

    monkeypatch.setattr(client_mcp, "gateway_get", no_call)
    r = await antigravity_mcp.gateway_get(str(uuid4()), str(uuid4()))
    assert r.is_error
    assert r.structured_content["error"]["code"] == "host_hook_binding_required"


async def test_facade_passes_only_host_bound_metadata_and_no_retry_key(binding_dir, monkeypatch):
    args = request()
    owner = str(uuid4())
    hook(payload(owner, args))
    captured = []

    async def receive(**kwargs):
        captured.append(kwargs)
        return client_mcp.types.CallToolResult(content=[])

    monkeypatch.setattr(client_mcp, "gateway_get", receive)
    await antigravity_mcp.gateway_get(args["operation_id"], args["request_key"])
    x = captured[0]
    assert set(x) == {"ctx", "operation_id"}
    assert client_mcp.request_meta(x["ctx"])["x-hermes-turn-metadata"]["conversation_id"] == owner


async def test_schema_preserves_codex_and_requires_retry_key_only_in_ag():
    ag = await antigravity_mcp.mcp.list_tools()
    codex = await client_mcp.mcp.list_tools()
    assert len(ag) == len(codex) == 5
    for tool in ag:
        assert "request_key" in tool.input_schema["required"]
        assert "conversation_id" not in tool.input_schema["properties"]
    for tool in codex:
        assert "request_key" not in tool.input_schema["properties"]


def test_quota_rejects_new_keys_without_discarding_old_ownership(binding_dir, monkeypatch):
    from hermes_a2a_gateway import antigravity_binding

    monkeypatch.setattr(antigravity_binding, "MAX_BINDINGS", 1)
    owner = str(uuid4())
    args = request()
    s = Bindings()
    s.attest(owner, 1, "gateway_get", args)
    with pytest.raises(BindingError, match="quota"):
        s.attest(owner, 2, "gateway_get", request())
    s.attest(owner, 3, "gateway_get", args)
    assert s.origin("gateway_get", args)["x-hermes-turn-metadata"]["conversation_id"] == owner
    with pytest.raises(BindingError, match="owner_or_content"):
        s.attest(str(uuid4()), 4, "gateway_get", args)
    assert (
        s.db.execute("pragma max_page_count").fetchone()[0] * s.db.execute("pragma page_size").fetchone()[0]
        == 64 * 1024 * 1024
    )
    s.close()
