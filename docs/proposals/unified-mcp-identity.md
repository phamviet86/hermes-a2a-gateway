# Proposal: unified MCP facade with pluggable host identity providers

| Field | Value |
| --- | --- |
| Status | **Implemented in v0.11.0** under the dated Desktop-first scope revision below. This file records the design; current behavior is in [Claude reference](../reference/claude-code.md) and [setup guide](../guides/client-claude.vi.md). Final native UI limits are in the [release evidence](../reports/release-v0.11.0-2026-10-14.md). |
| Target | v0.11.0 (minor, additive; no wire, schema or data migration) |
| Written | 2026-10-14, against `main` at v0.10.0 (`a304d01`) |
| Adds | Claude Code as a third trusted harness, beside Codex and Antigravity |
| Implementer | Another AI agent. Read [AGENTS.md](../../AGENTS.md) first; its invariants override this document. |

## Authorized scope revision — 2026-10-14

A2A-20261014-005, attempt 3: the operator explicitly approved **Claude Code
Desktop first**, accepting the eight observed Desktop hook/MCP identity joins
and measured lifecycle cases in the [attempt 2 addendum](../reports/claude-code-identity-spike-2026-10-14-attempt2.md)
as the Phase 2 gate for this narrowed scope. The original full Phase 0 matrix
has **not** passed. CLI/IDE, actual resume, process restart and CLI/Desktop
interoperability remain unverified and are not release acceptance claims.

D2: document Desktop compaction/sidebar reopen retaining ID, fork/clear changing
ID; actual resume remains unverified. D3: use a dedicated stable instance
`claude-desktop` (harness `claude`), without implying shared ownership with CLI.
Changing an instance starts a separate namespace and does not transfer access to
old operations. A future CLI/IDE scope requires its own evidence and explicit
operator decision; do not silently rename existing instances.

The live hook's optional `mcp_server` is an object `{name, source}`. Validate its
`name` against the configured server and validate the tool-name prefix. D1 shared
parent/subagent scope and D4 300-second single-use bindings remain unchanged.
This dated revision supersedes broader scope claims and D2/D3 recommendations
below; historical reports remain immutable.

## 1. Summary

The client core (daemon, SQLite inbox, broker, Hermes patch) is already
harness-agnostic: it isolates work by `(harness, instance, conversation)`. The only
host-specific part is **where a trusted conversation/call identity comes from**.
Today that is solved by a separate MCP facade per host (`client_mcp.py` for Codex
and generic metadata, `antigravity_mcp.py` + `antigravity_binding.py` for
Antigravity). Adding Claude the same way would create a third facade, hook and set
of docs with diverging schemas.

This proposal replaces "one facade per host" with **one facade + pluggable
identity providers**, selected by operator configuration, and a **single host-hook
module with per-host profiles**. Codex and Antigravity keep identical behavior and
data. Claude Code is then added as one small profile.

Deliverables, in order:

0. Live spike on Claude Code to confirm host facts (§8.0). **Gate for phase 2.**
1. Behavior-preserving refactor (§8.1).
2. Claude Code provider/profile (§8.2).
3. Documentation and release (§8.3).

## 2. Current state (verified in code at v0.10.0)

| Concern | Where | Behavior |
| --- | --- | --- |
| Harness/instance config | `client_mcp.harness_identity()` ([client_mcp.py:49](../../src/hermes_a2a_gateway/client_mcp.py)) | `HERMES_A2A_GATEWAY_CLIENT_HARNESS` (default `codex`), `..._HARNESS_INSTANCE` (default `default`). Operator-owned env, never a tool argument. |
| Identity validation | `NativeOrigin.from_meta()` ([native_delivery.py:57](../../src/hermes_a2a_gateway/native_delivery.py)) | `codex` → `threadId` + `x-codex-turn-metadata` + `callId` (UUID checks). Any other harness → `x-hermes-turn-metadata` with exactly `conversation_id`, `turn_id`, `call_id` (nonblank, ≤512 chars). |
| Storage key | `NativeOrigin.storage_thread_id` | `codex/default` keeps raw thread UUID; others use `harness:` + JSON `[harness, instance, conversation]`. **Must not change.** |
| Daemon protocol | `client.py` `/command`, `/healthz` | Nondefault identity uses `harness_v1/<action>` and requires `harness_identity_version == 1`; submit requires `sender_context_version == 1`. |
| Lost-ACK recovery | `client_mcp.invoke()` | On transport error after a submit was sent, calls `resolve_call` with the **same** meta/identity. |
| Antigravity | `antigravity_binding.py`, `antigravity_mcp.py` | PreToolUse hook binds model-supplied `request_key` + tool + HMAC(normalized args) → host `conversationId` (UUID) in a 0700/0600 SQLite registry; TTL 120 s, renewable for same owner/content; 100 000 rows / 64 MiB caps; rows never deleted. Facade requires `HARNESS=antigravity`, reads binding, forwards `x-hermes-turn-metadata {conversation_id, turn_id=key, call_id=key}`. Hook returns `ask` (never `allow`), `deny` on failure. |
| Sender labels | `sender_context.py` | `{harness, model, connection: "a2a"}`; `claude` → `Claude` / `Claude model` already exists. Labels never route. |
| Native push | `native_delivery.py` | Only `codex/default`. Every other namespace is explicit pull (`gateway_get`/`gateway_wait`). |

