"""Pure schemas for the v0.30 Hermes/Houdini control plane.

The objects in this module are deliberately JSON-shaped and Houdini-independent.  They
preserve alternatives and incomplete evidence rather than turning orchestration metadata
into an aesthetic ranking system.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

CONTROL_PLANE_SCHEMA_VERSION = "1.0"
EVIDENCE_STATES = {"pass", "warn", "pending", "blocked", "not_applicable"}
CAPABILITY_KINDS = {"tool", "recipe", "hda", "skill"}


def canonical_json(value: Any) -> str:
    """Return the stable JSON representation used by catalog and handoff hashes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _strings(name: str, values: Any) -> list[str]:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError(f"{name} must be a list of strings")
    return list(values)


def _object(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return dict(value)


@dataclass(frozen=True)
class CompatibilityIdentity:
    houdini_build: str
    python_version: str
    license_mode: str
    package_version: str
    protocol_version: str = "1.0"
    optional_dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "houdini_build",
            "python_version",
            "license_mode",
            "package_version",
            "protocol_version",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"compatibility.{name} must be a non-empty string")
        if not all(isinstance(item, str) and item for item in self.optional_dependencies):
            raise ValueError("compatibility.optional_dependencies must contain strings")

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["optional_dependencies"] = list(self.optional_dependencies)
        return data

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CompatibilityIdentity:
        data = _object("compatibility", value)
        data["optional_dependencies"] = tuple(
            _strings("compatibility.optional_dependencies", data.get("optional_dependencies", []))
        )
        return cls(**data)


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    version: str
    kind: str
    summary: str
    contexts: tuple[str, ...]
    risk: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: tuple[str, ...] = ()
    approvals: tuple[str, ...] = ()
    cook_budget: dict[str, Any] = field(default_factory=dict)
    license: dict[str, Any] = field(default_factory=dict)
    tested_builds: tuple[str, ...] = ()
    optional_dependencies: tuple[str, ...] = ()
    fallbacks: tuple[str, ...] = ()
    evidence_status: str = "pending"
    source: str = ""

    def __post_init__(self) -> None:
        if not self.capability_id or not self.version or not self.summary:
            raise ValueError("capability id, version, and summary are required")
        if self.kind not in CAPABILITY_KINDS:
            raise ValueError(f"unsupported capability kind: {self.kind}")
        if self.evidence_status not in EVIDENCE_STATES:
            raise ValueError(f"unsupported evidence status: {self.evidence_status}")
        if not self.contexts or not all(isinstance(item, str) and item for item in self.contexts):
            raise ValueError("capability contexts must contain at least one string")
        for name in ("outputs", "approvals", "tested_builds", "optional_dependencies", "fallbacks"):
            if not all(isinstance(item, str) and item for item in getattr(self, name)):
                raise ValueError(f"capability {name} must contain strings")

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for name in (
            "contexts",
            "outputs",
            "approvals",
            "tested_builds",
            "optional_dependencies",
            "fallbacks",
        ):
            data[name] = list(data[name])
        return data


@dataclass(frozen=True)
class IntentPlan:
    objective: str
    selected_capabilities: tuple[dict[str, str], ...]
    alternatives: tuple[dict[str, Any], ...]
    constraints: dict[str, Any]
    resource_estimate: dict[str, Any]
    approvals: tuple[dict[str, Any], ...]
    verification: dict[str, Any]
    human_decisions: tuple[dict[str, Any], ...] = ()
    automatic_ranking: bool = False
    winner: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ValueError("intent plan objective is required")
        if not self.selected_capabilities:
            raise ValueError("intent plan must select at least one capability")
        if self.automatic_ranking:
            raise ValueError("automatic aesthetic ranking is not permitted")
        if self.winner is not None:
            raise ValueError("intent plan winner must remain null pending human review")
        required_estimates = {"seconds", "memory_bytes", "frames", "output_bytes"}
        missing = required_estimates.difference(self.resource_estimate)
        if missing:
            raise ValueError(f"resource estimate missing keys: {sorted(missing)}")
        required_verification = {"graph", "data", "visual"}
        missing_verification = required_verification.difference(self.verification)
        if missing_verification:
            raise ValueError(f"verification missing keys: {sorted(missing_verification)}")

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "schema": "hermes.houdini.intent_plan",
                "schema_version": CONTROL_PLANE_SCHEMA_VERSION,
                "selected_capabilities": [dict(item) for item in self.selected_capabilities],
                "alternatives": [dict(item) for item in self.alternatives],
                "approvals": [dict(item) for item in self.approvals],
                "human_decisions": [dict(item) for item in self.human_decisions],
            }
        )
        return data

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> IntentPlan:
        data = _object("intent_plan", value)
        if data.get("schema", "hermes.houdini.intent_plan") != "hermes.houdini.intent_plan":
            raise ValueError("unsupported intent plan schema")
        if data.get("schema_version", CONTROL_PLANE_SCHEMA_VERSION) != CONTROL_PLANE_SCHEMA_VERSION:
            raise ValueError("unsupported intent plan schema version")
        data.pop("schema", None)
        data.pop("schema_version", None)
        for name in ("selected_capabilities", "alternatives", "approvals", "human_decisions"):
            values = data.get(name, [])
            if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
                raise ValueError(f"intent plan {name} must be a list of objects")
            data[name] = tuple(dict(item) for item in values)
        data["constraints"] = _object("intent_plan.constraints", data.get("constraints", {}))
        data["resource_estimate"] = _object(
            "intent_plan.resource_estimate", data.get("resource_estimate", {})
        )
        data["verification"] = _object("intent_plan.verification", data.get("verification", {}))
        return cls(**data)


