"""Tests for the pure acceptance schema and deterministic summary hashing."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from hermes_houdini.acceptance.schema import (
    ACCEPTANCE_SCHEMA,
    AcceptanceRequest,
    AcceptanceSummary,
    TierResult,
    canonical_sha256,
)


def _result(**overrides):
    values = {
        "tier": "pure",
        "status": "pass",
        "command": ["python", "-m", "pytest"],
        "started_at": "2026-08-25T12:00:00Z",
        "duration_seconds": 1.25,
        "budget": {"seconds": 10, "memory_bytes": 1024},
        "observed": {"tests": 2, "duration_seconds": 1.25},
        "artifacts": [],
        "warnings": [],
        "errors": [],
    }
    values.update(overrides)
    return TierResult.from_dict(values)


def test_summary_hash_is_key_order_invariant_and_excludes_self_hash():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert canonical_sha256(left) == canonical_sha256(right)

    request = AcceptanceRequest(tiers=("pure",), artifact_root="/private/tmp/hermes-acceptance")
    summary = AcceptanceSummary.create(
        request=request,
        results=(_result(),),
        build="none",
        license_mode="not_applicable",
        package_inventory=(),
    )
    payload = summary.as_dict()
    payload["summary_sha256"] = "not-the-real-hash"
    assert canonical_sha256(payload) == summary.summary_sha256
    assert payload["schema"] == ACCEPTANCE_SCHEMA


def test_semantically_identical_results_ignore_wall_clock_fields_in_hash():
    request = AcceptanceRequest(tiers=("pure",), artifact_root="/private/tmp/hermes-acceptance")
    first = AcceptanceSummary.create(request=request, results=(_result(),))
    second = AcceptanceSummary.create(
        request=request,
        results=(
            _result(started_at="2030-01-01T00:00:00Z", duration_seconds=99.0),
        ),
    )
    assert first.summary_sha256 == second.summary_sha256


@pytest.mark.parametrize("tiers", [("pure", "pure"), ("unknown",)])
def test_request_rejects_duplicate_and_unknown_tiers(tiers):
    with pytest.raises(ValueError, match="tier"):
        AcceptanceRequest(tiers=tiers, artifact_root="/private/tmp/hermes-acceptance")


@pytest.mark.parametrize("root", ["relative/path", "/", str(Path.home())])
def test_request_rejects_unsafe_artifact_roots(root):
    with pytest.raises(ValueError, match="artifact_root"):
        AcceptanceRequest(tiers=("pure",), artifact_root=root)


@pytest.mark.parametrize("value", [-1, math.inf, math.nan, "unbounded", True])
def test_result_rejects_invalid_budget_and_non_finite_values(value):
    with pytest.raises(ValueError, match="budget"):
        _result(budget={"seconds": value})


def test_result_rejects_malformed_fields_and_artifacts_outside_root():
    with pytest.raises(ValueError, match="status"):
        _result(status="success")
    with pytest.raises(ValueError, match="observed"):
        _result(observed={"seconds": math.inf})
    with pytest.raises(ValueError, match="artifact"):
        _result(
            artifacts=[{"path": "/etc/passwd", "kind": "text"}],
            artifact_root="/private/tmp/hermes-acceptance",
        )


def test_required_not_applicable_tier_keeps_summary_pending():
    request = AcceptanceRequest(tiers=("pure",), artifact_root="/private/tmp/hermes-acceptance")
    summary = AcceptanceSummary.create(
        request=request,
        results=(_result(status="not_applicable"),),
    )
    assert summary.overall_status == "pending"