## 3. Decision and rejected alternatives

**Chosen (C): one facade, identity provider chosen by config, shared hook registry.**

Rejected:

- **A. Keep one facade per host.** Works, but every host duplicates facade, hook,
  registry and docs; tool schemas drift (Antigravity already differs by
  `request_key`).
- **B. Generic MCP where the harness/model "declares" an ID** (tool argument or
  static config). Rejected because it breaks isolation:
  - A model-supplied conversation ID can be invented, reused across chats, lost
    after context compaction, or set by prompt injection to read/cancel another
    conversation's operations. AGENTS.md forbids model-supplied execution identity.
  - A static per-process ID merges all chats served by that MCP process (Codex
    Desktop and Antigravity serve many conversations from one process).
    [multi-harness.md](../reference/multi-harness.md) already forbids
    "environment-only conversation guess".

**Not changed:** `sender_context.connection` stays `"a2a"`. It is not declared by
anyone (constant default), and removing it would change broker validation,
idempotency hashes and the Hermes receiver patch for no benefit.

## 4. Non-goals

- No change to broker, PostgreSQL schema, wire contract, Hermes patch,
  `storage_thread_id` format, IDs, cursors or ciphertext.
- No new public CLI command (still only `broker`, `client`, `client-mcp`,
  `client-doctor`). Hooks run as `python -m ...` modules.
- No native push delivery for Antigravity or Claude.
- No per-harness quotas or artifact ACLs; no multi-user security boundary.
- No support for hosts without trusted per-call identity (e.g. Claude Desktop's
  ordinary chat, which has no hooks), except the explicit, opt-in degraded mode in §6.6.

## 5. Invariants the implementation must keep

Copy these into PR review as a checklist.

1. Identity comes only from host metadata or an exact-request host hook attestation;
   never from tool arguments, result content, environment-only guesses or operation
   lookups. Missing/inconsistent provenance → reject before persistence or dispatch.
2. Default `codex/default` behavior, MCP schema and stored rows are byte-for-byte
   unchanged. Existing Antigravity registry (path, table, key file, semantics) keeps
   working without migration; existing Antigravity MCP/hook configs keep working.
3. MCP stdout carries protocol frames only; hook stdout carries only the host's
   decision JSON; diagnostics go to stderr. Never log prompts, arguments, tokens,
   meta values or raw errors.
4. Hooks never return an auto-allow decision; they preserve the host's permission
   flow and fail closed on invalid/unknown gateway requests.
5. Registry storage: directory 0700, files 0600, owner = current UID, no symlinks,
   HMAC key outside SQLite, arguments only as keyed HMAC.
6. Ambiguous submits are never replayed with a new identity. Lost-ACK recovery uses
   the exact original origin.
7. Child/native environments keep scrubbing secret prefixes (unchanged code paths).

## 6. Design

### 6.1 Configuration

New operator-owned variable, read only from the MCP process environment:

```text
HERMES_A2A_GATEWAY_CLIENT_IDENTITY = codex-meta | hermes-meta | hook:antigravity | hook:claude | single-conversation
```

Defaults preserve today's behavior exactly:

| `CLIENT_HARNESS` | `CLIENT_IDENTITY` unset → | Notes |
| --- | --- | --- |
| `codex` | `codex-meta` | Current Codex path. |
| anything else | `hermes-meta` | Current generic `x-hermes-turn-metadata` path. |

Validation (fail at startup with a clear stderr message, exit nonzero):

