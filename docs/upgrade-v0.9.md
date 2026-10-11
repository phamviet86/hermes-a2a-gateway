# Upgrade 0.8 → 0.9 without replacing data or identities

Use [fresh installation](deployment.md) if no gateway is installed. Existing users
keep the same CPython 3.11 venv path, configuration, credentials, state directories,
PostgreSQL database, device IDs, contexts and MCP registration. Install into the
independent gateway environment; never into Hermes's environment. The public
release contains immutable wheel/source/patch/checksum assets, not runtime data.

1. Download **every asset** from the [v0.9.0 release](https://github.com/phamviet86/hermes-a2a-gateway/releases/tag/v0.9.0)
   into a private directory and verify `SHA256SUMS` with `shasum -a 256 -c` on macOS
   or `sha256sum --check` on Linux. Retain the original wheel/patch assets too.
2. Inspect active/uncertain operations, reconcile exact saved IDs, and stop only
   the affected canonical gateway services in an idle maintenance window. Stop
   the client writer before copying SQLite; verify its writer lock is released.
   Do not interpret a transport timeout as proof a writer stopped.
3. Back up the old gateway venv at its original path, launchers/units and protected
   configuration opaquely, preserving modes and symlinks. With writers stopped,
   make a consistent SQLite backup and PostgreSQL dump, plus Hermes session/history
   snapshots and only the receiver files to be changed. Keep keys separately
   protected (0700 directories, 0600 secret/state files); never print or hash them.
   Record nonsecret source/asset hashes and existing operation/flow/delivery/cursor
   metadata for before/after comparison. A reconstructed runtime is not a pristine
   prechange snapshot; identify its source wheel and preserved patches explicitly.
4. Update the supported receiver first, while stopped. For Hermes `490e6b5`, use
   the default manifest/patch with `hermes_patch.py`. If the old 0.8 patch is already
   applied, revert it using the matching **old** assets before applying the new
   default patch. Preserve unrelated changes; never force a conflicting patch.
   For the exact tested, already-patched `722bced` receiver, select the overlay:

   ```bash
   python3 hermes_patch.py check --root "$HERMES_CHECKOUT" \
     --manifest hermes-a2a-sender-722bced.json --patch hermes-a2a-sender-722bced.patch
   python3 hermes_patch.py apply --root "$HERMES_CHECKOUT" \
     --manifest hermes-a2a-sender-722bced.json --patch hermes-a2a-sender-722bced.patch
   ```

   The overlay's `original_sha256` means its exact pre-overlay patched baseline,
   not pristine upstream. Other revisions/hashes require a reviewed narrow port.
5. Install the same verified release wheel in broker and client gateway venvs:

   ```bash
   "$GATEWAY_VENV/bin/python" -m pip install --upgrade "$RELEASE_DIR/hermes_a2a_gateway-0.9.0-py3-none-any.whl"
   "$GATEWAY_VENV/bin/hermes-a2a-gateway" --version
   ```

   Keep the venv at its actual path. Migrations add nullable descriptor columns and
   indexes; they do not rewrite IDs, payload keys, legacy digests or session mappings.
6. Start the receiver and wait for **full native startup**, not only an open A2A
   port. Then start one broker dispatcher and one client writer; keep proxy/tunnel
   credentials unchanged. Run `client-doctor`, inspect database-backed readiness,
   and compare the saved nonsecret metadata. On the tested newer Hermes build,
   an A2A call during startup restore completed empty before its queued reply;
   do not use that port-open condition as readiness or replay an uncertain call.
7. Reload MCP connections in the caller application to load the new facade/schema.
   Preserve the same conversation. If a custom launcher scrubs gateway environment
   variables, retain only trusted per-registration `CLIENT_HARNESS`,
   `CLIENT_HARNESS_INSTANCE`, `CLIENT_MODEL` in addition to state/upload limits for
   `client-mcp`. Never pass broker/device secrets into the MCP process. Default
   Codex needs no extra harness environment. Non-Codex hosts must supply genuine
   `x-hermes-turn-metadata`; a static MCP registration alone is insufficient.
8. Retrieve a known operation first, then run bounded harmless new acceptance
   requests: three fields, family default/explicit override, same-flow recall,
   wrong-harness denial. Save the exact returned operation/result/task IDs before
   waiting. Never repeat submits to recover an unknown result.

## Rollback

Quiesce and stop the same writers. Revert **only** the selected receiver delta
using its matching manifest/patch (or restore verified prechange source files),
restore the gateway code/venv at its original path, and restore only owned launcher
changes. Retain additive nullable columns/indexes; older code ignores them.
Keep current stores, keys and all post-upgrade work. Do not restore an old whole
SQLite/PostgreSQL/session backup over newer operations. Full disaster recovery
needs a separately reconciled plan for newer work. Restart and repeat readiness
and exact-ID reads. Retain the newer code snapshot privately for investigation.

A failed PostgreSQL connection stops admission/dispatch; the production entry point
exits nonzero so a supervisor configured with `Restart=on-failure` recreates its
connection and singleton lock. Restart marks claimed work unknown and reconciles
saved handles; it never automatically replays an ambiguous send. Without a service
supervisor, the operator restarts the broker. Retained no-handle uncertainty pauses
its flow and counts toward admission by design. Resolve from authoritative upstream
execution evidence or obtain an explicit user decision for separate new work;
never erase it or rotate conversations automatically to evade the safety boundary.

Payload retention clears sensitive data; compact identity/receipt records remain
for deduplication. Their metadata footprint can grow. This release is a bounded,
single-owner Unix deployment, not an unbounded multi-tenant archival service.
