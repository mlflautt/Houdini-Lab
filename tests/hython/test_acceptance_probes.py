from __future__ import annotations

import json

import pytest
from hermes_houdini.acceptance.compatibility import probe_compatibility

BOX_EXPECTATION = {
    "expectation_id": "builtin-box-h22.0.368",
    "context": "SOP",
    "category": "Sop",
    "operator_type": "box",
    "required_parameters": {
        "type": {"type": "Menu", "default": 0},
        "size": {"type": "Float", "default": [1.0, 1.0, 1.0]},
        "t": {"type": "Float", "default": [0.0, 0.0, 0.0]},
    },
    "optional_parameters": {
        "consolidatepts": {"type": "Toggle", "default": True},
        "divrate": {"type": "Int", "default": [4, 4, 4]},
        "divs": {"type": "Int", "default": [3, 3, 3]},
        "dodivs": {"type": "Toggle", "default": False},
        "orderrate": {"type": "Int", "default": [4, 4, 4]},
        "orientedbbox": {"type": "Toggle", "default": False},
        "r": {"type": "Float", "default": [0.0, 0.0, 0.0]},
        "rebar": {"type": "Toggle", "default": False},
        "scale": {"type": "Float", "default": [1.0]},
        "surftype": {"type": "Menu", "default": 4},
        "vertexnormals": {"type": "Toggle", "default": False},
    },
    "tested_build_range": {"minimum": "22.0.368", "maximum": "22.0.368"},
}


pytestmark = pytest.mark.skipif(
    __import__("importlib").util.find_spec("hou") is None,
    reason="requires Houdini's Python runtime",
)


def test_read_only_probe_matches_builtin_box_without_scene_mutation() -> None:
    import hou

    before = {
        "frame": hou.frame(),
        "hip": hou.hipFile.path(),
        "nodes": tuple(node.path() for node in hou.node("/").allSubChildren()),
    }

    result = probe_compatibility(BOX_EXPECTATION)

    after = {
        "frame": hou.frame(),
        "hip": hou.hipFile.path(),
        "nodes": tuple(node.path() for node in hou.node("/").allSubChildren()),
    }
    assert result["status"] == "pass"
    assert result["live_build"] == "22.0.368"
    assert result["license"] == "Apprentice"
    assert result["mutation_performed"] is False
    assert after == before


def test_deliberate_live_mismatch_is_human_readable_and_deterministic() -> None:
    mismatch = dict(BOX_EXPECTATION)
    mismatch["required_parameters"] = {
        **BOX_EXPECTATION["required_parameters"],
        "removed_legacy_divisions": {"type": "Int", "default": [2, 2, 2]},
        "size": {"type": "Int", "default": [2, 2, 2]},
    }

    first = probe_compatibility(mismatch)
    second = probe_compatibility(mismatch)

    assert first == second
    assert first["status"] == "blocked"
    messages = [item["message"] for item in first["diffs"]]
    assert messages[:3] == [
        "box is missing required parameter removed_legacy_divisions "
        "(expected Int default [2, 2, 2])",
        "box.size type drift: expected Int, observed Float",
        "box.size default drift: expected [2, 2, 2], observed [1.0, 1.0, 1.0]",
    ]


def test_probe_writes_only_when_output_path_is_explicit(tmp_path) -> None:
    output = tmp_path / "box-probe.json"

    result = probe_compatibility(BOX_EXPECTATION, output_path=output)

    assert json.loads(output.read_text(encoding="utf-8")) == result
    with pytest.raises(FileExistsError):
        probe_compatibility(BOX_EXPECTATION, output_path=output)
