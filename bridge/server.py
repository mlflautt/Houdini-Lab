"""Bridge transport: localhost server + client.

Server: binds 127.0.0.1, requires HMAC signature, validates envelope, dispatches to the
in-Houdini package. Client: signs envelopes, posts over HTTP, verifies responses.

For local single-machine use, the server can shell out to `hython` to run a command and
return JSON, OR talk to an in-Houdini HTTP listener (started by scripts/123.py). Here we
implement the HMAC + envelope layer and a hython subprocess executor so it works headless.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from . import __version__  # noqa: F401
from .auth import load_secret, verify


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
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        return {"status": "error", "errors": [proc.stderr.strip() or "hython failed"]}
    return json.loads(proc.stdout.strip().splitlines()[-1])


class _Handler(BaseHTTPRequestHandler):
    secret: str = ""
    hython: str = "hython"

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        sig = self.headers.get("X-Hermes-Sig", "")
        if not verify(self.secret, body, sig):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"invalid signature")
            return
        env = json.loads(body.decode("utf-8"))
        result = execute_via_hython(env, self.hython)
        out = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args: Any) -> None:  # quiet
        pass


def serve(port: int = 8765, secret: str | None = None, hython: str = "hython") -> None:
    secret = secret or load_secret()
    _Handler.secret = secret
    _Handler.hython = hython
    srv = HTTPServer(("127.0.0.1", port), _Handler)
    print(f"Hermes Houdini bridge listening on 127.0.0.1:{port}")
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
    args = ap.parse_args()
    serve(port=args.port, hython=args.hython)


if __name__ == "__main__":
    main()
