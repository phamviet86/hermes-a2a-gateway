# Quickstart

v0.12 supports CPython 3.11–3.13 on Linux and macOS. The complete interpreter
matrix and PostgreSQL jobs passed before extending support. Package tests are
separate from installed Desktop or production acceptance.

## Common prerequisites

Use Linux or macOS, a verified release wheel/checksums, a private broker URL,
device token, fresh per-connection payload key, and verified TLS trust. Keep
credentials in protected configuration. Each broker requires PostgreSQL 16 and a
loopback Hermes peer. Never use another connection's token, key or store.

Install the verified wheel in a private virtual environment, using any supported CPython 3.11–3.13 (3.13 shown):

```bash
python3.13 -m venv /absolute/private/gateway-venv
/absolute/private/gateway-venv/bin/python -m pip install /absolute/path/to/verified-gateway.whl
/absolute/private/gateway-venv/bin/hermes-a2a-gateway --version
```

On macOS obtain the pinned interpreter with `brew install python@3.13`; on Linux
use a trusted CPython 3.11–3.13 package or `uv python install 3.13` followed by
`uv venv --python 3.13 /absolute/private/gateway-venv`. See
[release verification and deployment](deployment.md) before installing.

For multiple brokers, choose a connection name such as `helen`, create its private
launcher with the parameterized generator in [connections](client-connections.md),
and use MCP name `hermes-a2a-helen`. Its daemon, socket and hook registries must
all use the same `HERMES_A2A_GATEWAY_CLIENT_CONNECTION`. Existing installations
keep `default` and `hermes-a2a-gateway` unchanged.

## Codex Desktop

Prerequisites: supported local Codex CLI, the common installation, and the private
launcher created by the [Codex guide](client-codex.vi.md). For the default:

```bash
"$HOME/.config/hermes-a2a-gateway/launch" client
# In another terminal, with that daemon running:
"$HOME/.config/hermes-a2a-gateway/launch" client-doctor
codex mcp add hermes-a2a-gateway -- "$HOME/.config/hermes-a2a-gateway/launch" client-mcp
```

Set `tool_timeout_sec = 90` in that MCP entry as documented. Reuse a matching
existing entry instead of registering it twice. Doctor must show the intended
broker origin, authenticated transport and connection; verify trusted host
metadata with a harmless authorized call. Queue ACK does not prove consumption.

## Claude Code Desktop

Prerequisites: the Desktop Code tab, common installation and one running daemon.
Run the same `launch client` and `launch client-doctor` commands above for the
chosen connection. Follow the [Claude guide](client-claude.vi.md) to merge the MCP
entry and project-local PreToolUse hook, preserving all unrelated settings.
Set harness `claude`, harness instance `claude-desktop`, and identity `hook:claude`
on that MCP process. The hook executable is:

```bash
/absolute/private/gateway-venv/bin/python -m hermes_a2a_gateway.host_hook --profile claude
```

Configure it as a host hook, not as a manual attestation generator. For a named
connection set its connection variable on both hook and MCP process; use matcher
`mcp__hermes-a2a-<name>__*`. An explicit MCP name override must match both.
Reload the selected MCP entry/hook through the host. Doctor verifies transport;
a fresh native hook call verifies identity. Use get/wait for explicit results.

## Antigravity

Prerequisites: the supported Antigravity native PreToolUse wrapper and common
installation. Start the chosen daemon and run its `launch client-doctor`.
Follow the [Antigravity guide](client-antigravity.vi.md) to merge the MCP entry and
`call_mcp_tool` hook, with its configured ServerName and shared private binding
registry. The hook executable is:

```bash
/absolute/private/gateway-venv/bin/python -m hermes_a2a_gateway.host_hook --profile antigravity
```

Set the connection variable on hook and facade for a named broker. Each action
requires a fresh UUID `request_key`; retries preserve exact key and arguments,
while an ambiguous submit is never repeated. Verify a fresh native hook call;
manual fixture attestations do not establish host acceptance.

## Server

Prerequisites: PostgreSQL 16, a loopback-only Hermes A2A peer, a verified TLS proxy,
and protected broker database URL, distinct device token mapping and encryption
key. Install the same reviewed wheel, configure protected environment values using
the [server guide](server-hermes.vi.md), then start the broker:

```bash
/absolute/private/gateway-venv/bin/hermes-a2a-gateway broker
```

Keep Hermes loopback-only and HTTPS/device authentication enabled. Verify broker
readiness through the trusted TLS proxy, then `client-doctor` on the configured
client: authenticated transport, intended origin, peer policy, timeout warnings,
and key usage counts. Long jobs need coordinated receiver/broker budgets. Do not
raise timeouts or rotate keys to hide an unexplained failure.

## Recover and operate

Save `operation_id` after submission. If it is lost, use `gateway_list`, then
get/wait on the matching item; never resubmit a matching unknown operation.
See [agent operations](ai-operations.md), [rotation](rotation.md), and
[upgrade/rollback](../upgrades/upgrade-v0.12.md).
