from __future__ import annotations

import json
import math

import pytest
from hermes_houdini.acceptance.baselines import (
    BASELINE_METRICS,
    evaluate_baseline,
    normalize_baseline,
)


def _baseline(**overrides: object) -> dict[str, object]:
    budgets = {
        "points": 1_000,
        "primitives": 500,
        "peak_memory_bytes": 1_000_000,
        "cook_seconds": 10.0,
        "cache_bytes": 2_000_000,
        "frames": 24,
        "width": 1280,
        "height": 720,
        "render_samples": 64,
    }
    budgets.update(overrides)
    return {
        "schema": "hermes.houdini.acceptance.baseline.v1",
        "baseline_id": "unit-small-fixture",
        "baseline_version": "1.0.0",
        "budgets": budgets,
        "tolerances": {"default_warning_fraction": 0.1},
    }


def test_normalize_baseline_covers_every_resource_and_expands_warning_thresholds() -> None:
    normalized = normalize_baseline(_baseline())

    assert tuple(normalized["budgets"]) == BASELINE_METRICS
    assert normalized["warning_thresholds"]["points"] == 900
    assert normalized["warning_thresholds"]["cook_seconds"] == pytest.approx(9.0)
    assert normalized["tolerances"] == {"default_warning_fraction": 0.1}


def test_explicit_metric_tolerance_overrides_the_default() -> None:
    baseline = _baseline()
    baseline["tolerances"] = {
        "default_warning_fraction": 0.1,
        "metrics": {"cook_seconds": 0.25},
    }

    normalized = normalize_baseline(baseline)

    assert normalized["warning_thresholds"]["cook_seconds"] == pytest.approx(7.5)
    assert normalized["warning_thresholds"]["points"] == 900


def test_comparison_distinguishes_boundaries_warning_and_hard_violation() -> None:
    observed = dict(_baseline()["budgets"])
    observed.update(points=899, primitives=450, cook_seconds=10.001)

    result = evaluate_baseline(_baseline(), observed)

    assert result["status"] == "blocked"
    assert result["comparisons"]["points"]["outcome"] == "within_budget"
    assert result["comparisons"]["primitives"]["outcome"] == "warning"
    assert result["comparisons"]["cook_seconds"]["outcome"] == "hard_violation"


def test_exact_budget_is_warning_not_violation() -> None:
    observed = dict(_baseline()["budgets"])

    result = evaluate_baseline(_baseline(), observed)

    assert result["status"] == "warn"
    assert all(item["outcome"] == "warning" for item in result["comparisons"].values())


def test_missing_observation_is_pending_and_named() -> None:
    observed = dict(_baseline()["budgets"])
    del observed["cache_bytes"]

    result = evaluate_baseline(_baseline(), observed)

    assert result["status"] == "pending"
    assert result["comparisons"]["cache_bytes"] == {
        "outcome": "missing",
        "budget": 2_000_000,
        "warning_threshold": 1_800_000,
        "observed": None,
    }


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, -1, True, "12"])
def test_invalid_observation_is_blocked_without_comparing(bad: object) -> None:
    observed = dict(_baseline()["budgets"])
    observed["peak_memory_bytes"] = bad

    result = evaluate_baseline(_baseline(), observed)

    assert result["status"] == "blocked"
    assert result["comparisons"]["peak_memory_bytes"]["outcome"] == "invalid"
    json.dumps(result, allow_nan=False)


def test_invalid_baseline_rejects_missing_nonfinite_or_unknown_data() -> None:
    missing = _baseline()
    del missing["budgets"]["frames"]
    with pytest.raises(ValueError, match="missing baseline budgets: frames"):
        normalize_baseline(missing)

    with pytest.raises(ValueError, match="finite non-negative"):
        normalize_baseline(_baseline(cook_seconds=math.inf))

    with pytest.raises(ValueError, match="unknown baseline budgets: voxels"):
        normalize_baseline(_baseline(voxels=100))


def test_hard_violation_takes_precedence_over_missing_and_warning() -> None:
    observed = dict(_baseline()["budgets"])
    del observed["frames"]
    observed["points"] = 1_001

    result = evaluate_baseline(_baseline(), observed)

    assert result["status"] == "blocked"
    assert result["summary"] == {
        "missing": ["frames"],
        "warnings": [
            "cache_bytes",
            "cook_seconds",
            "height",
            "peak_memory_bytes",
            "primitives",
            "render_samples",
            "width",
        ],
        "hard_violations": ["points"],
        "invalid": [],
    }
