"""Key overlap diagnostics return counts only, never key identity or plaintext."""

from collections.abc import Iterable

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


def key_usage(current: Fernet, cipher: MultiFernet, previous: int, values: Iterable[bytes]) -> dict[str, int]:
    old = unreadable = 0
    for value in values:
        try:
            current.decrypt(bytes(value))
        except InvalidToken:
            try:
                cipher.decrypt(bytes(value))
            except InvalidToken:
                unreadable += 1
            else:
                old += 1
    return {"previous_keys": previous, "payloads_using_previous_keys": old, "unreadable_payloads": unreadable}
