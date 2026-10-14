# Unified MCP Phase 1 local verification — 2026-10-14

Request **A2A-20261014-005 / attempt 1**. Phase 1 implementation and local checks
complete; Phases 0, 2 and release remain incomplete. Base commit
`a304d0144599bbb18ca80a82b4e660dadcc9c178`; changes are uncommitted in the existing
checkout. The pre-existing staged documentation/configuration reorganization was
preserved. This report does not claim CI or release acceptance.

## Implementation

- `host_identity.py`: provider interface, operator configuration validation,
  metadata providers and exact-request Antigravity provider.
- `client_mcp.py`: common transport and facade with the established schema templates;
  startup selects metadata or hook schema. Antigravity wrappers resolve attestation
  in a worker thread before forwarding or opening upload files. Lost-ACK recovery
  retains the resolved original metadata.
- `host_hook.py` and `host_profiles.py`: shared registry/entrypoint and native
  Antigravity envelope parsing. No registry migration, schema, TTL, directory,
  key ownership, HMAC normalization or permission-decision changes.
- `antigravity_mcp.py` and `antigravity_binding.py`: compatible module aliases.
- `tests/test_host_identity.py` and `tests/fixtures/mcp-v010.json`: additive
  configuration, full schema/instruction snapshots, entrypoint and v0.10 registry
  compatibility coverage. Existing tests were not edited.
- README, environment example, changelog, reference docs and proposal status identify
  the changes as unreleased and keep Claude unavailable.

## Local validation

CPython 3.11.16, macOS; disposable Homebrew PostgreSQL **16.15** cluster with only
an isolated Unix socket, no TCP listener. The cluster was stopped after testing.

| Gate | Result |
| --- | --- |
| compileall src/tests/scripts | Passed |
| Ruff check / format | Passed (105 Python files formatted) |
| mypy src | Passed, 22 source files |
| Full pytest with disposable PostgreSQL | **310 passed, 1 skipped**, 79.29 s |
| Branch coverage | **83.51%**, required 65% unchanged |
| Codex app-server schema | Passed against local supported CLI |
| Build sdist and wheel | Passed |
| twine / distribution content | Passed |
| Clean wheel installation | Passed, MCP discovery and metadata refusal |
| Stage pinned compatibility assets | Passed |
| Write and verify SHA256SUMS | Passed |
| Git diff whitespace check | Passed |

Package validation used the unchanged **0.10.0 version field** in a scratch output
directory; these are local test builds, not v0.10.0 release replacements and not
v0.11.0 candidates. No assets were published or installed into live services.
The exact wheel SHA-256 was `d6ce04cfc147663e85a29d2ee8320e4396c75e67d035edb5c498b75f212c492a`.

## Live evidence and remaining gates

The [CLI spike](claude-code-identity-spike-2026-10-14.md) could not execute because
the standalone bundled Claude Code reported not logged in. Subsequently, native
Claude Desktop UI inspection found an existing Code session, so the CLI failure
must not be interpreted as proving Desktop lacks authentication.

A separate new-session folder chooser was opened for the scratch project. The
native UI automation did not complete folder selection: the Go to Folder sheet
repeatedly returned to `/` on Return/Escape, despite showing the correct scratch
path after text entry. No prompt was submitted and no new Code session was started.
The chooser may remain open and can be dismissed manually. No existing Code
conversation was edited or messaged. Both scratch MCP and hook configurations were
removed again. No probe event file exists, and no gateway/Hermes call was made.

**Phase 0 remains unpassed**: zero observed hook/MCP joins or argument hashes;
resume, fork, clear, compaction, concurrent sessions, subagents and delayed approval
are unrun. D2/D3 therefore remain unresolved. A normal CLI login, or a working
Desktop scratch-session selection with verified probe-only configuration, is needed
before resuming the full matrix. D1 shared flow, D4 300 seconds single-use and D5
excluded remain settled decisions.

**Phase 2 is not implemented. Phase 3 is not complete.** No live Codex/Antigravity
acceptance against the changed package, CI push/commit, PR, release publication,
or downloaded-release installation has been claimed or performed. The full
proposal cannot be marked implemented or released until those gates pass.
