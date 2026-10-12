# v0.10.0 — Native Antigravity conversation binding

Antigravity2.22.0 can now use a dedicated MCP facade with native PreToolUse hooks.
The host conversation UUID binds an exact tool/request_key/arguments combination;
the model-supplied retry key is never sufficient identity. Persistent ownership,
120second attestations and quotas fail closed on absent or conflicting identity.
Codex keeps its original MCP schema and routing. Default descriptive sender fields
are Antigravity / Gemini model / a2a; explicit model labels keep the same flow.

[Antigravity installation in Vietnamese](client-antigravity.vi.md),
[technical integration and boundaries](antigravity.md),
[shared install/operations](deployment.md), [Codex setup](client-codex.vi.md).
The broker and client use the same0.10.0 wheel. No new receiver patch is required:
retain the exact compatible0.9 receiver overlay, credentials, ledgers and IDs.
Upgrade code only after quiescent backup, and keep current data when rolling back.

Actual candidate acceptance on Antigravity2.22.0 observed overlapping separate chats,
exact retry returning one operation, rejected foreign reads/cancel/key reuse,
and a real Gemini→Claude model switch preserving flow and marker recall.
Post-context app reopen remains a user acceptance check. Model labels are descriptive,
not backend attestations. This is single-user conversation isolation, not protection
against a malicious same-UID process with arbitrary command/file access. Explicit
get/wait is required; Antigravity native push delivery is not implemented.

## Previous v0.9 release

# v0.9.0 — Sender labels, harness isolation and reliability fixes

Every new gateway operation carries exactly `harness`, `model` and `connection=a2a`.
The descriptor is descriptive data, never authentication or a capability registry.
Antigravity defaults to `Gemini model`; an explicit model label overrides the
family default without changing the trusted harness, flow or Hermes context.
Default Codex IDs, legacy missing descriptors, keys and idempotency hashes survive.
Other harnesses require trusted host turn metadata and use explicit result pull.

The release also stops polling completed operations, moves serialized SQLite I/O
(including FULL durable commits) off the event loop, makes close idempotent, adds
partial indexes and read-reconciliation backoff, batches retention housekeeping,
avoids repeated task-handle transactions and quadratic artifact prefix copying,
keeps later receipts progressing after an individual rejection, probes database
liveness and exits a failed dispatcher for supervised restart. Ambiguous work is
never automatically resubmitted or declared failed merely because its handle is missing.

Download the wheel, source, both compatibility variants, utility and checksums
from this release. [Fresh installation](deployment.md),
[0.8 → 0.9 upgrade and rollback](upgrade-v0.9.md),
[review of 38 external findings](review-2026-10-12.md),
[sender contract](sender-context.md), [harness contract](multi-harness.md),
[candidate verification](testing-report-v0.9.0.md).

The default receiver patch remains pinned to Hermes `490e6b5`. A separate narrow
sender overlay targets **only the exact already-patched hashes** at `722bced`;
it is not a generic pristine-upstream patch. Both fail closed on mismatches.
No Hermes venv, provider credentials, business records or existing session IDs
are replaced by installing a gateway wheel.

Live acceptance on the pre-release candidate observed Codex native MCP labels,
Antigravity family default and explicit Claude label with same-context synthetic
recall, and isolated Claude/Gemini contexts/results. The non-Codex requests used a
controlled host adapter, not the native applications. A model label override does
not itself switch the caller's actual model. See the dated deployment evidence for
final released-asset checks; historical passes alone do not prove final installation.
