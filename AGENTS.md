# Repository guidance

Read this file before changing code, tests, documentation, packaging or release metadata.
It is the entry point for AI agents: §1–2 orient you, §3–4 are binding rules,
§5–6 say how to validate and ship.

## 1. Mission and current contract

`hermes-a2a-gateway` connects local agent harnesses (Codex Desktop and an explicit
native Antigravity and Claude Code Desktop hook integrations) to a private Hermes server ("Helen") using MCP,
a local SQLite client daemon, authenticated HTTPS/SSE, a PostgreSQL broker and
loopback Hermes A2A. Direct and daemon-managed SSH tunnel transports are supported.
The only public commands are `broker`, `client`, `client-mcp`, and `client-doctor`.

```text
Harness (Codex / Antigravity) -- MCP --> client daemon + SQLite inbox
                          | direct HTTPS or HTTPS inside daemon-owned SSH tunnel
                     TLS proxy --> broker + PostgreSQL -- loopback A2A --> Hermes
```

The operator explicitly authorized the v0.7 breaking rename and removal of all
legacy gateway modes, executable aliases, setup skills and Hermes client plugin.
Do not restore `serve`, the inbound Codex gateway, CLI backend, seven `hermes_*`
tools or old configuration aliases. Historical evidence is not current setup guidance.

Canonical distribution, executable and MCP registration: `hermes-a2a-gateway`.
Python namespace: `hermes_a2a_gateway`. Configuration uses `HERMES_A2A_GATEWAY_*`;
`HERMES_A2A_ENDPOINT` and `HERMES_A2A_TOKEN` configure the server's Hermes peer.

## 2. Where to look

### Repository layout

