# Claude Code Desktop identity contract (v0.11.0)

Supported scope is **Claude Code in the Desktop Code tab**, using the observed
native PreToolUse hook and MCP toolUseId join. Ordinary Claude Desktop chat has
no such hook contract and is unsupported. CLI/IDE, actual resume, process restart
and CLI/Desktop interoperability remain **unverified**. The operator approved
this narrower initial scope on 2026-10-14; the original full probe matrix did not
pass. See the [Desktop probe addendum](../reports/claude-code-identity-spike-2026-10-14-attempt2.md).

## Identity and permissions

Configure harness `claude`, stable instance `claude-desktop`, and identity provider
`hook:claude`. These are operator settings, never tool arguments. Changing the
instance creates a different ownership namespace: old operation IDs do not become
readable in it. Do not rename or share this instance with CLI merely to recover
operations. Retain the original instance and host conversation for reads.

The host sends `session_id` (canonical UUID), `tool_use_id`, `tool_name`,
`tool_input`, and `hook_event_name="PreToolUse"`. Tool names must begin with
`mcp__<configured-server>__`. When `mcp_server` is present it must be an object
whose `name` matches that server; the observed shape is `{name, source}`.
The optional `agent_id` and `agent_type` are shape-checked but never route work.

The hook stores tool name and HMAC of normalized arguments under the host's call
ID. MCP `_meta["claudecode/toolUseId"]` must match that exact attestation. The
provider replaces metadata with `x-hermes-turn-metadata` containing
`conversation_id=session_id`, `turn_id=call_id=tool_use_id`. Supplied
`x-hermes-turn-metadata` cannot override the hook. These call/turn values are
adapter identifiers, not claims about the host's internal turn structure.

Successful hooks and non-gateway tools print nothing and retain the normal host
permission flow. Invalid gateway hooks emit a fixed PreToolUse deny response,
never allow. Invalid provenance fails before socket I/O or opening an upload file.
MCP stdout contains protocol frames only; no prompts, raw arguments or peer errors
are logged by this integration.

## Registry, normalization and lifetime

Default directory: `~/.local/state/hermes-a2a-gateway/claude`; optional override
`HERMES_A2A_GATEWAY_CLAUDE_BINDING_DIR` must be identical in hook and MCP processes.
The directory is 0700, files 0600, current-UID owned, and symlink files/directories
are rejected. `attestation.key` stays outside `bindings.sqlite3`. A `host-profile`
marker prevents interpreting an Antigravity registry as Claude or vice versa.
Never share registry paths between profiles. Existing Antigravity layout, key,
TTL, table and permanent ownership semantics are unchanged.

The Claude table adds nullable `consumed REAL` with an additive ALTER TABLE.
Bindings last **300 seconds** and are atomically consumed once. A retained call
ID cannot be renewed, reassigned, or consumed again, even for identical content.
At the TTL boundary the call fails closed. Re-issue an expired call to obtain a
new host call ID, but never replay an uncertain submit as new work. A lost submit
ACK is resolved using the already-resolved original metadata, without consuming
again or resubmitting.

Shared normalization fills optional defaults and canonicalizes numeric wait values
before HMAC. It happens before model defaults, artifact list wire conversion or
upload-file reading. Claude does not accept `request_key`. Bounds and field types
are checked; malformed/unknown tool arguments fail closed.

Quota remains 100,000 bindings and 64 MiB database size. On new attestation, rows
whose expiry or consumption is over 24 hours old may be pruned. Unexpired,
unconsumed rows are retained. This relies on host call IDs not being legitimately
re-presented as new calls. Same-UID processes are trusted; this is routing isolation,
not a sandbox against another process or agent with arbitrary local filesystem access.

## Lifecycle and results

- Independent Desktop sessions have different flows.
- Main agent and native subagents share the parent's session/flow. The parent can
  get/wait an operation submitted by a subagent; no resubmission is needed.
- Subagent submits serialize in that flow and share Helen's context. Prompts must
  be self-contained and saved operation IDs returned to the parent.
- Observed Desktop compaction and sidebar reopen retain the session ID. Native
  fork and `/clear` change it, therefore intentionally start a new flow.
- Desktop `/resume` showed an empty selector in the probe. Actual resume,
  process restart and CLI/IDE lifecycle are unverified; no recovery guarantee is
  inferred from sidebar navigation.
- Explicit inline/get/wait results only; Claude never uses Codex native queue
  delivery. Get/wait/cancel check ownership before broker access. Cancellation
  remains best effort. An uncertain submit/upload/cancel must not be blindly replayed.

No daemon/broker wire, PostgreSQL, inbox, ciphertext, namespace or peer-identity
migration is introduced. Existing daemon capability `harness_identity_version=1`
and sender context version 1 are still required.
