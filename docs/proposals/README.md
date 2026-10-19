# Proposals

This file is the single source of truth for proposal status. A proposal describes
intended work; it is not current behavior or installation guidance.

## Status

| Proposal | Status | Target | Decisions | Next step |
| --- | --- | --- | --- | --- |
| [unified-mcp-identity.md](unified-mcp-identity.md) | `implemented` | v0.11.0 | D1 share; D2 Desktop observed, resume unverified; D3 claude-desktop; D4 300 s; D5 no | Shipped v0.11.0 at 206b0f8; installed on both hosts. Final refreshed native UI checks pending; see [release evidence](../reports/release-v0.11.0-2026-10-14.md). Original full matrix incomplete |

## Lifecycle

| Status | Meaning | Who changes it |
| --- | --- | --- |
| `draft` | Under discussion; do not implement | Author |
| `approved` | Direction accepted; **implement only when the operator explicitly authorizes it in the current task** | Operator |
| `in-progress` | An authorized implementation is underway; note branch/PR in "Next step" | Implementing agent |
| `implemented` | Shipped in the named release; normative content moved to `reference/`/`guides/` | Implementing agent at release |
| `rejected` / `superseded` | Kept for the record; do not implement | Operator |

## Rules for agents

1. An agent may read any proposal, but must not start implementing one unless the
   operator explicitly asks for that proposal (or a named phase of it) in the
   current task. `approved` alone is not authorization.
2. Implement phases in order and stop at each gate the proposal defines (for
   example a live spike that must succeed before later phases).
3. Open decisions marked undecided must be resolved with the operator; record the
   answer and date in the proposal's decision table.
4. Update the status row above when work starts, pauses or ships. When implemented,
   move normative content into `../reference/` and `../guides/`, add a dated report
   to `../reports/`, and mark the proposal `implemented` with the release version.
5. [AGENTS.md](../../AGENTS.md) invariants override any proposal text. If they
   conflict, stop and ask the operator.

[Structured reply timeout](structured-reply-timeout.md): proposed; no receiver patch authorized or shipped.
