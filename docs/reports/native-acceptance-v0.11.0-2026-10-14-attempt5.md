# Installed v0.11.0 native acceptance — 2026-10-14, attempt 5

Request A2A-20261014-005. **All three installed-release native submit/get gates
now pass** for Codex, Claude Code Desktop and Antigravity. This addendum closes
the Codex loaded-facade gate left open in
[attempt 4](native-acceptance-v0.11.0-2026-10-14-attempt4.md). Earlier evidence
is unchanged; Claude and Antigravity tests were not repeated.

## Fresh Codex facade provenance

The operator reported completing the requested restart. Independent process
inspection then established the following (local times are UTC+7):

- Current native Codex backend PID 7786 started at 19:02:02, from the installed
  desktop app's bundled `codex` executable.
- Its gateway MCP children observed before the test were PIDs 7874 (19:02:11),
  8050 (19:02:58), 8101 and 8152 (19:03:12), 8223 (19:03:14), and subsequently
  8636 (19:04:07). Every candidate used the installed gateway venv Python with
  the owned `run.py client-mcp` launcher. The old Codex backend/facade group
  from attempt 4 was absent.
- The launcher imports `hermes_a2a_gateway.cli.main`, invokes it and does not
  manipulate `sys.path`. No launcher, configuration or environment was changed.
- The downloaded release wheel SHA256 was reverified as
  `1853b6c12c959d91b80c8a8b1a932533ec0bf893feafb29e7610cf09d15ce00a`.
  All 22 installed package Python modules matched its bytes. Release source
  remains `206b0f8d0a9e7e2c7977a7e3630d7bfabffe8260`.
- Every candidate Codex facade started after the installed facade timestamp
  2026-10-14 08:42:53 UTC (15:42:53 local). The only older gateway MCP processes
  in the full filtered inventory were the separately parented Claude candidate
  sessions; they were not Codex backend children.

This is bounded process-set provenance: all possible gateway children of the
current native Codex backend are freshly started from the verified installation.
It does not identify which individual child PID served each call, nor claim a
memory dump or runtime code attestation. Unlike attempt 4, there is no old-code
Codex candidate remaining in that backend. Successful native calls below verify
the serving connection, rather than relying only on the operator statement,
package checks or daemon health. No Codex UI automation was attempted.

## Same-owner reconciliation and new native execution

First, native `gateway_get` in this owner chat read saved operation
`788c88f6-315d-41ec-9368-1c0fd2f5e2b9` and returned the original completed
`ACK-A2A-005-CODEX-A4`, result `20ed11c0-c0b2-4fbb-acba-bf908ccab046`.
It was not resubmitted.

Then one new harmless request, marker
`A2A-20261014-005-CODEX-RELOADED-A5`, was submitted with wait_seconds=30.
A subsequent native get of its saved operation returned the identical completed
result. Actual structured tool results were inspected.

| Field | Value |
| --- | --- |
| Operation | `ccf54f29-0ff8-471e-8878-770ee761bbcb` |
| Flow | `2dd78584-6a02-4ba9-97a6-4317da8d6603` |
| Result | `54fac37f-864a-4364-94b1-aad21a8c7741` |
| Remote task | `task-212eea52eab24771` |
| Created | `2026-10-14T12:04:22.015809Z` |
| Completed | `2026-10-14T12:04:29.677720Z` |
| State / submission / delivery | `completed` / `accepted` / `inline_returned` |
| Text | `ACK-A2A-005-CODEX-A5` |
| Error / cancel state | null / null |
| Snapshot conflict / result expired | false / false |
| Artifacts | none |

## Combined acceptance and limits

- Codex: fresh installed facade provenance plus native submit/get passes here.
- Claude Code Desktop: attempt-4 operation
  `ed183b53-553a-4a10-888e-2f2026c667fd`, result
  `0f746eed-2b96-446d-9180-81a2f70176c4`, remains accepted.
- Antigravity: attempt-4 operation
  `f9b0230b-1179-4ec9-a7de-edb0c64ee107`, result
  `3180306e-6e8d-4228-a46b-c14d7f3e1942`, remains accepted.

There is no remaining blocker for these three scoped installed-release gates.
This does not expand the supported scope: Claude CLI/IDE, actual Claude resume
and restart/interoperability, real sleep/wake, and native queue consumption remain
unverified. Inline tool return and explicit get are not evidence of queue
consumption. No release rebuild, redeployment, service mutation, additional
Claude/Antigravity call or full-suite rerun was needed. Documentation-only
bookkeeping was checked with `git diff --check`.
