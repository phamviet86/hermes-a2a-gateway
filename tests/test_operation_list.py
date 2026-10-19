"""Lost-ID recovery cannot cross origins, consume a result or call a broker."""

import json
import time
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from cryptography.fernet import Fernet
from test_client import meta, origin, service, snapshot

from hermes_a2a_gateway import client_mcp
from hermes_a2a_gateway.client import create_client_app
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.client_store import ClientStore
from hermes_a2a_gateway.host_hook import BindingError, claude_values, normalized


@pytest.fixture
def settings(tmp_path):
    return ClientSettings(
        broker_url="https://broker.invalid",
        token="fixture",
        payload_key=Fernet.generate_key().decode(),
        state_dir=tmp_path / "inbox",
    )


def test_local_list_scoping_order_bounds_and_no_content(settings):
    store = ClientStore(settings)
    a, b = origin(), origin()
    try:
        first = store.create(a, "secret-one", [], 0)
        second = store.create(replace(a, call_id="second"), "secret-two", [], 0)
        other = store.create(b, "secret-other", [], 0)
        store.accept_snapshot(snapshot(store, first))
        before = list(map(tuple, store.db.execute("SELECT * FROM client_operations")))
        receipts = store.receipts()
        listed = store.list_operations(a)
        assert [item["operation_id"] for item in listed] == [second, first]
        assert listed[1]["result_available"] is True
        assert [i["operation_id"] for i in store.list_operations(a, include_finished=False)] == [second]
        assert store.list_operations(b)[0]["operation_id"] == other
        assert len(store.list_operations(a, 1)) == 1
        assert all(key not in json.dumps(listed) for key in ["secret-one", "secret-two", "untrusted text"])
        assert before == list(map(tuple, store.db.execute("SELECT * FROM client_operations")))
        assert store.receipts() == receipts
        store.db.execute("UPDATE client_operations SET expires=? WHERE operation_id=?", (time.time() - 1, first))
        store.db.commit()
        assert [i["operation_id"] for i in store.list_operations(a)] == [second]
        for value in (0, 51, True, 1.0, "10"):
            with pytest.raises(ValueError):
                store.list_operations(a, value)
        with pytest.raises(ValueError):
            store.list_operations(a, include_finished="true")
    finally:
        store.close()


async def test_list_api_uses_same_origin_and_never_refreshes(settings):
    requests = []
    client = service(settings, handler=lambda r: requests.append(r) or httpx.Response(500))
    owner = origin()
    op = client.store.create(owner, "fixture", [], 0)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_client_app(client, manage_lifecycle=False)),
            base_url="http://client",
        ) as api:
            response = await api.post("/command", json={"action": "list", "meta": meta(owner), "arguments": {}})
            assert response.json()["operations"][0]["operation_id"] == op
            response = await api.post("/command", json={"action": "list", "meta": meta(origin()), "arguments": {}})
            assert response.json()["operations"] == []
            response = await api.post("/command", json={"action": "list", "arguments": {}})
            assert response.status_code == 400
        result = await client_mcp.gateway_list(SimpleNamespace(request_context=SimpleNamespace(meta={})))
        assert result.is_error
        assert not requests
    finally:
        await client.close()


def test_hook_list_arguments_bound_to_attestation():
    from uuid import uuid4

    key, values = normalized("gateway_list", {"request_key": str(uuid4())})
    assert values == {"limit": 10, "include_finished": True}
    assert claude_values("gateway_list", {}) == values
    for args in ({"limit": 0}, {"limit": True}, {"include_finished": 1}, {"conversation_id": "forged"}):
        with pytest.raises(BindingError):
            claude_values("gateway_list", args)
