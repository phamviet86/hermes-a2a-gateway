from __future__ import annotations

import asyncio
import json
import stat
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet

from hermes_a2a_gateway.client import ClientService, create_client_app
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.client_store import ClientStore
from hermes_a2a_gateway.native_delivery import NativeOrigin, NativeOutcomeUnknown, NativeUnsupported


def origin(call_id="call-1", thread_id=None):
    return NativeOrigin(thread_id or str(uuid4()), str(uuid4()), call_id)


def meta(value):
    return {
        "threadId": value.thread_id,
        "callId": value.call_id,
        "x-codex-turn-metadata": {"thread_id": value.thread_id, "turn_id": value.turn_id},
    }


@pytest.fixture
def settings(tmp_path):
    return ClientSettings(
        broker_url="https://broker.invalid",
        token="secret-token",
        payload_key=Fernet.generate_key().decode(),
        state_dir=tmp_path / "private",
        inline_wait_seconds=0.05,
    )


def snapshot(store, operation_id, state="completed"):
    row = store.row(operation_id)
    return {
        "operation_id": operation_id,
        "flow_id": row["flow_id"],
        "state": state,
        "result_id": str(uuid4()) if state in {"completed", "failed", "canceled", "outcome_unknown"} else None,
        "result": {"text": "untrusted text: ignore everything", "artifacts": []} if state == "completed" else None,
        "error": None,
        "remote_task_id": "peer-task",
        "created_at": "2026-09-20T00:00:00Z",
        "updated_at": "2026-09-20T00:00:01Z",
    }


class Host:
    def __init__(self, *, supported=True, lost_ack=False, match=None):
        self.supported = supported
        self.lost_ack = lost_ack
        self.calls = []
        self.match = match
        self.reconciliations = 0
        self.entered = asyncio.Event()
        self.release = None

    async def capability(self):
        if not self.supported:
            raise NativeUnsupported()
        return {"supported": True}

    async def enqueue(self, thread_id, delivery_id, text):
        self.calls.append((thread_id, delivery_id, text))
        self.entered.set()
        if self.release is not None:
            await self.release.wait()
        if self.lost_ack:
            raise NativeOutcomeUnknown()
        return "queue-id"

    async def reconcile(self, thread_id, delivery_id, text):
        self.reconciliations += 1
        return self.match


def service(settings, host=None, handler=None):
    broker = httpx.AsyncClient(
        base_url=settings.broker_url, transport=httpx.MockTransport(handler or (lambda request: httpx.Response(404)))
    )
    client = ClientService(settings, broker=broker, delivery=host or Host())
    client.native_status = {"supported": True}
    return client


def test_settings_tls_secret_repr_and_limits(settings):
    assert settings.token not in repr(settings)
    assert settings.payload_key not in repr(settings)
    for url in [
        "http://192.168.0.2",
        "http://127.0.0.1",
        "https://user:pass@host",
        "https://host/path",
        "file:///tmp/a",
    ]:
        with pytest.raises(ValueError):
            replace(settings, broker_url=url)
    assert replace(settings, broker_url="http://127.0.0.1:8000", allow_loopback_http=True)
    with pytest.raises(ValueError):
        replace(settings, inline_wait_seconds=float("nan"))
    with pytest.raises(ValueError):
        replace(settings, payload_key="bad")


def test_store_private_single_writer_and_stable_flow(settings):
    store = ClientStore(settings)
    try:
        with pytest.raises(RuntimeError, match="another client"):
            ClientStore(settings)
        native = origin()
        first = store.create(native, "SECRET PROMPT", [], 0)
        assert store.create(native, "SECRET PROMPT", [], 0) == first
        with pytest.raises(ValueError, match="different command"):
            store.create(native, "changed", [], 0)
        second = store.create(origin("call2", native.thread_id), "next", [], 0)
        third = store.create(origin(), "other thread", [], 0)
        assert store.row(first)["flow_id"] == store.row(second)["flow_id"]
        assert store.row(first)["flow_id"] != store.row(third)["flow_id"]
        assert store.payload(first)["prompt"] == "SECRET PROMPT"
        for file in settings.state_dir.iterdir():
            assert b"SECRET PROMPT" not in file.read_bytes()
            assert stat.S_IMODE(file.stat().st_mode) == 0o600
        assert stat.S_IMODE(settings.state_dir.stat().st_mode) == 0o700
        with pytest.raises(KeyError):
            store.row(first, origin())
    finally:
        store.close()