| Provider | Allowed harness |
| --- | --- |
| `codex-meta` | `codex` only |
| `hermes-meta` | any non-`codex` harness |
| `hook:<profile>` | harness must equal `<profile>` (e.g. `hook:claude` ⇒ `HARNESS=claude`) |
| `single-conversation` | any non-`codex` harness; requires `..._CLIENT_CONVERSATION` (see §6.6) |

### 6.2 Provider interface

New module `src/hermes_a2a_gateway/host_identity.py`:

```python
class IdentityProvider(Protocol):
    name: str
    requires_request_key: bool  # adds `request_key` to tool schemas

    def origin_meta(self, tool: str, arguments: dict[str, Any], request_meta: dict[str, Any]) -> dict[str, Any]:
        """Return the meta dict passed to the daemon (shape accepted by NativeOrigin.from_meta).
        Raise IdentityError (safe code only) when provenance is missing or inconsistent."""
```

| Provider | `origin_meta` |
| --- | --- |
| `codex-meta` | Return the host request meta unchanged (today's `request_meta(ctx)`), validated by `NativeOrigin.from_meta`. |
| `hermes-meta` | Same as above for non-Codex harness. |
| `hook:antigravity` | Today's `Bindings.origin(tool, args)` keyed by `request_key`. |
| `hook:claude` | Look up binding by `request_meta["claudecode/toolUseId"]`; verify tool + HMAC(args) + not expired + not consumed; return `{"x-hermes-turn-metadata": {"conversation_id": session_id, "turn_id": tool_use_id, "call_id": tool_use_id}}`. |
| `single-conversation` | Return fixed conversation from config with `turn_id`/`call_id` from the host call ID if present, else reject (see §6.6). |

The provider result **replaces** the forwarded meta; host-supplied
`x-hermes-turn-metadata` is never passed through for hook providers.

### 6.3 One MCP facade

Refactor `client_mcp.py` so that:

- Tool functions build `arguments`, call `provider.origin_meta(...)` (in a thread for
  SQLite work), then the existing `invoke()` logic (health negotiation,
  `harness_v1/` prefix, lost-ACK `resolve_call` with the same meta).
- Tool schemas are generated at startup. When `provider.requires_request_key` is
  true (only `hook:antigravity`), every tool gets the `request_key` parameter
  exactly as today's Antigravity facade; otherwise schemas are exactly today's
  Codex schemas. Add a test that snapshots both schemas.
- Server `instructions` text is chosen per provider. Keep the current Codex text
  unchanged; move the Antigravity text verbatim; write Claude text (§6.5).
- Upload keeps "authenticate provenance before touching the file".
- `antigravity_mcp.py` becomes a thin alias: sets/validates
  `CLIENT_IDENTITY=hook:antigravity` and runs the unified server, so
  `python -m hermes_a2a_gateway.antigravity_mcp` keeps working.

### 6.4 Shared hook registry and hook entrypoint

Generalize `antigravity_binding.py` into `host_hook.py` (registry + dispatcher) and
`host_profiles.py` (per-host parsing). Keep `antigravity_binding.py` as an alias
module whose `main()` calls the Antigravity profile.

Registry changes:

- Same file layout and checks as today (`attestation.key`, `bindings.sqlite3`).
- Directory per profile: Antigravity keeps
  `HERMES_A2A_GATEWAY_ANTIGRAVITY_BINDING_DIR` / `~/.local/state/hermes-a2a-gateway/antigravity`.
  Claude uses `HERMES_A2A_GATEWAY_CLAUDE_BINDING_DIR` /
  `~/.local/state/hermes-a2a-gateway/claude`. Never share a registry between profiles.
- Antigravity table and semantics unchanged. For profiles keyed by a host call ID
  (Claude), add an **additive** nullable `consumed REAL` column created with
  `ALTER TABLE ... ADD COLUMN` only in that profile's DB, and allow pruning (below).

Profile contract (one small class per host):

| Profile field | Antigravity | Claude Code |
| --- | --- | --- |
| Parse hook stdin | `conversationId`, `stepIdx`, `toolCall.name == "call_mcp_tool"`, `args.ServerName`, `args.ToolName`, `args.Arguments` | `session_id`, `tool_name == "mcp__<server>__<tool>"`, `tool_input`, `tool_use_id`, optional `mcp_server`, optional `agent_id` |
| Join key | model `request_key` (UUID) | host `tool_use_id` |
| Conversation validation | UUID | UUID (confirm in spike) |
| Renew same key | yes (existing) | no — a host call ID is single-use |
| Consume on facade lookup | no (existing) | yes (`consumed` set atomically) |
| TTL | 120 s (existing) | 300 s, single-use (decided D4) |
| Prune | never (existing) | rows with `expires` or `consumed` older than 24 h may be deleted: host call IDs are never legitimately re-presented, so pruning cannot reassign ownership |
| Non-gateway tool | `{"decision":"ask"}` (existing) | exit 0, **no stdout** (host keeps normal permission flow) |
| Gateway request OK | `{"decision":"ask"}` (existing) | exit 0, no stdout |
| Gateway request invalid | `{"decision":"deny", ...}` (existing) | stdout `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"<safe fixed text>"}}`, exit 0 |

Argument normalization (`normalized()` / `DEFAULTS` / `REQUIRED`) is shared; the
Claude profile does not require or accept `request_key`.

### 6.5 Claude Code profile details

Host facts observed by static inspection of the Claude Code 2.1.295 binary bundled
with Claude Desktop (must be confirmed live in §8.0):

- PreToolUse hook stdin contains `session_id`, `hook_event_name: "PreToolUse"`,
  `tool_name`, `tool_input`, `tool_use_id`, and for MCP tools `mcp_server`.
- MCP `tools/call` request `_meta` contains `"claudecode/toolUseId"` equal to the
  hook's `tool_use_id`. `_meta` does **not** contain the session ID.
- MCP tool names are `mcp__<registered-server-name>__<tool>`.

Mapping: `conversation_id = session_id`, `turn_id = call_id = tool_use_id`. Stable
adapter identifiers, not a claim about Claude's internal turn IDs.

Subagents (decided D1): a subagent call maps to its parent's `session_id`, so the
main agent and all its subagents share one flow and one Helen conversation.
`agent_id`/`agent_type` are never part of the routing key, binding key or sender
labels; the hook may validate them for shape only. Consequences to keep:

- The main agent can `gateway_get`/`gateway_wait` an operation submitted by a
  subagent (same owner scope), so a finished or interrupted subagent never forces
  a resubmit.
- Existing per-flow serialization applies: parallel subagents that submit to Helen
  are queued one after another. This is the intended invariant, not a defect;
  document it as a known limit.
- Helen's context is shared, so subagent prompts must be self-contained.

Server name: profile accepts `HERMES_A2A_GATEWAY_MCP_SERVER_NAME` (default
`hermes-a2a-gateway`) and checks both `tool_name` prefix and `mcp_server` when present.

Operator configuration (to document in a new guide, §8.3). Note the existing
Codex `launch` wrapper strips every `HERMES_A2A_GATEWAY_*` variable from its parent
environment, so Claude must invoke the venv executable directly (as Antigravity
does) or the launcher must be extended to accept the three harness variables.
Prefer direct invocation:

```bash
claude mcp add --scope user hermes-a2a-gateway \
  -e HERMES_A2A_GATEWAY_CLIENT_HARNESS=claude \
  -e HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE=claude-code \
  -e HERMES_A2A_GATEWAY_CLIENT_IDENTITY=hook:claude \
  -- /absolute/gateway-venv/bin/hermes-a2a-gateway client-mcp
```

Add `HERMES_A2A_GATEWAY_CLIENT_STATE_DIR` only when the daemon uses a non-default
state directory. Hook in `~/.claude/settings.json` (merge; preserve existing hooks):

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "mcp__hermes-a2a-gateway__.*",
      "hooks": [{
        "type": "command",
        "command": "/absolute/gateway-venv/bin/python -m hermes_a2a_gateway.host_hook --profile claude",
        "timeout": 10
      }]
    }]
  }
}
```

Claude facade instructions (draft): same rules as Codex text, minus native queue;
add "Conversation identity comes from the Claude Code host; do not pass or invent
IDs. Results are read with gateway_get/gateway_wait only. Never resubmit an
ambiguous submit; read the saved operation_id. Subagents share this session's
Helen conversation: write self-contained prompts with the needed context, do not
assume Helen knows another subagent's work, and report saved operation_ids back to
the main agent."

Scope: Claude Code CLI, the Code tab of Claude Desktop and IDE extensions, as long
as they load the user settings that contain the hook. Claude Desktop ordinary chat
(`claude_desktop_config.json`) has no hooks and is unsupported.

### 6.6 Optional degraded mode: `single-conversation`

For hosts without any trusted per-call identity. One instance = one fixed Hermes
conversation for every chat in that host. It is honest isolation **between
instances only**; chats inside the instance share context with Helen. Requires
`HERMES_A2A_GATEWAY_CLIENT_CONVERSATION` (operator-chosen stable string) and a host
call ID to recover lost ACKs; without a host call ID, submit lost-ACK recovery is
impossible and the provider must reject submit. **Implement only if the operator
asks;** it is listed so the agent does not invent an unsafe variant.

## 7. Open decisions (resolve with the operator before phase 2 merges)

| # | Question | Recommended default |
| --- | --- | --- |
| D1 | Subagents (Task/Agent tool) share the parent `session_id`. Share the parent's Hermes flow, or isolate per `agent_id`? | **Decided 2026-10-14: share** (one Claude session = one Helen conversation; see §6.5). Rationale: the main agent must be able to read subagent operations instead of resubmitting; `agent_id` is ephemeral and would create abandoned flows. Per-agent isolation is out of scope; a future opt-in setting (e.g. `CLAUDE_SUBAGENT_SCOPE=isolated`) requires a new proposal. The spike still records whether subagent calls carry the parent `session_id`. |
| D2 | `--resume`, `--fork-session`, `/clear`, compaction: does `session_id` change? | Whatever the host does is authoritative: same ID → same flow; new ID → new flow. Document observed behavior. |
| D3 | Instance name for CLI vs Desktop Code tab | One instance `claude-code` if both share `~/.claude` session store; otherwise separate names. Changing a name loses access to prior operations. |
| D4 | Attestation TTL | **Decided 2026-10-14: 300 s (5 min), single-use.** The spike still records hook→call delay; an approval slower than 5 min fails closed and the user re-issues the call. |
| D5 | Implement `single-conversation` (§6.6)? | No, unless requested. |

## 8. Work plan

### 8.0 Phase 0 — live spike on Claude Code (operator-authorized, manual)

Goal: replace §6.5 assumptions with observed facts. No gateway daemon, broker or
Hermes involved; nothing is sent off the machine.

1. Write a throwaway stdio MCP server (outside the repo, e.g. the agent scratchpad)
   exposing one tool `probe(text: str)`. For each call, append to a 0600 file:
   key names of `_meta`, the value of `_meta["claudecode/toolUseId"]`, SHA-256 of the
   canonical JSON of arguments. Never write argument values.
2. Write a throwaway PreToolUse hook (matcher `mcp__probe__.*`) that appends: key
   names of stdin, `session_id`, `tool_use_id`, `tool_name`, `mcp_server`,
   `agent_id`/`agent_type` if present, SHA-256 of canonical `tool_input`, timestamp.
   It prints nothing (normal permission flow).
3. Register both with `--scope local` in a scratch project (never user scope during
   the spike), and record the Claude Code version.
4. Exercise: plain call; call with permission prompt waiting ~3 min; two concurrent
   sessions; subagent call; `--resume`; `--fork-session` (if available); `/clear`;
   after compaction; Desktop Code tab (if used by the operator); calls with omitted
   optional arguments.
5. Record in `docs/reports/claude-code-identity-spike-YYYY-MM-DD.md`: confirmed
   fields, whether hook `tool_use_id` == MCP `_meta` toolUseId, whether hashes match
   (if not, what normalization differs), session ID behavior for D1/D2/D3, max
   observed hook→call delay for D4. Then remove the probe registrations.

Exit criterion: toolUseId matches in 100 % of calls and hashes match after shared
normalization. If not, stop and revise this proposal (fallback: `request_key` join
key exactly like Antigravity).

### 8.1 Phase 1 — behavior-preserving refactor

| Task | Files |
| --- | --- |
| Add provider interface, `codex-meta`, `hermes-meta`, `hook:antigravity`; config parsing/validation (§6.1) | new `host_identity.py`; `client_settings.py` (only if settings belong there) |
| Unify facade; schema generation; per-provider instructions | `client_mcp.py` |
| Generalize registry + profile dispatch; Antigravity profile = current logic | new `host_hook.py`, `host_profiles.py`; `antigravity_binding.py` → alias |
| Keep module entrypoints working | `antigravity_mcp.py` → alias |
| Keep `cli.py` public commands unchanged | `cli.py` (no new command) |

Acceptance: every existing test passes **unmodified** (`test_client_mcp.py`,
`test_multi_harness.py`, `test_antigravity_binding.py`, `test_native_delivery.py`,
etc.). Only additive tests. Codex schema snapshot unchanged. An existing Antigravity
registry created by v0.10.0 is read without migration.

### 8.2 Phase 2 — Claude Code provider (after phase 0 succeeds)

| Task | Files |
| --- | --- |
| Claude profile: parse stdin, deny JSON, server-name check, single-use binding, TTL, pruning, `consumed` column | `host_profiles.py`, `host_hook.py` |
| `hook:claude` provider using `_meta["claudecode/toolUseId"]` | `host_identity.py` |
| Claude instructions text | `client_mcp.py` |
| Apply D1–D4 decisions | as above |

### 8.3 Phase 3 — documentation and release

- `docs/reference/multi-harness.md`: describe providers and config matrix.
- New `docs/reference/claude-code.md` (contract, lifecycle, limits; mirror
  `antigravity.md` structure) and `docs/guides/client-claude.vi.md` (install, MCP
  registration, hook merge, rollback, verification).
- `docs/reference/antigravity.md`: mention the unified facade and that old module
  paths remain aliases.
- `README.md`, `README.vi.md`, `.env.example` (`CLIENT_IDENTITY`,
  `CLAUDE_BINDING_DIR`, `MCP_SERVER_NAME`), `CHANGELOG.md`, `docs/release-notes.md`,
  [docs/README.md](../README.md) map, `SECURITY.md` boundary note.
- Mark this proposal "Implemented in v0.11.0" and link the reference docs.
- New dated `docs/reports/testing-report-v0.11.0.md` separating offline tests from
  live Claude/Antigravity/Codex acceptance.

## 9. Test plan (offline, required)

Add `tests/test_host_identity.py` and `tests/test_claude_hook.py` (names indicative):

- Config: defaults per harness; every invalid provider/harness pair rejected at startup.
- Codex: schema and instructions identical to v0.10.0 snapshot; meta passthrough unchanged.
- Antigravity via unified facade: all current `test_antigravity_binding.py` scenarios
  also pass through the new entrypoint; old module entrypoints still work; v0.10.0
  registry file reused.
- Claude hook: valid input → no stdout, binding stored; wrong server/tool prefix →
  no binding; missing/blank `session_id` or `tool_use_id`, non-UUID session, oversized
  stdin, malformed JSON, storage permission/symlink problems → deny JSON.
- Claude facade: missing `_meta` toolUseId → `host_hook_binding_required` before any
  socket I/O; mismatched args HMAC / tool / expired / already consumed → rejected;
  success forwards only `x-hermes-turn-metadata` with expected values; host-supplied
  `x-hermes-turn-metadata` ignored; lost-ACK `resolve_call` uses identical meta and
  does not re-consume.
- Isolation: two Claude sessions with identical prompts get different flows; one
  session cannot get/wait/cancel the other's operation (404 before broker); same
  conversation string under `antigravity` and `claude` harnesses stays separate.
- Subagents (D1): hook input with an `agent_id` and the parent `session_id` binds to
  the parent conversation; the main agent can get/wait an operation submitted from
  a subagent call; `agent_id` never changes the flow or storage key.
- Concurrency: two hooks racing on the same `tool_use_id` with different sessions →
  one wins, other denied; pruning never deletes an unexpired, unconsumed row.
- Security hygiene: no prompt/argument/meta values in stdout/stderr/logs; registry
  file modes asserted.
- Run the full validation suite from AGENTS.md, including PostgreSQL coverage gate
  and clean-wheel checks.

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| Claude Code changes hook/`_meta` shape in a later version | Fail closed; profile validates exact fields; document tested version; `client-doctor` could report hook registry health (optional). |
| Permission prompt longer than TTL | 300 s TTL (D4); fail closed with a clear error asking the user to re-issue the call (new `tool_use_id`, new attestation). |
| Model retries an ambiguous submit as a new call (new `tool_use_id`) | Same as Codex: instructions forbid it; durable operation IDs + get/wait; never auto-replay. |
| Registry growth from per-call rows | Claude profile prunes consumed/expired rows (§6.4); Antigravity unchanged. |
| Same-UID process forges hook writes | Accepted boundary, same as today; documented as routing isolation, not a sandbox. |

## 11. Definition of done

- Phases 0–3 complete; D1–D4 resolved and documented.
- All AGENTS.md validation commands pass, including the PostgreSQL coverage gate,
  wheel build, `twine check`, `check_dist.py`, `check_wheel_install.py`, checksums.
- Codex and Antigravity behavior unchanged (tests + one live harmless check each,
  authorized by the operator).
- Live harmless Claude Code acceptance: two sessions isolated, retry/get/wait,
  cross-session rejection, resume behavior as documented; recorded in a dated report.
- Diff contains no private files, runtime stores, logs or credentials.
