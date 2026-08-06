"""Session auth helpers: secrets + HMAC signing for the bridge transport."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

__all__ = ["BridgeError", "load_secret", "make_secret", "sign", "verify"]


class BridgeError(Exception):
    pass


def make_secret() -> str:
    """Generate a new session secret (store out of repo; gitignored)."""
    return secrets.token_hex(32)


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def sign(secret: str, payload: bytes) -> str:
    return hmac.new(_derive_key(secret), payload, hashlib.sha256).hexdigest()


def verify(secret: str, payload: bytes, signature: str) -> bool:
    expected = sign(secret, payload)
    return hmac.compare_digest(expected, signature)


def load_secret(env_var: str = "HERMES_HOUDINI_BRIDGE_SECRET") -> str:
    val = os.environ.get(env_var, "")
    if not val:
        raise BridgeError(f"{env_var} not set")
    return val
