# Post-acceptance cleanup and operator guidance — 2026-10-14

Request A2A-20261014-006. The two local acceptance commits `b621793` and
`a53d7b6` were retained without duplication. Fresh origin/main was their ancestor
(two commits behind the local branch); no divergence or unrelated edits existed.

## Cleanup

- Native Claude UI showed all owned acceptance/probe sessions Idle. The original
  user chat had a draft, so no UI navigation, project removal or app quit was used.
- Exact owned acceptance MCP PIDs 5216, 95942 and 96421 were rechecked for expected
  parent, command and isolated test-project working directory, then received
  SIGTERM. All three were confirmed absent. Session parent processes, other
  sessions, Codex/Antigravity MCPs and daemon/services were not terminated.
- Both owned scratch projects already lacked active `.mcp.json` and
  `.claude/settings.local.json`; no temporary configuration needed another removal.
- The isolated PostgreSQL 16 test data directory was removed only after verifying
  its version, absence of postmaster.pid and absence of its server process.
  Its test logs were retained. This was the disposable offline-suite database,
  not the broker's PostgreSQL store.
- Probe sources/events, candidate config backups, build evidence, private worker
  context, test chat history and scratch project registrations remain available.
  Removing registrations through the active user UI would require disturbing
  that view; no hidden app-database edit or permanent history deletion was used.
- Installed venvs, downloaded release, deployment receipts, rollback backups and
  scripts, binding registries/keys, credentials, runtime stores and services remain.

## Configuration review and docs

The installed Antigravity entry still uses installed-venv Python with
`hermes_a2a_gateway.antigravity_mcp`, harness `antigravity`, stable instance
`antigravity-desktop`, and the matching `antigravity_binding` PreToolUse hook.
These compatibility aliases remain supported; no persistent setting was changed.

Claude's accepted setup was project-local and its temporary configs were removed.
The updated guide describes persistent setup in the real project using direct
installed-venv `client-mcp` plus `host_hook --profile claude`, stable
`claude` / `claude-desktop` / `hook:claude`, preserving existing permissions and
settings. User-scope/CLI/IDE/resume are not described as validated.

Both guides now distinguish a new workstation from an existing v0.11.0 daemon,
list all five tools, explain bounded waits and uncertain-result reconciliation,
and provide operator setup/use prompts. Antigravity prefers restarting only its
MCP server and reusing compatible entries instead of duplicate registration.
Entrypoint links/status wording were reconciled with shipped v0.11.0 evidence.

Validation: relative Markdown file links and JSON blocks checked; tool names,
wait bounds/defaults, aliases and identity settings compared with current source;
`git diff --check`. No source changes, release rebuild, runtime upgrade, extra
live model test or full-suite rerun was required. The human explicitly authorized
pushing the documentation and the two retained acceptance commits after review.
