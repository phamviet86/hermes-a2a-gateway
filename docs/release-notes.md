# Hermes A2A Gateway v0.12.0 (candidate)

Device-token overlap and MultiFernet previous keys support staged rotation. Count-only readiness reports show retained old-key usage; restarts are still required.

Text attachment inputs now include Markdown, CSV and valid JSON. Binary inputs remain unsupported.

Running snapshots expose bounded `last_peer_activity_at` and `running_seconds`; silence never authorizes resubmission.

Receiver timeout diagnostics distinguish `peer_reply_timeout` from ambiguous broker transport expiry. Configure long-task budgets together; never replay uncertain work.

`gateway_list` recovers lost operation IDs locally within the calling conversation.

Named connections run one daemon per broker with separate credentials and state.
The default connection keeps the v0.11.0 paths and identities.

# Hermes A2A Gateway v0.11.0

The MCP facade now selects pluggable host identity providers. Codex and Antigravity
retain their schemas, instructions, IDs and registry behavior; old Antigravity
module entrypoints remain supported.

Claude Code **Desktop Code tab** adds native PreToolUse identity joined to MCP
toolUseId. Attestations bind exact normalized arguments, expire at 300 seconds and
are consumed atomically once. Claude uses dedicated instance `claude-desktop`,
shared parent/subagent flow and explicit pull only. No broker wire/schema,
existing inbox, key, ciphertext, peer-identity or namespace migration is required.

The 2026-10-14 operator-approved initial scope is Desktop first. Eight isolated
Desktop probe joins matched; compaction/sidebar reopen retained identity,
fork/clear changed it, and a native subagent shared its parent identity. These are
bounded probe results. Separate live gateway acceptance verified two isolated
Desktop sessions, saved-operation wait/get, cross-session read rejection and
shared parent/subagent reads.

CLI/IDE, actual resume, process restart and CLI/Desktop interoperability remain
unverified. Ordinary Desktop chat and single-conversation mode are unsupported.
Changing instance does not transfer access to prior operations.

See [Desktop setup](guides/client-claude.vi.md) and [identity contract](reference/claude-code.md).
Offline validation: 356 passed, 1 skipped; 84.36% coverage with PostgreSQL 16.
Compile, lint, formatting, typing, Codex schema, clean-wheel, distribution and
compatibility/checksum checks passed. See [candidate evidence](reports/testing-report-v0.11.0.md).
Release assets are published only from the exact successful main/push CI commit.
Installed-release and native host regression evidence are separate from the
source-candidate observations.
