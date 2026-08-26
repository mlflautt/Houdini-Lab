from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hermes_houdini.acceptance.integrated import IntegratedAcceptanceAdapter, runtime_identity
from hermes_houdini.acceptance.runner import DEFAULT_BUDGETS


def _cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).parents[2] / "scripts" / "run_acceptance.py"
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_live_default_budget_matches_frozen_fixture_contract() -> None:
    expected = {
        "max_points": 10_000,
        "max_primitives": 10_000,
        "max_frames": 8,
        "max_memory_bytes": 256 * 1024 * 1024,
        "max_artifact_bytes": 256 * 1024 * 1024,
        "width": 640,
        "height": 360,
        "samples": 16,
        "max_seconds": 120.0,
        "max_work_items": 1,
    }
    assert DEFAULT_BUDGETS["graph-edit"] == expected
    assert DEFAULT_BUDGETS["karma"] == expected


def test_plan_names_approval_boundaries_without_creating_root(tmp_path: Path) -> None:
    root = tmp_path / "planned"
    result = _cli(
        "--plan",
        "--tier",
        "pdg-child",
        "--tier",
        "karma",
        "--artifact-root",
        str(root),
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["approvals_required"] == {
        "karma": ["render", "external_process"],
        "pdg-child": ["external_process"],
    }
    assert not root.exists()


def test_plan_records_tier_scoped_authorization_assertions(tmp_path: Path) -> None:
    root = tmp_path / "planned"
    result = _cli(
        "--plan",
        "--tier",
        "viewport",
        "--tier",
        "karma",
        "--artifact-root",
        str(root),
        "--allow-viewport",
        "--allow-karma",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["approvals_granted"] == [
        "viewport:interactive_viewport",
        "karma:render",
        "karma:external_process",
    ]
    assert not root.exists()


def test_live_execute_requires_hython_before_creating_root(tmp_path: Path) -> None:
    root = tmp_path / "must-not-exist"
    result = _cli(
        "--execute",
        "--tier",
        "graph-edit",
        "--artifact-root",
        str(root),
    )
    assert result.returncode != 0
    assert "require this entry point to run with Houdini Hython" in result.stderr
    assert not root.exists()


def test_runtime_identity_binds_repository_commit_and_dirty_state() -> None:
    repository = Path(__file__).parents[2]
    _, _, inventory = runtime_identity(repository)
    source = next(item for item in inventory if item["kind"] == "repository")
    assert len(source["commit"]) == 40
    assert isinstance(source["dirty"], bool)


def test_viewport_adapter_fails_closed_without_separate_authorization(tmp_path: Path) -> None:
    repository = Path(__file__).parents[2]
    adapter = IntegratedAcceptanceAdapter(repository_root=repository)
    result = adapter.run(
        tier="viewport",
        artifact_root=str(tmp_path / "unused"),
        budget=DEFAULT_BUDGETS["viewport"],
    )
    assert result["status"] == "blocked"
    assert "authorization" in result["errors"][0]
    assert not (tmp_path / "unused").exists()
