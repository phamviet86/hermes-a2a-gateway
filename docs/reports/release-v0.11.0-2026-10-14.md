# v0.11.0 release and deployment evidence — 2026-10-14

Request A2A-20261014-005, attempt 3. Implementation is shipped for the authorized
Desktop-first scope. **Final native UI acceptance is incomplete**, as detailed
below. This report adds to, and does not rewrite, the immutable
[candidate evidence](testing-report-v0.11.0.md).

## Release provenance

- [PR 13](https://github.com/phamviet86/hermes-a2a-gateway/pull/13) merged.
- Exact release source: `206b0f8d0a9e7e2c7977a7e3630d7bfabffe8260`.
- [Main/push CI 38536522490](https://github.com/phamviet86/hermes-a2a-gateway/actions/runs/38536522490): success, including PostgreSQL and macOS/Linux jobs.
- [Publisher 38536805103](https://github.com/phamviet86/hermes-a2a-gateway/actions/runs/38536805103): success from that same source.
- [v0.11.0 release](https://github.com/phamviet86/hermes-a2a-gateway/releases/tag/v0.11.0): eight immutable assets; annotated tag resolved to the source above.
- Wheel SHA256: `1853b6c12c959d91b80c8a8b1a932533ec0bf893feafb29e7610cf09d15ce00a`.

The local source suite passed 356 tests with one opt-in skip and 84.36% coverage.
The exact release commit additionally passed CI. Earlier candidate build artifacts
were not published or used for the installed release.

## Installed artifacts

Both hosts independently downloaded the published assets and verified GitHub
asset digests and SHA256SUMS. The original independent Python 3.11 gateway venvs
were upgraded from v0.10.0 to v0.11.0; 22 installed Python modules matched the
wheel, and pip check passed. Protected backups and code-only rollback scripts
were retained outside the repository. No credentials or backup contents are
included in this report.

Server: only the owned broker was stopped/restarted after its ledger was idle.
A consistent PostgreSQL backup and prior venv/configuration were saved. Database
metadata before/after was exactly equal, prior operation/result/receipt identities
were retained, and the schema was unchanged. This is metadata evidence, not a
plaintext content audit. One dispatcher lock was present after restart; readiness
and device-authenticated peer-policy requests returned 200. Dependencies were
unchanged. Hermes receiver source/PID and proxy PID were unchanged.

Client: only the owned LaunchAgent was stopped; the SQLite writer lock was acquired
before consistent backup and package replacement. All 278 pre-upgrade operation
identity/digest records, 33 flow mappings and cursor 1108 were preserved. The
post-upgrade doctor reported ok, daemon ok and no transport error. Current stores,
configuration, keys and post-upgrade work are retained by the code-only rollback.

## Native acceptance and remaining limits

Codex: an actual native MCP submit on the upgraded daemon/broker completed with
the exact harmless acknowledgement. A subsequent get returned the same operation,
result and flow. No model-generated identity or submit replay was used. The
pre-existing Codex MCP connection was not forcibly restarted, so this does not
prove that its already loaded facade process re-imported the newly installed code.
Offline schema/behavior snapshots cover the shared facade refactor.

Claude: the source-candidate Desktop tests in the earlier report passed real
submit/wait/get, two-session isolation and shared parent/subagent read ownership.
The test project's commands were then pointed at the installed release for a
fresh-session check. UI state stopped updating reliably before a new released-wheel
call could be observed, so **installed-wheel native Claude acceptance is not claimed**.
Only temporary project MCP/hook registrations were removed afterward; private
registry and configuration backups were retained. No global Claude registration
or permission policy was changed.

Antigravity: the existing MCP/hook configuration still targets the original venv
and supported legacy module aliases. One harmless native acceptance request was
sent. The window title changed, but accessibility content and screenshots remained
stale; no operation ID, approval card or gateway result could be observed. Its
gateway execution outcome is **unverified**. The request was not sent again.
A quit warning was canceled to avoid interrupting unknown background work; no
forced host restart or permission bypass was performed. A read-only browser UI
fallback was blocked by the browser and was not bypassed.

To close these gates, restore responsive native UI, inspect the existing
Antigravity acceptance chat and any saved operation before further action, then
read its exact operation rather than resubmitting. Verify a fresh installed-wheel
Claude session and, if needed, a safely refreshed Codex MCP connection. Do not
claim completion from package equality, health or queue acknowledgement alone.

CLI/IDE, actual Claude resume, process restart and CLI/Desktop interoperability
remain outside the verified initial scope. No native queue/wake acceptance,
artifact upload, live cancellation or network failure injection is claimed here.
