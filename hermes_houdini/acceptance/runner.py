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
    "single-frame": ("pure", "hython-read"),
    "frame-range": ("pure", "hython-read"),
    "pdg-child": ("pure", "hython-read"),
    "simulation": ("pure", "hython-read"),
    "viewport": ("pure", "hython-read"),
    "karma": ("pure", "hython-read"),
}
_EXPENSIVE_TIERS = frozenset(
    {"frame-range", "pdg-child", "simulation", "viewport", "karma"}
)
DEFAULT_BUDGETS: dict[str, dict[str, Any]] = {
    "pure": {"seconds": 60, "memory_bytes": 536_870_912},
    "hython-read": {"seconds": 30, "memory_bytes": 536_870_912, "frames": 0},
    "graph-edit": {"seconds": 30, "memory_bytes": 536_870_912, "frames": 0},
    "single-frame": {"seconds": 60, "memory_bytes": 1_073_741_824, "frames": 1},
    "frame-range": {"seconds": 120, "memory_bytes": 1_073_741_824, "frames": 8},
    "pdg-child": {"seconds": 120, "memory_bytes": 1_073_741_824, "work_items": 4},
    "simulation": {"seconds": 120, "memory_bytes": 1_073_741_824, "frames": 8},
    "viewport": {"seconds": 120, "memory_bytes": 1_073_741_824, "resolution": [640, 360]},
    "karma": {
        "seconds": 120,
        "memory_bytes": 1_073_741_824,
        "resolution": [640, 360],
        "samples": 16,
    },
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
        results = []
        for tier in required:
            budget = request.budget_for(tier, DEFAULT_BUDGETS[tier])
            adapter = self._adapters.get(tier)
            started_at = _now()
            before = time.monotonic()
            if adapter is None:
                results.append(
                    _mapped_result(
                        tier=tier,
                        status="pending",
                        budget=budget,
                        started_at=started_at,
                        duration_seconds=0.0,
                        warning="no adapter registered; tier was not run",
                    )
                )
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
                raw["artifact_root"] = request.artifact_root
                results.append(TierResult.from_dict(raw))
            except TimeoutError as exc:
                results.append(
                    _mapped_result(
                        tier=tier,
                        status="blocked",
                        budget=budget,
                        started_at=started_at,
                        duration_seconds=time.monotonic() - before,
                        error=f"tier timed out: {exc}",
                    )
                )
            except Exception as exc:
                results.append(
                    _mapped_result(
                        tier=tier,
                        status="blocked",
                        budget=budget,
                        started_at=started_at,
                        duration_seconds=time.monotonic() - before,
                        error=f"adapter result invalid or failed: {exc}",
                    )
                )
        return AcceptanceSummary.create(
            request=request,
            results=tuple(results),
            required_tiers=required,
            build=build,
            license_mode=license_mode,
            package_inventory=package_inventory,
        )


__all__ = ["DEFAULT_BUDGETS", "AcceptanceRunner", "TierAdapter", "plan_tiers"]
