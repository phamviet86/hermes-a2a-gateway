# Rotate device tokens and payload keys

Use protected environment injection and a private configuration editor. Never put
credentials in prompts, command-line arguments, logs or committed files. Back up
current and previous keys with their stores. Operate one affected connection at a
time; never copy a key/token between connections.

## Device bearer tokens

1. Provision a new distinct token (at least 32 characters) for the same device.
2. Change that broker device's `HERMES_A2A_GATEWAY_BROKER_DEVICE_TOKENS` value
   from a string to `[old_token, new_token]` in protected configuration. Each
   device accepts 1–2 tokens; every token must be distinct, including within a list.
3. Restart only that broker. Both credentials now authenticate as the same device;
   the application never logs which token matched.
4. Update only the affected client's protected token and restart that daemon.
   Verify `client-doctor` and read a known operation without submitting work.
5. Remove the old token from broker configuration and restart it. A single string
   remains valid. Confirm the old credential is rejected through an authorized,
   bounded authentication check.

Overlap avoids credential mismatch across the rollout. Broker/client restarts
still interrupt streams; there is no live reload or process handoff. Observe
saved IDs after reconnect, and never replay ambiguous work. This does not promise
zero process downtime.

## Payload keys

Set the new key as current and retain the old current key in the corresponding
comma-separated previous-key setting:

| Store | Current | Previous |
| --- | --- | --- |
| Broker | `HERMES_A2A_GATEWAY_BROKER_ENCRYPTION_KEY` | `HERMES_A2A_GATEWAY_BROKER_PREVIOUS_ENCRYPTION_KEYS` |
| One client | `HERMES_A2A_GATEWAY_CLIENT_PAYLOAD_KEY` | `HERMES_A2A_GATEWAY_CLIENT_PREVIOUS_PAYLOAD_KEYS` |

Restart the affected process. `MultiFernet([current, *previous])` encrypts new
content with current and decrypts with any configured key. No IDs, ciphertexts,
receipts or cursors are rewritten; there is no re-encryption job.

Monitor broker `/healthz.key_rotation` and `client-doctor`'s daemon key report.
`previous_keys` counts configured old keys; `payloads_using_previous_keys` counts
retained ciphertext objects which authenticate/decrypt only with an old key.
`unreadable_payloads` must be zero. These reports contain counts only.
When the daemon is unavailable doctor cannot verify stored usage counts.

Wait for expiry/purge and a zero usage count before removing old keys. Broker
results and replay events can outlive input payloads (defaults seven days versus
one); sender descriptors and client retained descriptors must also be considered.
The shortest payload TTL alone is not sufficient. Existing expired ciphertext
may remain until the dispatcher/client purge runs. Verify counts again after
purge and before dropping any key. Preserve keys for retained backups separately;
a zero live-store count says nothing about backup decryption.

Never delete a key while retained payloads still need it. Never replace keys to
fix an authentication error. Never test a rotation on production as part of an
unreviewed code upgrade. See [upgrade/rollback](../upgrades/upgrade-v0.12.md).
