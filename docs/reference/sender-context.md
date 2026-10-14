# Sender labels received by Helen

Every new client submit carries one `sender_context` object with exactly:

```json
{"harness": "Antigravity", "model": "Claude model", "connection": "a2a"}
```

These are descriptive labels, not verified model specifications, authentication,
capability claims or routing identity. `connection` describes the A2A peer method,
regardless of MCP, HTTPS or SSH transport layers. The harness label is generated
from the trusted MCP adapter identity described in [multi-harness](multi-harness.md).
The model label never changes that identity, flow, instance, context or access scope.

| Configured harness | Display harness | Default model label |
| --- | --- | --- |
| `codex` | Codex | Codex model |
| `antigravity` | Antigravity | Gemini model |
| `claude` | Claude | Claude model |
| `gemini` | Gemini | Gemini model |
| Other valid harness ID | That configured ID | `null` (unknown) |

The user-selected `gateway_submit(model="...")` label overrides the operator's
`HERMES_A2A_GATEWAY_CLIENT_MODEL` environment label, which overrides the family
fallback. Supply the tool parameter only for an explicitly user-selected model;
it is a declaration, not a claim that the gateway inspected the executing model.
For example Antigravity with `model="Claude model"` stays Antigravity and reports
Claude model. No capability reference is embedded in transport; Helen maintains
her model reference separately. No extra registry or peer binding is created.
Labels are bounded (harness 64 characters, model 256), nonblank and reject control
characters. An unknown harness remains itself and has unknown model unless supplied.

## Persistence and replay

The client snapshots the descriptor before durable admission, encrypts it with the
operation outbox, and retains an encrypted `sender_context` SQLite BLOB after ACK
clears the prompt payload. The broker validates the three-field object, includes
it in operation idempotency hashing and encrypted payload, and retains a separate
encrypted `sender_context` bytea column after dispatch payload deletion. Client
result retention and broker result expiry clear these snapshots under existing
pruning schedules. This is bounded operation metadata, not a durable model registry.

A reconnect/retry uses the saved payload; it does not recompute defaults. Reusing
one native call ID with a changed label is rejected as conflicting content. For a
model change, issue a new invocation in the same conversation: its new snapshot
shares the existing flow and deterministic peer context. No conversation fork.

Both migrations only add nullable columns. Old ciphertext, digests, IDs, flows,
cursors and receipt state remain unchanged. Old pending operations and direct legacy broker clients
may omit the descriptor; they remain unknown and are never backfilled from current
configuration. Broker HTTP serialization omits the absent optional descriptor to
preserve legacy idempotency hashes. Client legacy exact-call recovery retains its
original digest and operation; it never invents historical metadata.

## Receiving support and limits

`HermesBrokerPeer` forwards the object as A2A `message.metadata.sender_context`.
The repo-owned `compat/hermes/hermes-a2a-compat.patch`, version
`0.8.1-sender-context`, targets upstream commit
`490e6b5966de330285905f52ebaee23c842dc3ea`. Its receiver:

- Validates the same three-field shape without granting policy or changing peer IDs.
- Saves the object on the corresponding user entry in the existing context JSONL
  conversation log; old entries remain untouched.
- Places the descriptor in local `MessageEvent.metadata.sender_context`.
- Includes bounded JSON labels inside the existing untrusted inbound framing so
  Helen sees them even when profile forwarding uses `hermes chat` CLI text.

The native event metadata field exists at that pinned upstream revision in
`gateway/platforms/event.py`. Offline tests exercise event metadata with model
execution replaced; live acceptance and actual installed revision are separate
observations in the dated release report. Profile CLI forwarding receives framed labels
as text, not an additional native metadata channel. New descriptor-bearing conversation entries flush/fsync the file and directories
before model dispatch; a write/fsync failure returns a failed task without model
execution. Legacy entries keep best-effort behavior. This is no peer registry.
Offline tests cover the exact patched receiver and mocked model execution; they do
not prove deployed Helen has loaded this patch or verified the model label.

## Operator deployment steps

1. Keep stable operator-owned `CLIENT_HARNESS` and `CLIENT_HARNESS_INSTANCE` settings.
   Optionally set `HERMES_A2A_GATEWAY_CLIENT_MODEL`; leave it unset for family fallback.
2. Upgrade broker and client together before sending the new descriptor. The new
   facade requires daemon health `sender_context_version=1` before submitting,
   preventing silent loss through an old daemon (get/wait remain usable). An older
   broker rejects the added field; there is no silent metadata-stripping retry.
3. Apply the matching receiver compatibility patch only to its supported source
   commit, through `scripts/hermes_patch.py`, with Hermes stopped under the approved
   deployment procedure. Preserve source/data/key rollback separately.
4. If the previous compatibility patch is installed, this new manifest deliberately
   refuses its differing hashes. Revert using that exact previous patch/manifest,
   then check/apply the new patch; resolve any other source changes manually.
5. Restart/refresh components only within an authorized deployment, then verify a
   harmless authorized request at Helen and read back its exact conversation entry.

For0.9, use the [ordered upgrade/rollback guide](../upgrades/upgrade-v0.9.md), including the
separate strict overlay for the tested newer receiver. See [candidate verification](../reports/testing-report-v0.9.0.md)
for actual live evidence and limitations; installing a wheel alone does not prove
receiver support or native non-Codex application integration.
