"""Pure-Python unit tests — run WITHOUT Houdini (pytest tests/unit)."""
from __future__ import annotations

import os
import sys

# Make repo root importable
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from hermes_houdini.dispatcher import Dispatcher  # noqa: E402
from hermes_houdini.ids import ctx_code, make_id, tag_kwargs  # noqa: E402
from hermes_houdini.policy import ApprenticePolicy, default_policy  # noqa: E402
from hermes_houdini.registry import REGISTRY, Registry  # noqa: E402
from hermes_houdini.schemas.command import (  # noqa: E402
    CommandEnvelope,
    RiskClass,
    Status,
)


def test_command_roundtrip():
    env = CommandEnvelope(tool="node.create", arguments={"a": 1}, request_id="r1")
    d = env.as_dict()
    assert d["tool"] == "node.create"
    assert d["policy"]["risk"] == "low"
    env2 = CommandEnvelope.from_dict(d)
    assert env2.tool == "node.create"
    assert env2.arguments["a"] == 1


def test_policy_render_ceiling():
    p = ApprenticePolicy()
    assert p.validate_render_resolution(1280, 720)[0] is True
    assert p.validate_render_resolution(1920, 1080)[0] is False


def test_policy_path_denied_by_default():
    p = ApprenticePolicy()  # no roots
    assert p.is_path_allowed("/Users/m1/Desktop/x") is False


def test_policy_path_allowed_with_root(tmp_path):
    p = default_policy([str(tmp_path)])
    assert p.check_path(str(tmp_path / "out.hipnc"))[0] is True
    assert p.check_path("/etc/passwd")[0] is False


def test_policy_arbitrary_code_blocked_in_safe():
    p = ApprenticePolicy()
    ok, msg = p.validate_operation(RiskClass.HIGH, __import__(
        "hermes_houdini.schemas.command", fromlist=["CodeMode"]).CodeMode.SAFE, True)
    assert ok is False


def test_stable_id_deterministic():
    a = make_id("Sop", "obj/HERMES_ASSET/SRC")
    b = make_id("Sop", "obj/HERMES_ASSET/SRC")
    assert a == b
    assert a.startswith("HOU-SOP-")


def test_ctx_code():
    assert ctx_code("Sop") == "SOP"
    assert ctx_code("Lop") == "LOP"
    assert ctx_code("Obj") == "OBJ"


def test_tag_kwargs():
    t = tag_kwargs("hero", created_by="skill:x@1")
    assert t["hermes_role"] == "hero"


def test_registry_resolve_latest():
    r = Registry()
    r.register("t", "1.0.0", lambda: 1, kind="tool")
    r.register("t", "1.2.0", lambda: 2, kind="tool")
    assert r.resolve("t").version == "1.2.0"
    assert r.resolve("t", "1.0.0").version == "1.0.0"


def test_dispatcher_blocks_unknown_tool():
    d = Dispatcher(policy=ApprenticePolicy())
    env = CommandEnvelope(tool="does.not.exist", request_id="x")
    out = d.process_one(env)
    assert out.result.status == Status.BLOCKED
    assert out.result.errors


def test_dispatcher_blocks_medium_risk_approval():
    d = Dispatcher(policy=ApprenticePolicy())
    # register a medium-risk tool
    def risky(**kw):
        return {"ok": True}
    REGISTRY.register("risky.op", "1.0.0", risky, kind="tool", risk="medium")
    env = CommandEnvelope(tool="risky.op", request_id="r")
    out = d.process_one(env)
    assert out.result.status == Status.BLOCKED
    assert "approval" in out.result.errors[0].lower()


def test_dispatcher_executes_low_risk_tool():
    d = Dispatcher(policy=ApprenticePolicy())
    REGISTRY.register("safe.op", "1.0.0", lambda x=1: {"v": x}, kind="tool", risk="low")
    env = CommandEnvelope(tool="safe.op", arguments={"x": 7}, request_id="r")
    out = d.process_one(env)
    assert out.result.status == Status.SUCCESS
    assert out.result.data["v"] == 7
