# Documentation map

Version documented: **v0.11.0**. Release artifacts and their provenance are on the versioned GitHub release. Start from the repository [README](../README.md) for the
product summary; use this page to find the right document. AI agents should read
[AGENTS.md](../AGENTS.md) first.

| Folder | Contains | Status |
| --- | --- | --- |
| [`guides/`](#guides) | Install, configure and operate a deployment | Current, maintained |
| [`reference/`](#reference) | Normative contracts and integration boundaries | Current, maintained |
| [`upgrades/`](#upgrades) | Version migration, upgrade and rollback procedures | Current for the named versions |
| [`proposals/`](#proposals) | Designs approved for implementation but not yet shipped | Not current behavior |
| [`reports/`](#reports) | Dated test/verification reports and reviews from v0.7 onward | Immutable evidence |
| [`history/`](history/README.md) | Releases up to v0.6, retired modes and investigations | Immutable evidence |
| [`release-notes.md`](release-notes.md) | Notes for the current release; read by `scripts/publish_release.py` | Current |

## Guides

| Document | Use it for |
| --- | --- |
| [deployment.md](guides/deployment.md) | Shared release download/checksum, install, operations, upgrade and rollback reference |
| [server-hermes.vi.md](guides/server-hermes.vi.md) | Server: Hermes, PostgreSQL, broker, TLS proxy (Vietnamese) |
| [client-codex.vi.md](guides/client-codex.vi.md) | Workstation: client daemon and Codex Desktop MCP registration (Vietnamese) |
| [client-antigravity.vi.md](guides/client-antigravity.vi.md) | Workstation: Antigravity facade and PreToolUse hook (Vietnamese) |
| [client-claude.vi.md](guides/client-claude.vi.md) | Claude Code Desktop registration, hook merge and rollback |
| [ssh-tunnel.vi.md](guides/ssh-tunnel.vi.md) | Direct vs daemon-managed SSH transport, retries, diagnostics (Vietnamese) |
| [ai-operations.md](guides/ai-operations.md) | How an AI agent should use the five `gateway_*` tools safely |

## Reference

| Document | Defines |
| --- | --- |
| [client-server-contract.md](reference/client-server-contract.md) | Client ↔ broker wire contract, IDs, idempotence, SSE, receipts |
| [multi-harness.md](reference/multi-harness.md) | Trusted harness/instance/conversation isolation and host metadata |
| [sender-context.md](reference/sender-context.md) | Descriptive harness/model/connection labels delivered to Helen |
| [antigravity.md](reference/antigravity.md) | Antigravity host-hook attestation, lifecycle, retries and limits |
| [claude-code.md](reference/claude-code.md) | Claude Code Desktop host identity, lifecycle and unverified scope |
| [hermes-compatibility.md](reference/hermes-compatibility.md) | Versioned Hermes receiver patch in `compat/hermes` |

## Upgrades

| Document | Covers |
| --- | --- |
| [migration-v0.7.md](upgrades/migration-v0.7.md) | v0.6/legacy → v0.7 rename, removal of legacy modes, rollback |
| [upgrade-v0.9.md](upgrades/upgrade-v0.9.md) | Ordered, data-preserving upgrade/rollback for v0.9 and later |

## Proposals

Status, lifecycle and the rules for implementing a proposal are kept in one place:
[proposals/README.md](proposals/README.md). Current proposals:
[unified-mcp-identity.md](proposals/unified-mcp-identity.md) (adds Claude Code,
target v0.11.0).

A proposal describes intended work. It is not installation guidance and does not
change current behavior until implemented, tested and released.

## Reports

Dated evidence for v0.7.0–v0.10.0 releases and the 2026-10-12 review; see
[reports/README.md](reports/README.md). Add a new dated report for new live results;
never rewrite an existing one.

Current unreleased work: [Claude CLI spike, blocked](reports/claude-code-identity-spike-2026-10-14.md)
and [unified MCP Phase 1 local verification](reports/unified-mcp-phase1-2026-10-14.md).
[Attempt 2 Desktop live addendum](reports/claude-code-identity-spike-2026-10-14-attempt2.md) records 8/8 identity joins and remaining lifecycle gates. These reports do not establish v0.11.0 release acceptance.

## Placement rules

- New how-to for operators → `guides/` (Vietnamese guides use the `.vi.md` suffix).
- New or changed contract, protocol limit or trust boundary → `reference/`.
- Version-specific migration → `upgrades/`.
- Design that is not implemented yet → `proposals/`.
- Live/test evidence → new dated file in `reports/`.
- Private orchestration notes (`docs/worker-context-*.md`) are git-ignored and
  excluded from the sdist; never commit or link them.

Candidate verification: [v0.11.0 tests and live Desktop scope](reports/testing-report-v0.11.0.md).

Upgrade: [v0.10 to v0.11](upgrades/upgrade-v0.11.md).

Release provenance and remaining native checks: [v0.11.0 release/deployment evidence](reports/release-v0.11.0-2026-10-14.md).

Latest native acceptance: [installed v0.11.0 attempt 4](reports/native-acceptance-v0.11.0-2026-10-14-attempt4.md) — Claude Desktop and Antigravity pass; Codex facade reload provenance remains pending.
