# v0.9 candidate verification — 2026-10-12

This report separates source tests, installed pre-release observations and final
release installation. No live task runs in CI. Final public release/CI identity
and installed downloaded-asset receipts are reported by the deployment owner;
this pre-publication document does not assert those later steps already happened.

## Local source and package gates

- CPython3.11, real isolated PostgreSQL16.15: **275 passed, 1 skipped**, coverage
  **83.45%** against the65% full gate. The skip is the opt-in disposable macOS
  LaunchAgent containment test, not missing PostgreSQL coverage.
- Compile, Ruff lint/format, mypy production modules and supported local Codex
  App Server schema: PASS.
- Wheel/sdist build, twine metadata, forbidden-content inspection, clean wheel
  installation/MCP discovery/missing-metadata refusal, staged compatibility assets
  and checksum write/read verification: PASS.
- Additional regressions cover actual PostgreSQL backend termination, supervised
  failure notification,503 readiness/admission, exact-handle recovery after restart,
  no replay of ambiguous sends, active-only client recovery, receipts progressing
  around individual rejection, idempotent FD close, responsive health during slow
  FULL SQLite I/O,200 binary chunks with one accumulated encode, strict card port,
  CA startup, empty SSE cursor and uppercase checksum.
- Existing real verified-TLS/SNI positive and negative tests, independent-flow
  concurrency, encrypted persistence, legacy migration, cancellation/ACK loss,
  SSE replay/gaps, retention and pinned receiver tests remain in the full suite.

See [38-item disposition](review-2026-10-12.md) for calibrated severity, references
and limitations. Earlier portable coverage64.79% with PostgreSQL skipped describes
a different test environment and does not replace the full gate.

## Installed pre-release candidate observations

The initial deployment used an unpublished0.8.0 wheel containing sender/harness
changes; it is a candidate, not the final0.9 release artifact. Client metadata
comparison retained229 existing operation/flow/thread/turn/call/delivery records.
Native executor reports quiescent server snapshots, unchanged baseline IDs/cursors
and existing sessions, additive nullable sender column, independent broker venv,
and active canonical broker/receiver/proxy after the narrow receiver delta.
The server is Hermes `722bcedb382ef632aeb262b80bcfbff5a902494b`, newer than the
original compatibility pin. Its sender-only overlay is published separately with
strict before/after hashes; unrelated source changes were retained. Offline
checks executed the staged actual receiver with model execution replaced.

Live harmless acceptance retrieved exact operation/results and receiver JSONL:

| Caller evidence | Received descriptor | Continuity/isolation |
|---|---|---|
| Native Codex MCP | Codex / Codex model / a2a | Existing conversation/flow retained |
| Controlled Antigravity adapter, first turn | Antigravity / Gemini model / a2a | Synthetic marker established |
| Same adapter/conversation, explicit override | Antigravity / Claude model / a2a | Same flow/context, marker recalled without repeating it |
| Controlled Claude adapter, same external conversation ID | Claude / Claude model / a2a | Distinct flow/context, marker null |
| Controlled Gemini adapter, same external conversation ID | Gemini / Gemini model / a2a | Distinct flow/context, marker null |

All corresponding user entries contained exactly three descriptor keys. Wrong-
harness get/wait/cancel/exact-call resolution returned404 before broker mutation.
Default/override used the same Antigravity flow `656b5d33-8d1e-4956-9893-ff456db4d1ae`
and context `d79ce308-810e-5ee0-9da9-a2f08e7dfe86`.

The non-Codex callers were controlled trusted-host fixtures communicating through
the real deployed client/broker/Helen, **not native Antigravity/Claude/Gemini
application integrations**. Model override is a descriptive label; no claim that
this fixture changed the actual caller or Helen provider model. Only Codex/default
has native queue support; the observed installed CLI/schema used explicit pull.
MCP facade replacement requires caller reload to expose the new model parameter.

## Deviations and recovery

On Mac, the initial pip command ran before the daemon had released its writer lock
and before the runtime snapshot completed. No new daemon was started then. The old
runtime was reconstructed from its preserved original0.8.0 release wheel plus the
exact saved installed `client_mcp.py` modification, then backed up while quiescent.
That is a **reconstructed rollback runtime**, not an untouched prechange venv
snapshot. Consistent original state/config backups were taken before the new daemon
started/migrated. Credentials were copied opaquely; no values or secret hashes were
logged, no keys/IDs rotated. The deployment record retains this provenance.

The first harmless A2A call arrived during native gateway startup restore. Hermes
queued it but prematurely completed its task empty; a later response was logged
without a pending waiter. Its exact original operation was retrieved; it was not
replayed. A separately identified post-readiness request returned the correct three
labels. This observed newer-Hermes startup limitation is documented in the upgrade
guide; port-open readiness is insufficient. No blanket upstream fix is claimed.

Rollback is code/owned-delta restoration with current stores retained. Whole
pre-upgrade database/session snapshots are disaster-recovery evidence, not a plan
to overwrite post-upgrade work. See [upgrade/rollback](upgrade-v0.9.md).
