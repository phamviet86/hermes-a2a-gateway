# Named client connections

Each connection is one daemon talking to one broker. `connection` does not change
the harness `(harness, instance, conversation)` identity. Never share a device token,
payload key, SQLite file, socket, lock or hook registry between connections.

| Setting | `default` (unchanged) | Named connection `<name>` |
| --- | --- | --- |
| Config | `~/.config/hermes-a2a-gateway/` | `~/.config/hermes-a2a-gateway/connections/<name>/` |
| State | `~/.local/state/hermes-a2a-gateway/client` | `~/.local/state/hermes-a2a-gateway/connections/<name>/client` |
| MCP name | `hermes-a2a-gateway` | `hermes-a2a-<name>` |
| Hook stores | `~/.local/state/hermes-a2a-gateway/{claude,antigravity}` | `~/.local/state/hermes-a2a-gateway/connections/<name>/{claude,antigravity}` |

Names match `[a-z0-9][a-z0-9-]{0,31}`. Explicit state, hook-directory and
`HERMES_A2A_GATEWAY_MCP_SERVER_NAME` settings override derived defaults.

## Set up

Start with the private launcher generator in the [Codex client guide](client-codex.vi.md).
Parameterize its `base` and `state` variables with the following, before creating
any files. Keep its exclusive-create and private-permission checks:

```python
from hermes_a2a_gateway.connections import config_path, state_path, connection_name

connection = connection_name("helen")  # choose a distinct name for each broker
base = config_path(connection)
state = state_path("client", connection)
```

Add `"HERMES_A2A_GATEWAY_CLIENT_CONNECTION": connection` to that generator's `values`
dictionary. The launcher must export this variable for the daemon, MCP process
and set the same non-secret value explicitly on the native hook. Use the expanded
non-secret MCP allowlist in the current Codex launcher generator; never forward
the daemon's token, current key or previous keys to the MCP/hook processes. Obtain a newly authorized device token from
each broker owner and generate a fresh payload key for each connection. Do not
copy the default connection's credentials. When using SSH, allocate a distinct
local port and update the matching loopback HTTPS broker URL.

```bash
connection=helen
base="$HOME/.config/hermes-a2a-gateway/connections/$connection"
"$base/launch" client-doctor
"$base/launch" client
codex mcp add "hermes-a2a-$connection" -- "$base/launch" client-mcp
```

For background operation use LaunchAgent label
`com.hermes.a2a.gateway.client.<name>` or systemd template unit
`hermes-a2a-gateway-client@<name>.service`; its `ExecStart` points to this
connection's `launch client`. Copy the detailed guide's service definition,
changing the label, launcher and log paths for each connection. Run only one
service manager per connection.

Register the Claude and Antigravity MCP entries under the same derived name.
For Claude, scope the PreToolUse matcher to `mcp__hermes-a2a-<name>__*`; for
Antigravity, the wrapper's `ServerName` must equal `hermes-a2a-<name>`.
Invoke each hook directly through the installed Python with this connection's
non-secret environment (`HERMES_A2A_GATEWAY_CLIENT_CONNECTION=<name>` and any
explicit server-name/binding-directory overrides), using `python -m
hermes_a2a_gateway.host_hook --profile claude` or `--profile antigravity`. The
standard CLI launcher accepts only client/client-mcp/client-doctor; do not pass
a hook module to it. Keep separate binding directories.
See [Claude](client-claude.vi.md) and [Antigravity](client-antigravity.vi.md).
Do not register a second connection with the default MCP entry's name.

`client-doctor` reports `connection_name`, sanitized `broker_origin`, discovered
configuration directory names and collision warnings. Discovery covers supported
`client.json` launchers, not arbitrary service manager environment overrides.
Resolve `shared_state_directory` and `shared_ssh_local_port` before starting.
MCP instructions and each tool result identify their connection.

## Remove one connection

Stop only its named service and daemon; remove only its MCP entry and hook
matcher. Back up its private state and keys consistently while the writer is
stopped. Remove its own config/state directories only after checking the backup.
Do not remove default/shared installations, another connection, or unrelated SSH
processes. Never delete a writer lock to force another daemon to start.
