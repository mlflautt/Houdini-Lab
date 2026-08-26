"""Pure acceptance contracts and orchestration; safe to import without Houdini."""

from .baselines import BASELINE_METRICS, BASELINE_SCHEMA, evaluate_baseline, normalize_baseline
from .compatibility import (
    COMPATIBILITY_SCHEMA,
    compare_compatibility,
    normalize_expectation,
    probe_compatibility,
    validate_compatibility_output_path,
)
from .integrated import IntegratedAcceptanceAdapter, runtime_identity
from .runner import DEFAULT_BUDGETS, AcceptanceRunner, TierAdapter, plan_tiers
from .schema import (
    ACCEPTANCE_SCHEMA,
    EVIDENCE_STATES,
    TIER_IDS,
    AcceptanceRequest,
    AcceptanceSummary,
    TierResult,
    aggregate_status,
    canonical_json,
    canonical_sha256,
)

__all__ = [
    "ACCEPTANCE_SCHEMA",
    "BASELINE_METRICS",
    "BASELINE_SCHEMA",
    "COMPATIBILITY_SCHEMA",
    "DEFAULT_BUDGETS",
    "EVIDENCE_STATES",
    "TIER_IDS",
    "AcceptanceRequest",
    "AcceptanceRunner",
    "AcceptanceSummary",
    "IntegratedAcceptanceAdapter",
    "TierAdapter",
    "TierResult",
    "aggregate_status",
    "canonical_json",
    "canonical_sha256",
    "compare_compatibility",
    "evaluate_baseline",
    "normalize_baseline",
    "normalize_expectation",
    "plan_tiers",
    "probe_compatibility",
    "runtime_identity",
    "validate_compatibility_output_path",
]
