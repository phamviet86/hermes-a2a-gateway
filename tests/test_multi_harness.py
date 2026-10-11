"""Offline isolation at the local trusted-adapter boundary."""

from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from test_client import Host, meta, origin, service, snapshot

from hermes_a2a_gateway import client_mcp
from hermes_a2a_gateway.client import create_client_app
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.client_store import ClientStore
from hermes_a2a_gateway.native_delivery import NativeOrigin


@pytest.fixture
def settings(tmp_path):
    return ClientSettings(
        broker_url="https://broker.invalid",
        token="fixture",
        payload_key=Fernet.generate_key().decode(),
        state_dir=tmp_path / "private",
    )


def generic(value):
    return {
        "x-hermes-turn-metadata": {
            "conversation_id": value.thread_id,
            "turn_id": value.turn_id,
            "call_id": value.call_id,
        }
    }


def test_identical_ids_isolate_flows_calls_and_survive_restart(settings):
    base = origin()
    origins = [
        base,
        replace(base, instance="other"),
        replace(base, harness="antigravity"),
        replace(base, harness="antigravity", instance="other"),
    ]
    store = ClientStore(settings)
    operations = [store.create(o, "fixture", [], 0) for o in origins]
    flows = [store.row(op)["flow_id"] for op in operations]
    assert len(set(operations)) == len(set(flows)) == 4
    assert store.row(operations[0])["thread_id"] == base.thread_id
    for o, op in zip(origins, operations, strict=True):
        assert store.create(o, "fixture", [], 0) == op
        assert store.resolve_call(o)["operation_id"] == op
    store.close()
    # Existing schema requires no rebuild or payload/ID rewrite. Reopen twice.
    for _ in range(2):
        store = ClientStore(settings)
        for i, o in enumerate(origins):
            assert store.row(operations[i], o)["flow_id"] == flows[i]
            for j, op in enumerate(operations):
                if i != j:
                    with pytest.raises(KeyError):
                        store.view(op, o, consume=True)
        store.close()


@pytest.mark.parametrize("other_harness", [True, False])
@pytest.mark.parametrize("action", ["get", "wait", "cancel", "resolve_call"])
async def test_daemon_denies_other_harness_before_broker_or_mutation(settings, action, other_harness):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(500)

    client = service(settings, handler=handler)
    owner = origin()
    op = client.store.create(owner, "fixture", [], 0)
    foreign = replace(owner, harness="antigravity") if other_harness else replace(owner, instance="other")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_client_app(client, manage_lifecycle=False)), base_url="http://client"
    ) as transport:
        response = await transport.post(
            "/command",
            json={
                "action": "harness_v1/" + action,
                "identity": {"harness": foreign.harness, "instance": foreign.instance},
                "meta": generic(foreign) if other_harness else meta(foreign),
                "arguments": {"operation_id": op, "timeout": 0},
            },
        )
    assert response.status_code == 404
    assert requests == []
    assert client.store.row(op)["cancel_state"] is None
    assert client.store.row(op)["delivery_state"] == "inline_pending"
    await client.close()


async def test_only_default_codex_delivers_including_uncertain_restart(settings):
    host = Host()
    client = service(settings, host)
    base = origin()
    origins = [base, replace(base, harness="antigravity"), replace(base, instance="other")]
    operations = []
    for o in origins:
        op = client.store.create(o, "fixture", [], 0)
        operations.append(op)
        client.store.accept_snapshot(snapshot(client.store, op))
        client.store.release_inline(op)
    await client.deliver_ready()
    assert len(host.calls) == 1 and host.calls[0][0] == base.thread_id
    for op in operations[1:]:
        assert client.store.row(op)["delivery_state"] == "unsupported"
        client.store.finish_delivery(op, "delivery_outcome_unknown")
    await client.close()
    host = Host(match="wrong-queue")
    client = service(settings, host)
    await client.deliver_ready()
    assert host.calls == [] and host.reconciliations == 0
    assert client.store.view(operations[1], origins[1])["state"] == "completed"
    await client.close()


def test_adapter_config_is_trusted_and_no_fallback_or_operation_lookup(monkeypatch):
    value = replace(origin(), harness="antigravity")
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS", "antigravity")
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE", "laptop")
    ctx = SimpleNamespace(request_context=SimpleNamespace(meta=generic(value)))
    assert client_mcp.request_meta(ctx) == generic(value)
    parsed = NativeOrigin.from_meta(client_mcp.request_meta(ctx), client_mcp.harness_identity())
    assert parsed.instance == "laptop" and parsed.harness == "antigravity"
    ctx.request_context.meta = meta(value)
    with pytest.raises(ValueError):
        client_mcp.request_meta(ctx)
    ctx.request_context.meta = None
    with pytest.raises(ValueError):
        client_mcp.request_meta(ctx)
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS", "../invalid")
    with pytest.raises(ValueError):
        client_mcp.request_meta(ctx)


@pytest.mark.parametrize(
    "identity",
    [
        {},
        {"harness": "other"},
        {"harness": "other", "instance": 1},
        {"harness": "codex", "instance": "x", "extra": "y"},
    ],
)
def test_invalid_identity_rejected(identity):
    with pytest.raises(ValueError):
        NativeOrigin.from_meta(meta(origin()), identity)


def test_generic_conversation_ids_need_not_be_uuid():
    value = NativeOrigin("conversation/42", "turn-7", "call-2", "other", "one")
    parsed = NativeOrigin.from_meta(generic(value), {"harness": "other", "instance": "one"})
    assert parsed == value
    assert parsed.storage_thread_id.startswith("harness:")
    assert str(uuid4()) != parsed.storage_thread_id


@pytest.mark.parametrize("capability", [None, 1])
async def test_facade_negotiates_nondefault_identity_before_command(monkeypatch, capability):
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS", "codex")
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE", "other")
    requests = []
    real_client = httpx.AsyncClient

    def handler(request):
        import json

        requests.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json={"harness_identity_version": capability})
        payload = json.loads(request.content)
        assert payload["identity"] == {"harness": "codex", "instance": "other"}
        assert payload["action"] == "harness_v1/get"
        assert "identity" not in payload["arguments"]
        return httpx.Response(200, json={"state": "accepted"})

    monkeypatch.setattr(
        client_mcp.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), base_url="http://client"),
    )
    ctx = SimpleNamespace(request_context=SimpleNamespace(meta=meta(origin())))
    response = await client_mcp.invoke(ctx, "get", {"operation_id": str(uuid4())})
    assert response.is_error == (capability is None)
    assert requests == (["GET"] if capability is None else ["GET", "POST"])


@pytest.mark.parametrize("field,value", [("conversation_id", ""), ("turn_id", 1), ("call_id", "x" * 513)])
def test_generic_invalid_host_metadata_fails(field, value):
    data = generic(origin())
    data["x-hermes-turn-metadata"][field] = value
    with pytest.raises(ValueError):
        NativeOrigin.from_meta(data, {"harness": "other", "instance": "default"})


async def test_failed_negotiation_never_resolves_call_on_legacy_daemon(monkeypatch):
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE", "other")
    real_client = httpx.AsyncClient
    requests = []

    def handler(request):
        requests.append(request.method)
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(
        client_mcp.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), base_url="http://client"),
    )
    response = await client_mcp.invoke(
        SimpleNamespace(request_context=SimpleNamespace(meta=meta(origin()))), "submit", {"prompt": "fixture"}
    )
    assert response.is_error
    assert requests == ["GET"]