def test_inbox_cursor_atomic_dedup_conflict_and_retention(settings):
    store = ClientStore(settings)
    native = origin()
    op = store.create(native, "prompt", [], 0)
    result = snapshot(store, op)
    bad = {**result, "flow_id": str(uuid4())}
    with pytest.raises(ValueError, match="flow identity"):
        store.accept_snapshot(bad, 7)
    assert store.cursor == 0
    assert store.row(op)["snapshot"] is None
    store.accept_snapshot(result, 7)
    store.accept_snapshot(result, 7)
    assert store.cursor == 7
    assert len(store.receipts()) == 1
    store.accept_snapshot(snapshot(store, op, "running"), 8)
    assert store.view(op, native)["state"] == "completed"
    assert not store.view(op, native)["snapshot_conflict"]
    store.accept_snapshot({**result, "result": {"text": "changed", "artifacts": []}}, 9)
    assert store.view(op, native)["snapshot_conflict"]
    assert store.view(op, native)["result"] == result["result"]
    with store.db:
        store.db.execute("UPDATE client_operations SET expires=0")
    store.prune()
    assert store.view(op, native)["result_expired"]
    assert store.view(op, native)["result"] is None
    assert store.view(op, native)["result_id"] == result["result_id"]
    store.accept_snapshot(result, 10)
    assert store.view(op, native)["result"] is None
    assert store.cursor == 10
    store.close()


async def test_broker_lost_ack_recovers_exact_id_without_resend(settings):
    accepted = {}
    posts = []

    def broker(request):
        if request.method == "GET":
            op = request.url.path.rsplit("/", 1)[1]
            return httpx.Response(200, json=accepted[op]) if op in accepted else httpx.Response(404)
        body = json.loads(request.content)
        posts.append(body)
        accepted[body["operation_id"]] = snapshot(client.store, body["operation_id"], "accepted")
        raise httpx.ReadTimeout("ACK lost")

    client = service(settings, handler=broker)
    native = origin()
    op = client.store.create(native, "secret", [], 0)
    with pytest.raises(httpx.ReadTimeout):
        await client.dispatch_pending()
    assert client.store.row(op)["submission_state"] == "pending"
    await client.close()
    client = service(settings, handler=broker)
    await client.dispatch_pending()
    assert len(posts) == 1
    assert client.store.row(op)["submission_state"] == "accepted"
    assert client.store.row(op)["payload"] is None
    await client.close()


async def test_broker_unaccepted_retry_uses_original_command_and_expiry(settings):
    posts = []

    def broker(request):
        if request.method == "GET":
            return httpx.Response(404)
        posts.append(json.loads(request.content))
        raise httpx.ConnectError("offline")

    client = service(settings, handler=broker)
    op = client.store.create(origin(), "secret", [], 0)
    for _ in range(2):
        with pytest.raises(httpx.ConnectError):
            await client.dispatch_pending()
    assert posts[0] == posts[1]
    with client.store.db:
        client.store.db.execute("UPDATE client_operations SET payload_expires=0")
    await client.dispatch_pending()
    assert len(posts) == 2
    assert client.store.row(op)["submission_state"] == "outcome_unknown"
    client.store.prune()
    assert client.store.row(op)["payload"] is None
    await client.close()