@dataclass(frozen=True)
class HandoffBundle:
    project_id: str
    session_id: str
    project_root: str
    compatibility: CompatibilityIdentity
    intent_plan: IntentPlan
    checkpoint: str
    replay_logs: tuple[str, ...]
    artifacts: tuple[dict[str, Any], ...]
    stable_nodes: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()
    rejected_alternatives: tuple[dict[str, Any], ...] = ()
    human_feedback: tuple[dict[str, Any], ...] = ()
    pending_gates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.project_id or not self.session_id or not self.project_root:
            raise ValueError("handoff project_id, session_id, and project_root are required")
        if not isinstance(self.checkpoint, str):
            raise ValueError("handoff checkpoint must be a string")
        for name in ("replay_logs", "warnings", "pending_gates"):
            if not all(isinstance(item, str) for item in getattr(self, name)):
                raise ValueError(f"handoff {name} must contain strings")
        for item in self.evidence:
            if item.get("status") not in EVIDENCE_STATES:
                raise ValueError(f"invalid handoff evidence status: {item.get('status')}")

    def payload(self) -> dict[str, Any]:
        return {
            "schema": "hermes.houdini.handoff",
            "schema_version": CONTROL_PLANE_SCHEMA_VERSION,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "project_root": self.project_root,
            "compatibility": self.compatibility.as_dict(),
            "intent_plan": self.intent_plan.as_dict(),
            "checkpoint": self.checkpoint,
            "replay_logs": list(self.replay_logs),
            "artifacts": [dict(item) for item in self.artifacts],
            "stable_nodes": [dict(item) for item in self.stable_nodes],
            "evidence": [dict(item) for item in self.evidence],
            "warnings": list(self.warnings),
            "rejected_alternatives": [dict(item) for item in self.rejected_alternatives],
            "human_feedback": [dict(item) for item in self.human_feedback],
            "pending_gates": list(self.pending_gates),
        }

    def as_dict(self) -> dict[str, Any]:
        data = self.payload()
        data["content_sha256"] = content_hash(data)
        return data

    @classmethod
    def from_dict(cls, value: dict[str, Any], *, verify_hash: bool = True) -> HandoffBundle:
        data = _object("handoff", value)
        if data.get("schema") != "hermes.houdini.handoff":
            raise ValueError("unsupported handoff schema")
        if data.get("schema_version") != CONTROL_PLANE_SCHEMA_VERSION:
            raise ValueError("unsupported handoff schema version")
        recorded_hash = data.pop("content_sha256", "")
        if verify_hash and (not recorded_hash or recorded_hash != content_hash(data)):
            raise ValueError("handoff content hash mismatch")
        data.pop("schema")
        data.pop("schema_version")
        data["compatibility"] = CompatibilityIdentity.from_dict(data["compatibility"])
        data["intent_plan"] = IntentPlan.from_dict(data["intent_plan"])
        for name in ("replay_logs", "warnings", "pending_gates"):
            data[name] = tuple(_strings(f"handoff.{name}", data.get(name, [])))
        for name in ("artifacts", "stable_nodes", "evidence", "rejected_alternatives", "human_feedback"):
            values = data.get(name, [])
            if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
                raise ValueError(f"handoff.{name} must be a list of objects")
            data[name] = tuple(dict(item) for item in values)
        return cls(**data)


__all__ = [
    "CAPABILITY_KINDS",
    "CONTROL_PLANE_SCHEMA_VERSION",
    "EVIDENCE_STATES",
    "CapabilityRecord",
    "CompatibilityIdentity",
    "HandoffBundle",
    "IntentPlan",
    "canonical_json",
    "content_hash",
]
