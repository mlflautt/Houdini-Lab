"""Bridge client: signs command envelopes and posts them to the bridge server."""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from ..hermes_houdini.schemas.command import CommandEnvelope
from .auth import load_secret, sign


class Client:
    def __init__(self, base_url: str = "http://127.0.0.1:8765",
                 secret: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret = secret or load_secret()

    def send(self, env: CommandEnvelope) -> dict[str, Any]:
        payload = json.dumps(env.as_dict(), separators=(",", ":")).encode("utf-8")
        sig = sign(self.secret, payload)
        req = urllib.request.Request(
            self.base_url + "/",
            data=payload,
            headers={"Content-Type": "application/json", "X-Hermes-Sig": sig},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Send a command envelope to the bridge")
    ap.add_argument("--tool", required=True)
    ap.add_argument("--args", default="{}", help="JSON object of tool arguments")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    env = CommandEnvelope(tool=args.tool, arguments=json.loads(args.args))
    out = Client(base_url=f"http://127.0.0.1:{args.port}").send(env)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
