# Claude Code identity spike — 2026-10-14

Request: A2A-20261014-005, attempt 1. Outcome: **blocked before model execution**.

The locally installed Claude Desktop-bundled Claude Code executable reports
`2.1.295 (Claude Code)`. It is not present on the shell PATH. A new private scratch
project outside the repository contains a stdio probe server and PreToolUse hook.
The probe has no gateway imports, sockets, broker or Hermes transport. Its only
persistent events are allowlisted identity fields, key names, timestamps and
SHA-256 argument digests; no argument values are logged. Event files use 0600.

The attempted command used `--strict-mcp-config` with only the scratch probe,
`--setting-sources local`, `--tools ''`, `--permission-mode default`, and a harmless
print-mode request to call the probe once, omitting its optional numeric argument.
It returned exit 1: `Not logged in · Please run /login`.
No permission bypass, token extraction or authentication changes were attempted.
No probe events were produced. No gateway, broker or Hermes request was issued.
No user-scope MCP registration was added. Scratch hook/MCP configuration was
removed after the blocked attempt; no existing application settings were edited.

| Check | Evidence |
| --- | --- |
| Host version | Executed `--version`: 2.1.295 |
| toolUseId hook/MCP equality | Unrun, zero calls |
| Argument/default normalization | Unrun |
| Three-minute permission delay / D4 measured delay | Unrun |
| Concurrent sessions / subagents / D1 observation | Unrun |
| Resume / fork / clear / compaction / D2 | Unrun |
| Desktop Code / CLI shared store / D3 | Unrun |

Phase 0 does not pass. Phase 2 must not start on this evidence. D1 (shared parent
flow), D4 (300 seconds, single-use), and D5 (excluded) remain operator decisions;
D2/D3 remain unresolved observations. Phase 1 is independent behavior-preserving
work and may proceed. Resume the probe after the operator authenticates this
Claude Code host through its normal login flow. Desktop ordinary chat is not a
substitute for Code hook evidence. Static binary observations are not live proof.
