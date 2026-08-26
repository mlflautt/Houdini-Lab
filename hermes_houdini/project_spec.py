"""Pure parsing and normalization for ``hermes.houdini.project.v1``.

This module validates project intent only.  It performs no capability discovery,
adapter selection, compilation, Houdini import, graph mutation, or execution.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

PROJECT_SCHEMA = "hermes.houdini.project.v1"
PROJECT_CONTEXTS = frozenset({"SOP", "OBJ", "LOP", "DOP", "TOP", "COP", "CHOP", "APEX"})
EVIDENCE_STATES = frozenset({"pass", "warn", "pending", "blocked", "not_applicable"})
BUDGET_FIELDS = (
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
_INTEGER_BUDGETS = frozenset(BUDGET_FIELDS) - {"cook_seconds"}
_SEMVER = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_HOUDINI_BUILD = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
_TOP_FIELDS = (
    "schema",
    "project_id",
    "title",
    "brief",
    "references",
    "compatibility",
    "roots",
    "seed_policy",
    "timeline",
    "budgets",
    "capability_instances",
    "variants",
    "output_contracts",
    "evidence_gates",
    "human_decisions",
    "automatic_ranking",
    "winner",
)


def _object(value: object, path: str, fields: Sequence[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"{path} keys must be strings")
    missing = [field for field in fields if field not in value]
    unknown = sorted(set(value) - set(fields))
    if missing:
        raise ValueError(f"{path} missing fields: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"{path} unknown fields: {', '.join(unknown)}")
    return value


def _list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _identifier(value: object, path: str) -> str:
    identifier = _string(value, path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", identifier):
        raise ValueError(f"{path} must be a stable identifier")
    return identifier


def _semver(value: object, path: str) -> str:
    version = _string(value, path)
    if not _SEMVER.fullmatch(version):
        raise ValueError(f"{path} must be an exact semantic version")
    return version


def _integer(value: object, path: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{path} must be a {qualifier} integer")
    if value < (1 if positive else 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{path} must be a {qualifier} integer")
    return value


def _number(value: object, path: str, *, integer: bool = False) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite non-negative number")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{path} must be a finite non-negative number")
    if integer and not isinstance(value, int):
        raise ValueError(f"{path} must be a non-negative integer")
    return value


def _unique(values: Sequence[str], path: str) -> None:
    seen: set[str] = set()
    for index, value in enumerate(values):
        if value in seen:
            raise ValueError(f"{path}[{index}] duplicates id: {value}")
        seen.add(value)


def _string_list(value: object, path: str, *, identifiers: bool = False) -> list[str]:
    result = []
    for index, item in enumerate(_list(value, path)):
        result.append(
            _identifier(item, f"{path}[{index}]")
            if identifiers
            else _string(item, f"{path}[{index}]")
        )
    return result


def _json_value(value: object, path: str, active: set[int] | None = None) -> Any:
    """Copy a value into JSON-safe types and reject recursive YAML aliases."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must not contain NaN or Infinity")
        return value
    if not isinstance(value, (Mapping, list)):
        raise ValueError(f"{path} contains a non-JSON value of type {type(value).__name__}")
    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        raise ValueError(f"{path} contains a recursive YAML alias")
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            if not all(isinstance(key, str) for key in value):
                raise ValueError(f"{path} object keys must be strings")
            return {key: _json_value(item, f"{path}.{key}", active) for key, item in value.items()}
        return [_json_value(item, f"{path}[{index}]", active) for index, item in enumerate(value)]
    finally:
        active.remove(identity)


def _project_root(value: str | Path) -> Path:
    root = Path(value).expanduser()
    if not root.is_absolute():
        raise ValueError("project_root must be absolute")
    return root.resolve(strict=False)


def _relative_path(value: object, path: str, root: Path, *, allow_dot: bool = False) -> str:
    raw = _string(value, path)
    embedded = Path(raw).expanduser()
    if embedded.is_absolute():
        raise ValueError(f"{path} must be project-relative")
    resolved = (root / embedded).resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{path} must resolve beneath project_root") from exc
    normalized = relative.as_posix() or "."
    if normalized == "." and not allow_dot:
        raise ValueError(f"{path} must name a path beneath project_root")
    return normalized


def _budget(value: object, path: str) -> dict[str, int | float]:
    raw = _object(value, path, BUDGET_FIELDS)
    return {
        field: _number(raw[field], f"{path}.{field}", integer=field in _INTEGER_BUDGETS)
        for field in BUDGET_FIELDS
    }