async def test_inline_result_excludes_late_queue_even_at_deadline(settings):
    host = Host()
    client = service(settings, host)
    native = origin()
    pending = asyncio.create_task(client.submit(native, "prompt", [], 0.05))
    await asyncio.sleep(0)
    op = client.store.ids()[0]
    await client.ingest(snapshot(client.store, op))
    # The daemon cannot claim native delivery while the MCP consumer owns inline wait.
    with client.store.db:
        client.store.db.execute("UPDATE client_operations SET inline_deadline=0")
    await client.deliver_ready()
    result = await pending
    assert result["delivery_state"] == "inline_returned"
    await client.deliver_ready()
    assert not host.calls
    await client.close()


async def test_late_reference_queue_is_bound_and_exactly_claimed(settings):
    host = Host()
    client = service(settings, host)
    native = origin()
    result = await client.submit(native, "prompt", [], 0)
    op = result["operation_id"]
    await client.ingest(snapshot(client.store, op))
    await client.deliver_ready()
    await client.deliver_ready()
    assert len(host.calls) == 1
    thread, delivery_id, text = host.calls[0]
    assert thread == native.thread_id
    assert delivery_id == client.store.row(op)["delivery_id"]
    assert "untrusted text" not in text
    assert op in text and "gateway_get" in text
    assert client.store.row(op)["delivery_state"] == "queued"
    # Pull remains available, without claiming queue acceptance proves host consumption.
    assert (await client.get(native, op))["result"]["text"].startswith("untrusted")
    await client.close()


@pytest.mark.parametrize("match,expected", [(None, "delivery_outcome_unknown"), ("exact-queue-id", "queued")])
async def test_lost_native_ack_restart_never_requeues(settings, match, expected):
    host = Host(lost_ack=True)
    client = service(settings, host)
    native = origin()
    op = (await client.submit(native, "prompt", [], 0))["operation_id"]
    await client.ingest(snapshot(client.store, op))
    await client.deliver_ready()
    assert client.store.row(op)["delivery_state"] == "delivery_outcome_unknown"
    await client.close()
    restarted_host = Host(match=match)
    client = service(settings, restarted_host)
    await client.deliver_ready()
    await client.deliver_ready()
    assert not restarted_host.calls
    assert restarted_host.reconciliations == 1
    assert client.store.row(op)["delivery_state"] == expected
    assert (await client.get(native, op))["result_id"]
    await client.close()


async def test_crash_after_intent_preserves_unknown(settings):
    client = service(settings)
    native = origin()
    op = (await client.submit(native, "prompt", [], 0))["operation_id"]
    await client.ingest(snapshot(client.store, op))
    assert client.store.claim_delivery(op)
    await client.close()
    host = Host()
    client = service(settings, host)
    assert client.store.row(op)["delivery_state"] == "delivery_outcome_unknown"
    assert any(r["status"] == "delivery_outcome_unknown" for r in client.store.receipts())
    await client.deliver_ready()
    assert host.calls == []
    await client.close()


async def test_unsupported_native_leaves_pull_and_wait_usable(settings):
    client = service(settings)
    client.native_status = {"supported": False}
    native = origin()
    op = (await client.submit(native, "prompt", [], 0))["operation_id"]
    await client.ingest(snapshot(client.store, op))
    await client.deliver_ready()
    assert client.store.row(op)["delivery_state"] == "unsupported"
    assert (await client.wait(native, op, 0))["delivery_state"] == "inline_returned"
    with pytest.raises(KeyError):
        await client.wait(origin(), op, 0)
    await client.close()


async def test_cancel_lost_ack_is_not_replayed(settings):
    posts = []

    def broker(request):
        posts.append(request)
        raise httpx.ReadTimeout("lost")

    client = service(settings, handler=broker)
    native = origin()
    op = client.store.create(native, "p", [], 0)
    assert (await client.cancel(native, op))["cancel_state"] == "outcome_unknown"
    assert (await client.cancel(native, op))["cancel_state"] == "outcome_unknown"
    assert len(posts) == 1
    await client.close()


