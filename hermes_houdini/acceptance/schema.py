"""Pure data contracts for tiered Hermes/Houdini acceptance evidence."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ACCEPTANCE_SCHEMA = "hermes.houdini.acceptance.v1"
TIER_IDS = (
    "pure",
    "hython-read",
    "graph-edit",
    "single-frame",
    "frame-range",
    "pdg-child",
    "simulation",
    "viewport",
    "karma",
)
EVIDENCE_STATES = ("pass", "warn", "pending", "blocked", "not_applicable")
_RUNTIME_HASH_KEYS = frozenset({"started_at", "duration_seconds"})


def _canonical_value(value: Any, *, exclude_runtime: bool, root: bool = False) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item, exclude_runtime=exclude_runtime)
            for key, item in value.items()
            if not (
                exclude_runtime
                and (key in _RUNTIME_HASH_KEYS or (root and key == "summary_sha256"))
            )
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item, exclude_runtime=exclude_runtime) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("canonical JSON does not permit NaN or Infinity")
    return value


def canonical_json(value: Any, *, exclude_runtime: bool = False) -> str:
    """Serialize JSON deterministically, rejecting non-finite numbers."""
    normalized = _canonical_value(value, exclude_runtime=exclude_runtime, root=True)
    try:
        return json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not canonical JSON: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    """Hash semantic evidence while excluding self-hash and wall-clock fields."""
    return hashlib.sha256(canonical_json(value, exclude_runtime=True).encode("utf-8")).hexdigest()


def _json_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _strings(value: Any, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{label} must be a list of non-empty strings")
    return tuple(value)


def _validate_finite(value: Any, *, label: str, nonnegative: bool = False) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError(f"{label} contains a non-finite numeric value")
        if nonnegative and value < 0:
            raise ValueError(f"{label} contains a negative numeric value")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_finite(item, label=f"{label}.{key}", nonnegative=nonnegative)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_finite(item, label=f"{label}[{index}]", nonnegative=nonnegative)
        return
    raise ValueError(f"{label} contains a non-JSON value")


def _validate_budget(value: Any, *, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, list, tuple, Mapping)):
        raise ValueError(f"{label} values must be non-negative finite numbers")
    if isinstance(value, (int, float)):
        _validate_finite(value, label=label, nonnegative=True)
        return
    items = value.items() if isinstance(value, Mapping) else enumerate(value)
    for key, item in items:
        _validate_budget(item, label=f"{label}.{key}")


def validate_artifact_root(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("artifact_root must be a non-empty absolute path")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        raise ValueError("artifact_root must be absolute")
    lexical = Path(value).absolute()
    root = candidate.resolve(strict=False)
    forbidden = {Path("/"), Path.home().resolve(), Path.home().resolve().parent}
    denied_roots = (
        Path("/System"),
        Path("/etc"),
        Path("/private/etc"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/Applications"),
    )
    if root in forbidden or any(
        lexical.is_relative_to(denied) or root.is_relative_to(denied)
        for denied in denied_roots
    ):
        raise ValueError("artifact_root must be a narrow writable project or temporary path")
    return str(root)


def _validate_artifacts(
    artifacts: tuple[dict[str, Any], ...], *, artifact_root: str | None
) -> None:
    root = Path(validate_artifact_root(artifact_root)) if artifact_root else None
    for index, artifact in enumerate(artifacts):
        try:
            canonical_json(artifact)
        except ValueError as exc:
            raise ValueError(f"artifact {index} is not canonical JSON: {exc}") from exc
        path_value = artifact.get("path")
        if not isinstance(path_value, str) or not Path(path_value).is_absolute():
            raise ValueError(f"artifact {index} path must be absolute")
        if root is not None and not Path(path_value).resolve(strict=False).is_relative_to(root):
            raise ValueError(f"artifact {index} path is outside artifact_root")
        for hash_name in ("sha256",):
            digest = artifact.get(hash_name)
            if digest is not None and (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest.lower())
            ):
                raise ValueError(f"artifact {index} {hash_name} must be a SHA-256 hex digest")


@dataclass(frozen=True)
class AcceptanceRequest:
    """A selection and budget request; constructing one never executes a tier."""

    tiers: tuple[str, ...]
    artifact_root: str
    budgets: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        tiers = tuple(self.tiers)
        unknown = [tier for tier in tiers if tier not in TIER_IDS]
        if unknown:
            raise ValueError(f"unknown tier(s): {unknown}")
        if len(set(tiers)) != len(tiers):
            raise ValueError("duplicate tier selections are not permitted")
        if not tiers:
            raise ValueError("at least one explicit tier is required")
        object.__setattr__(self, "tiers", tiers)
        object.__setattr__(self, "artifact_root", validate_artifact_root(self.artifact_root))
        budgets = _json_object(self.budgets, label="budgets")
        unknown_budgets = set(budgets).difference(TIER_IDS)
        if unknown_budgets:
            raise ValueError(f"budgets contain unknown tier(s): {sorted(unknown_budgets)}")
        normalized = {}
        for tier, budget in budgets.items():
            normalized[tier] = _json_object(budget, label=f"budget.{tier}")
            _validate_budget(normalized[tier], label=f"budget.{tier}")
        object.__setattr__(self, "budgets", normalized)

    def budget_for(self, tier: str, default: Mapping[str, Any]) -> dict[str, Any]:
        return dict(self.budgets.get(tier, default))

    def as_dict(self) -> dict[str, Any]:
        return {
            "tiers": list(self.tiers),
            "artifact_root": self.artifact_root,
            "budgets": {tier: dict(value) for tier, value in self.budgets.items()},
        }


@dataclass(frozen=True)
class TierResult:
    tier: str
    status: str
    command: tuple[str, ...]
    started_at: str
    duration_seconds: float
    budget: Mapping[str, Any]
    observed: Mapping[str, Any]
    artifacts: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.tier not in TIER_IDS:
            raise ValueError(f"unknown tier: {self.tier}")
        if self.status not in EVIDENCE_STATES:
            raise ValueError(f"invalid status: {self.status}")
        if not self.command or not all(isinstance(item, str) and item for item in self.command):
            raise ValueError("command must contain non-empty strings")
        if not isinstance(self.started_at, str) or not self.started_at:
            raise ValueError("started_at must be a non-empty string")
        _validate_finite(self.duration_seconds, label="duration_seconds", nonnegative=True)
        if isinstance(self.duration_seconds, bool):
            raise ValueError("duration_seconds must be numeric")
        _validate_budget(self.budget, label="budget")
        _validate_finite(self.observed, label="observed")
        if self.status == "pass" and self.errors:
            raise ValueError("a passing result cannot contain errors")

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "status": self.status,
            "command": list(self.command),
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "budget": dict(self.budget),
            "observed": dict(self.observed),
            "artifacts": [dict(item) for item in self.artifacts],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TierResult:
        data = _json_object(value, label="tier result")
        artifact_root = data.pop("artifact_root", None)
        required = {
            "tier",
            "status",
            "command",
            "started_at",
            "duration_seconds",
            "budget",
            "observed",
            "artifacts",
            "warnings",
            "errors",
        }
        missing = required.difference(data)
        extra = set(data).difference(required)
        if missing or extra:
            raise ValueError(
                f"malformed tier result; missing={sorted(missing)}, extra={sorted(extra)}"
            )
        command = data["command"]
        if isinstance(command, str):
            command = [command]
        data["command"] = _strings(command, label="command")
        data["budget"] = _json_object(data["budget"], label="budget")
        data["observed"] = _json_object(data["observed"], label="observed")
        raw_artifacts = data["artifacts"]
        if not isinstance(raw_artifacts, (list, tuple)) or not all(
            isinstance(item, Mapping) for item in raw_artifacts
        ):
            raise ValueError("artifacts must be a list of objects")
        data["artifacts"] = tuple(dict(item) for item in raw_artifacts)
        _validate_artifacts(data["artifacts"], artifact_root=artifact_root)
        data["warnings"] = _strings(data["warnings"], label="warnings") if data["warnings"] else ()
        data["errors"] = _strings(data["errors"], label="errors") if data["errors"] else ()
        return cls(**data)


def aggregate_status(results: tuple[TierResult, ...], required_tiers: tuple[str, ...]) -> str:
    by_tier = {result.tier: result for result in results}
    required = [by_tier.get(tier) for tier in required_tiers]
    if any(result is not None and result.status == "blocked" for result in required):
        return "blocked"
    if any(
        result is None or result.status in {"pending", "not_applicable"}
        for result in required
    ):
        return "pending"
    if any(
        result is not None and (result.status == "warn" or result.warnings) for result in required
    ):
        return "warn"
    return "pass"


@dataclass(frozen=True)
class AcceptanceSummary:
    request: AcceptanceRequest
    required_tiers: tuple[str, ...]
    results: tuple[TierResult, ...]
    overall_status: str
    build: str = ""
    license_mode: str = ""
    package_inventory: tuple[dict[str, Any], ...] = ()
    summary_sha256: str = ""

    def payload(self) -> dict[str, Any]:
        return {
            "schema": ACCEPTANCE_SCHEMA,
            "request": self.request.as_dict(),
            "required_tiers": list(self.required_tiers),
            "results": [result.as_dict() for result in self.results],
            "overall_status": self.overall_status,
            "build": self.build,
            "license": self.license_mode,
            "package_inventory": [dict(item) for item in self.package_inventory],
        }

    def as_dict(self) -> dict[str, Any]:
        payload = self.payload()
        payload["summary_sha256"] = self.summary_sha256 or canonical_sha256(payload)
        return payload

    @classmethod
    def create(
        cls,
        *,
        request: AcceptanceRequest,
        results: tuple[TierResult, ...],
        required_tiers: tuple[str, ...] | None = None,
        build: str = "",
        license_mode: str = "",
        package_inventory: tuple[dict[str, Any], ...] = (),
    ) -> AcceptanceSummary:
        required = required_tiers or request.tiers
        unknown = set(required).difference(TIER_IDS)
        if unknown or len(set(required)) != len(required):
            raise ValueError(f"invalid required tiers: {sorted(unknown)}")
        if len({result.tier for result in results}) != len(results):
            raise ValueError("summary contains duplicate tier results")
        status = aggregate_status(results, tuple(required))
        summary = cls(
            request=request,
            required_tiers=tuple(required),
            results=tuple(results),
            overall_status=status,
            build=build,
            license_mode=license_mode,
            package_inventory=tuple(dict(item) for item in package_inventory),
        )
        object.__setattr__(summary, "summary_sha256", canonical_sha256(summary.payload()))
        return summary


__all__ = [
    "ACCEPTANCE_SCHEMA",
    "EVIDENCE_STATES",
    "TIER_IDS",
    "AcceptanceRequest",
    "AcceptanceSummary",
    "TierResult",
    "aggregate_status",
    "canonical_json",
    "canonical_sha256",
    "validate_artifact_root",
]
