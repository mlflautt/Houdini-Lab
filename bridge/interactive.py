"""Outside-Houdini client for the authenticated interactive runtime channel."""

from __future__ import annotations

import base64
import json
import socket
from typing import Any

from .framing import recv_frame, send_frame


class InteractiveTransportError(RuntimeError):
    """Raised when the active Houdini runtime cannot be reached or decoded."""


def forward_signed_payload(
    payload: bytes,
    signature: str,
    host: str = "127.0.0.1",
    port: int = 8766,
    timeout: float = 130.0,
) -> dict[str, Any]:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise InteractiveTransportError("interactive runtime host must be loopback")
    wrapper = json.dumps(
        {
            "payload_b64": base64.b64encode(payload).decode("ascii"),
            "signature": signature,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            send_frame(sock, wrapper)
            response = recv_frame(sock)
        decoded = json.loads(response.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise InteractiveTransportError("interactive runtime returned a non-object")
        return decoded
    except (OSError, ValueError, EOFError, json.JSONDecodeError) as exc:
        raise InteractiveTransportError(f"interactive runtime unavailable: {exc}") from exc


__all__ = ["InteractiveTransportError", "forward_signed_payload"]