async def test_unix_api_missing_wrong_metadata_and_upload_bounds(settings):
    client = service(settings)
    app = create_client_app(client, manage_lifecycle=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://client") as ipc:
        assert (await ipc.post("/command", json={"action": "submit", "arguments": {"prompt": "p"}})).status_code == 400
        native = origin()
        response = await ipc.post(
            "/command", json={"action": "submit", "meta": meta(native), "arguments": {"prompt": "p", "wait_seconds": 0}}
        )
        op = response.json()["operation_id"]
        wrong = await ipc.post(
            "/command", json={"action": "get", "meta": meta(origin()), "arguments": {"operation_id": op}}
        )
        assert wrong.status_code == 404
        assert (await ipc.get("/healthz")).json()["explicit_pull_available"]
    with pytest.raises(ValueError):
        await client.upload(b"x" * (settings.max_upload_bytes + 1), "text/plain")
    await client.close()


async def test_event_stream_replay_and_gap_recovers_known_ids(settings):
    client = None
    requests = []
    event = None

    def broker(request):
        requests.append(str(request.url))
        if request.url.path == "/v1/events":
            after = int(request.url.params["after"])
            if after == 0:
                return httpx.Response(410, json={"error": {"details": {"resume_after": 12}}})
            return httpx.Response(
                200,
                text=f"id: 13\nevent: operation\ndata: {json.dumps(event)}\n\n",
                headers={"Content-Type": "text/event-stream"},
            )
        return httpx.Response(200, json=event)

    client = service(settings, handler=broker)
    native = origin()
    op = client.store.create(native, "p", [], 0)
    event = snapshot(client.store, op)
    events = asyncio.create_task(client._events())
    try:
        async with asyncio.timeout(3):
            while client.store.cursor != 13:
                await asyncio.sleep(0.01)
        assert client.store.view(op, native)["result_id"] == event["result_id"]
        assert any("after=12" in url for url in requests)
        assert any(op in url for url in requests)
    finally:
        events.cancel()
        await asyncio.gather(events, return_exceptions=True)
        await client.close()


def test_pending_admission_and_result_ttl(settings):
    store = ClientStore(replace(settings, max_pending=1))
    first = store.create(origin(), "p", [], 0)
    with pytest.raises(ValueError, match="limit"):
        store.create(origin(), "q", [], 0)
    store.accept_snapshot(snapshot(store, first))
    assert store.create(origin(), "q", [], 0)
    store.close()


async def test_unknown_exact_saved_handle_resolution_can_queue_once(settings):
    host = Host()
    client = service(settings, host)
    native = origin()
    op = (await client.submit(native, "p", [], 0))["operation_id"]
    unknown = snapshot(client.store, op, "outcome_unknown")
    await client.ingest(unknown)
    assert (await client.get(native, op))["state"] == "outcome_unknown"
    await client.deliver_ready()
    assert not host.calls
    final = {**unknown, "state": "completed", "result": {"text": "recovered", "artifacts": []}}
    await client.ingest(final)
    assert not client.store.view(op, native)["snapshot_conflict"]
    assert client.store.view(op, native)["result"]["text"] == "recovered"
    await client.deliver_ready()
    assert len(host.calls) == 1
    await client.ingest(final, 99)
    await client.deliver_ready()
    assert len(host.calls) == 1
    await client.close()


async def test_unknown_without_same_exact_handle_cannot_resolve(settings):
    client = service(settings)
    native = origin()
    op = (await client.submit(native, "p", [], 0))["operation_id"]
    unknown = {**snapshot(client.store, op, "outcome_unknown"), "remote_task_id": None}
    await client.ingest(unknown)
    await client.ingest({**unknown, "state": "completed", "remote_task_id": "guessed", "result": {"text": "unsafe"}})
    result = client.store.view(op, native)
    assert result["state"] == "outcome_unknown"
    assert result["snapshot_conflict"]
    await client.close()


def test_lost_local_ack_lookup_uses_exact_call_not_latest_candidate(settings):
    store = ClientStore(settings)
    native = origin()
    op = store.create(native, "p", [], 0)
    assert store.resolve_call(native)["operation_id"] == op
    with pytest.raises(KeyError):
        store.resolve_call(NativeOrigin(native.thread_id, native.turn_id, "different-call"))
    with pytest.raises(KeyError):
        store.resolve_call(NativeOrigin(native.thread_id, str(uuid4()), native.call_id))
    store.close()


def test_diagnostic_snapshot_survives_restart_and_expires(settings):
    store = ClientStore(settings)
    native = origin()
    op = store.create(native, "prompt", [], 0)
    result = snapshot(store, op, "failed")
    result["error"] = {
        "code": "peer_rejected",
        "message": "peer could not complete the operation",
        "details": {
            "reason": "context_rate_limited",
            "execution_started": False,
            "retry_after_seconds": 30,
            "recommended_action": "wait_then_submit_new",
        },
    }
    store.accept_snapshot(result, 2)
    before = store.view(op, native)
    store.close()
    store = ClientStore(settings)
    assert store.view(op, native)["error"] == before["error"]
    with store.db:
        store.db.execute("UPDATE client_operations SET expires=0")
    store.prune()
    assert "details" not in (store.view(op, native).get("error") or {})
    store.close()


async def test_doctor_reads_policy_without_submitting(settings):
    from hermes_a2a_gateway.diagnostics import DIAGNOSTICS_URI

    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/v1/peer-policy":
            return httpx.Response(
                200,
                json={
                    "diagnostics_extension": DIAGNOSTICS_URI,
                    "policy": "sliding_window",
                    "context_limit": 5,
                    "window_seconds": 60,
                },
            )
        return httpx.Response(200, json={"ok": True})

    service = ClientService(
        settings,
        broker=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://broker.invalid"),
        delivery=Host(),
    )
    try:
        value = await service.diagnostics()
        assert value["peer_policy"]["policy"] == "sliding_window"
        assert all(method == "GET" for method, _ in calls)
    finally:
        await service.broker.aclose()
        service.store.close()


def test_close_does_not_close_reused_descriptor(settings):
    import os

    store = ClientStore(settings)
    fd = store.lock_fd
    store.close()
    with open(os.devnull) as replacement:
        assert replacement.fileno() == fd
        store.close()
        os.fstat(replacement.fileno())


async def test_recovery_skips_final_but_reconciles_unknown(settings):
    broker = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    client = ClientService(settings, broker=broker, delivery=Host(supported=False))
    completed = client.store.create(origin(), "completed fixture", [], 0)
    unknown = client.store.create(origin(), "unknown fixture", [], 0)
    client.store.accept_snapshot(snapshot(client.store, completed))
    client.store.accept_snapshot(snapshot(client.store, unknown, "outcome_unknown"))
    reads = []

    async def record(operation):
        reads.append(operation)
        return True

    client.refresh = record
    try:
        await client.recover()
        assert reads == [unknown]
        assert completed in client.store.ids(deliverable=True)
    finally:
        await client.close()


async def test_slow_durable_write_does_not_block_health(settings, monkeypatch):
    import threading
    import time

    broker = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    client = ClientService(settings, broker=broker, delivery=Host(supported=False))
    entered = threading.Event()
    original = client.store.create

    def slow(*args, **kwargs):
        entered.set()
        time.sleep(0.2)
        return original(*args, **kwargs)

    monkeypatch.setattr(client.store, "create", slow)
    task = asyncio.create_task(client.submit(origin(), "synthetic slow commit", [], 0))
    try:
        while not entered.is_set():
            await asyncio.sleep(0.001)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(create_client_app(client)), base_url="http://client"
        ) as ipc:
            response = await asyncio.wait_for(ipc.get("/healthz"), 0.1)
            assert response.status_code == 200 and not task.done()
        await task
        assert client.store.db.execute("PRAGMA synchronous").fetchone()[0] == 2
    finally:
        await asyncio.gather(task, return_exceptions=True)
        await client.close()


