"""Deterministic verification escalation and human-authority tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hermes_houdini.verification_routing import route_verification


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _base_reports(tmp_path: Path, *, structural: str = "pass", visual: str = "pass"):
    structural_path = _write(
        tmp_path / "structural.json",
        {"schema": "fixture.structural", "status": structural},
    )
    visual_path = _write(
        tmp_path / "visual.json",
        {"schema": "hermes.visual_verification", "status": visual},
    )
    return structural_path, visual_path


def _local_critique(tmp_path: Path, *, status: str = "pass", digest: str = "a") -> Path:
    return _write(
        tmp_path / f"local-{status}-{digest}.json",
        {
            "schema": "hermes.local_visual_critique",
            "status": "available_unverified",
            "model": {"name": "qwen3-vl:8b", "digest": digest * 64},
            "critique": {"mechanical_status": status},
            "decision_authority": "advisory_only",
            "winner": None,
        },
    )


def _calibration(tmp_path: Path, *, digest: str = "a", status: str = "pass") -> Path:
    return _write(
        tmp_path / f"calibration-{digest}-{status}.json",
        {
            "schema": "hermes.local_critic_calibration",
            "status": status,
            "model_reliability": "calibrated" if status == "pass" else "available_unverified",
            "model": {"name": "qwen3-vl:8b", "digest": digest * 64},
            "winner": None,
        },
    )


def test_mechanical_failure_blocks_model_override_and_external_execution(tmp_path):
    structural, visual = _base_reports(tmp_path, structural="fail", visual="warn")
    result = route_verification(
        project_root=str(tmp_path),
        structural_paths=[str(structural)],
        visual_path=str(visual),
        output_path=str(tmp_path / "route.json"),
        external_critic_requested=True,
        allow_external=True,
    )
    assert result["mechanical_gate"]["status"] == "fail"
    assert result["mechanical_gate"]["model_may_override"] is False
    assert result["next_action"] == "repair_mechanical_failure"
    assert result["external_critic"]["route"] == "blocked_by_mechanical_gate"
    assert result["external_critic"]["execution_performed"] is False
    assert result["winner"] is None


def test_pass_with_no_allowlisted_local_model_remains_ready_for_human_taste(tmp_path):
    structural, visual = _base_reports(tmp_path)
    probe = _write(
        tmp_path / "probe.json",
        {
            "schema": "hermes.local_critic_probe",
            "status": "available_no_allowlisted_model",
            "installed_allowlisted_models": [],
        },
    )
    result = route_verification(
        project_root=str(tmp_path),
        structural_paths=[str(structural)],
        visual_path=str(visual),
        probe_path=str(probe),
        output_path=str(tmp_path / "route.json"),
    )
    assert result["mechanical_gate"]["status"] == "pass"
    assert result["next_action"] == "ready_with_optional_local_critic_unavailable"
    assert result["human_review"]["required_now"] is False


def test_calibrated_model_disagreement_routes_to_human_without_ranking(tmp_path):
    structural, visual = _base_reports(tmp_path)
    local = _local_critique(tmp_path, status="warn")
    calibration = _calibration(tmp_path)
    result = route_verification(
        project_root=str(tmp_path),
        structural_paths=[str(structural)],
        visual_path=str(visual),
        local_critique_path=str(local),
        calibration_path=str(calibration),
        output_path=str(tmp_path / "route.json"),
    )
    assert result["local_critic"]["reliability"] == "calibrated"
    assert result["disagreements"]["calibrated_critic"] is True
    assert result["human_review"]["triggers"] == ["calibrated_critic_disagreement"]
    assert result["next_action"] == "human_review_model_disagreement"
    assert result["automatic_ranking"] is False
    assert result["human_rating"] is None


def test_mismatched_calibration_model_cannot_reduce_human_review(tmp_path):
    structural, visual = _base_reports(tmp_path)
    local = _local_critique(tmp_path, status="pass", digest="a")
    calibration = _calibration(tmp_path, digest="b")
    result = route_verification(
        project_root=str(tmp_path),
        structural_paths=[str(structural)],
        visual_path=str(visual),
        local_critique_path=str(local),
        calibration_path=str(calibration),
        output_path=str(tmp_path / "route.json"),
    )
    assert result["evidence"]["calibration"]["same_model"] is False
    assert result["local_critic"]["reliability"] == "available_unverified"
    assert result["local_critic"]["may_reduce_human_review"] is False
    assert result["next_action"] == "calibrate_local_critic_or_continue_to_human_taste"


def test_structural_pixel_disagreement_and_final_taste_are_explicit_human_triggers(tmp_path):
    structural, visual = _base_reports(tmp_path, structural="pass", visual="fail")
    result = route_verification(
        project_root=str(tmp_path),
        structural_paths=[str(structural)],
        visual_path=str(visual),
        output_path=str(tmp_path / "route.json"),
        final_taste_review=True,
    )
    assert result["human_review"]["required_now"] is True
    assert result["human_review"]["triggers"] == [
        "structural_pixel_disagreement",
    ]
    assert result["human_review"]["deferred_triggers"] == [
        "final_taste_choice_until_mechanical_pass"
    ]
    assert result["next_action"] == "human_review_then_mechanical_repair"


def test_routes_may_not_read_evidence_outside_project_root(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    structural = _write(tmp_path / "outside.json", {"status": "pass"})
    visual = _write(
        project / "visual.json", {"schema": "hermes.visual_verification", "status": "pass"}
    )
    with pytest.raises(ValueError, match="inside project_root"):
        route_verification(
            project_root=str(project),
            structural_paths=[str(structural)],
            visual_path=str(visual),
            output_path=str(project / "route.json"),
        )
