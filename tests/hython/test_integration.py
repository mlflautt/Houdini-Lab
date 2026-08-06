"""hython integration tests. Require Houdini (`hou`). Skipped otherwise."""
from __future__ import annotations

import pytest

hou = pytest.importorskip("hou")

from hermes_houdini.dispatcher import Dispatcher  # noqa: E402
from hermes_houdini.policy import ApprenticePolicy  # noqa: E402
from hermes_houdini.schemas.command import CommandEnvelope  # noqa: E402
from hermes_houdini.tools import REGISTRY  # noqa: E402  (registers tools)
from hermes_houdini.transactions import next_checkpoint_path  # noqa: E402


def test_registry_has_tools():
    tools = REGISTRY.list(kind="tool")
    names = {t.name for t in tools}
    assert "node.create" in names
    assert "hip.describe" in names


def test_create_node_and_describe():
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_TEST_GEO")
    d = Dispatcher(policy=ApprenticePolicy())
    env = CommandEnvelope(tool="node.create", request_id="t1",
                          arguments={"parent_path": geo.path(),
                                      "operator_type": "box",
                                      "name": "SRC_BOX", "category": "Sop",
                                      "role": "test"})
    out = d.process_one(env)
    assert out.result.status.value == "success"
    assert out.result.data["type"] == "box"
    geo.destroy()


def test_checkpoint_path_increment(tmp_path):
    base = str(tmp_path / "shot_v001.hipnc")
    p1 = next_checkpoint_path(base)
    assert p1.endswith("_v001.hipnc") or p1.endswith("v001.hipnc")
