# Installed v0.11.0 native acceptance — 2026-10-14, attempt 4

Request A2A-20261014-005. Claude Code Desktop and Antigravity pass the
installed-release, newly loaded facade gate. Codex native submit/get passes,
but its serving facade process has not been positively correlated with the
new installation. Overall three-host acceptance remains incomplete.

This adds to [release/deployment evidence](release-v0.11.0-2026-10-14.md);
no prior report, release asset, installation or database was replaced.

## Provenance and process evidence

Release source: `206b0f8d0a9e7e2c7977a7e3630d7bfabffe8260`.
Downloaded wheel SHA256:
`1853b6c12c959d91b80c8a8b1a932533ec0bf893feafb29e7610cf09d15ce00a`.
The checksum and all 22 installed Python modules were rechecked against that
wheel during this attempt. Installed facade modification time was
2026-10-14 08:42:53 UTC. All process times below are Asia/Ho_Chi_Minh (UTC+7).

- Antigravity: Customizations → Installed → MCP Servers →
  hermes-a2a-gateway → Restart replaced PID 97426 (15:35:36) with PID 5111
  (18:16:20). Command uses the installed venv Python and
  `-m hermes_a2a_gateway.antigravity_mcp`. Only this MCP server was restarted.
- Claude: a fresh Desktop Code session in the existing isolated test project
  loaded PID 5216 (18:17:11), using the installed venv executable
  `hermes-a2a-gateway client-mcp`. Project-only MCP and PreToolUse commands
  both referenced the installed venv, with `claude` / `claude-desktop` /
  `hook:claude`. Manual mode and individual Allow once approvals were retained.
- Codex: several old facade processes and a newer process coexist. A bounded
  read-only socket observation did not establish which serves this chat.
  No process was killed, and the newer process was not assumed to be ours.

## Native results

Each new test was submitted once with wait_seconds=30, followed by native
`gateway_get` of its saved operation. Results were completed, accepted,
inline_returned, with no error or artifacts. Actual get tool JSON was inspected,
not only the host model's summary.

| Host | Operation | Flow | Result | Acknowledgement |
| --- | --- | --- | --- | --- |
| Antigravity | `f9b0230b-1179-4ec9-a7de-edb0c64ee107` | `807f50e4-9da1-4daa-803a-fc35aaef2552` | `3180306e-6e8d-4228-a46b-c14d7f3e1942` | `ACK-A2A-005-AG-A4` |
| Claude Desktop | `ed183b53-553a-4a10-888e-2f2026c667fd` | `9e523100-834b-434b-8105-9d65bac7a7d3` | `0f746eed-2b96-446d-9180-81a2f70176c4` | `ACK-A2A-005-CLAUDE-A4` |
| Codex | `788c88f6-315d-41ec-9368-1c0fd2f5e2b9` | `2dd78584-6a02-4ba9-97a6-4317da8d6603` | `20ed11c0-c0b2-4fbb-acba-bf908ccab046` | `ACK-A2A-005-CODEX-A4` |

Antigravity remote task `task-1598e381ccec4538`, created 11:16:50.970589Z,
completed 11:16:53.995321Z. Native conversation remained
`a7664432-aa97-4069-b303-2b89261c120e`.
Submit request key `9a6d36ef-ffb5-4b53-9110-3882f0ad4362`; get request key
`61f6c0d4-1a93-4a11-a83d-eb8c89cf1299`.

Claude remote task `task-3fec653b9dfe4100`, created 11:17:37.522924Z,
completed 11:17:45.160317Z. Desktop UI session
`local_dcd136b6-8abd-40cf-836e-c06e51374519` (UI ID, not a claim about hook session ID).

Codex remote task `task-f914a177aa444042`, created 11:18:52.055301Z,
completed 11:18:56.551600Z. This is valid native execution evidence but does
not independently prove a newly loaded facade.

## Prior Antigravity work reconciled first

Before any new submission, the original native tool output for marker
`A2A-20261014-005-ANTIGRAVITY-v011` was opened. Operation
`0f99a2d6-1fdf-4f95-8fb7-4a5d501eaece` was completed with
`ACK-A2A-005-AG`, result `b5db11dd-a3b4-4dde-89af-6400ae810c4b`,
remote task `task-cd082d79dd2a4860`. It was not resent. After MCP restart,
the same native chat read that exact operation before submitting the distinct
attempt-4 marker. Thus the earlier unknown outcome is resolved.

## Remaining human action and scope

Computer Use rejected access to `com.openai.codex` with:
“Computer Use is not allowed to use the app 'com.openai.codex' for safety reasons.”
No alternate UI automation or permission weakening was attempted.

The central intake should ask the operator to open Codex Settings → MCP servers,
select the existing hermes-a2a-gateway entry and use Restart, leaving its command,
environment and permissions unchanged. The desktop Restart action is described
in [official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
but this installed app's exact control could not be visually inspected. If the
control is absent, report that fact rather than deleting/recreating the server.
This is not a request to restart the whole app or log in again.

Expected observable: MCP reconnect completes and a new owned facade process
starts after the installed release. Then continue the same worker chat and
read saved operation `788c88f6-315d-41ec-9368-1c0fd2f5e2b9`; only after provenance
is established, perform one distinctly marked new submit/get if needed for the
post-reload acceptance. No gateway tool permission card is currently pending.

The temporary Claude project configs were removed after completion; candidate
backups and test history remain. The original visible Claude chat was restored.
CLI/IDE, actual Claude resume/restart/interoperability and native queue consumption
remain outside the verified scope. No rebuild, redeployment or full-suite rerun
was necessary for this evidence-only attempt.