| Path | Contents |
| --- | --- |
| `src/hermes_a2a_gateway/` | Package source (ownership in §3) |
| `tests/` | Pytest suite; fake A2A peer in `fake_a2a.py`; PostgreSQL tests need a DSN (§5) |
| `scripts/` | Release, dist/wheel checks, compat staging, Hermes patch tool, app-server schema check |
| `compat/hermes/` | Exact-commit Hermes receiver patches and vendored fixtures (§4) |
| `docs/` | Documentation; start at [docs/README.md](docs/README.md) |
| `README.md`, `README.vi.md` | User-facing summary (English / Vietnamese) |
| `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, `.env.example` | Release log, threat boundaries, contribution rules, configuration reference |

### Documentation layout

| Folder | Purpose | Editable? |
| --- | --- | --- |
| `docs/guides/` | Install/operate (`deployment.md`, `*.vi.md` server/client/SSH guides, `ai-operations.md`) | Yes, keep in sync with code |
| `docs/reference/` | Normative contracts: `client-server-contract.md`, `multi-harness.md`, `sender-context.md`, `antigravity.md`, `hermes-compatibility.md` | Yes, change with code |
| `docs/upgrades/` | Version migration/upgrade/rollback | Yes, for the named versions |
| `docs/proposals/` | Designs not yet implemented; status in `docs/proposals/README.md` | Yes; not current behavior |
| `docs/reports/` | Dated verification reports and reviews (v0.7+) | **No** — immutable evidence |
| `docs/history/` | ≤v0.6 releases, retired modes, investigations | **No** — immutable evidence |
| `docs/release-notes.md` | Current release notes; path is read by `scripts/publish_release.py` | Yes, per release |

### Pending work (proposals)

Unimplemented designs live in `docs/proposals/`, and
[docs/proposals/README.md](docs/proposals/README.md) is the only status list. Read it
when asked about planned work. Implement a proposal only when the operator
explicitly authorizes that proposal (or a named phase) in the current task;
`approved` status alone is not authorization. Follow its phases and gates, record
decisions with the operator, and update the status row as work progresses.

`docs/worker-context-*.md` are private, git-ignored orchestration notes; never
commit, package or link them.

### Read first, by task

| Task | Read |
| --- | --- |
| Any change | This file, [README](README.md), [docs/README.md](docs/README.md) |
| Client ↔ broker protocol, IDs, idempotence, SSE | [client-server-contract](docs/reference/client-server-contract.md) |
| Harness isolation, host metadata, new harness | [multi-harness](docs/reference/multi-harness.md), [sender-context](docs/reference/sender-context.md), [antigravity](docs/reference/antigravity.md) |
| Planned work, e.g. unified MCP / Claude Code integration | [proposals status](docs/proposals/README.md), then the named proposal |
| Hermes receiver patch / `compat/hermes` | [hermes-compatibility](docs/reference/hermes-compatibility.md) |
| Deployment, install, SSH | [deployment](docs/guides/deployment.md), [server](docs/guides/server-hermes.vi.md), [Codex client](docs/guides/client-codex.vi.md), [Antigravity client](docs/guides/client-antigravity.vi.md), [SSH](docs/guides/ssh-tunnel.vi.md) |
| Upgrades, data preservation, rollback | [upgrade-v0.9](docs/upgrades/upgrade-v0.9.md), [migration-v0.7](docs/upgrades/migration-v0.7.md) |
| Agent tool usage semantics | [ai-operations](docs/guides/ai-operations.md) |

## 3. Ownership and invariants

Module ownership (`src/hermes_a2a_gateway/`):

- `broker*.py`: PostgreSQL ledger, authenticated API, loopback Hermes dispatch.
- `client*.py`: single-writer SQLite inbox, MCP facade and transport lifecycle.
- `host_identity.py`, `host_hook.py`, `host_profiles.py`: shared provenance providers and native hook registries.
- `antigravity_*.py`: compatible aliases for the native Antigravity hook and MCP facade;
  see [docs/reference/antigravity.md](docs/reference/antigravity.md).
- `ssh_tunnel.py`: client-owned SSH process, strict authentication, retry and cleanup.
- `native_delivery.py`: `NativeOrigin` identity validation and version/schema-gated
  native queue delivery.
- `sender_context.py`: descriptive sender labels only; never routing identity.
- `a2a.py`, `settings.py`, `models.py`: internal loopback peer protocol transport.
- `cli.py`: the four public commands; `diagnostics.py`: `client-doctor` reporting.

Invariants:

- MCP stdout contains protocol frames only; diagnostics go to stderr.
- No model-supplied URL, SSH target, credential or execution identity. Native origin
  comes from trusted host MCP metadata or an exact-request native Antigravity or Claude Desktop
  hook attestation; a retry key is never sufficient identity by itself. Reject missing
  or inconsistent provenance.
- Verify TLS and SSH host keys, retain device bearer authentication inside tunnels,
  bind local forwards to loopback, and never invoke SSH through shell interpolation.
  Only the daemon owns its tunnel; never kill unrelated SSH processes or services.
- Broker requires HTTPS at a trusted proxy for remote deployment. Hermes remains
  loopback-only. Development loopback HTTP is explicit and never a remote fallback.
- Secret inputs come from protected environment injection. Never log, echo or commit
  tokens, keys, prompt payloads, private configuration or raw authentication errors.
  Native/SSH child environments must scrub both new and historical secret prefixes.
- Payload encryption keys stay outside stores. Enforce retention, restrictive modes
  and quotas. Results/artifacts/backups can also be sensitive.
- Retry network connectivity with bounds and backoff, not ambiguous agent work.
  Reconcile Hermes mutations only by exact saved task identity. Preserve
  `outcome_unknown` when evidence is insufficient. Native queue insertion is not
  idempotent; uncertain acknowledgement remains `delivery_outcome_unknown` and
  must not be blindly re-enqueued. Queue ACK does not prove Desktop consumption.
- Cancellation is best-effort; never claim upstream computation stopped without proof.
- Preserve A2A v1 shapes; do not add the legacy stream `final` field.
- Preserve per-flow serialization, bounded admission, one broker dispatcher and one
  active client writer per SQLite file. Do not run old/new daemons on the same inbox.
- v0.6 client and broker data survive the rename. Preserve `broker_v06_*` schema,
  the peer context UUID namespace, device/flow/native origin IDs, operation/result/
  delivery IDs, receipts, cursor, ciphertext and keys. Additive migrations only.
  Legacy SQLite data is archived, not interpreted as a modern inbox or discarded.
- Harness isolation keys on `(harness, instance, conversation)`. Keep the default
  `codex/default` storage IDs and the `harness:` storage-key format unchanged.
- Explicit submit waits support 0–60 seconds; the configured inline wait is the
  default, not an undisclosed smaller ceiling. Reject invalid arguments clearly
  before persistence or dispatch, without exposing submitted content.

## 4. Hermes compatibility assets

`compat/hermes` owns the exact-commit upstream patch and licensed test fixtures.
Do not format or modify vendored originals; their hashes are compatibility gates.
`A2A_GATEWAY_TOKEN` is a protected Hermes-side policy selector, not a substitute
for existing remote authentication or trust checks. Preserve peer/context/session identities. Validate
structured diagnostics; never place arbitrary peer text into plaintext error columns.
Stage compatibility assets with `scripts/stage_compat_assets.py` before writing
release checksums. Package tests must exercise the patch offline against pinned source.

## 5. Development and validation

1. Inspect `git status` and preserve unrelated user changes.
2. Use CPython 3.11–3.13 and the project virtual environment; keep lint/type targets at the minimum 3.11.
3. Keep work scoped. Add regression tests for protocol, persistence, authentication,
   timeouts, idempotence, cancellation, restart, tunnel lifecycle and network policy.
4. Update README, `.env.example`, relevant docs and CHANGELOG for public changes.
   Place docs by the layout in §2; keep [docs/README.md](docs/README.md) current.
5. Historical reports are immutable evidence; add dated reports to `docs/reports/`
   for new live results.

Run from the repository root:

```bash
.venv/bin/python -m compileall -q src tests scripts
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src
.venv/bin/pytest --cov=hermes_a2a_gateway --cov-report=term-missing
```

The full coverage gate requires `HERMES_A2A_GATEWAY_TEST_POSTGRES_DSN` pointing to
an isolated disposable PostgreSQL 16 database. CI runs the full suite with PostgreSQL;
macOS/Linux also run portable tests and clean-wheel installation. Do not lower the
full-suite coverage gate merely because PostgreSQL is absent locally.

```bash
build_dir=$(mktemp -d)
.venv/bin/python -m build --outdir "$build_dir"
.venv/bin/python -m twine check "$build_dir"/*
.venv/bin/python scripts/check_dist.py "$build_dir"
.venv/bin/python scripts/check_wheel_install.py "$build_dir"/*.whl
.venv/bin/python scripts/write_sha256sums.py "$build_dir"
.venv/bin/python scripts/write_sha256sums.py --check "$build_dir"
```

Native protocol changes also require `scripts/check_app_server_schema.py` against
the supported local Codex CLI. Live model tasks are opt-in, uniquely identified,
harmless, authorized by the operator, and never run in CI. Simulated reconnect tests
do not prove real machine sleep/wake or native Desktop consumption.

## 6. Completion and release

Relevant tests, clean wheel and CI pass. The diff contains no private files, runtime
stores, logs, credentials or stale artifacts. Documentation matches implemented limits.
Publish immutable release assets from the exact successful main/push CI commit.
Install and verify downloaded release artifacts on both hosts; report provenance and
actual end-to-end evidence separately from package/transport checks.

Removal/upgrade plans identify exact owned installations, back up data and keys,
check interpreter dependencies, stop writers before consistent copy, and preserve a
rollback path. Do not remove Hermes, Codex, PostgreSQL, provider authentication,
unrelated SSH tunnels, user workspaces or shared runtimes as gateway cleanup.
