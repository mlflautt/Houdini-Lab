"""Pure resource-baseline normalization and evaluation.

Baselines are diagnostic safety records.  They neither call Houdini nor grant an
approval, and they deliberately say nothing about artistic quality.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

BASELINE_SCHEMA = "hermes.houdini.acceptance.baseline.v1"
BASELINE_METRICS = (
    "points",
    "primitives",
    "peak_memory_bytes",
    "cook_seconds",
    "cache_bytes",
    "frames",
    "width",
    "height",
    "render_samples",
)
_INTEGER_METRICS = frozenset(BASELINE_METRICS) - {"cook_seconds"}


def _number(value: object, *, label: str, integer: bool = False) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite non-negative number")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
    if integer and not isinstance(value, int):
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _fraction(value: object, *, label: str) -> float:
    number = _number(value, label=label)
    if number >= 1:
        raise ValueError(f"{label} must be at least 0 and less than 1")
    return float(number)


def normalize_baseline(baseline: Mapping[str, object]) -> dict[str, Any]:
    """Validate a versioned baseline and derive deterministic warning thresholds."""

    if not isinstance(baseline, Mapping):
        raise ValueError("baseline must be a mapping")
    if baseline.get("schema") != BASELINE_SCHEMA:
        raise ValueError(f"baseline schema must be {BASELINE_SCHEMA}")
    for field in ("baseline_id", "baseline_version"):
        if not isinstance(baseline.get(field), str) or not baseline[field]:
            raise ValueError(f"{field} must be a non-empty string")

    raw_budgets = baseline.get("budgets")
    if not isinstance(raw_budgets, Mapping):
        raise ValueError("budgets must be a mapping")
    missing = sorted(set(BASELINE_METRICS) - set(raw_budgets))
    unknown = sorted(set(raw_budgets) - set(BASELINE_METRICS))
    if missing:
        raise ValueError(f"missing baseline budgets: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"unknown baseline budgets: {', '.join(unknown)}")
    budgets = {
        metric: _number(
            raw_budgets[metric],
            label=f"budget {metric}",
            integer=metric in _INTEGER_METRICS,
        )
        for metric in BASELINE_METRICS
    }

    raw_tolerances = baseline.get("tolerances", {})
    if not isinstance(raw_tolerances, Mapping):
        raise ValueError("tolerances must be a mapping")
    default_fraction = _fraction(
        raw_tolerances.get("default_warning_fraction", 0.1),
        label="default warning fraction",
    )
    raw_metric_fractions = raw_tolerances.get("metrics", {})
    if not isinstance(raw_metric_fractions, Mapping):
        raise ValueError("tolerance metrics must be a mapping")
    unknown_tolerances = sorted(set(raw_metric_fractions) - set(BASELINE_METRICS))
    if unknown_tolerances:
        raise ValueError(f"unknown tolerance metrics: {', '.join(unknown_tolerances)}")
    metric_fractions = {
        metric: _fraction(value, label=f"warning fraction {metric}")
        for metric, value in raw_metric_fractions.items()
    }
    thresholds = {
        metric: budget * (1 - metric_fractions.get(metric, default_fraction))
        for metric, budget in budgets.items()
    }
    tolerances: dict[str, object] = {"default_warning_fraction": default_fraction}
    if metric_fractions:
        tolerances["metrics"] = {key: metric_fractions[key] for key in sorted(metric_fractions)}
    return {
        "schema": BASELINE_SCHEMA,
        "baseline_id": baseline["baseline_id"],
        "baseline_version": baseline["baseline_version"],
        "budgets": budgets,
        "tolerances": tolerances,
        "warning_thresholds": thresholds,
    }


def _observed_number(value: object, metric: str) -> int | float | None:
    try:
        return _number(value, label=metric, integer=metric in _INTEGER_METRICS)
    except ValueError:
        return None


def _reportable_observation(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return repr(value)


def evaluate_baseline(
    baseline: Mapping[str, object], observed: Mapping[str, object]
) -> dict[str, Any]:
    """Compare observations to a baseline without running work or approving overruns."""

    normalized = normalize_baseline(baseline)
    if not isinstance(observed, Mapping):
        raise ValueError("observed resources must be a mapping")
    comparisons: dict[str, dict[str, object]] = {}
    summary = {
        "missing": [],
        "warnings": [],
        "hard_violations": [],
        "invalid": [],
    }
    for metric in BASELINE_METRICS:
        budget = normalized["budgets"][metric]
        threshold = normalized["warning_thresholds"][metric]
        value = observed.get(metric)
        if metric not in observed:
            outcome = "missing"
            summary["missing"].append(metric)
            value = None
        else:
            numeric = _observed_number(value, metric)
            if numeric is None:
                outcome = "invalid"
                summary["invalid"].append(metric)
            elif numeric > budget:
                outcome = "hard_violation"
                summary["hard_violations"].append(metric)
            elif numeric >= threshold:
                outcome = "warning"
                summary["warnings"].append(metric)
            else:
                outcome = "within_budget"
        comparisons[metric] = {
            "outcome": outcome,
            "budget": budget,
            "warning_threshold": threshold,
            "observed": _reportable_observation(value),
        }

    if summary["hard_violations"] or summary["invalid"]:
        status = "blocked"
    elif summary["missing"]:
        status = "pending"
    elif summary["warnings"]:
        status = "warn"
    else:
        status = "pass"
    summary = {key: sorted(values) for key, values in summary.items()}
    return {
        "schema": BASELINE_SCHEMA,
        "baseline_id": normalized["baseline_id"],
        "baseline_version": normalized["baseline_version"],
        "status": status,
        "comparisons": comparisons,
        "summary": summary,
        "approval_granted": False,
    }


__all__ = [
    "BASELINE_METRICS",
    "BASELINE_SCHEMA",
    "evaluate_baseline",
    "normalize_baseline",
]
