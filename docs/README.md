# Documentation by task

Current candidate: **v0.12.0**. Existing default connections retain v0.11 paths,
identities and credentials. Python 3.12/3.13 remain candidates until the full
Linux/macOS CI matrix passes. Versioned release assets establish provenance;
local builds and fake peers do not establish production/Desktop acceptance.

## Install

- [Quickstart](guides/quickstart.md): prerequisites and minimum steps per harness/server.
- [Deployment](guides/deployment.md): verify release assets, install and operate both ends.
- [Codex Desktop](guides/client-codex.vi.md): private launcher, MCP and native delivery.
- [Claude Code Desktop](guides/client-claude.vi.md): project-local MCP/hook registration.
- [Antigravity](guides/client-antigravity.vi.md): native wrapper/hook registration.
- [Hermes server](guides/server-hermes.vi.md): PostgreSQL, TLS proxy and loopback peer.

## Upgrade

- [v0.11 → v0.12](upgrades/upgrade-v0.12.md): additive migrations, connections and rollback.
- [v0.10 → v0.11](upgrades/upgrade-v0.11.md): unified MCP/hook rollout.
- [v0.9](upgrades/upgrade-v0.9.md): ordered receiver overlay and rollback.
- [v0.6/legacy → v0.7](upgrades/migration-v0.7.md): rename and data preservation.

## Operate

- [Client connections](guides/client-connections.md): one isolated daemon per broker.
- [AI operations](guides/ai-operations.md): submit, recover IDs, wait, diagnose and report evidence.

## Rotate

- [Tokens and payload keys](guides/rotation.md): overlap, TTL, count-only diagnostics and removal gates.

## Troubleshoot

- [SSH transport](guides/ssh-tunnel.vi.md): verified tunnels, reconnect and diagnostics.
- Use the error-code table in the AI operations guide listed above. Silence or a lost
  ACK never authorizes replay. Read current readiness before interpreting older evidence.

## Contracts

- [Client/server HTTP and SSE](reference/client-server-contract.md): ownership, snapshots and migrations.
- [Multiple harnesses](reference/multi-harness.md): trusted identity and local isolation.
- [Sender context](reference/sender-context.md): descriptive labels, not routing identity.
- [Antigravity](reference/antigravity.md): native hook contract and limits.
- [Claude Code](reference/claude-code.md): Desktop provenance and scope.
- [Hermes compatibility](reference/hermes-compatibility.md): pinned receiver assets and timeout chain.

## Evidence and planning

- [Release notes](release-notes.md): current candidate behavior and acceptance limits.
- [Reports](reports/README.md): immutable dated verification, including installed v0.11 acceptance.
- [History](history/README.md): retired releases/modes, not current setup instructions.
- [Proposals](proposals/README.md): planned designs; status alone does not authorize implementation.

Ten pre-existing relative links inside reports/history refer to documents moved
before v0.12. Those immutable files are preserved. The documentation link test
records those exact legacy failures and rejects any new broken link; current
guides, contracts and this index must resolve.