def _normalize_references(value: object, root: Path) -> list[dict[str, str]]:
    result = []
    for index, item in enumerate(_list(value, "references")):
        path = f"references[{index}]"
        raw = _object(item, path, ("reference_id", "path", "description"))
        result.append(
            {
                "reference_id": _identifier(raw["reference_id"], f"{path}.reference_id"),
                "path": _relative_path(raw["path"], f"{path}.path", root),
                "description": _string(raw["description"], f"{path}.description"),
            }
        )
    _unique([item["reference_id"] for item in result], "references")
    return result


def _normalize_compatibility(value: object) -> dict[str, Any]:
    raw = _object(
        value,
        "compatibility",
        ("houdini_build", "license_mode", "package_version", "optional_dependencies"),
    )
    build = _string(raw["houdini_build"], "compatibility.houdini_build")
    if not _HOUDINI_BUILD.fullmatch(build):
        raise ValueError("compatibility.houdini_build must be an exact numeric build")
    dependencies = []
    for index, item in enumerate(
        _list(raw["optional_dependencies"], "compatibility.optional_dependencies")
    ):
        path = f"compatibility.optional_dependencies[{index}]"
        dependency = _object(item, path, ("dependency_id", "version"))
        dependencies.append(
            {
                "dependency_id": _identifier(dependency["dependency_id"], f"{path}.dependency_id"),
                "version": _semver(dependency["version"], f"{path}.version"),
            }
        )
    _unique([item["dependency_id"] for item in dependencies], "compatibility.optional_dependencies")
    return {
        "houdini_build": build,
        "license_mode": _string(raw["license_mode"], "compatibility.license_mode"),
        "package_version": _semver(raw["package_version"], "compatibility.package_version"),
        "optional_dependencies": dependencies,
    }


def _normalize_roots(value: object, root: Path) -> dict[str, str]:
    raw = _object(value, "roots", ("project", "assets", "cache", "renders"))
    return {
        name: _relative_path(raw[name], f"roots.{name}", root, allow_dot=name == "project")
        for name in ("project", "assets", "cache", "renders")
    }


def _normalize_seed_policy(value: object) -> dict[str, Any]:
    raw = _object(value, "seed_policy", ("mode", "seed"))
    if raw["mode"] != "fixed":
        raise ValueError("seed_policy.mode must be fixed")
    return {"mode": "fixed", "seed": _integer(raw["seed"], "seed_policy.seed")}


def _normalize_timeline(value: object) -> dict[str, int | float]:
    raw = _object(value, "timeline", ("start_frame", "end_frame", "fps"))
    start = _integer(raw["start_frame"], "timeline.start_frame")
    end = _integer(raw["end_frame"], "timeline.end_frame")
    if end < start:
        raise ValueError("timeline.end_frame must be greater than or equal to timeline.start_frame")
    fps = _number(raw["fps"], "timeline.fps")
    if fps <= 0:
        raise ValueError("timeline.fps must be greater than zero")
    return {"start_frame": start, "end_frame": end, "fps": fps}


def _normalize_budgets(value: object) -> dict[str, Any]:
    raw = _object(value, "budgets", ("aggregate", "stages"))
    stages = []
    for index, item in enumerate(_list(raw["stages"], "budgets.stages")):
        path = f"budgets.stages[{index}]"
        stage = _object(item, path, ("instance_id", "limits"))
        stages.append(
            {
                "instance_id": _identifier(stage["instance_id"], f"{path}.instance_id"),
                "limits": _budget(stage["limits"], f"{path}.limits"),
            }
        )
    _unique([item["instance_id"] for item in stages], "budgets.stages")
    return {"aggregate": _budget(raw["aggregate"], "budgets.aggregate"), "stages": stages}


def _normalize_instances(value: object) -> list[dict[str, Any]]:
    fields = (
        "instance_id",
        "capability_id",
        "capability_version",
        "context",
        "inputs",
        "output_contracts",
        "variant_scope",
        "dependencies",
        "requested_evidence",
    )
    result = []
    for index, item in enumerate(_list(value, "capability_instances")):
        path = f"capability_instances[{index}]"
        raw = _object(item, path, fields)
        context = _string(raw["context"], f"{path}.context")
        if context not in PROJECT_CONTEXTS:
            raise ValueError(f"{path}.context must be a declared Houdini context")
        inputs = raw["inputs"]
        if not isinstance(inputs, Mapping):
            raise ValueError(f"{path}.inputs must be an object")
        result.append(
            {
                "instance_id": _identifier(raw["instance_id"], f"{path}.instance_id"),
                "capability_id": _identifier(raw["capability_id"], f"{path}.capability_id"),
                "capability_version": _semver(
                    raw["capability_version"], f"{path}.capability_version"
                ),
                "context": context,
                "inputs": _json_value(inputs, f"{path}.inputs"),
                "output_contracts": _string_list(
                    raw["output_contracts"], f"{path}.output_contracts", identifiers=True
                ),
                "variant_scope": _string_list(
                    raw["variant_scope"], f"{path}.variant_scope", identifiers=True
                ),
                "dependencies": _string_list(
                    raw["dependencies"], f"{path}.dependencies", identifiers=True
                ),
                "requested_evidence": _string_list(
                    raw["requested_evidence"], f"{path}.requested_evidence", identifiers=True
                ),
            }
        )
    if not result:
        raise ValueError("capability_instances must contain at least one instance")
    _unique([item["instance_id"] for item in result], "capability_instances")
    return result