async def test_bad_receipt_does_not_starve_later_receipts(settings):
    calls = []
    failed = None

    def peer(request):
        value = json.loads(request.content)
        calls.append(value["operation_id"])
        return httpx.Response(404 if value["operation_id"] == failed else 200, json={"ok": True})

    broker = httpx.AsyncClient(transport=httpx.MockTransport(peer), base_url="https://broker.test")
    client = ClientService(settings, broker=broker, delivery=Host(supported=False))
    failed = client.store.create(origin(), "receipt failure", [], 0)
    later = client.store.create(origin(), "later receipt", [], 0)
    client.store.accept_snapshot(snapshot(client.store, failed))
    client.store.accept_snapshot(snapshot(client.store, later))
    try:
        await client.flush_receipts()
        assert calls == [failed, later]
        assert [x["operation_id"] for x in client.store.receipts()] == [failed]
        assert client.health()["receipt_errors"] == 1
        await client.flush_receipts()
        assert calls == [failed, later]
    finally:
        await client.close()


async def test_missing_operation_argument_is_bad_request(settings):
    broker = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    client = ClientService(settings, broker=broker, delivery=Host(supported=False))
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(create_client_app(client)), base_url="http://client"
        ) as ipc:
            response = await ipc.post("/command", json={"action": "get", "meta": meta(origin()), "arguments": {}})
            assert response.status_code == 400 and response.json()["error"]["code"] == "missing_argument"
    finally:
        await client.close()


