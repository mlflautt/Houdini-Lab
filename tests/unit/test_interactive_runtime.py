"""Persistent authenticated runtime tests without Houdini."""

from __future__ import annotations

import json
import os
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from bridge.auth import sign  # noqa: E402
from bridge.interactive import forward_signed_payload  # noqa: E402
from hermes_houdini.dispatcher import Dispatcher  # noqa: E402
from hermes_houdini.registry import REGISTRY  # noqa: E402
from hermes_houdini.runtime import InteractiveRuntime, RequestBroker  # noqa: E402
from hermes_houdini.schemas.command import CommandEnvelope  # noqa: E402


def _roundtrip(runtime: InteractiveRuntime, secret: str, envelope: CommandEnvelope) -> dict:
    payload = json.dumps(envelope.as_dict(), separators=(",", ":")).encode()
    result = {}
    error = []

    def send() -> None:
        try:
            result.update(
                forward_signed_payload(
                    payload, sign(secret, payload), port=runtime.port, timeout=2.0
                )
            )
        except Exception as exc:  # surfaced in the test thread
            error.append(exc)

    thread = threading.Thread(target=send)
    thread.start()
    deadline = time.monotonic() + 2.0
    while thread.is_alive() and time.monotonic() < deadline:
        runtime.pump()
        thread.join(timeout=0.01)
    thread.join(timeout=0.1)
    assert not thread.is_alive(), "interactive request did not finish"
    assert not error, error
    return result


def _start_or_skip(runtime: InteractiveRuntime) -> None:
    try:
        runtime.start()
    except PermissionError:
        pytest.skip("loopback socket binding is denied by this sandbox")


def test_request_broker_rejects_unsafe_request_ids():
    broker = RequestBroker()
    for request_id in ("../escape", "contains spaces", "x" * 129):
        with pytest.raises(ValueError):
            broker.submit(request_id)


def test_sequential_commands_share_runtime_and_replays_are_rejected():
    secret = "runtime-test-secret"
    state = {"value": 0}

    def increment(amount=1):
        state["value"] += amount
        return dict(state)

    REGISTRY.register("runtime.increment", "1.0.0", increment, risk="low")
    runtime = InteractiveRuntime(
        secret=secret, port=0, dispatcher=Dispatcher(), request_timeout=1.0
    )
    _start_or_skip(runtime)
    try:
        first_env = CommandEnvelope(
            tool="runtime.increment", request_id="runtime-1", arguments={"amount": 2}
        )
        first = _roundtrip(runtime, secret, first_env)
        second = _roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="runtime.increment", request_id="runtime-2", arguments={"amount": 3}
            ),
        )
        replay = _roundtrip(runtime, secret, first_env)
        assert first["data"]["value"] == 2
        assert second["data"]["value"] == 5
        assert replay["status"] == "error"
        assert "replayed" in replay["errors"][0]
        assert state["value"] == 5
    finally:
        runtime.stop()


def test_interactive_runtime_rejects_invalid_signature():
    runtime = InteractiveRuntime(secret="correct", port=0, request_timeout=0.2)
    _start_or_skip(runtime)
    try:
        envelope = CommandEnvelope(tool="approval.list", request_id="bad-signature")
        payload = json.dumps(envelope.as_dict(), separators=(",", ":")).encode()
        result = forward_signed_payload(payload, "bad", port=runtime.port, timeout=1.0)
        assert result["status"] == "error"
        assert "signature" in result["errors"][0]
    finally:
        runtime.stop()


def test_timed_out_pending_request_is_not_executed_later():
    secret = "timeout-secret"
    state = {"executions": 0}

    def mutate():
        state["executions"] += 1
        return dict(state)

    REGISTRY.register("runtime.timeout_mutate", "1.0.0", mutate, risk="low")
    runtime = InteractiveRuntime(secret=secret, port=0, request_timeout=0.05)
    _start_or_skip(runtime)
    try:
        envelope = CommandEnvelope(tool="runtime.timeout_mutate", request_id="runtime-timeout")
        payload = json.dumps(envelope.as_dict(), separators=(",", ":")).encode()
        result = forward_signed_payload(
            payload, sign(secret, payload), port=runtime.port, timeout=1.0
        )
        assert result["status"] == "error"
        assert "before execution" in result["errors"][0]
        assert runtime.pump() == 0
        assert state["executions"] == 0
    finally:
        runtime.stop()
