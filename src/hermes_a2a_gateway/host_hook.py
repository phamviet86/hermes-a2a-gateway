"""Host-hook attestations, not model-declared conversation identities.

The model supplies a retry key. Antigravity's PreToolUse hook binds that key and
exact arguments to its own conversationId before MCP execution. The facade has
no global/current conversation and never reads the application's chat stores.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import math
import os
import secrets
import sqlite3
import stat
import time
from pathlib import Path
from typing import Any
from uuid import UUID

ENV = "HERMES_A2A_GATEWAY_ANTIGRAVITY_BINDING_DIR"
SERVER = "hermes-a2a-gateway"
TTL = 120
MAX_BINDINGS = 100_000
MAX_DB_BYTES = 64 * 1024 * 1024
DEFAULTS: dict[str, dict[str, Any]] = {
    "gateway_submit": {"artifact_ids": None, "wait_seconds": None, "model": None},
    "gateway_get": {},
    "gateway_wait": {"timeout": 30.0},
    "gateway_cancel": {},
    "gateway_upload_artifact": {"content_type": "application/octet-stream"},
}
REQUIRED = {
    "gateway_submit": {"prompt"},
    "gateway_get": {"operation_id"},
    "gateway_wait": {"operation_id"},
    "gateway_cancel": {"operation_id"},
    "gateway_upload_artifact": {"path"},
}


class BindingError(ValueError):
    """Safe error code only; never include arguments or hook payloads."""


def normalized(tool: str, arguments: Any) -> tuple[str, dict[str, Any]]:
    if tool not in DEFAULTS or not isinstance(arguments, dict):
        raise BindingError("invalid_binding_request")
    allowed = REQUIRED[tool] | DEFAULTS[tool].keys() | {"request_key"}
    if set(arguments) - allowed or not REQUIRED[tool] <= arguments.keys():
        raise BindingError("invalid_binding_request")
    try:
        key = arguments["request_key"]
        if not isinstance(key, str) or str(UUID(key)) != key:
            raise ValueError
    except (KeyError, ValueError):
        raise BindingError("request_key_uuid_required") from None
    return key, normalized_values(tool, {k: v for k, v in arguments.items() if k != "request_key"})


def normalized_values(tool: str, arguments: Any) -> dict[str, Any]:
    """Shared canonical defaults/numeric normalization, before daemon transforms."""
    if tool not in DEFAULTS or not isinstance(arguments, dict):
        raise BindingError("invalid_binding_request")
    if set(arguments) - (REQUIRED[tool] | DEFAULTS[tool].keys()) or not REQUIRED[tool] <= arguments.keys():
        raise BindingError("invalid_binding_request")
    values = {**DEFAULTS[tool], **arguments}
    for numeric in ("wait_seconds", "timeout"):
        if numeric in values and values[numeric] is not None:
            if isinstance(values[numeric], bool) or not isinstance(values[numeric], (float, int)):
                raise BindingError("invalid_binding_request")
            values[numeric] = float(values[numeric])
    return values


def claude_values(tool: str, arguments: Any) -> dict[str, Any]:
    values = normalized_values(tool, arguments)
    for name in REQUIRED[tool]:
        value = values[name]
        if not isinstance(value, str) or not value or len(value) > (262144 if name == "prompt" else 4096):
            raise BindingError("invalid_binding_request")
    for name in ("wait_seconds", "timeout"):
        value = values.get(name)
        if value is not None and (not math.isfinite(value) or not 0 <= value <= 60):
            raise BindingError("invalid_binding_request")
    if tool == "gateway_wait" and values["timeout"] is None:
        raise BindingError("invalid_binding_request")
    model = values.get("model")
    if model is not None and (not isinstance(model, str) or not 1 <= len(model) <= 256):
        raise BindingError("invalid_binding_request")
    artifacts = values.get("artifact_ids")
    if artifacts is not None and (
        not isinstance(artifacts, list) or len(artifacts) > 16 or any(not isinstance(value, str) for value in artifacts)
    ):
        raise BindingError("invalid_binding_request")
    if "content_type" in values and not isinstance(values["content_type"], str):
        raise BindingError("invalid_binding_request")
    return values


def valid_call_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512 or any(ord(c) < 32 for c in value):
        raise BindingError("trusted_hook_identity_required")
    return value


def private_file(path: Path) -> None:
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o600:
        raise BindingError("unsafe_binding_storage")


class Bindings:
    def __init__(self, directory: Path | None = None, *, profile: str = "antigravity"):
        self.directory = directory or Path(
            os.environ.get(ENV, str(Path.home() / ".local/state/hermes-a2a-gateway/antigravity"))
        )
        if not self.directory.is_absolute():
            raise BindingError("unsafe_binding_storage")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = self.directory.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o700:
            raise BindingError("unsafe_binding_storage")
        marker = self.directory / "host-profile"
        if profile == "claude":
            # Never reinterpret an existing Antigravity registry as Claude state.
            if not marker.exists() and (self.directory / "bindings.sqlite3").exists():
                raise BindingError("binding_profile_conflict")
            try:
                fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(b"claude\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            private_file(marker)
            if marker.read_bytes() != b"claude\n":
                raise BindingError("binding_profile_conflict")
        elif profile != "antigravity" or marker.exists():
            raise BindingError("binding_profile_conflict")
        key_path = self.directory / "attestation.key"
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as stream:
                stream.write(secrets.token_bytes(32))
                stream.flush()
                os.fsync(stream.fileno())
        private_file(key_path)
        with os.fdopen(os.open(key_path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
            self.key = stream.read()
        if len(self.key) != 32:
            raise BindingError("unsafe_binding_storage")
        db_path = self.directory / "bindings.sqlite3"
        with contextlib.suppress(FileExistsError):
            os.close(os.open(db_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600))
        private_file(db_path)
        self.db = sqlite3.connect(db_path, timeout=5, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        page_size = self.db.execute("PRAGMA page_size").fetchone()[0]
        self.db.execute(f"PRAGMA max_page_count={MAX_DB_BYTES // page_size}")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS bindings (request_key TEXT PRIMARY KEY, "
            "conversation TEXT NOT NULL, tool TEXT NOT NULL, digest TEXT NOT NULL, "
            "step INTEGER NOT NULL, expires REAL NOT NULL)"
        )

    def close(self) -> None:
        self.db.close()

    def digest(self, tool: str, values: dict[str, Any]) -> str:
        raw = json.dumps([tool, values], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hmac.new(self.key, raw, hashlib.sha256).hexdigest()

    def attest(self, conversation: str, step: int, tool: str, arguments: Any) -> None:
        try:
            if str(UUID(conversation)) != conversation or type(step) is not int or step < 0:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise BindingError("trusted_hook_identity_required") from None
        key, values = normalized(tool, arguments)
        digest = self.digest(tool, values)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute(
                "SELECT conversation,tool,digest FROM bindings WHERE request_key=?", (key,)
            ).fetchone()
            if old and (old[0] != conversation or old[1] != tool or not hmac.compare_digest(old[2], digest)):
                raise BindingError("request_key_owner_or_content_conflict")
            if not old and self.db.execute("SELECT COUNT(*) FROM bindings").fetchone()[0] >= MAX_BINDINGS:
                raise BindingError("binding_quota_exceeded")
            self.db.execute(
                "INSERT INTO bindings VALUES(?,?,?,?,?,?) ON CONFLICT(request_key) "
                "DO UPDATE SET step=excluded.step,expires=excluded.expires",
                (key, conversation, tool, digest, step, time.time() + TTL),
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def origin(self, tool: str, arguments: Any) -> dict[str, Any]:
        key, values = normalized(tool, arguments)
        old = self.db.execute(
            "SELECT conversation,tool,digest,expires FROM bindings WHERE request_key=?", (key,)
        ).fetchone()
        if (
            not old
            or old[1] != tool
            or not hmac.compare_digest(old[2], self.digest(tool, values))
            or old[3] < time.time()
        ):
            raise BindingError("fresh_host_hook_attestation_required")
        # A retry key is a stable adapter call/turn ID, not a claimed native turn ID.
        return {"x-hermes-turn-metadata": {"conversation_id": old[0], "turn_id": key, "call_id": key}}


CLAUDE_TTL = 300
PRUNE_AFTER = 24 * 60 * 60


class ClaudeBindings(Bindings):
    """Single-use host-call attestations in a separate profile registry."""

    def __init__(self, directory: Path | None = None):
        directory = directory or Path(
            os.environ.get(
                "HERMES_A2A_GATEWAY_CLAUDE_BINDING_DIR",
                str(Path.home() / ".local/state/hermes-a2a-gateway/claude"),
            )
        )
        super().__init__(directory, profile="claude")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            columns = {row[1] for row in self.db.execute("PRAGMA table_info(bindings)")}
            if "consumed" not in columns:
                self.db.execute("ALTER TABLE bindings ADD COLUMN consumed REAL")
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            self.close()
            raise

    def attest_call(self, conversation: str, call: str, tool: str, arguments: Any) -> None:
        try:
            if not isinstance(conversation, str) or str(UUID(conversation)) != conversation:
                raise ValueError
        except ValueError:
            raise BindingError("trusted_hook_identity_required") from None
        call = valid_call_id(call)
        digest = self.digest(tool, claude_values(tool, arguments))
        now = time.time()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            # Re-presenting a retained call ID never renews or reassigns it.
            if self.db.execute("SELECT 1 FROM bindings WHERE request_key=?", (call,)).fetchone():
                raise BindingError("host_call_already_attested")
            self.db.execute(
                "DELETE FROM bindings WHERE expires < ? OR consumed < ?",
                (now - PRUNE_AFTER, now - PRUNE_AFTER),
            )
            if self.db.execute("SELECT COUNT(*) FROM bindings").fetchone()[0] >= MAX_BINDINGS:
                raise BindingError("binding_quota_exceeded")
            self.db.execute(
                "INSERT INTO bindings(request_key,conversation,tool,digest,step,expires,consumed) "
                "VALUES(?,?,?,?,0,?,NULL)",
                (call, conversation, tool, digest, now + CLAUDE_TTL),
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def consume(self, call: str, tool: str, arguments: Any) -> dict[str, Any]:
        call = valid_call_id(call)
        digest = self.digest(tool, claude_values(tool, arguments))
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute(
                "SELECT conversation,tool,digest,expires,consumed FROM bindings WHERE request_key=?", (call,)
            ).fetchone()
            now = time.time()
            if (
                not old
                or old[1] != tool
                or not hmac.compare_digest(old[2], digest)
                or old[3] <= now
                or old[4] is not None
            ):
                raise BindingError("fresh_host_hook_attestation_required")
            self.db.execute("UPDATE bindings SET consumed=? WHERE request_key=?", (now, call))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return {"x-hermes-turn-metadata": {"conversation_id": old[0], "turn_id": call, "call_id": call}}


def claude_denial() -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Gateway requires fresh host attestation of this exact request.",
        }
    }


def claude_hook(payload: Any) -> dict[str, Any] | None:
    from .host_profiles import ClaudeProfile

    try:
        request = ClaudeProfile().parse(payload)
        if request is not None:
            conversation, call, tool, arguments = request
            bindings = ClaudeBindings()
            try:
                bindings.attest_call(conversation, call, tool, arguments)
            finally:
                bindings.close()
        return None  # Keep the normal host permission flow; never auto-allow.
    except (ValueError, TypeError, AttributeError, OSError, sqlite3.Error, RecursionError, OverflowError):
        return claude_denial()


def hook(payload: Any) -> dict[str, str]:
    try:
        from .host_profiles import AntigravityProfile

        request = AntigravityProfile().parse(payload)
        if request is None:
            return {"decision": "ask"}
        conversation, step, tool, arguments = request
        bindings = Bindings()
        try:
            bindings.attest(conversation, step, tool, arguments)
        finally:
            bindings.close()
        return {"decision": "ask"}
    except (ValueError, TypeError, AttributeError, OSError, sqlite3.Error):
        return {
            "decision": "deny",
            "reason": "Gateway requires a unique retry key attested by this conversation's host hook.",
        }


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Native gateway host attestation hook")
    parser.add_argument("--profile", choices=["antigravity", "claude"], default="antigravity")
    profile = parser.parse_args().profile

    os.umask(0o077)
    try:
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError
        answer = claude_hook(json.loads(raw)) if profile == "claude" else hook(json.loads(raw))
    except (ValueError, OSError, RecursionError):
        answer = (
            claude_denial() if profile == "claude" else {"decision": "deny", "reason": "Invalid gateway hook input."}
        )
    if answer is not None:
        print(json.dumps(answer))


if __name__ == "__main__":
    main()