def test_missing_ca_is_rejected_before_client_state_creation(settings):
    with pytest.raises(ValueError, match="CA_FILE"):
        replace(settings, ca_file=str(settings.state_dir / "not-a-certificate"))
    assert not settings.state_dir.exists()


def test_liveness_optional_for_old_snapshots_and_preserved_for_new(settings):
    from datetime import UTC, datetime, timedelta

    store = ClientStore(settings)
    owner = origin()
    try:
        operation = store.create(owner, "fixture", [], 0)
        legacy = snapshot(store, operation, state="running")
        store.accept_snapshot(legacy)
        assert store.view(operation, owner)["last_peer_activity_at"] is None
        assert store.view(operation, owner)["running_seconds"] is None
        instant = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
        store.accept_snapshot(
            {**legacy, "last_peer_activity_at": instant, "running_started_at": instant, "running_seconds": 30}
        )
        view = store.view(operation, owner)
        assert view["last_peer_activity_at"] == instant and view["running_seconds"] >= 30
    finally:
        store.close()


def test_client_key_rotation_counts_and_new_write_key(settings):
    from cryptography.fernet import InvalidToken

    owner = origin()
    store = ClientStore(settings)
    operation = store.create(owner, "fixture", [], 0)
    store.close()
    new = Fernet.generate_key().decode()
    rotated_settings = replace(settings, payload_key=new, previous_payload_keys=(settings.payload_key,))
    store = ClientStore(rotated_settings)
    try:
        assert store.payload(operation)["prompt"] == "fixture"
        assert store.key_rotation() == {"previous_keys": 1, "payloads_using_previous_keys": 2, "unreadable_payloads": 0}
        fresh = store.create(origin(), "new", [], 0)
        assert Fernet(new.encode()).decrypt(store.row(fresh)["payload"])
        with pytest.raises(InvalidToken):
            Fernet(settings.payload_key.encode()).decrypt(store.row(fresh)["payload"])
        assert new not in repr(rotated_settings) and settings.payload_key not in repr(rotated_settings)
        store.accept_snapshot(snapshot(store, operation))
        assert store.key_rotation()["payloads_using_previous_keys"] == 1
        store.db.execute("UPDATE client_operations SET expires=0,payload_expires=0 WHERE operation_id=?", (operation,))
        store.db.commit()
        store.prune()
        assert store.key_rotation()["payloads_using_previous_keys"] == 0
    finally:
        store.close()


async def test_daemon_health_exposes_count_only_key_rotation(settings):
    client = service(settings)
    try:
        report = client.health()["key_rotation"]
        assert report == {"previous_keys": 0, "payloads_using_previous_keys": 0, "unreadable_payloads": 0}
        assert settings.payload_key not in json.dumps(client.health())
    finally:
        await client.close()
