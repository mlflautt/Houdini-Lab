"""Persistent authenticated command runtime hosted inside interactive Houdini.

Socket threads authenticate and enqueue plain command envelopes. Only :meth:`pump`, called
from Houdini's event loop, invokes the dispatcher and therefore HOM-mutating tool handlers.
"""

from __future__ import annotations

import base64
import binascii
import json
import queue
import re
import socketserver
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from bridge.auth import verify
from bridge.framing import recv_frame, send_frame

from .dispatcher import Dispatcher
from .schemas.command import CommandEnvelope, Status, ToolResult


@dataclass
class PendingCall:
    request_id: str
    event: threading.Event = field(default_factory=threading.Event)
    state: str = "pending"
    result: dict[str, Any] | None = None


class RequestBroker:
    """Thread-safe pending-result routing with bounded replay protection."""

    def __init__(self, replay_ttl_seconds: float = 300.0, max_pending: int = 256) -> None:
        self.replay_ttl_seconds = replay_ttl_seconds
        self.max_pending = max_pending
        self._calls: dict[str, PendingCall] = {}
        self._recent: dict[str, float] = {}
        self._lock = threading.Lock()

    def submit(self, request_id: str) -> PendingCall:
        if not request_id:
            raise ValueError("request_id is required on the interactive channel")
        if len(request_id) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]+", request_id):
            raise ValueError("request_id contains invalid characters or is too long")
        with self._lock:
            self._purge_locked()
            if request_id in self._calls or request_id in self._recent:
                raise ValueError(f"duplicate or replayed request_id: {request_id}")
            if len(self._calls) >= self.max_pending:
                raise RuntimeError("interactive request queue is full")
            call = PendingCall(request_id=request_id)
            self._calls[request_id] = call
            return call

    def begin(self, request_id: str) -> bool:
        with self._lock:
            call = self._calls.get(request_id)
            if call is None:
                if request_id in self._recent:
                    return False  # cancelled or already completed network request
                return True  # locally enqueued command with no socket waiter
            if call.state != "pending":
                return False
            call.state = "executing"
            return True

    def complete(self, request_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            call = self._calls.pop(request_id, None)
            if call is None:
                return
            call.state = "done"
            call.result = result
            self._recent[request_id] = time.monotonic() + self.replay_ttl_seconds
            call.event.set()

    def cancel_if_pending(self, request_id: str) -> bool:
        with self._lock:
            call = self._calls.get(request_id)
            if call is None or call.state != "pending":
                return False
            self._calls.pop(request_id)
            call.state = "cancelled"
            self._recent[request_id] = time.monotonic() + self.replay_ttl_seconds
            call.event.set()
            return True

    def _purge_locked(self) -> None:
        now = time.monotonic()
        expired = [request_id for request_id, expiry in self._recent.items() if expiry <= now]
        for request_id in expired:
            self._recent.pop(request_id, None)


class _RuntimeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], runtime: InteractiveRuntime) -> None:
        self.runtime = runtime
        super().__init__(address, _RuntimeHandler)


class _RuntimeHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        runtime: InteractiveRuntime = self.server.runtime  # type: ignore[attr-defined]
        self.request.settimeout(runtime.request_timeout + 5.0)
        try:
            request = recv_frame(self.request)
            response = runtime.handle_request(request)
        except Exception as exc:
            response = _error_result("", f"{type(exc).__name__}: {exc}")
        send_frame(
            self.request,
            json.dumps(response, separators=(",", ":")).encode("utf-8"),
        )


class InteractiveRuntime:
    def __init__(
        self,
        secret: str,
        host: str = "127.0.0.1",
        port: int = 8766,
        dispatcher: Dispatcher | None = None,
        request_timeout: float = 120.0,
    ) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("interactive runtime must bind to loopback")
        if not secret:
            raise ValueError("interactive runtime secret is required")
        self.secret = secret
        self.host = host
        self.port = port
        self.dispatcher = dispatcher or Dispatcher()
        self.dispatcher.bridge_mode = "authenticated-loopback"
        self.request_timeout = request_timeout
        self.broker = RequestBroker()
        self._server: _RuntimeServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> int:
        if self._server is not None:
            return int(self._server.server_address[1])
        self._server = _RuntimeServer((self.host, self.port), self)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="hermes-houdini-listener",
            daemon=True,
        )
        self._thread.start()
        self.port = int(self._server.server_address[1])
        return self.port

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._thread is not None and self._thread.is_alive()

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=2.0)
        self.dispatcher.bridge_mode = "local-dispatcher"

    def handle_request(self, request: bytes) -> dict[str, Any]:
        request_id = ""
        try:
            wrapper = json.loads(request.decode("utf-8"))
            if not isinstance(wrapper, dict):
                raise ValueError("request wrapper must be an object")
            signature = str(wrapper.get("signature", ""))
            payload = base64.b64decode(str(wrapper.get("payload_b64", "")), validate=True)
            if not verify(self.secret, payload, signature):
                raise PermissionError("invalid interactive signature")
            data = json.loads(payload.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("command envelope must be an object")
            envelope = CommandEnvelope.from_dict(data)
            request_id = envelope.request_id
            call = self.broker.submit(request_id)
            self.dispatcher.enqueue(envelope)
            if not call.event.wait(self.request_timeout):
                if self.broker.cancel_if_pending(request_id):
                    return _error_result(request_id, "request timed out before execution")
                return {
                    "request_id": request_id,
                    "status": Status.PARTIAL.value,
                    "errors": ["request is still executing; do not retry this request_id"],
                }
            return call.result or _error_result(request_id, "request completed without a result")
        except (
            ValueError,
            TypeError,
            PermissionError,
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            return _error_result(request_id, f"{type(exc).__name__}: {exc}")

    def pump(self, max_commands: int = 4) -> int:
        """Execute queued commands; call only from Houdini's main event loop."""
        processed = 0
        for _ in range(max_commands):
            try:
                envelope = self.dispatcher.queue.get_nowait()
            except queue.Empty:
                break
            if not self.broker.begin(envelope.request_id):
                continue
            outcome = self.dispatcher.process_one(envelope)
            self.broker.complete(envelope.request_id, outcome.result.as_dict())
            processed += 1
        return processed


def _error_result(request_id: str, message: str) -> dict[str, Any]:
    result = ToolResult(request_id=request_id, status=Status.ERROR)
    result.errors.append(message)
    return result.as_dict()


__all__ = ["InteractiveRuntime", "PendingCall", "RequestBroker"]
