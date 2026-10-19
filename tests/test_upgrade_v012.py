"""Real v0.11 wheel migration and two-way process interoperability (disposable only).

Set HERMES_A2A_GATEWAY_TEST_LEGACY_PYTHON to a venv containing the pinned v0.11
wheel, and the normal disposable PostgreSQL DSN. CI prepares that baseline.
"""

import json
import os
import subprocess

import httpx
import pytest
from test_client_server_integration import (
    TOKEN_A,
    Process,
    command,
    eventually,
    origin,
    snapshot,
    unix_socket_ready,
)
from test_client_server_integration import postgres_schema as _postgres_schema
from test_client_server_integration import stack as _stack

from hermes_a2a_gateway.broker_settings import BrokerSettings
from hermes_a2a_gateway.broker_store import BrokerStore
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.client_store import ClientStore

postgres_schema = _postgres_schema
stack = _stack


@pytest.fixture
def legacy_python():
    path = os.environ.get("HERMES_A2A_GATEWAY_TEST_LEGACY_PYTHON")
    if not path:
        pytest.skip("set HERMES_A2A_GATEWAY_TEST_LEGACY_PYTHON for the pinned v0.11 wheel migration gate")
    result = subprocess.run(
        [
            path,
            "-c",
            "import hermes_a2a_gateway as p; from hermes_a2a_gateway.client_settings import ClientSettings; "
            "assert 'connection' not in ClientSettings.__dataclass_fields__; print(p.__version__)",
        ],
        cwd="/tmp",
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "0.11.0"
    return path


class LegacyProcess(Process):
    def __init__(self, python, module, env, directory, name):
        self.python = python
        super().__init__(module, {k: v for k, v in env.items() if k != "PYTHONPATH"}, directory, name)

    def start(self):
        with (self.directory / (self.name + ".log")).open("ab") as output:
            self.process = subprocess.Popen(
                [self.python, "-m", self.module],
                env=self.env,
                cwd="/tmp",
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
            )


def start_legacy(stack, python, role):
    process = LegacyProcess(python, "hermes_a2a_gateway." + role, stack.env.copy(), stack.directory, "old-" + role)
    stack.processes.append(process)

    def ready():
        try:
            if role == "broker":
                return httpx.get(stack.broker_url + "/healthz", timeout=0.2, trust_env=False).status_code == 200
            return unix_socket_ready(stack.directory / "client/client.sock")
        except httpx.TransportError:
            return False

    eventually(ready)
    return process


@pytest.mark.parametrize("legacy_role", ["client", "broker"])
def test_old_new_process_interoperability(stack, legacy_python, legacy_role):
    stack.env["HERMES_A2A_GATEWAY_CLIENT_NATIVE_DELIVERY"] = "false"
    if legacy_role == "broker":
        start_legacy(stack, legacy_python, "broker")
        stack.start_client()
    else:
        stack.start_broker()
        start_legacy(stack, legacy_python, "client")
    meta = origin()
    submitted = command(stack, "submit", meta, prompt="compatible baseline request", wait_seconds=0)
    assert submitted.status_code == 200
    operation = submitted.json()["operation_id"]
    eventually(lambda: snapshot(stack, operation))
    pulled = eventually(lambda: command(stack, "get", meta, operation_id=operation).json().get("result"))
    assert "compatible baseline request" in pulled["text"]
    assert stack.peer.submissions == 1
    if legacy_role == "broker":
        value = command(stack, "get", meta, operation_id=operation).json()
        assert value["last_peer_activity_at"] is None and value["running_seconds"] is None


LEGACY_SEED = r"""
import json
from hermes_a2a_gateway.client_settings import ClientSettings
from hermes_a2a_gateway.client_store import ClientStore
from hermes_a2a_gateway.broker_settings import BrokerSettings
from hermes_a2a_gateway.broker_store import BrokerStore
from hermes_a2a_gateway.native_delivery import NativeOrigin
from uuid import uuid4

client = ClientStore(ClientSettings.from_env())
broker = BrokerStore(BrokerSettings.from_env())
broker.acquire_dispatcher()
operations = []
for state in ('completed', 'running', 'outcome_unknown', 'pending'):
    owner = NativeOrigin(str(uuid4()), str(uuid4()), 'legacy-' + state)
    operation = client.create(owner, 'legacy fixture ' + state, [], 0)
    broker.accept('device-a', client.payload(operation))
    if state != 'pending':
        assert broker.claim()['operation_id'] == operation
        broker.save_handle('device-a', operation, 'legacy-handle-' + state)
    if state == 'completed':
        broker.finish('device-a', operation, 'completed', {'text': 'legacy completed', 'artifacts': []})
    elif state == 'outcome_unknown':
        broker.finish('device-a', operation, 'outcome_unknown', None, 'submission_unknown', 'No automatic resend.')
    snap = broker.get('device-a', operation)
    client.accept_snapshot(snap)
    if state == 'completed':
        client.view(operation, owner, consume=True)
        broker.receipt('device-a', operation, snap['result_id'], 'stored')
    operations.append({
        'label': state, 'operation_id': operation, 'flow_id': snap['flow_id'],
        'result_id': snap['result_id'], 'remote_task_id': snap['remote_task_id'],
        'thread_id': owner.thread_id, 'turn_id': owner.turn_id, 'call_id': owner.call_id,
    })
cursor = broker.events('device-a', 0)[-1][0]
client.advance(cursor)
manifest = {
    'operations': operations, 'cursor': cursor,
    'client_receipts': [list(row) for row in client.db.execute(
        'SELECT * FROM client_receipts ORDER BY operation_id,status')],
    'broker_receipts': [[str(row['operation_id']), str(row['result_id']), row['status']]
                        for row in broker.conn.execute(
                            'SELECT * FROM broker_v06_receipts ORDER BY operation_id,status')],
}
client.close()
broker.close()
print(json.dumps(manifest))
"""


def test_populated_v011_stores_upgrade_in_place_without_replay(stack, legacy_python):
    stack.env["HERMES_A2A_GATEWAY_CLIENT_NATIVE_DELIVERY"] = "false"
    environment = {k: v for k, v in stack.env.items() if k != "PYTHONPATH"}
    seeded = subprocess.run(
        [legacy_python, "-c", LEGACY_SEED], cwd="/tmp", env=environment, capture_output=True, text=True, check=True
    )
    manifest = json.loads(seeded.stdout)
    client_settings = ClientSettings(
        broker_url=stack.proxy.url,
        token=TOKEN_A,
        payload_key=environment["HERMES_A2A_GATEWAY_CLIENT_PAYLOAD_KEY"],
        state_dir=stack.directory / "client",
        allow_loopback_http=True,
        native_delivery=False,
    )
    broker_settings = BrokerSettings(
        database_url=environment["HERMES_A2A_GATEWAY_BROKER_DATABASE_URL"],
        device_tokens={"device-a": TOKEN_A},
        encryption_key=environment["HERMES_A2A_GATEWAY_BROKER_ENCRYPTION_KEY"],
    )
    client = ClientStore(client_settings)
    broker = BrokerStore(broker_settings)
    try:
        assert client.cursor == manifest["cursor"]
        assert [
            list(row) for row in client.db.execute("SELECT * FROM client_receipts ORDER BY operation_id,status")
        ] == manifest["client_receipts"]
        receipts = [
            [str(row["operation_id"]), str(row["result_id"]), row["status"]]
            for row in broker.conn.execute("SELECT * FROM broker_v06_receipts ORDER BY operation_id,status")
        ]
        assert receipts == manifest["broker_receipts"]
        assert broker.events("device-a", 0)[-1][0] == manifest["cursor"]
        for old in manifest["operations"]:
            row = client.row(old["operation_id"])
            for key in ("operation_id", "flow_id", "thread_id", "turn_id", "call_id"):
                assert row[key] == old[key]
            current = broker.get("device-a", old["operation_id"])
            for key in ("operation_id", "flow_id", "result_id", "remote_task_id"):
                assert current[key] == old[key]
        assert client_settings.connection == "default"
    finally:
        client.close()
        broker.close()
    stack.start_broker()
    stack.start_client()
    pending = next(op for op in manifest["operations"] if op["label"] == "pending")
    eventually(lambda: snapshot(stack, pending["operation_id"]))
    meta = {
        "threadId": pending["thread_id"],
        "callId": pending["call_id"],
        "x-codex-turn-metadata": {"thread_id": pending["thread_id"], "turn_id": pending["turn_id"]},
    }
    pulled = eventually(lambda: command(stack, "get", meta, operation_id=pending["operation_id"]).json().get("result"))
    assert "legacy fixture pending" in pulled["text"]
    assert stack.peer.submissions == 1  # only pending work; never replay running or unknown work
    for old in manifest["operations"]:
        if old["label"] in {"running", "outcome_unknown"}:
            value = eventually(lambda old=old: snapshot(stack, old["operation_id"], "outcome_unknown"))
            assert value["remote_task_id"] == old["remote_task_id"]
            if old["result_id"]:
                assert value["result_id"] == old["result_id"]
