# Structured receiver reply timeout diagnostics

Status: proposed, not implemented. The pinned compat receiver currently returns
plain-text timeout sentinels. A future exact-commit receiver patch could emit the
existing diagnostics extension with reason `peer_reply_timeout`,
recommended_action `contact_operator`, and no claim that execution stopped.
Preserve authentication, peer identity, stream draining and task ownership.
No receiver change or new patch is part of v0.12. The gateway accepts the bounded
reason and uses exact sentinel fallback only with an operator-pinned compat commit.
