"""Bridge client: signs command envelopes and posts them to the bridge server."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from dataclasses import replace
from typing import Any

from hermes_houdini.schemas.command import CommandEnvelope

from .auth import BridgeError, load_secret, sign, verify


class Client:
    def __init__(self, base_url: str = "http://127.0.0.1:8765", secret: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret = secret or load_secret()

    def send(self, env: CommandEnvelope) -> dict[str, Any]:
        if not env.request_id:
            env = replace(env, request_id=uuid.uuid4().hex)
        payload = json.dumps(env.as_dict(), separators=(",", ":")).encode("utf-8")
        sig = sign(self.secret, payload)
        req = urllib.request.Request(
            self.base_url + "/",
            data=payload,
            headers={"Content-Type": "application/json", "X-Hermes-Sig": sig},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(req, timeout=180)
        except urllib.error.HTTPError as exc:
            response = exc
        with response as resp:
            body = resp.read()
            response_signature = resp.headers.get("X-Hermes-Sig", "")
            if not verify(self.secret, body, response_signature):
                raise BridgeError("bridge response signature is missing or invalid")
            result = json.loads(body.decode("utf-8"))
            if not isinstance(result, dict):
                raise BridgeError("bridge response must be a JSON object")
            return result


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Send a command envelope to the bridge")
    action = ap.add_mutually_exclusive_group(required=True)
    action.add_argument("--tool")
    action.add_argument("--approve", metavar="APPROVAL_ID")
    action.add_argument("--deny", metavar="APPROVAL_ID")
    action.add_argument("--list-approvals", action="store_true")
    ap.add_argument("--args", default="{}", help="JSON object of tool arguments")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if args.approve:
        env = CommandEnvelope(tool="approval.grant", arguments={"approval_id": args.approve})
    elif args.deny:
        env = CommandEnvelope(tool="approval.deny", arguments={"approval_id": args.deny})
    elif args.list_approvals:
        env = CommandEnvelope(tool="approval.list")
    else:
        env = CommandEnvelope(tool=args.tool, arguments=json.loads(args.args))
    out = Client(base_url=f"http://127.0.0.1:{args.port}").send(env)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
