# Trusted multi-harness client adapters

One daemon, device and SQLite inbox can serve multiple local MCP harnesses.
An operator configures each `client-mcp` process using
`HERMES_A2A_GATEWAY_CLIENT_HARNESS` and
`HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE`. Both are lowercase ASCII identifiers
matching `[a-z0-9][a-z0-9_.-]{0,63}`. Defaults are `codex` and `default` for existing
installations. Use stable, distinct instance names for separate installations or
accounts of the same harness. Changing either name starts a separate namespace;
it does not transfer access to previous operations.

The MCP facade reads these values from its operator-owned environment, never
from tool arguments or result content. The daemon receives a separate `identity`
envelope alongside host metadata. The private user-owned Unix socket is the trust
boundary: processes running as the same OS user are trusted adapters and can
impersonate each other. This is routing isolation, not a sandbox against a malicious
same-user process. Do not expose `/command` as an unauthenticated TCP service or
allow model tools to modify adapter configuration or host request metadata.

Codex continues to require its consistent `threadId`, `callId` and
`x-codex-turn-metadata` host metadata. Other harness adapters must provide
`x-hermes-turn-metadata` with exactly `conversation_id`, `turn_id`, `call_id` in
MCP request metadata. Each value is a nonblank string of at most 512 characters;
conversation and turn IDs must be stable host identities and call IDs must identify
one exact invocation. Replaying that exact invocation recovers the same operation;
reusing it with different content is rejected. The adapter must obtain all three
from its host, not the model. A host without trusted request metadata needs a host
integration before it can use this facade. No fallback conversation, random call
identity, environment-only conversation guess or operation-to-owner lookup exists.

## Durable binding and compatibility

Flow and local call identity are keyed by `(harness, instance, conversation)`.
Default Codex stores its original thread UUID unchanged. Other namespaces use
`harness:` followed by a compact JSON array of those three strings as the internal
SQLite thread key. The prefix is disjoint from valid default Codex UUIDs and the
JSON encoding is unambiguous even for conversation IDs containing delimiters.
The existing TEXT columns and uniqueness constraints support this representation;
no table rebuild, destructive migration or reinterpretation of old rows is needed.
Existing flow, device, operation, result, delivery, cursor and peer context IDs stay
unchanged. New scoped conversations receive new flow UUIDs; the broker's existing
device/flow contract separates their Hermes sessions without a broker migration.

Get, wait, cancel and lost-ACK resolution check the scoped owner before reading,
refreshing or mutating broker operations. Knowing another namespace's operation ID
does not grant access. Exact call resolution uses the same scope. Broker result
snapshots must still match the stored flow. Admission limits, retention and device
artifact storage are shared; this feature does not provide per-harness quotas or
artifact ACLs. Never use it as a multi-user security boundary.

Nondefault facades require daemon health capability `harness_identity_version=1`
before issuing commands. This prevents an older daemon from ignoring the identity
envelope. Nondefault commands also use a versioned `harness_v1/` action so an
old daemon rejects them if a downgrade races the capability check. No lost-ACK
lookup is attempted when a command never passed negotiation. Upgrade both components together before enabling additional namespaces.

## Result delivery

Inline results and explicit get/wait work for every supported trusted adapter.
Only `codex/default` uses the verified native Codex queue adapter. All other
harnesses and Codex instances use explicit pull and are never enqueued or reconciled
through that adapter, including after restart. A new push integration must bind to
its own verified host instance before this restriction can be relaxed. Queue ACKs
still do not prove consumption; uncertain queue submissions are never replayed.

Example operator configuration for a host adapter (metadata support required):

```text
HERMES_A2A_GATEWAY_CLIENT_HARNESS=antigravity
HERMES_A2A_GATEWAY_CLIENT_HARNESS_INSTANCE=workstation-main
```

Run `tests/test_multi_harness.py` for offline ownership, identical-ID, recovery and
delivery regression checks. These checks do not prove live host integration.

Descriptive model labels travel separately; see [sender labels](sender-context.md).
They never participate in the scoped routing key.


Antigravity2.22.0 supplies conversation identity through its native lifecycle hook.
The dedicated [Antigravity facade](antigravity.md) attests exact MCP requests with that
host identity; the generic facade still requires trusted MCP metadata.

## v0.11 provider selection

The MCP facade accepts `HERMES_A2A_GATEWAY_CLIENT_IDENTITY` in the MCP process.
`codex-meta` requires harness `codex`; `hermes-meta` requires a non-Codex harness;
`hook:antigravity` requires `antigravity`; `hook:claude` requires `claude`. Unset preserves the existing metadata
provider for each harness. Unsupported provider/harness pairs fail at startup
with a fixed diagnostic. No identity value comes from tool arguments.

The unified `client-mcp` entrypoint selects the established Codex or Antigravity
schema and instructions. The Antigravity module remains an alias and selects
`hook:antigravity`; conflicting explicit configuration is rejected. The shared
hook runs as `python -m hermes_a2a_gateway.host_hook --profile antigravity`.
The old hook module is still supported. Paths, key files, table definition,
120-second renewable attestations and permanent key ownership are unchanged.

Claude Code Desktop uses `hook:claude` and the dedicated stable instance
`claude-desktop`. See [Claude contract](claude-code.md). CLI/IDE, actual resume,
process restart and CLI/Desktop interoperability remain unverified. The
single-conversation provider is not implemented.

`gateway_list(limit=10, include_finished=true)` is a read-only, local lost-ID recovery tool scoped to the same trusted storage thread as get/wait. Limit is 1–50; no broker refresh or delivery consumption occurs.
