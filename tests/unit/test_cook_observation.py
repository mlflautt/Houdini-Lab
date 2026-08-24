"""Pure Milestone 3 cook, validation, and observation contracts."""

from __future__ import annotations

import pytest
from hermes_houdini.cook import (
    CookJobManager,
    budget_violations,
    normalize_estimate,
    normalize_frame_range,
    validate_cook_spec,
)
from hermes_houdini.observation import validate_viewport_capture
from hermes_houdini.schemas.command import Policy
from hermes_houdini.validation import validate_metric_expectations


def _estimate(points=8, primitives=6, memory_bytes=4096, seconds=0.1):
    return {
        "points": points,
        "primitives": primitives,
        "memory_bytes": memory_bytes,
        "seconds": seconds,
    }


def test_estimate_is_strict_finite_json_resource_contract():
    assert normalize_estimate(_estimate())["points"] == 8
    with pytest.raises(ValueError, match="missing keys"):
        normalize_estimate({"points": 8})
    with pytest.raises(ValueError, match="finite"):
        normalize_estimate(_estimate(seconds=float("nan")))
    with pytest.raises(ValueError, match="unknown keys"):
        normalize_estimate({**_estimate(), "voxels": 1})


def test_declared_estimate_must_fit_all_policy_dimensions():
    policy = Policy(max_points=7, max_primitives=5, max_memory_bytes=1000, max_seconds=0.01)
    violations = budget_violations(_estimate(), policy)
    assert len(violations) == 4
    with pytest.raises(ValueError, match="declared estimate exceeds policy"):
        validate_cook_spec(scope="single_node", frame=None, estimate=_estimate(), policy=policy)


def test_one_frame_scope_requires_explicit_frame_and_frame_budget():
    with pytest.raises(ValueError, match="requires"):
        validate_cook_spec(scope="one_frame", frame=None, estimate=_estimate(), policy=Policy())
    with pytest.raises(ValueError, match="only valid"):
        validate_cook_spec(scope="single_node", frame=2, estimate=_estimate(), policy=Policy())


def test_frame_range_is_inclusive_bounded_and_mutually_exclusive_with_frame():
    policy = Policy(max_frames=4)
    assert normalize_frame_range([1, 4], policy) == [1.0, 2.0, 3.0, 4.0]
    assert normalize_frame_range([1, 2, 0.5], policy) == [1.0, 1.5, 2.0]
    validate_cook_spec(
        scope="frame_range",
        frame=None,
        frame_range=[1, 4],
        estimate=_estimate(),
        policy=policy,
    )
    with pytest.raises(ValueError, match="max_frames"):
        normalize_frame_range([1, 5], policy)
    with pytest.raises(ValueError, match="greater than zero"):
        normalize_frame_range([1, 4, 0], policy)
    with pytest.raises(ValueError, match="only valid for one_frame"):
        validate_cook_spec(
            scope="frame_range",
            frame=1,
            frame_range=[1, 4],
            estimate=_estimate(),
            policy=policy,
        )


def test_job_manager_cancels_only_before_run():
    manager = CookJobManager(max_jobs=4)
    job = manager.submit(
        node_path="/obj/G/OUT",
        node_session_id=42,
        scope="single_node",
        frame=None,
        frame_range=None,
        force=False,
        estimate=_estimate(),
        policy=Policy(),
        log_path="/tmp/cook.jsonl",
    )
    assert job.state == "pending"
    assert manager.cancel(job.job_id).state == "cancelled"
    with pytest.raises(ValueError, match="only pending"):
        manager.begin(job.job_id)


def test_metric_validation_reports_contract_failures_without_mutation():
    metrics = {
        "points": 8,
        "primitives": 6,
        "bounds": [[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]],
        "point_attributes": ["P"],
        "primitive_attributes": [],
        "point_groups": [],
        "primitive_groups": [],
        "node_errors": [],
        "node_warnings": [],
    }
    passed = validate_metric_expectations(
        metrics,
        {
            "min_points": 1,
            "max_points": 8,
            "required_point_attributes": ["P"],
            "require_finite_bounds": True,
        },
    )
    assert passed["valid"] is True
    failed = validate_metric_expectations(metrics, {"max_points": 7})
    assert failed["valid"] is False
    assert "points 8" in failed["issues"][0]


def test_viewport_capture_enforces_apprentice_ceiling_and_png():
    validate_viewport_capture(width=1280, height=720, frame=1, output_path="preview.png")
    with pytest.raises(ValueError, match="exceeds Apprentice ceiling"):
        validate_viewport_capture(width=1920, height=1080, frame=1, output_path="preview.png")
    with pytest.raises(ValueError, match=".png"):
        validate_viewport_capture(width=1280, height=720, frame=1, output_path="preview.jpg")
