"""Pure acceptance contracts and orchestration; safe to import without Houdini."""

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
    "DEFAULT_BUDGETS",
    "EVIDENCE_STATES",
    "TIER_IDS",
    "AcceptanceRequest",
    "AcceptanceRunner",
    "AcceptanceSummary",
    "TierAdapter",
    "TierResult",
    "aggregate_status",
    "canonical_json",
    "canonical_sha256",
    "plan_tiers",
]