def _normalize_variants(value: object) -> list[dict[str, Any]]:
    fields = (
        "variant_id",
        "title",
        "description",
        "human_rating",
        "selected_for_continuation",
    )
    result = []
    for index, item in enumerate(_list(value, "variants")):
        path = f"variants[{index}]"
        raw = _object(item, path, fields)
        if raw["human_rating"] is not None:
            raise ValueError(f"{path}.human_rating must remain null pending human review")
        if raw["selected_for_continuation"] is not None:
            raise ValueError(
                f"{path}.selected_for_continuation must remain null pending human review"
            )
        result.append(
            {
                "variant_id": _identifier(raw["variant_id"], f"{path}.variant_id"),
                "title": _string(raw["title"], f"{path}.title"),
                "description": _string(raw["description"], f"{path}.description"),
                "human_rating": None,
                "selected_for_continuation": None,
            }
        )
    if result and len(result) < 3:
        raise ValueError("variants must contain at least three equal-status alternatives")
    _unique([item["variant_id"] for item in result], "variants")
    return result


def _normalize_output_contracts(value: object, root: Path) -> list[dict[str, str]]:
    fields = ("contract_id", "producer_instance_id", "context", "name", "artifact_path")
    result = []
    for index, item in enumerate(_list(value, "output_contracts")):
        path = f"output_contracts[{index}]"
        raw = _object(item, path, fields)
        context = _string(raw["context"], f"{path}.context")
        if context not in PROJECT_CONTEXTS:
            raise ValueError(f"{path}.context must be a declared Houdini context")
        result.append(
            {
                "contract_id": _identifier(raw["contract_id"], f"{path}.contract_id"),
                "producer_instance_id": _identifier(
                    raw["producer_instance_id"], f"{path}.producer_instance_id"
                ),
                "context": context,
                "name": _string(raw["name"], f"{path}.name"),
                "artifact_path": _relative_path(
                    raw["artifact_path"], f"{path}.artifact_path", root
                ),
            }
        )
    _unique([item["contract_id"] for item in result], "output_contracts")
    return result


def _normalize_evidence_gates(value: object) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(_list(value, "evidence_gates")):
        path = f"evidence_gates[{index}]"
        raw = _object(item, path, ("gate_id", "evidence_type", "required", "status"))
        if not isinstance(raw["required"], bool):
            raise ValueError(f"{path}.required must be a boolean")
        status = _string(raw["status"], f"{path}.status")
        if status not in EVIDENCE_STATES:
            raise ValueError(f"{path}.status is not a supported evidence state")
        result.append(
            {
                "gate_id": _identifier(raw["gate_id"], f"{path}.gate_id"),
                "evidence_type": _identifier(raw["evidence_type"], f"{path}.evidence_type"),
                "required": raw["required"],
                "status": status,
            }
        )
    _unique([item["gate_id"] for item in result], "evidence_gates")
    return result


def _normalize_human_decisions(value: object) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(_list(value, "human_decisions")):
        path = f"human_decisions[{index}]"
        raw = _object(item, path, ("decision_id", "prompt", "winner", "selected_for_continuation"))
        if raw["winner"] is not None:
            raise ValueError(f"{path}.winner must remain null pending human review")
        if raw["selected_for_continuation"] is not None:
            raise ValueError(
                f"{path}.selected_for_continuation must remain null pending human review"
            )
        result.append(
            {
                "decision_id": _identifier(raw["decision_id"], f"{path}.decision_id"),
                "prompt": _string(raw["prompt"], f"{path}.prompt"),
                "winner": None,
                "selected_for_continuation": None,
            }
        )
    _unique([item["decision_id"] for item in result], "human_decisions")
    return result


