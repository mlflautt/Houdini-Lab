"""Pure acceptance planning and adapter orchestration.

This module deliberately has no Houdini import. Live adapters are registered by the
integration layer and remain responsible for their own bounded execution.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from .schema import TIER_IDS, AcceptanceRequest, AcceptanceSummary, TierResult

_CHEAP_PREREQUISITES = {
    "pure": (),
    "hython-read": ("pure",),
    "graph-edit": ("pure", "hython-read"),
    "single-frame": ("pure", "hython-read", "graph-edit"),
    "frame-range": ("pure", "hython-read", "graph-edit"),
    "pdg-child": ("pure", "hython-read", "graph-edit"),
    "simulation": ("pure", "hython-read", "graph-edit"),
    "viewport": ("pure", "hython-read", "graph-edit"),
    "karma": ("pure", "hython-read", "graph-edit"),
}
_EXPENSIVE_TIERS = frozenset(
    {"frame-range", "pdg-child", "simulation", "viewport", "karma"}
)
_LIVE_BUDGET = {
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
DEFAULT_BUDGETS: dict[str, dict[str, Any]] = {
    "pure": {"seconds": 60, "memory_bytes": 536_870_912},
    **{tier: dict(_LIVE_BUDGET) for tier in TIER_IDS if tier != "pure"},
}


class TierAdapter(Protocol):
    """Narrow seam implemented by live or compatibility tier providers."""

    def run(
        self, *, tier: str, artifact_root: str, budget: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...


def plan_tiers(tiers: tuple[str, ...]) -> dict[str, Any]:
    unknown = [tier for tier in tiers if tier not in TIER_IDS]
    if unknown:
        raise ValueError(f"unknown tier(s): {unknown}")
    if len(set(tiers)) != len(tiers):
        raise ValueError("duplicate tier selections are not permitted")
    if not tiers:
        raise ValueError("at least one explicit tier is required")
    selected = [tier for tier in TIER_IDS if tier in tiers]
    required = set(selected)
    for tier in selected:
        required.update(_CHEAP_PREREQUISITES[tier])
    return {
        "schema": "hermes.houdini.acceptance.plan.v1",
        "selected_tiers": selected,
        "required_tiers": [tier for tier in TIER_IDS if tier in required],
        "expensive_tiers": [tier for tier in selected if tier in _EXPENSIVE_TIERS],
        "executes": False,
        "approvals_granted": [],
        "approvals_required": {
            tier: {
                "pdg-child": ["external_process"],
                "simulation": ["simulation"],
                "viewport": ["interactive_viewport"],
                "karma": ["render", "external_process"],
            }.get(tier, [])
            for tier in selected
        },
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _mapped_result(
    *,
    tier: str,
    status: str,
    budget: Mapping[str, Any],
    started_at: str,
    duration_seconds: float,
    warning: str = "",
    error: str = "",
) -> TierResult:
    return TierResult.from_dict(
        {
            "tier": tier,
            "status": status,
            "command": ["adapter", tier],
            "started_at": started_at,
            "duration_seconds": duration_seconds,
            "budget": dict(budget),
            "observed": {},
            "artifacts": [],
            "warnings": [warning] if warning else [],
            "errors": [error] if error else [],
        }
    )


class AcceptanceRunner:
    """Execute only planned tiers through explicitly registered adapters."""

    def __init__(self, *, adapters: Mapping[str, TierAdapter] | None = None) -> None:
        self._adapters = dict(adapters or {})
        unknown = set(self._adapters).difference(TIER_IDS)
        if unknown:
            raise ValueError(f"adapters registered for unknown tier(s): {sorted(unknown)}")

    def execute(
        self,
        request: AcceptanceRequest,
        *,
        build: str = "",
        license_mode: str = "",
        package_inventory: tuple[dict[str, Any], ...] = (),
    ) -> AcceptanceSummary:
        plan = plan_tiers(request.tiers)
        required = tuple(plan["required_tiers"])
        results: list[TierResult] = []
        by_tier: dict[str, TierResult] = {}
        for tier in required:
            budget = request.budget_for(tier, DEFAULT_BUDGETS[tier])
            prerequisites = [by_tier[item] for item in _CHEAP_PREREQUISITES[tier]]
            blocked = [item.tier for item in prerequisites if item.status == "blocked"]
            incomplete = [
                item.tier
                for item in prerequisites
                if item.status in {"pending", "not_applicable"}
            ]
            if blocked or incomplete:
                status = "blocked" if blocked else "pending"
                message = (
                    f"required prerequisite tier(s) did not pass: "
                    f"{', '.join(blocked or incomplete)}"
                )
                result = _mapped_result(
                    tier=tier,
                    status=status,
                    budget=budget,
                    started_at=_now(),
                    duration_seconds=0.0,
                    error=message if blocked else "",
                    warning=message if incomplete else "",
                )
                results.append(result)
                by_tier[tier] = result
                continue
            adapter = self._adapters.get(tier)
            started_at = _now()
            before = time.monotonic()
            if adapter is None:
                result = _mapped_result(
                    tier=tier,
                    status="pending",
                    budget=budget,
                    started_at=started_at,
                    duration_seconds=0.0,
                    warning="no adapter registered; tier was not run",
                )
                results.append(result)
                by_tier[tier] = result
                continue
            try:
                raw = dict(
                    adapter.run(
                        tier=tier,
                        artifact_root=request.artifact_root,
                        budget=budget,
                    )
                )
                if raw.get("tier") != tier:
                    raise ValueError(
                        f"adapter returned wrong tier {raw.get('tier')!r}; expected {tier!r}"
                    )
                if raw.get("budget") != budget:
                    raise ValueError("adapter returned a budget different from the request")
                raw["artifact_root"] = request.artifact_root
                result = TierResult.from_dict(raw)
            except TimeoutError as exc:
                result = _mapped_result(
                    tier=tier,
                    status="blocked",
                    budget=budget,
                    started_at=started_at,
                    duration_seconds=time.monotonic() - before,
                    error=f"tier timed out: {exc}",
                )
            except Exception as exc:
                result = _mapped_result(
                    tier=tier,
                    status="blocked",
                    budget=budget,
                    started_at=started_at,
                    duration_seconds=time.monotonic() - before,
                    error=f"adapter result invalid or failed: {exc}",
                )
            results.append(result)
            by_tier[tier] = result
        return AcceptanceSummary.create(
            request=request,
            results=tuple(results),
            required_tiers=required,
            build=build,
            license_mode=license_mode,
            package_inventory=package_inventory,
        )


__all__ = ["DEFAULT_BUDGETS", "AcceptanceRunner", "TierAdapter", "plan_tiers"]
