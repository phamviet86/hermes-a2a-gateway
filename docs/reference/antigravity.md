# Antigravity native integration (0.10.0)

This integration uses Antigravity's native **PreToolUse hook**, not a guessed
process/workspace/current-chat ID. Its schema is selected by the unified MCP facade.
The existing client/broker0.9 protocol (`harness_v1/`, capability1) is sufficient;
no Hermes receiver, broker database, Codex registration or running daemon change
is needed. Install the same0.10.0 wheel on client and broker; the receiver overlay is unchanged from0.9.0.

## Host contract

[Google's hook documentation](https://www.antigravity.google/docs/hooks) documents
host-supplied `conversationId` and `stepIdx`. In actual Antigravity2.22.0,
MCP tools are wrapped as `call_mcp_tool` with `ServerName`, `ToolName`, and JSON
`Arguments`; that wrapper shape is runtime-verified, rather than documented as
part of MCP itself. The native hook receives the active conversation UUID before
execution. No chat stores, transcript files, provider auth or private APIs are read.

The model supplies a random UUID **request_key**, which is an idempotency key,
not a conversation identity. Before a gateway call, the host hook atomically binds
that key, tool and exact normalized arguments to its trusted conversation UUID.
The dedicated MCP facade reads that attestation and forwards the trusted UUID
through the existing scoped daemon protocol. It has no shared active-chat pointer.

A protected SQLite registry keeps key ownership across process/app restarts.
Arguments are represented only by keyed HMAC, never stored as plaintext prompts.
The local random HMAC key remains outside SQLite. The registry directory is0700;
key/database are0600 and symlinks are rejected. Attestation expires after120seconds;
a fresh native hook renews it only for the original conversation and content.
Ownership does not expire, so a different conversation cannot reclaim an old key.
New keys fail closed at100000 bindings; SQLite growth is capped at64MiB. Existing
keys can still be renewed at the row quota. No automatic deletion reassigns ownership.
Keep the registry and key when upgrading or rolling back; do not prune ownership
rows while retained operations/retry keys can still be used.

For submit, the bound key supplies stable adapter call/turn identifiers. They are
adapter identifiers, not claims about Antigravity native turn IDs. The actual
conversation UUID supplies the routing identity. New model labels or executing
models do not participate in that key. Default labels remain Antigravity / Gemini
model / a2a; only an explicit descriptive model override changes the label.

## Configure without disturbing Codex

Install the release wheel into an independent Python3.11 venv. Retain the prior
Antigravity gateway registration as an opaque private rollback copy. Merge only
that entry into the existing `~/.gemini/config/mcp_config.json` (or the selected
workspace configuration); preserve other registrations, settings and credentials:

```json
{
  "mcpServers": {
    "hermes-a2a-gateway": {
      "command": "/absolute/gateway-venv/bin/python",
      "args": ["-m", "hermes_a2a_gateway.antigravity_mcp"],
      "env": {
        "HERMES_A2A_GATEWAY_CLIENT_HARNESS": "antigravity",
        "HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE": "antigravity-desktop"
      }
    }
  }
}
```

Merge this named entry into `~/.gemini/config/hooks.json`. Both processes must use
the same protected registry location (default
`~/.local/state/hermes-a2a-gateway/antigravity`). A custom location requires
`HERMES_A2A_GATEWAY_ANTIGRAVITY_BINDING_DIR` in both process environments.

```json
{
  "hermes-a2a-binding": {
    "PreToolUse": [{
      "matcher": "call_mcp_tool",
      "hooks": [{
        "type": "command",
        "command": "/absolute/gateway-venv/bin/python -m hermes_a2a_gateway.antigravity_binding",
        "timeout": 10
      }]
    }]
  }
}
```

The hook returns `ask` for valid requests and unrelated MCP servers, retaining
Antigravity's Ask/previous-grant behavior rather than automatically allowing tools.
It returns `deny` for a gateway request missing host identity/key, a conflicting
owner/content or unavailable storage. Existing permission policy is not weakened.
If another integration hooks the same wrapper, verify its combined policy.

Stop only owned test turns before refreshing/restarting Antigravity. On2.22.0,
editing config did not refresh the existing MCP process; restarting loaded the
new schema. Confirm every tool requires request_key before submitting real work.
The old generic facade still rejects absent host metadata; do not relax it.

## Lifecycle, retry and limits

- New conversation: Antigravity allocates its own UUID; first attested call creates
  a distinct harness/instance/conversation flow. No manual chat-ID entry is needed.
- Existing/reopened conversation: host supplies the same UUID; use get/wait on
  saved operation IDs, or a new key for deliberately new work. Model changes keep
  the same flow and context. A host fork with a new UUID intentionally gets a new flow.
- New action: generate a new random request_key and retain it with exact arguments.
  Do not use fixed examples as production keys or share keys between chats.
- Uncertain submit: never generate a new key to retry. Use saved get/wait, or repeat
  the exact original key/arguments through the native hook. Existing daemon
  idempotence returns the same operation/task, including after restart. Changed
  content under that key fails before dispatch.
- Get/wait: each new read may use a new key; result ownership comes from the host
  conversation, never the requested operation's stored owner. Wrong-session reads
  and cancel are404 before upstream mutation.
- Cancel is best effort. Upload/cancel uncertain acknowledgements retain existing
  gateway uncertainty semantics; a request_key is not permission to blindly retry
  an upload or cancel. Upload is only for explicitly requested bounded regular files.
- No native push delivery: results must be read with get/wait. Shared local device
  credentials, quotas and artifact storage remain shared; this is single-user
  conversation separation, not a security boundary against a malicious same-UID
  process or an agent granted arbitrary local file/command access.
- Disabling/breaking the hook fails closed for new unattested requests. An already
  attested exact request remains valid until its120second expiry. Do not treat the
  local grant lifetime as revocation or universal exactly-once execution.

Rollback restores only the original Antigravity gateway registration and removes
only the owned hook entry. Preserve current binding registry, daemon data, account,
credentials and operations. Reload the application. The0.9 generic facade cannot
provide native Antigravity identity by itself, so rollback restores that known limit.

## Evidence

Offline tests: `tests/test_antigravity_binding.py`, existing native Codex,
`test_multi_harness.py`, sender, broker and restart tests. Actual app acceptance is
recorded separately in the host's dated deployment report. A manually invoked
hook/facade fixture is not native app evidence. Actual app reopening after established context still requires the user acceptance
check. A model switch was observed on Antigravity2.22.0; model labels remain descriptive.

## v0.11 compatible entrypoints

The unified facade moves the existing facade and registry implementation into shared modules.
The old `antigravity_mcp` and `antigravity_binding` module paths remain compatible
aliases. New registrations may use `client-mcp` with
`HERMES_A2A_GATEWAY_CLIENT_IDENTITY=hook:antigravity`, or the shared hook module
`hermes_a2a_gateway.host_hook --profile antigravity`. Existing registrations need
no edits; no registry migration or application restart has been performed here.
