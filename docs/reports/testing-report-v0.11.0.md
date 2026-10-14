# v0.11.0 candidate verification — 2026-10-14

Request A2A-20261014-005, attempt 3. This records the source candidate before
publication and installed-release verification. It does not attest a release tag,
CI run or deployment. Host-specific receipts remain in private worker evidence.

## Scope decision

The operator accepted the eight Desktop probe joins in the
[attempt 2 report](claude-code-identity-spike-2026-10-14-attempt2.md) as the Phase 2
gate for **Claude Code Desktop first**, with dedicated instance `claude-desktop`.
The original complete Phase 0 matrix did not pass. CLI/IDE, actual resume, process
restart and CLI/Desktop interoperability remain unverified. D1 shares the parent
flow, D4 uses 300-second single-use attestations, and D5 is excluded.

## Offline implementation and package checks

CPython 3.11.16, isolated PostgreSQL 16.15 over a Unix socket, no production stores.
Final full suite: **356 passed, 1 skipped, 84.36% coverage** (65% gate unchanged).
The skip is the opt-in macOS LaunchAgent containment test. An earlier invocation
used the wrong test socket and failed setup; the corrected complete run passed.
The isolated database server was stopped after the run.

Compileall, Ruff lint/format, mypy (22 modules), and the supported local Codex
app-server schema check passed. Build, twine, distribution safety, clean-wheel
installation, pinned compatibility staging and checksum verification passed.
These are local artifacts, not immutable GitHub release assets.

Existing tests were preserved. Additive tests cover unchanged complete Codex and
Antigravity schema/instruction snapshots, the old Antigravity registry schema and
key, alias entrypoints, provider configuration, hook input/storage failures,
normalization, expiry/replay, atomic concurrent ownership/consumption, pruning,
forged metadata, provenance before file access, exact lost-ACK recovery, and
session/harness/subagent ownership rejection before broker access.

## Live Claude Desktop gateway acceptance

Claude Code 2.1.295 in authenticated Desktop, project-local configuration in a
throwaway workspace, Manual permission mode, Allow once for each gateway call.
The candidate MCP executable used the existing v0.10.0 daemon/broker; no runtime
upgrade, second daemon, credential extraction or permission bypass occurred.
This was real gateway/Hermes execution, separate from the identity-only probe.

Two native sessions submitted the same harmless acknowledgement prompt once each
with wait_seconds=0. Each saved its operation and used wait(timeout=30) then get.
Both reached completed and returned the expected acknowledgement; operation IDs,
result IDs and flow IDs were distinct. Initial pending/outcome_unknown was
reconciled by the saved operation, never by another submit.

Session B attempted get of session A's operation and received
`not_found_or_missing_argument`; the original error JSON was inspected in the
Desktop tool details. Own-operation terminal JSON was also inspected directly.
A native subagent of B read B's operation successfully, followed by a parent read
of the same unchanged result. The subagent panel showed discovery plus one get.
Private hook registry readback showed separate session identities and consumed
bindings. Parent/subagent shared the same recorded conversation identity.

This establishes the tested explicit-pull flow, cross-session get rejection and
shared parent/subagent read ownership. Offline tests additionally cover foreign
wait/cancel and a subagent-originated submit read by its parent. No live cancellation,
artifact upload, network-disconnect injection, actual resume or process restart
is claimed. The probe's fork/clear/compact/sidebar observations remain bounded
probe evidence. Claude has no native queue/push delivery.

## Remaining release acceptance

Exact-commit CI, publication, downloaded artifact installation/provenance on both
hosts, and final native Codex/Antigravity regression checks are separate gates.
They are not passed by this candidate report. Do not infer native Desktop
consumption from queue ACK, package installation or a transport health result.
