"""Request descriptors stay independent from durable routing identity."""

import hashlib
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from test_client_mcp import context

from hermes_a2a_gateway import client_mcp
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.client_store import ClientStore, canonical
from hermes_a2a_gateway.native_delivery import NativeOrigin
from hermes_a2a_gateway.sender_context import SenderContext, sender_context


@pytest.mark.parametrize(
    "harness,label,model",
    [
        ("codex", "Codex", "Codex model"),
        ("antigravity", "Antigravity", "Gemini model"),
        ("claude", "Claude", "Claude model"),
        ("gemini", "Gemini", "Gemini model"),
        ("other", "other", None),
    ],
)
def test_defaults_override_and_exact_simple_contract(harness, label, model):
    assert sender_context(harness) == {"harness": label, "model": model, "connection": "a2a"}
    assert sender_context(harness, "Claude model")["model"] == "Claude model"


@pytest.mark.parametrize("model", ["", " ", "x" * 257, "bad\nlabel", 42])
def test_invalid_descriptor_fails(model):
    with pytest.raises(ValueError):
        sender_context("codex", model)
    with pytest.raises(ValueError):
        SenderContext(harness="Codex", model="ok", connection="ssh")


def settings_for(path):
    return ClientSettings(
        broker_url="https://broker.invalid", token="fixture", payload_key=Fernet.generate_key().decode(), state_dir=path
    )


def test_persistence_retry_model_change_and_scoped_routing(tmp_path):
    settings = settings_for(tmp_path / "state")
    first = NativeOrigin(str(uuid4()), str(uuid4()), "call", "antigravity")
    store = ClientStore(settings)
    op = store.create(first, "fixture", [], 0)
    payload = store.payload(op)
    assert payload["sender_context"]["model"] == "Gemini model"
    assert store.create(first, "fixture", [], 0) == op
    with pytest.raises(ValueError):
        store.create(first, "fixture", [], 0, "Claude model")
    store.close()
    store = ClientStore(settings)
    assert store.payload(op) == payload
    second = replace(first, turn_id=str(uuid4()), call_id="next")
    other = replace(first, harness="claude")
    op2 = store.create(second, "fixture", [], 0, "Claude model")
    op3 = store.create(other, "fixture", [], 0, "Claude model")
    assert store.row(op)["flow_id"] == store.row(op2)["flow_id"]
    assert store.row(op3)["flow_id"] != store.row(op)["flow_id"]
    with pytest.raises(KeyError):
        store.view(op, other)
    store.db.execute("UPDATE client_operations SET payload=NULL WHERE operation_id=?", (op,))
    store.db.commit()
    assert json.loads(store.cipher.decrypt(store.row(op)["sender_context"])) == payload["sender_context"]
    store.close()


def test_legacy_sqlite_migration_preserves_digest_payload_and_ids(tmp_path):
    settings = settings_for(tmp_path / "state")
    store = ClientStore(settings)
    o = NativeOrigin(str(uuid4()), str(uuid4()), "legacy")
    op = store.create(o, "fixture", [], 0)
    payload = store.payload(op)
    payload.pop("sender_context")
    legacy = store.cipher.encrypt(canonical(payload).encode())
    digest = hashlib.sha256(canonical({"prompt": "fixture", "artifact_ids": []}).encode()).hexdigest()
    store.db.execute("UPDATE client_operations SET payload=?,digest=? WHERE operation_id=?", (legacy, digest, op))
    store.db.execute("ALTER TABLE client_operations DROP COLUMN sender_context")
    store.db.commit()
    flow = store.row(op)["flow_id"]
    store.close()
    store = ClientStore(settings)
    assert store.row(op)["payload"] == legacy and store.row(op)["flow_id"] == flow
    assert store.row(op)["sender_context"] is None
    assert store.create(o, "fixture", [], 0) == op
    assert store.payload(op) == payload
    store.close()


async def test_tool_explicit_model_beats_operator_default(monkeypatch):
    recorded = []

    async def invoke(ctx, action, arguments):
        recorded.append(arguments)

    monkeypatch.setattr(client_mcp, "invoke", invoke)
    monkeypatch.setenv("HERMES_A2A_GATEWAY_CLIENT_MODEL", "Gemini model")
    await client_mcp.gateway_submit("fixture", context(), model="Claude model")
    await client_mcp.gateway_submit("fixture", context())
    assert [r["model"] for r in recorded] == ["Claude model", "Gemini model"]


@pytest.mark.parametrize("version", [None, 1])
async def test_submit_requires_sender_context_daemon_capability(monkeypatch, version):
    import json

    import httpx

    requests = []
    real_client = httpx.AsyncClient

    def handler(request):
        requests.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json={"sender_context_version": version})
        body = json.loads(request.content)
        assert body["action"] == "submit"
        return httpx.Response(200, json={"state": "accepted"})

    monkeypatch.setattr(
        client_mcp.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), base_url="http://client"),
    )
    response = await client_mcp.invoke(context(), "submit", {"prompt": "fixture", "model": "Claude model"})
    assert response.is_error == (version is None)
    assert requests == (["GET"] if version is None else ["GET", "POST"])
