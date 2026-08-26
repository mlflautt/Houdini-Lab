"""Live Hython coverage for G001-B fixtures and tier separation."""

from __future__ import annotations

from pathlib import Path

import hou
import pytest
from hermes_houdini.acceptance.fixtures import CREATED_BY
from hermes_houdini.acceptance.hython_tiers import (
    TINY_CEILINGS,
    run_frame_range_tier,
    run_graph_edit_tier,
    run_hython_read_tier,
    run_karma_tier,
    run_pdg_child_tier,
    run_simulation_tier,
    run_single_frame_tier,
    run_viewport_tier,
)


@pytest.fixture(autouse=True)
def _restore_shared_hython_session():
    original_frame = float(hou.frame())
    yield
    for root_path in ("/out", "/stage", "/tasks", "/obj"):
        root = hou.node(root_path)
        for node in reversed(root.children() if root is not None else ()):  # top-level ownership
            if node.userData("hermes_created_by") == CREATED_BY and node.parent() is not None:
                node.destroy()
    hou.setFrame(original_frame)


def _budget(**overrides):
    return {**TINY_CEILINGS, **overrides}


def _build(tmp_path: Path):
    suffix = tmp_path.name[-16:].replace("-", "_")
    return run_graph_edit_tier(
        artifact_root=str(tmp_path / "fixture"),
        budget=_budget(),
        fixture_name=f"G001B_{suffix}",
    )


def test_graph_edit_builds_readable_tagged_source_without_forced_cook(tmp_path):
    result = _build(tmp_path)
    assert result["status"] == "pass", result["errors"]
    observed = result["observed"]
    assert observed["cook_scope"] == "none"
    assert observed["forced_cook"] is False
    assert Path(observed["scene_path"]).suffix == ".hipnc"
    assert Path(observed["scene_path"]).is_file()
    assert hou.node(observed["output_node_path"]).name() == "OUT_GEO"
    assert hou.node(observed["simulation_node_path"]).name() == "OUT_SIM"
    assert all(
        node["hermes_id"] and node["hermes_role"] and node["hermes_created_by"]
        for node in observed["managed_nodes"]
    )


def test_graph_edit_refuses_existing_artifact_root(tmp_path):
    root = tmp_path / "used"
    root.mkdir()
    result = run_graph_edit_tier(artifact_root=str(root), budget=_budget(), fixture_name="UNUSED_NAME")
    assert result["status"] == "blocked"
    assert "must be unused" in result["errors"][0]


def test_read_only_preserves_dirty_state_and_frame(tmp_path):
    built = _build(tmp_path)["observed"]
    node = hou.node(built["output_node_path"])
    before = node.needsToCook()
    frame = float(hou.frame())
    result = run_hython_read_tier(node_path=node.path(), budget=_budget())
    assert result["status"] == "pass"
    assert node.needsToCook() == before
    assert float(hou.frame()) == frame
    assert result["observed"]["cook_scope"] == "none"


def test_read_only_missing_node_is_actionably_blocked():
    result = run_hython_read_tier(node_path="/obj/DOES_NOT_EXIST", budget=_budget())
    assert result["status"] == "blocked"
    assert "node not found" in result["errors"][0]


def test_single_frame_cooks_only_one_frame_and_restores_state(tmp_path):
    built = _build(tmp_path)["observed"]
    hou.setFrame(17)
    result = run_single_frame_tier(node_path=built["output_node_path"], frame=3, budget=_budget())
    assert result["status"] == "pass", result["errors"]
    assert result["observed"]["frames"] == [3.0]
    assert result["observed"]["cook_scope"] == "one_frame"
    assert result["observed"]["frame_after"] == 17.0
    assert result["observed"]["frame_metrics"][0]["points"] == 8


def test_frame_range_is_distinct_bounded_and_restores_state(tmp_path):
    built = _build(tmp_path)["observed"]
    hou.setFrame(19)
    result = run_frame_range_tier(
        node_path=built["output_node_path"], frames=[1, 2, 3], budget=_budget()
    )
    assert result["status"] == "pass", result["errors"]
    assert result["observed"]["cook_scope"] == "frame_range"
    assert len(result["observed"]["frame_metrics"]) == 3
    assert result["observed"]["frame_after"] == 19.0


def test_frame_range_refuses_more_than_eight_frames(tmp_path):
    built = _build(tmp_path)["observed"]
    result = run_frame_range_tier(
        node_path=built["output_node_path"], frames=list(range(1, 10)), budget=_budget()
    )
    assert result["status"] == "blocked"
    assert "exceeds budget.max_frames" in result["errors"][0]


def test_budget_refuses_values_above_frozen_ceiling():
    result = run_hython_read_tier(
        node_path="/obj", budget=_budget(max_points=TINY_CEILINGS["max_points"] + 1)
    )
    assert result["status"] == "blocked"
    assert "frozen ceiling" in result["errors"][0]


def test_pdg_child_requires_explicit_external_process_authorization(tmp_path):
    built = _build(tmp_path)["observed"]
    result = run_pdg_child_tier(
        pdg_node_path=built["pdg_node_path"], output_path=built["pdg_output_path"],
        budget=_budget(), authorized=False,
    )
    assert result["status"] == "blocked"
    assert not Path(built["pdg_output_path"]).exists()


def test_simulation_requires_explicit_authorization_and_does_not_cook(tmp_path):
    built = _build(tmp_path)["observed"]
    node = hou.node(built["simulation_node_path"])
    before = node.needsToCook()
    result = run_simulation_tier(
        node_path=node.path(), frames=[1, 2, 3], budget=_budget(), authorized=False
    )
    assert result["status"] == "blocked"
    assert node.needsToCook() == before


def test_viewport_is_authentically_pending_in_hython(tmp_path):
    built = _build(tmp_path)["observed"]
    output = tmp_path / "viewport.png"
    result = run_viewport_tier(
        viewer_name="sceneviewer1", viewport_name="persp1",
        camera_path=built["viewport_camera_path"], output_path=str(output), frame=1,
        budget=_budget(),
    )
    assert hou.isUIAvailable() is False
    assert result["status"] == "pending"
    assert not output.exists()


def test_karma_requires_explicit_render_authorization(tmp_path):
    built = _build(tmp_path)["observed"]
    result = run_karma_tier(
        rop_path=built["karma_rop_path"], output_path=built["render_output_path"],
        log_path=str(tmp_path / "karma.jsonl"), frame=1, budget=_budget(), authorized=False,
    )
    assert result["status"] == "blocked"
    assert not Path(built["render_output_path"]).exists()


def test_karma_refuses_fixture_samples_above_explicit_budget(tmp_path):
    built = _build(tmp_path)["observed"]
    result = run_karma_tier(
        rop_path=built["karma_rop_path"], output_path=built["render_output_path"],
        log_path=str(tmp_path / "karma.jsonl"), frame=1, budget=_budget(samples=4),
        authorized=True,
    )
    assert result["status"] == "blocked"
    assert "fixture samples 8 exceeds budget.samples 4" in result["errors"][0]
    assert not Path(built["render_output_path"]).exists()


def test_all_results_are_manifest_compatible_plain_mappings(tmp_path):
    built = _build(tmp_path)
    required = {
        "tier", "status", "command", "started_at", "duration_seconds", "budget", "observed",
        "artifacts", "warnings", "errors",
    }
    assert required == set(built)
    assert isinstance(built["observed"], dict)
    assert all(isinstance(item, dict) for item in built["artifacts"])
