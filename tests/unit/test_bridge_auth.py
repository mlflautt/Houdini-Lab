"""Bridge auth unit tests (no Houdini)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from bridge.auth import BridgeError, make_secret, sign, verify  # noqa: E402


def test_sign_verify_roundtrip():
    secret = make_secret()
    payload = b'{"tool":"node.create"}'
    sig = sign(secret, payload)
    assert verify(secret, payload, sig) is True
    assert verify(secret, payload + b"x", sig) is False
    assert verify("wrong", payload, sig) is False


def test_load_secret_missing(monkeypatch):
    monkeypatch.delenv("HERMES_HOUDINI_BRIDGE_SECRET", raising=False)
    import bridge.auth as auth
    try:
        auth.load_secret()
    except BridgeError:
        pass
    else:
        raise AssertionError("expected BridgeError")
