# Upgrade v0.11 to v0.12

This is a candidate upgrade; review the task validation report and CI before
publishing. No live host upgrade or receiver patch is performed by this work.

1. Pause new submissions and wait for definitive results where possible. Do not
   resubmit unknown work. Save operation and remote task IDs.
2. Stop only the affected broker dispatcher and client writer. Take consistent
   private backups of PostgreSQL, each connection's SQLite/inbox, configuration,
   credentials and all active/previous keys. Keep records created after upgrade.
3. Install the same reviewed v0.12 wheel server-first. PostgreSQL migrations add
   nullable activity/start columns in place. Client storage identities, receipts,
   flows, SSE cursor and default paths/MCP name are preserved.
4. Restart the broker, then the default client with its unchanged environment.
   Restart recovery marks claimed work unknown; only the same saved remote handle
   may resolve it. Pending work can dispatch; claimed work must never replay.
5. Run `client-doctor`; verify TLS, authentication, peer policy, connection name
   and broker origin. Retrieve known results. Native Desktop delivery requires
   separate installed-host validation, not just fake-peer tests.
6. Add named connections only after the default works; use fresh credentials and
   keys and separate state/socket/attestation locations. See
   [connections](../guides/client-connections.md).

## Rollback

Quiesce affected writers and reinstall the reviewed v0.11 wheel. Leave additive
PostgreSQL columns and SQLite data intact; do not drop tables/columns or restore
an old backup over newer records. Old clients ignore new snapshot fields. Unset
new optional settings only after preserving their values in private backups.
Before rolling back rotation, keep tokens/keys compatible with the older wheel:
v0.11 accepts only one token/key, so outstanding ciphertext encrypted under other
keys must expire or remain accessible under the newer wheel. Never discard a key
to make rollback start. Return to v0.12 if old-key counts remain nonzero.
Named connections require explicit v0.11 STATE_DIR, hook paths and server-name
support; safest rollback is to stop those named registrations and retain their
state until the upgraded wheel is restored. Do not repoint them at default state.

## Development upgrade gate

The process suite uses the exact v0.11 baseline commit
`245b7179366f194caf7a76eeb5e87fb1ca3e864c`. Install its wheel in a separate
CPython 3.11 virtual environment and set
`HERMES_A2A_GATEWAY_TEST_LEGACY_PYTHON` to that environment's Python. With the
normal disposable PostgreSQL DSN, run `pytest tests/test_upgrade_v012.py`.
It seeds all four lifecycle cases with the actual old code, verifies receipts,
IDs and SSE cursor after in-place migration, completes pending work without
replaying running/unknown work, and exercises both old-client/new-broker and
new-client/old-broker processes. CI prepares this baseline automatically.

Connection markers reject adopting a different connection's state or hook store,
even when explicit paths collide. Unmarked v0.11 stores belong to `default`; keep
the default name during upgrade. No existing identity or ciphertext is renamed.
