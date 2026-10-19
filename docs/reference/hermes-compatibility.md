# Hermes compatibility for long conversations

Gateway 0.9 ships a narrow, optional-to-install but required-for-long-conversations
patch for Hermes commit `490e6b5966de330285905f52ebaee23c842dc3ea`.
Installing the gateway wheel alone does not change Hermes's conversation policy.
The patch is an integration maintained by this repository, not an upstream Hermes
release. Do not apply it to an unverified Hermes version.

The authenticated broker can select a five-accepted-submissions/60-second sliding
window per peer, target agent and context. Other peers retain the legacy total-turn
guard; the existing global request limiter and tool approval rules remain active.
No prompt or model-supplied metadata can select the new policy. Contexts and session
identity remain unchanged; the guard is not a general detector of agent call loops.

## Release assets and upgrade safety

Alongside the wheel and source archive, download `hermes-a2a-compat.patch`,
`hermes-a2a-compat.json`, `hermes_patch.py` and `SHA256SUMS` from the same release.
Verify the downloaded assets against `SHA256SUMS` before execution. The JSON manifest pins
the upstream commit and the original/patched file hashes. The installer must
refuse unknown source, conflicting edits and partial application; an already
matching installation is reported without applying it twice.

Before applying: stop new gateway submissions, drain active work, and preserve
consistent private backups of both ledgers, credentials/configuration and the
affected Hermes files. Do not stop native Hermes while unrelated jobs are active.
Run the downloaded utility with the actual installed Hermes checkout path:

```bash
python3 hermes_patch.py check --root "$HERMES_CHECKOUT"
python3 hermes_patch.py apply --root "$HERMES_CHECKOUT"
# Rollback, only after stopping affected work and verifying the same checkout:
# python3 hermes_patch.py revert --root "$HERMES_CHECKOUT"
```

Keep the patch, JSON manifest and utility together. `HERMES_CHECKOUT` is an
operator-resolved path, not a model-supplied target. Apply only after check succeeds.
Restore services in server-first order and
verify `client-doctor` reports the selected credential's active peer policy.

## Credential selection

Set server-only `A2A_GATEWAY_TOKEN` to a nonempty private credential and use the
same value as the broker's `HERMES_A2A_TOKEN`, through protected environment
injection. The selector is checked in constant time and only on loopback requests.
Existing Hermes authentication and trust checks still apply. If Hermes already
requires a bearer credential, reuse that authorized broker credential.

On an existing localhost-only deployment without tokens, provision a dedicated
secret for the selector and broker; keep the underlying localhost-only policy
unchanged. Local callers without that secret retain the legacy policy; they do not
receive sliding-window privileges. This does not enable unauthenticated remote
access. Keep existing peer/context/session identities unchanged. Never send the
selector in prompts or MCP arguments.

The patched Agent Card advertises support. The authenticated
`/gateway-capabilities` endpoint reports whether the supplied credential actually
selects it; the broker exposes a sanitized view through `/v1/peer-policy` and the
client doctor. An unavailable or older peer is reported as unknown/legacy, not
as verified long-conversation support.

## Errors and rollback

Structured rejection diagnostics use the versioned metadata key
`https://github.com/phamviet86/hermes-a2a-gateway/extensions/diagnostics/v1`.
The broker validates an allowlist and persists details encrypted under its normal
result retention. Get/wait and event replay use the same stored snapshot. Raw
peer text is not persisted in plaintext error columns or treated as instructions.
Hermes's own task store is memory-resident; broker evidence and historical
conversations are separate from that receiver task-cache lifetime.

If acceptance fails, quiesce affected writers, revert only the verified patch and
the selected configuration delta, and reinstall the previous wheel. Preserve new
ledger records; do not overwrite a live database with its pre-upgrade backup.
Keep backups private and record exact versions and checksums. A future Hermes
upgrade requires a newly verified patch or equivalent upstream implementation.

Local client snapshots keep the existing SQLite result model: restrictive file permissions and retention, not new at-rest snapshot encryption. Broker diagnostic details are encrypted; local snapshots contain only the bounded allowlisted fields, never a newly copied raw peer rejection message.

## Sender overlay on the tested newer receiver

The separate `hermes-a2a-sender-722bced.json/.patch` assets apply only to the exact
already-patched baseline at Hermes `722bcedb382ef632aeb262b80bcfbff5a902494b`.
They preserve the existing policy and unrelated modifications. See
[ordered upgrade and rollback](../upgrades/upgrade-v0.9.md). The default patch still targets
`490e6b5`; neither variant permits a force apply or arbitrary revision.

## Timeout chain (v0.12)

| Layer | Setting / range | Outcome |
| --- | --- | --- |
| Client inline/tool wait | submit wait and wait timeout, 0–60 s | Returns current snapshot; Hermes keeps running. |
| Broker stream | `HERMES_A2A_GATEWAY_BROKER_PEER_TIMEOUT_SECONDS`, default 300, max 3600 s | Loss of a definitive terminal event becomes `outcome_unknown`; reconcile only the saved handle. |
| Hermes receiver reply | `A2A_REPLY_TIMEOUT`, default 300 s | Receiver can return failed with `[agent did not reply in time]` or `[profile did not reply in time]`; execution may continue. |
| Hermes per-agent execution | `timeout` in A2A agent configuration (falls back to reply timeout) | Limits that agent subprocess; an ordinary failed task does not prove absence of earlier effects. |
| Hermes orphan sweep | `_orphan_timeout()`, reply timeout clamped to 300–86400 s | Marks orphaned receiver tasks failed; distinct from the stream budget and client wait. |

Keep draining the initial stream through its terminal event; disconnecting early
can stop Hermes. Set `HERMES_A2A_GATEWAY_BROKER_EXPECTED_PEER_REPLY_SECONDS`
to the operator's configured reply budget. The broker warns at startup and in
`/healthz.timeout_warnings` if its stream budget is less than that budget + 30 s.
It never reads Hermes configuration files.

Structured diagnostics reason `peer_reply_timeout` takes precedence over text.
The current pinned receiver does not emit that reason. Exact sentinel fallback
requires explicit operator attestation through
`HERMES_A2A_GATEWAY_BROKER_PEER_COMPAT_COMMIT=490e6b5966de330285905f52ebaee23c842dc3ea`
(the exact upstream commit in the shipped compat manifest). Unverified receiver
versions keep ordinary failure behavior. Do not infer the installed receiver's
commit from the gateway wheel version. No vendored receiver is changed.

`peer_reply_timeout` means: Hermes stopped waiting; the agent may still be
running; do not resubmit automatically. Check with the server owner before new
work, using existing operation/remote task evidence.
