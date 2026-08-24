"""Bounded length-prefixed framing shared by the bridge and Houdini runtime."""

from __future__ import annotations

import socket
import struct

MAX_FRAME_BYTES = 1_048_576
_HEADER = struct.Struct("!I")


def send_frame(sock: socket.socket, payload: bytes) -> None:
    if not payload or len(payload) > MAX_FRAME_BYTES:
        raise ValueError(f"frame size must be between 1 and {MAX_FRAME_BYTES} bytes")
    sock.sendall(_HEADER.pack(len(payload)) + payload)


def recv_frame(sock: socket.socket) -> bytes:
    header = _recv_exact(sock, _HEADER.size)
    size = _HEADER.unpack(header)[0]
    if size < 1 or size > MAX_FRAME_BYTES:
        raise ValueError(f"invalid frame size: {size}")
    return _recv_exact(sock, size)


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise EOFError("connection closed before frame completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


__all__ = ["MAX_FRAME_BYTES", "recv_frame", "send_frame"]
