"""Bridge transport: localhost server + client.

Server: binds 127.0.0.1, requires an HMAC-signed request, and dispatches a structured
envelope to the in-Houdini package. Client: signs envelopes and posts over HTTP.

Interactive mode forwards into the persistent Houdini event-loop runtime. Hython mode remains
available for isolated probes and integration jobs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from hermes_houdini.schemas.command import CommandEnvelope, Status, ToolResult

from . import __version__  # noqa: F401
from .auth import load_secret, sign, verify
from .framing import MAX_FRAME_BYTES
from .interactive import InteractiveTransportError, forward_signed_payload


def _serialize(env: dict[str, Any]) -> bytes:
    return json.dumps(env, separators=(",", ":")).encode("utf-8")


def execute_via_hython(env: dict[str, Any], hython: str = "hython") -> dict[str, Any]:
    """Run one command envelope inside Houdini via hython and return the ToolResult dict.

    Uses a tiny inline driver that imports the package, resolves the tool, and runs it.
    This keeps the Houdini surface narrow and replayable.
    """
    script = (
        "import json, sys\n"
        "from hermes_houdini.schemas.command import CommandEnvelope, ToolResult\n"
        "from hermes_houdini.dispatcher import Dispatcher\n"
        "from hermes_houdini.policy import ApprenticePolicy\n"
        "env = json.loads(sys.argv[1])\n"
        "e = CommandEnvelope.from_dict(env)\n"
        "d = Dispatcher(policy=ApprenticePolicy())\n"
        "out = d.process_one(e)\n"
        "print(json.dumps(out.result.as_dict()))\n"
    )
    proc = subprocess.run(
        [hython, "-c", script, json.dumps(env)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return {"status": "error", "errors": [proc.stderr.strip() or "hython failed"]}
    return json.loads(proc.stdout.strip().splitlines()[-1])


class _Handler(BaseHTTPRequestHandler):
    secret: str = ""
    hython: str = "hython"
    mode: str = "interactive"
    houdini_host: str = "127.0.0.1"
    houdini_port: int = 8766

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/":
            self._write_json(404, _error_result("", "endpoint not found"))
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._write_json(400, _error_result("", "invalid Content-Length"))
            return
        if length < 1 or length > MAX_FRAME_BYTES:
            self._write_json(413, _error_result("", "request body size is invalid"))
            return
        body = self.rfile.read(length)
        sig = self.headers.get("X-Hermes-Sig", "")
        if not verify(self.secret, body, sig):
            self._write_json(403, _error_result("", "invalid signature"))
            return
        request_id = ""
        try:
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("command envelope must be an object")
            envelope = CommandEnvelope.from_dict(data)
            request_id = envelope.request_id
            if not request_id:
                raise ValueError("request_id is required")
            if self.mode == "interactive":
                result = forward_signed_payload(body, sig, self.houdini_host, self.houdini_port)
            else:
                result = execute_via_hython(data, self.hython)
            self._write_json(200, result)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._write_json(400, _error_result(request_id, f"{type(exc).__name__}: {exc}"))
        except InteractiveTransportError as exc:
            self._write_json(503, _error_result(request_id, str(exc)))

    def _write_json(self, status: int, result: dict[str, Any]) -> None:
        out = json.dumps(result, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.send_header("X-Hermes-Sig", sign(self.secret, out))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args: Any) -> None:  # quiet
        pass


def _error_result(request_id: str, message: str) -> dict[str, Any]:
    result = ToolResult(request_id=request_id, status=Status.ERROR)
    result.errors.append(message)
    return result.as_dict()


def create_server(
    port: int = 8765,
    secret: str | None = None,
    hython: str = "hython",
    mode: str = "interactive",
    houdini_host: str = "127.0.0.1",
    houdini_port: int = 8766,
) -> ThreadingHTTPServer:
    if mode not in {"interactive", "hython"}:
        raise ValueError("mode must be 'interactive' or 'hython'")
    if houdini_host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Houdini runtime host must be loopback")
    secret = secret or load_secret()
    handler = type("ConfiguredHermesHandler", (_Handler,), {})
    handler.secret = secret
    handler.hython = hython
    handler.mode = mode
    handler.houdini_host = houdini_host
    handler.houdini_port = houdini_port
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def serve(
    port: int = 8765,
    secret: str | None = None,
    hython: str = "hython",
    mode: str = "interactive",
    houdini_host: str = "127.0.0.1",
    houdini_port: int = 8766,
) -> None:
    srv = create_server(
        port=port,
        secret=secret,
        hython=hython,
        mode=mode,
        houdini_host=houdini_host,
        houdini_port=houdini_port,
    )
    bound_port = int(srv.server_address[1])
    print(f"Hermes Houdini bridge listening on 127.0.0.1:{bound_port} (mode={mode})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Hermes Houdini outside-Houdini bridge")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--hython", default="hython")
    ap.add_argument("--mode", choices=("interactive", "hython"), default="interactive")
    ap.add_argument("--houdini-port", type=int, default=8766)
    args = ap.parse_args()
    serve(
        port=args.port,
        hython=args.hython,
        mode=args.mode,
        houdini_port=args.houdini_port,
    )


if __name__ == "__main__":
    main()
