"""Pure registry for exact, versioned project contract adapters.

Adapter records are composition metadata.  This module deliberately does not import
Houdini, inspect the recipe catalog, or execute either recipes or native fallbacks.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

ADAPTER_SCHEMA = "hermes.houdini.project_adapter.v1"
REGISTRY_SCHEMA = "hermes.houdini.project_adapter_registry.v1"
EVIDENCE_STATES = {"pass", "warn", "pending", "blocked", "not_applicable"}
RISK_CLASSES = {"read_only", "low", "medium", "high", "external"}
CONTEXTS = {"SOP", "OBJ", "LOP", "DOP", "TOP", "COP", "CHOP", "APEX", "ROP"}
_SEMVER = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]*")
_RECORD_FIELDS = {
    "schema",
    "adapter_id",
    "version",
    "from_contract",
    "to_contract",
    "source_context",
    "target_context",
    "recipe",
    "native_fallback",
    "risk",
    "approvals",
    "budget_effect",
    "tested_builds",
    "license_modes",
    "optional_dependencies",
    "evidence_status",
    "source_audit",
}


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"adapter record must be finite JSON data: {exc}") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _required_string(record: Mapping[str, Any], name: str) -> str:
    value = record.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"adapter.{name} must be a non-empty string")
    return value


def _strings(record: Mapping[str, Any], name: str, *, nonempty: bool = False) -> list[str]:
    value = record.get(name)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"adapter.{name} must be a list of non-empty strings")
    if nonempty and not value:
        raise ValueError(f"adapter.{name} must not be empty")
    if len(value) != len(set(value)):
        raise ValueError(f"adapter.{name} must not contain duplicates")
    return list(value)


def _json_value(value: Any, path: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain finite values")
        return value
    if isinstance(value, list):
        return [_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{path} keys must be non-empty strings")
            normalized[key] = _json_value(item, f"{path}.{key}")
        return normalized
    raise ValueError(f"{path} must contain JSON-shaped values")


def _identity(record: Mapping[str, Any]) -> dict[str, str]:
    return {
        "adapter_id": str(record["adapter_id"]),
        "version": str(record["version"]),
        "source": str(record["source"]),
        "content_sha256": str(record["content_sha256"]),
    }


def normalize_adapter_record(value: Mapping[str, Any], *, source: str = "") -> dict[str, Any]:
    """Validate one descriptor and return canonical JSON-shaped adapter metadata."""
    if not isinstance(value, Mapping):
        raise ValueError("adapter record must be an object")
    unknown = set(value) - _RECORD_FIELDS
    if unknown:
        raise ValueError(f"adapter has unknown fields: {sorted(unknown)}")
    missing = _RECORD_FIELDS.difference(value) - {"recipe", "native_fallback"}
    if missing:
        raise ValueError(f"adapter is missing fields: {sorted(missing)}")
    if value.get("schema") != ADAPTER_SCHEMA:
        raise ValueError(f"adapter.schema must be {ADAPTER_SCHEMA}")

    adapter_id = _required_string(value, "adapter_id")
    if _IDENTIFIER.fullmatch(adapter_id) is None:
        raise ValueError("adapter.adapter_id must be a lowercase dotted identifier")
    version = _required_string(value, "version")
    if _SEMVER.fullmatch(version) is None:
        raise ValueError("adapter.version must be exact semantic version X.Y.Z")

    recipe = value.get("recipe")
    native_fallback = value.get("native_fallback")
    if (recipe is None) == (native_fallback is None):
        raise ValueError("adapter requires exactly one of recipe or native_fallback")
    normalized_recipe: dict[str, str] | None = None
    if recipe is not None:
        if not isinstance(recipe, Mapping) or set(recipe) != {"id", "version"}:
            raise ValueError("adapter.recipe must contain exactly id and version")
        recipe_id = _required_string(recipe, "id")
        recipe_version = _required_string(recipe, "version")
        if _IDENTIFIER.fullmatch(recipe_id) is None:
            raise ValueError("adapter.recipe.id must be a lowercase dotted identifier")
        if _SEMVER.fullmatch(recipe_version) is None:
            raise ValueError("adapter.recipe.version must be exact semantic version X.Y.Z")
        normalized_recipe = {"id": recipe_id, "version": recipe_version}
    elif not isinstance(native_fallback, str) or _IDENTIFIER.fullmatch(native_fallback) is None:
        raise ValueError("adapter.native_fallback must be a lowercase dotted identifier")

    source_context = _required_string(value, "source_context")
    target_context = _required_string(value, "target_context")
    if source_context not in CONTEXTS or target_context not in CONTEXTS:
        raise ValueError("adapter contexts must be exact supported Houdini context names")
    risk = _required_string(value, "risk")
    if risk not in RISK_CLASSES:
        raise ValueError(f"adapter.risk is unsupported: {risk}")
    evidence_status = _required_string(value, "evidence_status")
    if evidence_status not in EVIDENCE_STATES:
        raise ValueError(f"adapter.evidence_status is unsupported: {evidence_status}")

    normalized = {
        "schema": ADAPTER_SCHEMA,
        "adapter_id": adapter_id,
        "version": version,
        "from_contract": _required_string(value, "from_contract"),
        "to_contract": _required_string(value, "to_contract"),
        "source_context": source_context,
        "target_context": target_context,
        "risk": risk,
        "approvals": _strings(value, "approvals"),
        "budget_effect": _json_value(value["budget_effect"], "adapter.budget_effect"),
        "tested_builds": _strings(value, "tested_builds", nonempty=True),
        "license_modes": _strings(value, "license_modes", nonempty=True),
        "optional_dependencies": _strings(value, "optional_dependencies"),
        "evidence_status": evidence_status,
        "source_audit": _strings(value, "source_audit", nonempty=True),
        "source": str(source),
    }
    if normalized_recipe is not None:
        normalized["recipe"] = normalized_recipe
    else:
        normalized["native_fallback"] = native_fallback
    if not isinstance(normalized["budget_effect"], dict):
        raise ValueError("adapter.budget_effect must be an object")
    normalized["content_sha256"] = _sha256(normalized)
    return normalized


def load_adapter_record(path: str | Path) -> dict[str, Any]:
    """Load one explicitly named YAML descriptor without discovery or execution."""
    descriptor_path = Path(path)
    try:
        value = yaml.safe_load(descriptor_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load adapter descriptor {descriptor_path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"adapter descriptor {descriptor_path} must contain an object")
    return normalize_adapter_record(value, source=descriptor_path.as_posix())


def build_adapter_registry(paths: Iterable[str | Path]) -> dict[str, Any]:
    """Load explicit paths into a stable registry ordered independently of input order."""
    if isinstance(paths, (str, bytes, Path)):
        raise ValueError("adapter paths must be an iterable of paths, not one path")
    records = [load_adapter_record(path) for path in paths]
    records.sort(key=lambda item: (item["adapter_id"], item["version"], item["source"]))
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        key = (record["adapter_id"], record["version"], record["source"])
        if key in seen:
            raise ValueError(f"duplicate adapter registry identity: {key}")
        seen.add(key)
    registry = {"schema": REGISTRY_SCHEMA, "record_count": len(records), "records": records}
    registry["registry_sha256"] = _sha256(registry)
    return registry


def resolve_adapter(
    registry: Mapping[str, Any],
    *,
    from_contract: str,
    to_contract: str,
    version: str,
    build: str,
    license_mode: str,
    allowed_dependencies: Iterable[str],
) -> dict[str, Any]:
    """Resolve one exact adapter identity and report all candidates without preference."""
    if not isinstance(registry, Mapping) or not isinstance(registry.get("records"), list):
        raise ValueError("adapter registry must contain a records list")
    for name, value in {
        "from_contract": from_contract,
        "to_contract": to_contract,
        "build": build,
        "license_mode": license_mode,
    }.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"resolve.{name} must be a non-empty string")
    if not isinstance(version, str) or _SEMVER.fullmatch(version) is None:
        raise ValueError("resolve.version must be exact semantic version X.Y.Z")
    if isinstance(allowed_dependencies, (str, bytes)):
        raise ValueError("resolve.allowed_dependencies must be an iterable of strings")
    dependencies = list(allowed_dependencies)
    if not all(isinstance(item, str) and item for item in dependencies):
        raise ValueError("resolve.allowed_dependencies must contain non-empty strings")
    dependencies = sorted(set(dependencies))
    allowed = set(dependencies)

    contract_candidates = [
        record
        for record in registry["records"]
        if isinstance(record, Mapping)
        and record.get("from_contract") == from_contract
        and record.get("to_contract") == to_contract
    ]
    contract_candidates.sort(
        key=lambda record: (
            str(record.get("adapter_id", "")),
            str(record.get("version", "")),
            str(record.get("source", "")),
        )
    )
    exact = [record for record in contract_candidates if record.get("version") == version]
    identities = [_identity(record) for record in exact or contract_candidates]
    query = {
        "from_contract": from_contract,
        "to_contract": to_contract,
        "version": version,
        "build": build,
        "license_mode": license_mode,
        "allowed_dependencies": dependencies,
    }
    if not exact:
        return {"status": "missing", "query": query, "candidates": identities}
    if len(exact) > 1:
        return {"status": "ambiguous", "query": query, "candidates": identities}

    record = exact[0]
    reasons = []
    if build not in record["tested_builds"]:
        reasons.append({"code": "unsupported_build", "required": list(record["tested_builds"])})
    if license_mode not in record["license_modes"]:
        reasons.append(
            {"code": "unsupported_license", "required": list(record["license_modes"])}
        )
    missing_dependencies = [
        dependency for dependency in record["optional_dependencies"] if dependency not in allowed
    ]
    if missing_dependencies:
        reasons.append({"code": "missing_dependencies", "required": missing_dependencies})
    if reasons:
        return {
            "status": "incompatible",
            "query": query,
            "candidates": identities,
            "reasons": reasons,
        }
    return {
        "status": "resolved",
        "query": query,
        "candidates": identities,
        "adapter": dict(record),
    }


__all__ = [
    "build_adapter_registry",
    "load_adapter_record",
    "normalize_adapter_record",
    "resolve_adapter",
]