def _validate_references(normalized: Mapping[str, Any]) -> None:
    instances = {item["instance_id"]: item for item in normalized["capability_instances"]}
    variants = {item["variant_id"] for item in normalized["variants"]}
    contracts = {item["contract_id"]: item for item in normalized["output_contracts"]}
    gates = {item["gate_id"] for item in normalized["evidence_gates"]}
    stage_ids = {item["instance_id"] for item in normalized["budgets"]["stages"]}
    if stage_ids != set(instances):
        missing = sorted(set(instances) - stage_ids)
        extra = sorted(stage_ids - set(instances))
        raise ValueError(
            f"budgets.stages must match capability instances; missing={missing}, extra={extra}"
        )
    for index, instance in enumerate(normalized["capability_instances"]):
        path = f"capability_instances[{index}]"
        for dependency in instance["dependencies"]:
            if dependency not in instances:
                raise ValueError(f"{path}.dependencies references unknown instance: {dependency}")
        for variant in instance["variant_scope"]:
            if variant not in variants:
                raise ValueError(f"{path}.variant_scope references unknown variant: {variant}")
        for gate in instance["requested_evidence"]:
            if gate not in gates:
                raise ValueError(f"{path}.requested_evidence references unknown gate: {gate}")
        for contract_id in instance["output_contracts"]:
            contract = contracts.get(contract_id)
            if contract is None:
                raise ValueError(
                    f"{path}.output_contracts references unknown contract: {contract_id}"
                )
            if contract["producer_instance_id"] != instance["instance_id"]:
                raise ValueError(
                    f"{path}.output_contracts references a contract owned by another instance"
                )
            if contract["context"] != instance["context"]:
                raise ValueError(f"{path}.output_contracts context does not match the instance")
    for index, contract in enumerate(normalized["output_contracts"]):
        if contract["producer_instance_id"] not in instances:
            raise ValueError(
                f"output_contracts[{index}].producer_instance_id references unknown instance"
            )


def normalize_project_spec(
    value: Mapping[str, object], *, project_root: str | Path
) -> dict[str, Any]:
    """Validate and normalize one project mapping into canonical JSON-shaped intent."""

    root = _project_root(project_root)
    raw = _object(value, "project", _TOP_FIELDS)
    if raw["schema"] != PROJECT_SCHEMA:
        raise ValueError(f"project.schema must be {PROJECT_SCHEMA}")
    if raw["automatic_ranking"] is not False:
        raise ValueError("project.automatic_ranking must be false")
    if raw["winner"] is not None:
        raise ValueError("project.winner must remain null pending human review")
    normalized = {
        "schema": PROJECT_SCHEMA,
        "project_id": _identifier(raw["project_id"], "project.project_id"),
        "title": _string(raw["title"], "project.title"),
        "brief": _string(raw["brief"], "project.brief"),
        "references": _normalize_references(raw["references"], root),
        "compatibility": _normalize_compatibility(raw["compatibility"]),
        "roots": _normalize_roots(raw["roots"], root),
        "seed_policy": _normalize_seed_policy(raw["seed_policy"]),
        "timeline": _normalize_timeline(raw["timeline"]),
        "budgets": _normalize_budgets(raw["budgets"]),
        "capability_instances": _normalize_instances(raw["capability_instances"]),
        "variants": _normalize_variants(raw["variants"]),
        "output_contracts": _normalize_output_contracts(raw["output_contracts"], root),
        "evidence_gates": _normalize_evidence_gates(raw["evidence_gates"]),
        "human_decisions": _normalize_human_decisions(raw["human_decisions"]),
        "automatic_ranking": False,
        "winner": None,
    }
    _validate_references(normalized)
    return normalized


def load_project_spec(path: str | Path, *, project_root: str | Path) -> dict[str, Any]:
    """Load one explicitly supplied YAML file and normalize it; no discovery is performed."""

    root = _project_root(project_root)
    source = Path(path).expanduser()
    source = source if source.is_absolute() else root / source
    resolved = source.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("project specification path must resolve beneath project_root") from exc
    with resolved.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, Mapping):
        raise ValueError("project specification YAML root must be an object")
    return normalize_project_spec(value, project_root=root)


def project_spec_sha256(normalized: Mapping[str, object]) -> str:
    """Hash every semantic field using stable canonical JSON."""

    if not isinstance(normalized, Mapping):
        raise ValueError("normalized project specification must be an object")
    safe = _json_value(normalized, "project")
    encoded = json.dumps(
        safe, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "BUDGET_FIELDS",
    "PROJECT_CONTEXTS",
    "PROJECT_SCHEMA",
    "load_project_spec",
    "normalize_project_spec",
    "project_spec_sha256",
]
