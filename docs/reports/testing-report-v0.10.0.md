# v0.10.0 verification scope

The Antigravity adapter adds a separate native hook/facade without replacing Codex
identity or the existing0.9 broker protocol. Full local candidate validation used
isolated PostgreSQL16:290 passed,1 opt-in test skipped,83.58% coverage. Lint,
format, types, compile, native Codex schema, wheel/sdist safety, clean-wheel install
and compatibility checksum gates passed. Release CI rechecks the exact main commit
on Linux/macOS and PostgreSQL; publication only follows successful CI.

Actual Antigravity2.22.0 candidate acceptance used two native conversations with
concurrent requests. Helen returned correct three-field labels and separate
markers/flows. Exact retry retained the original operation/task. A foreign get,
wait and cancel were rejected, and foreign retry-key reuse was denied by the
host hook. The app's actual Gemini3.8FlashMedium → ClaudeOpus4.6(Thinking) switch
kept the original conversation/flow and recalled its earlier marker without that
marker in the new prompt. Model labels remain descriptive.

These are candidate app observations, distinct from final installed release
checks. Reopening after established context has not yet been accepted: the Mac
locked, and the user deferred that check to their own workstation. The final
release requires app restart to load the new facade/schema; every Antigravity
tool requires request_key. No native push delivery or Windows support is claimed.
See [Antigravity setup](client-antigravity.vi.md) and [boundaries](antigravity.md).

Upgrade/rollback preserves stores, credentials and IDs. Existing receiver overlays
are unchanged. Host-specific operation IDs, private backups and final installation
receipts belong in external host records, not the public distribution.
