# Upgrade v0.10.0 to v0.11.0

This release unifies the MCP facade and adds Claude Code Desktop native hook
identity. There is no broker/client wire or inbox migration, no receiver patch
change, and no change to existing namespace IDs. Existing Antigravity module
entrypoints and registry semantics remain compatible. Older installations must
first follow their applicable [migration](migration-v0.7.md) and
[upgrade](upgrade-v0.9.md) guidance.

1. Identify the exact independent Python 3.11 gateway venv on both hosts, the owned
   client/broker services, current release, protected configuration, keys and state
   paths. Do not upgrade Hermes's Python environment or unrelated services.
2. Download all eight versioned v0.11.0 GitHub assets independently on each host.
   Verify SHA256SUMS, wheel metadata and release/tag provenance from the successful
   main/push CI commit. Do not substitute a checkout build for published artifacts.
3. Reconcile pending work by its exact operation ID; do not replay an ambiguous
   submit. Require a quiescent ledger. Stop only the owned client writer/broker,
   obtain the SQLite writer lock and confirm the broker dispatcher is stopped.
4. Save protected rollback copies of each venv, configuration and keys. Back up
   SQLite consistently while its writer is stopped and use a consistent PostgreSQL
   dump. Retain modern inbox/ledger IDs, receipts, cursor and ciphertext. Treat
   backups as sensitive; never print their contents or credentials.
5. Install the verified wheel in each original venv after checking Python and
   dependency compatibility. Keep dependencies unchanged when already compatible;
   run pip check and compare installed package files with the wheel. Start only
   the owned services and verify readiness, authenticated transport and prior exact
   operation readback. Record package, transport and native acceptance separately.
6. Existing MCP processes may retain old imported code. Refresh each host through
   its supported lifecycle only after its active work is safe. Test a harmless
   native Codex and Antigravity call; do not infer refreshed code from on-disk files.
   Add Claude project MCP/hook entries using the [Desktop guide](../guides/client-claude.vi.md),
   merge rather than overwrite user settings, and keep instance `claude-desktop`.

Rollback is code-only at the original venv path, after stopping owned writers.
Restore the saved venv and matching configuration entries only when needed; retain
current databases, keys and post-upgrade operations. Do not restore an old database
snapshot over newer work. Keep the replaced venv for investigation. Remove only
newly added Claude MCP/hook entries if rolling back that integration; preserve the
private Claude registry and do not reuse it for Antigravity. Already issued bindings
may remain valid until their TTL expires. Do not remove authentication, shared
runtimes, unrelated tunnels, user workspaces or native application data.

Claude CLI/IDE, actual resume, process restart and CLI/Desktop interoperability
remain unverified in the initial Desktop-first scope. Host restart for installation
is not evidence that Claude session resume semantics were tested.
