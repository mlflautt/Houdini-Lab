"""Tests for acceptance tier planning, execution mapping, and the unified CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from hermes_houdini.acceptance.runner import AcceptanceRunner, plan_tiers
from hermes_houdini.acceptance.schema import AcceptanceRequest


class PassingAdapter:
    def run(self, *, tier, artifact_root, budget):
        return {
            "tier": tier,
            "status": "pass",
            "command": ["fake", tier],
            "started_at": "2026-08-25T12:00:00Z",
            "duration_seconds": 0.1,
            "budget": budget,
            "observed": {"adapter": "fake"},
            "artifacts": [],
            "warnings": [],
            "errors": [],
        }


class FailingAdapter:
    def run(self, *, tier, artifact_root, budget):
        raise TimeoutError("bounded fake timed out")


def test_plan_aggregates_only_required_cheap_prerequisites():
    plan = plan_tiers(("karma", "simulation"))
    assert plan["selected_tiers"] == ["simulation", "karma"]
    assert plan["required_tiers"] == [
        "pure",
        "hython-read",
        "graph-edit",
        "simulation",
        "karma",
    ]
    assert "viewport" not in plan["required_tiers"]
    assert plan["executes"] is False


def test_runner_maps_missing_timeout_and_warning_status_mechanically(tmp_path):
    request = AcceptanceRequest(
        tiers=("pure", "hython-read", "graph-edit"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    runner = AcceptanceRunner(
        adapters={"pure": PassingAdapter(), "hython-read": FailingAdapter()}
    )
    summary = runner.execute(request)
    statuses = {item.tier: item.status for item in summary.results}
    assert statuses == {"pure": "pass", "hython-read": "blocked", "graph-edit": "blocked"}
    assert summary.overall_status == "blocked"


def test_runner_rejects_adapter_result_for_wrong_tier(tmp_path):
    class WrongTier(PassingAdapter):
        def run(self, *, tier, artifact_root, budget):
            result = super().run(tier=tier, artifact_root=artifact_root, budget=budget)
            result["tier"] = "karma"
            return result

    request = AcceptanceRequest(tiers=("pure",), artifact_root=str(tmp_path / "artifacts"))
    summary = AcceptanceRunner(adapters={"pure": WrongTier()}).execute(request)
    assert summary.overall_status == "blocked"
    assert "wrong tier" in summary.results[0].errors[0]


def test_runner_stops_after_blocked_prerequisite(tmp_path):
    called = []

    class RecordingAdapter(PassingAdapter):
        def run(self, *, tier, artifact_root, budget):
            called.append(tier)
            return super().run(tier=tier, artifact_root=artifact_root, budget=budget)

    request = AcceptanceRequest(
        tiers=("graph-edit",), artifact_root=str(tmp_path / "artifacts")
    )
    runner = AcceptanceRunner(
        adapters={
            "pure": FailingAdapter(),
            "hython-read": RecordingAdapter(),
            "graph-edit": RecordingAdapter(),
        }
    )
    summary = runner.execute(request)
    assert called == []
    assert [item.status for item in summary.results] == ["blocked", "blocked", "blocked"]


def test_runner_rejects_adapter_budget_drift(tmp_path):
    class BudgetDrift(PassingAdapter):
        def run(self, *, tier, artifact_root, budget):
            result = super().run(tier=tier, artifact_root=artifact_root, budget=budget)
            result["budget"] = {**budget, "seconds": 999}
            return result

    request = AcceptanceRequest(tiers=("pure",), artifact_root=str(tmp_path / "artifacts"))
    summary = AcceptanceRunner(adapters={"pure": BudgetDrift()}).execute(request)
    assert summary.overall_status == "blocked"
    assert "budget different" in summary.results[0].errors[0]


def _cli(*arguments):
    script = Path(__file__).parents[2] / "scripts" / "run_acceptance.py"
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_default_is_help_and_list_tiers_is_json():
    default = _cli()
    assert default.returncode == 0
    assert "--list-tiers" in default.stdout
    listed = _cli("--list-tiers")
    assert listed.returncode == 0
    assert json.loads(listed.stdout)["tiers"][-1]["id"] == "karma"


def test_cli_plan_does_not_import_hou_spawn_or_create_artifact_root(tmp_path):
    root = tmp_path / "must-not-exist"
    result = _cli("--plan", "--tier", "pure", "--artifact-root", str(root))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["executes"] is False
    assert not root.exists()
    assert "hou" not in sys.modules


def test_cli_exposes_separate_expensive_tier_authorizations():
    result = _cli("--help")
    assert result.returncode == 0
    for flag in (
        "--allow-pdg-child",
        "--allow-simulation",
        "--allow-viewport",
        "--allow-karma",
    ):
        assert flag in result.stdout


def test_cli_execution_requires_explicit_tier_and_absolute_artifact_root():
    result = _cli("--execute", "--tier", "pure", "--artifact-root", "relative")
    assert result.returncode != 0
    assert "artifact_root" in result.stderr


def test_unknown_tier_is_rejected_usefully():
    with pytest.raises(ValueError, match="unknown tier"):
        plan_tiers(("not-a-tier",))
