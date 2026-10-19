# Hermes A2A Gateway v0.12.0

One workstation can run named connections, one daemon per broker. Each has
separate credentials, state, socket and hook registry. Default paths, MCP name,
flow IDs and harness identity semantics remain compatible with v0.11. Explicit
path overrides cannot adopt another connection's stores. Every application tool
result identifies its connection; doctor/instructions show a sanitized origin.

`gateway_list` recovers operation IDs in the calling trusted conversation without
broker access or delivery consumption. Submit once, then get/wait; never replay
an unknown outcome or uncertain native delivery.

Long-running snapshots add nullable last peer activity, running start and elapsed
seconds through additive PostgreSQL migrations. Stream activity writes are
bounded to once per 30 seconds. Streams still drain to a terminal event.
Receiver reply timeout diagnostics prefer structured reasons; exact sentinel
fallback requires an explicitly verified compat commit. Startup/readiness warn
when broker/receiver budgets have less than 30 seconds of margin.

Input references now allow UTF-8 text/plain, text/markdown, text/csv and valid
application/json. Upload types are inferred only when omitted. Existing quotas,
size limits and untrusted-reference framing remain. Binary inputs are unsupported.

Device token overlap and MultiFernet previous keys support staged rotation.
Count-only readiness/doctor reports distinguish old-key usage and unreadable
ciphertext. Restarts are required; there is no zero-downtime process handoff.
Retain old keys until every relevant ciphertext expires/purges, including replay
events and results, and keep keys for backups separately.

The CI matrix tests Python 3.11–3.13 on Linux/macOS, and PostgreSQL on 3.11/3.13.
All eight jobs passed on the implementation commit
[e693390](https://github.com/phamviet86/hermes-a2a-gateway/actions/runs/39196761281)
before extending release support to CPython 3.11–3.13. Installation and wheel
checks now enforce Python requirements normally. No dependency lower bound was raised.

See [quickstart](guides/quickstart.md), [connections](guides/client-connections.md),
[rotation](guides/rotation.md), [operations](guides/ai-operations.md) and
[upgrade/rollback](upgrades/upgrade-v0.12.md). Fake-peer/process/wheel tests are
separate from live Hermes, Desktop consumption, macOS CI and release provenance.
Live host deployment remains a separate operator action. Release automation builds
and publishes only the exact commit that passes the main-branch CI matrix.

Historical reports/history are unchanged. Ten already-broken historical relative
links remain recorded by the link checker; no new broken links are permitted.
