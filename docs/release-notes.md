# Hermes A2A Gateway v0.11.0 — candidate

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
probe results, not release installation or live gateway acceptance.

CLI/IDE, actual resume, process restart and CLI/Desktop interoperability remain
unverified. Ordinary Desktop chat and single-conversation mode are unsupported.
Changing instance does not transfer access to prior operations.

See [Desktop setup](guides/client-claude.vi.md) and [identity contract](reference/claude-code.md).
Publication, CI and installed-release evidence must be established separately;
this file currently describes a candidate, not a completed release.
