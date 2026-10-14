# Claude Desktop Code identity spike addendum — 2026-10-14

Request **A2A-20261014-005 / attempt 2**. This is new evidence; it does not rewrite
or invalidate the earlier CLI authentication result, which applies only to the
standalone CLI. The human confirmed Desktop Code is authenticated.

## Setup and permission behavior

The existing scratch probe source was reused. Only its removed `.mcp.json` and
`.claude/settings.local.json` were recreated (0600), outside the repository.
The native folder chooser was resolved by double-clicking the resolved Go to
Folder result, then clicking Open. There is no remaining folder-chooser blocker.
The isolated workspace was trusted through its normal UI. Its MCP source was
reported by the hook as `project`; no user-scope registration was added.

Three disposable Desktop Code chats were used: A, B, and B's native fork. The
pre-existing repository chat was never messaged. Each probe ran in Manual mode,
with **Allow once** for each individual tool invocation. No Always allow or
permission bypass was used. The native Agent test was explicitly scoped to one
subagent and one harmless probe call. Host tool discovery also ran; the probe did
not contact the gateway, broker or Hermes. No credentials were extracted or copied.

Claude Code executable version remains **2.1.295**, observed in attempt 1. The
Desktop UI shows Code sessions and Opus 5.5; the displayed model is descriptive,
not evidence about the hook protocol version or model capabilities.

## Native observations

**Eight hooks and eight MCP calls; 8/8 toolUseId joins and 8/8 canonical argument
SHA-256 comparisons match.** No missing/duplicate call identity was observed.

- Hook keys on ordinary calls: `cwd`, `effort`, `hook_event_name`, `mcp_server`,
  `permission_mode`, `prompt_id`, `scratchpad_dir`, `session_id`, `tool_input`,
  `tool_name`, `tool_use_id`, `transcript_path`.
- MCP metadata keys: `claudecode/toolUseId`, `progressToken`. There was no session
  ID in MCP metadata. Hook session IDs were canonical UUIDs.
- **Important shape correction:** `mcp_server` is an object
  `{"name":"probe","source":"project"}`, not a server-name string. A Claude
  parser must validate its `name` when present, alongside the full tool prefix.
- Omitted optional numeric arguments, explicit integer `30`, and explicit `30.5`
  were preserved between hook and MCP. This probe does not prove coercion of every
  gateway schema type; production shared normalization still needs offline tests.
- The native general-purpose subagent supplied `agent_id` and `agent_type` and
  retained B's parent `session_id`. D1's shared-flow choice matches this observation.
- Maximum observed hook-to-call delay: **219.776 seconds**, following deliberate
  delayed approval. The identity and digest remained unchanged. This is below
  the chosen 300-second TTL; it is not a TTL-expiry implementation test.

| Desktop case | Host session ID | Hook-to-call seconds | toolUseId / hash |
| --- | --- | ---: | --- |
| A plain omitted | `fde0cb15-e986-4368-b732-eafa2a27bfee` | 16.072 | match |
| B concurrent omitted | `2157f3b5-cd4b-4886-a0d0-1b808319dfed` | 14.774 | match |
| B native subagent | `2157f3b5-cd4b-4886-a0d0-1b808319dfed` | 11.991 | match |
| A delayed explicit integer | `fde0cb15-e986-4368-b732-eafa2a27bfee` | 219.776 | match |
| B after compaction | `2157f3b5-cd4b-4886-a0d0-1b808319dfed` | 8.984 | match |
| B fork | `34118174-74b7-49b1-8834-69034b414d0d` | 9.672 | match |
| Fork after clear | `d5d40dce-a910-4cce-b4de-c17ccae921ff` | 15.917 | match |
| A sidebar reopen fractional | `fde0cb15-e986-4368-b732-eafa2a27bfee` | 10.780 | match |

D2 observations are **Desktop-specific**:

- `/compact` completed visibly (52.5k tokens saved); B retained its session ID.
- **Fork from here** created a distinct host session ID.
- `/clear` emptied the disposable fork and its next call used a new host session ID.
- Navigating away and reopening A through the sidebar retained A's ID. This is
  sidebar reopen evidence, not proof of a process restart or CLI `--resume`.
- Desktop `/resume` opened its native selector but displayed **No Claude Code
  sessions found on this computer**. It was closed without selecting anything.
  No resume invocation completed. CLI `--resume` and `--fork-session` remain unrun.

For D3, the final hook classified its host-provided `transcript_path` as being
under the default `~/.claude/projects` directory (`true`). Only this boolean was
logged; no transcript file or private path value was read or logged. This supports
the proposed common-store hypothesis but does not prove cross-host resume: the
Desktop resume selector was empty and no authenticated CLI session was exercised.
Do not silently claim CLI/Desktop interoperability or settle D3 beyond this evidence.

## Evidence preservation and cleanup

The private event file is 0600, contains only identity fields, key names, timestamps,
argument digests and the single path-category boolean. It contains no argument
values, prompt text, transcript contents or credentials. SHA-256 of all 16 event
lines: `0502c442043ca1b24b590dd2f35b62118ed3d7bc889defbf775f976ba7e36634`.
Probe source and event file remain in the scratch directory recorded in the
ignored worker context. Scratch MCP/hook configuration files were removed after
all calls completed. Already-loaded host processes were not forcibly terminated;
no application restart or unrelated session interruption was performed.

## Gate status and remaining decision

The **Desktop identity join sub-gate passes (8/8)**, and the measured Desktop
lifecycle cases above are complete. **The full Phase 0 matrix is still incomplete**:
actual resume, CLI-specific lifecycle cases and cross-host D3 equivalence remain
unverified. No claims of CLI acceptance are derived from Desktop results.

Phase 1 implementation and its prior local checks remain unchanged: 310 passed,
1 skipped, 83.51% coverage plus packaging/schema gates. Phase 2 was not started;
no CI, release, installation or gateway live acceptance was performed in this attempt.

Central follow-up: resolve whether to narrow the first supported scope to the
observed Desktop Code cases (with resume explicitly unverified), or arrange an
actual supported resume/CLI case to finish the original matrix. This is a lifecycle
and supported-scope decision, **not a request to log into Desktop**. No credential
workaround or generic standalone CLI login requirement is imposed by this result.
