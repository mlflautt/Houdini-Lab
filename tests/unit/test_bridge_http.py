"""Full client -> HTTP bridge -> interactive runtime tests."""

from __future__ import annotations

import os
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from bridge.client import Client  # noqa: E402
from bridge.server import create_server  # noqa: E402
from hermes_houdini.dispatcher import Dispatcher  # noqa: E402
from hermes_houdini.registry import REGISTRY  # noqa: E402
from hermes_houdini.runtime import InteractiveRuntime  # noqa: E402
from hermes_houdini.schemas.command import CommandEnvelope  # noqa: E402


def _client_roundtrip(
    client: Client, runtime: InteractiveRuntime, envelope: CommandEnvelope
) -> dict:
    result = {}
    errors = []

    def send() -> None:
        try:
            result.update(client.send(envelope))
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=send)
    thread.start()
    deadline = time.monotonic() + 3.0
    while thread.is_alive() and time.monotonic() < deadline:
        runtime.pump()
        thread.join(timeout=0.01)
    thread.join(timeout=0.1)
    assert not thread.is_alive(), "bridge request did not finish"
    assert not errors, errors
    return result


def test_http_bridge_persists_state_and_resumes_approved_command():
    secret = "http-bridge-test-secret"
    state = {"value": 0}

    def mutate(amount=1):
        state["value"] += amount
        return dict(state)

    REGISTRY.register("bridge.mutate", "1.0.0", mutate, risk="medium")
    runtime = InteractiveRuntime(
        secret=secret, port=0, dispatcher=Dispatcher(), request_timeout=1.0
    )
    try:
        runtime.start()
        server = create_server(
            port=0,
            secret=secret,
            mode="interactive",
            houdini_port=runtime.port,
        )
    except PermissionError:
        runtime.stop()
        pytest.skip("loopback socket binding is denied by this sandbox")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    client = Client(base_url=f"http://127.0.0.1:{server.server_address[1]}", secret=secret)
    try:
        blocked = _client_roundtrip(
            client, runtime, CommandEnvelope(tool="bridge.mutate", arguments={"amount": 4})
        )
        assert blocked["status"] == "blocked"
        assert state["value"] == 0
        approval_id = blocked["data"]["approval"]["approval_id"]

        granted = _client_roundtrip(
            client,
            runtime,
            CommandEnvelope(tool="approval.grant", arguments={"approval_id": approval_id}),
        )
        assert granted["status"] == "success"
        assert granted["data"]["value"] == 4
        assert granted["data"]["approval"]["decision"] == "granted"
        assert state["value"] == 4
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2.0)
        runtime.stop()
