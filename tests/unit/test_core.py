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
    Policy,
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
    assert env2.as_dict()["policy"]["max_memory_bytes"] == 536_870_912


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


def test_policy_path_resolves_symlinks_before_allowlisting(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    escape = allowed / "escape"
    escape.symlink_to("/etc")
    p = default_policy([str(allowed)])
    assert p.check_path(str(escape / "passwd"))[0] is False


def test_policy_arbitrary_code_blocked_in_safe():
    p = ApprenticePolicy()
    ok, msg = p.validate_operation(
        RiskClass.HIGH,
        __import__("hermes_houdini.schemas.command", fromlist=["CodeMode"]).CodeMode.SAFE,
        True,
    )
    assert ok is False


def test_registered_external_tool_reaches_exact_approval_gate(tmp_path):
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    outcome = dispatcher.process_one(
        CommandEnvelope(
            tool="render.karma.preview",
            arguments={
                "rop_path": "/out/MANAGED_PREVIEW",
                "output_path": str(tmp_path / "preview.png"),
                "log_path": str(tmp_path / "preview.jsonl"),
            },
            policy=Policy(allow_external_process=True, risk=RiskClass.EXTERNAL),
        )
    )
    assert outcome.result.status == Status.BLOCKED
    assert outcome.result.data["approval"]["risk"] == "external"


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


def test_registry_numeric_versions_do_not_sort_lexically():
    registry = Registry()
    registry.register("recipe", "1.2.0", lambda: 1, kind="recipe")
    registry.register("recipe", "1.10.0", lambda: 2, kind="recipe")
    assert registry.resolve("recipe").version == "1.10.0"


def test_bundled_recipe_and_hda_catalogs_are_discoverable_and_gated(tmp_path):
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    described = dispatcher.process_one(
        CommandEnvelope(
            tool="recipe.describe",
            request_id="describe-relic-recipe",
            arguments={"recipe_id": "sop.fractal_relic_candidate"},
        )
    )
    assert described.result.status == Status.SUCCESS
    assert described.result.data["version"] == "2.0.0"
    assert described.result.data["meta"]["contexts"] == ["SOP"]

    recipe = REGISTRY.resolve("sop.fractal_relic_candidate")
    fragment = recipe.handler(
        parent_path="/obj/RELIC",
        inputs={"candidate_code": "A"},
        ref_prefix="test_",
        position_offset=[0.0, 0.0],
    )
    assert fragment["outputs"] == {"out": "test_out", "compare": "test_compare"}

    blocked_recipe = dispatcher.process_one(
        CommandEnvelope(
            tool="recipe.instantiate",
            request_id="instantiate-recipe",
            arguments={
                "recipe_id": "sop.fractal_relic_candidate",
                "parent_path": "/obj/RELIC",
                "batch_id": "recipe-test",
                "checkpoint_dir": str(tmp_path / "checkpoints"),
                "log_path": str(tmp_path / "recipe.jsonl"),
            },
        )
    )
    assert blocked_recipe.result.status == Status.BLOCKED
    assert blocked_recipe.result.data["approval"]["risk"] == "medium"

    blocked_hda = dispatcher.process_one(
        CommandEnvelope(
            tool="hda.build_registered",
            request_id="build-hda",
            arguments={
                "hda_id": "hermes::fractal_relic",
                "dest_dir": str(tmp_path / "hda"),
            },
        )
    )
    assert blocked_hda.result.status == Status.BLOCKED
    assert REGISTRY.resolve("hermes::fractal_relic").meta["engine_export_allowed"] is False


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
    assert out.result.data["approval"]["approval_id"]


def test_dispatcher_grants_medium_risk_once():
    calls = []

    def risky(**kw):
        calls.append(kw)
        return {"executed": True}

    REGISTRY.register("approval.test", "1.0.0", risky, kind="tool", risk="medium")
    dispatcher = Dispatcher(policy=ApprenticePolicy())
    blocked = dispatcher.process_one(
        CommandEnvelope(
            tool="approval.test", request_id="approval-original", arguments={"value": 7}
        )
    )
    approval_id = blocked.result.data["approval"]["approval_id"]
    granted = dispatcher.process_one(
        CommandEnvelope(
            tool="approval.grant",
            request_id="approval-grant",
            arguments={"approval_id": approval_id},
        )
    )
    assert granted.result.status == Status.SUCCESS
    assert granted.result.request_id == "approval-original"
    assert granted.result.data["approval"]["decision"] == "granted"
    assert calls == [{"value": 7}]

    replay = dispatcher.process_one(
        CommandEnvelope(
            tool="approval.grant",
            request_id="approval-replay",
            arguments={"approval_id": approval_id},
        )
    )
    assert replay.result.status == Status.ERROR
    assert calls == [{"value": 7}]


def test_dispatcher_denies_pending_approval():
    REGISTRY.register(
        "approval.deny_test",
        "1.0.0",
        lambda: {"executed": True},
        kind="tool",
        risk="medium",
    )
    dispatcher = Dispatcher(policy=ApprenticePolicy())
    blocked = dispatcher.process_one(
        CommandEnvelope(tool="approval.deny_test", request_id="deny-original")
    )
    approval_id = blocked.result.data["approval"]["approval_id"]
    pending = dispatcher.process_one(
        CommandEnvelope(tool="approval.list", request_id="approval-list")
    )
    assert pending.result.data["pending"][0]["approval_id"] == approval_id

    denied = dispatcher.process_one(
        CommandEnvelope(
            tool="approval.deny",
            request_id="approval-deny",
            arguments={"approval_id": approval_id},
        )
    )
    assert denied.result.data["decision"] == "denied"
    assert dispatcher.approvals.describe() == []


def test_dispatcher_executes_low_risk_tool():
    d = Dispatcher(policy=ApprenticePolicy())
    REGISTRY.register("safe.op", "1.0.0", lambda x=1: {"v": x}, kind="tool", risk="low")
    env = CommandEnvelope(tool="safe.op", arguments={"x": 7}, request_id="r")
    out = d.process_one(env)
    assert out.result.status == Status.SUCCESS
    assert out.result.data["v"] == 7


def test_dispatcher_bootstraps_builtin_tools():
    Dispatcher(policy=ApprenticePolicy())
    names = {entry.name for entry in REGISTRY.list(kind="tool")}
    assert "system.capabilities" in names
    assert "node.create" in names
    assert "graph.apply_batch" in names
    assert "cook.job.submit" in names
    assert "cook.job.run" in names
    assert "geometry.validate" in names
    assert "graph.capture_svg" in names
    assert "viewport.capture" in names


def test_command_rejects_unknown_protocol_version():
    data = CommandEnvelope(tool="hip.describe").as_dict()
    data["protocol_version"] = "99.0"
    try:
        CommandEnvelope.from_dict(data)
    except ValueError as exc:
        assert "unsupported protocol_version" in str(exc)
    else:
        raise AssertionError("expected ValueError")
