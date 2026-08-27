"""Pure integration pipeline for validated Hermes Houdini project plans.

This module is the only G002 seam that imports the four parallel lane modules.  It
normalizes a project, selects exact capability records, adapts the frozen plain
mapping contracts, compiles a non-executable plan, and builds a dry observation
index.  It never imports ``hou`` or executes a planned stage.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

from .capabilities import build_catalog
from .project_adapters import normalize_adapter_record
from .project_compiler import compile_project
from .project_observer import build_project_index
from .project_spec import load_project_spec, project_spec_sha256

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ADAPTER_ROOT = _ROOT / "project_contracts" / "adapters"
_PARENT_CONTRACTS = {
    "SOP": "project.parent.sop.v1",
    "OBJ": "project.parent.obj.v1",
    "LOP": "project.parent.lop.v1",
    "DOP": "project.parent.dop.v1",
    "TOP": "project.parent.top.v1",
    "COP": "project.parent.cop.v1",
    "CHOP": "project.parent.chop.v1",
    "APEX": "project.parent.apex.v1",
}
_BUDGET_ALIASES = {
    "max_points": "points",
    "max_primitives": "primitives",
    "max_memory_bytes": "peak_memory_bytes",
    "max_seconds": "cook_seconds",
    "max_frames": "frames",
    "render_frames": "frames",
}


def _canonical_hash(value: Mapping[str, Any], *, exclude: Iterable[str] = ()) -> str:
    payload = {key: item for key, item in value.items() if key not in set(exclude)}
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_project_adapter_registry(
    adapter_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load the exact packaged adapter descriptors with portable source identities."""
    root = Path(adapter_root or _DEFAULT_ADAPTER_ROOT).resolve(strict=True)
    paths = sorted(root.glob("*.yaml"), key=lambda path: path.name)
    if not paths:
        raise ValueError(f"no project adapter descriptors found beneath {root}")
    records = []
    for path in paths:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ValueError(f"cannot load adapter descriptor {path}: {exc}") from exc
        if not isinstance(value, Mapping):
            raise ValueError(f"adapter descriptor {path} must contain an object")
        records.append(
            normalize_adapter_record(
                value,
                source=f"project_contracts/adapters/{path.name}",
            )
        )
    records.sort(key=lambda item: (item["adapter_id"], item["version"], item["source"]))
    registry: dict[str, Any] = {
        "schema": "hermes.houdini.project_adapter_registry.v1",
        "record_count": len(records),
        "records": records,
    }
    registry["registry_sha256"] = _canonical_hash(registry)
    return registry


def select_project_catalog(
    project: Mapping[str, Any], *, catalog: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Select only exact capability identities named by a normalized project."""
    source = dict(catalog or build_catalog())
    records = source.get("records")
    if not isinstance(records, list):
        raise ValueError("capability catalog must contain a records list")
    identities = {
        (item.get("capability_id"), item.get("capability_version"))
        for item in project.get("capability_instances", [])
        if isinstance(item, Mapping)
    }
    selected = [
        dict(record)
        for record in records
        if isinstance(record, Mapping)
        and (record.get("capability_id"), record.get("version")) in identities
    ]
    selected.sort(
        key=lambda item: (
            str(item.get("kind", "")),
            str(item.get("capability_id", "")),
            str(item.get("version", "")),
            str(item.get("source", "")),
        )
    )
    result: dict[str, Any] = {
        "schema": source.get("schema", "hermes.houdini.capability_catalog"),
        "schema_version": source.get("schema_version", "1.0"),
        "package_version": source.get("package_version"),
        "filters": {"exact_project_identities": sorted(f"{a}@{b}" for a, b in identities)},
        "record_count": len(selected),
        "records": selected,
    }
    result["catalog_sha256"] = _canonical_hash(result)
    return result


def _compiler_adapter(record: Mapping[str, Any]) -> dict[str, Any]:
    adapted = dict(record)
    license_modes = adapted.get("license_modes", [])
    if not isinstance(license_modes, list) or len(license_modes) != 1:
        raise ValueError(
            f"adapter {adapted.get('adapter_id')} must declare exactly one compiler license mode"
        )
    adapted["license_mode"] = license_modes[0]
    raw_effect = adapted.get("budget_effect", {})
    if not isinstance(raw_effect, Mapping):
        raise ValueError(f"adapter {adapted.get('adapter_id')} budget_effect must be an object")
    effect: dict[str, int | float] = {}
    for name, value in raw_effect.items():
        target = _BUDGET_ALIASES.get(str(name))
        if target is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"adapter budget effect {name} must be numeric")
        effect[target] = effect.get(target, 0) + value
    adapted["budget_effect"] = effect
    return adapted


def adapt_project_for_compiler(
    project: Mapping[str, Any], *, adapter_records: Iterable[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Reconcile the accepted lane mappings without mutating either source mapping."""
    stages = project.get("budgets", {}).get("stages", [])
    if not isinstance(stages, list):
        raise ValueError("project budgets.stages must be a list")
    stage_budgets = {
        item["instance_id"]: dict(item["limits"])
        for item in stages
        if isinstance(item, Mapping)
        and isinstance(item.get("instance_id"), str)
        and isinstance(item.get("limits"), Mapping)
    }
    gates = {
        item["gate_id"]: dict(item)
        for item in project.get("evidence_gates", [])
        if isinstance(item, Mapping) and isinstance(item.get("gate_id"), str)
    }
    instances: list[dict[str, Any]] = []
    ports_by_instance: dict[str, dict[str, str]] = {}
    permitted_project_fallbacks: set[str] = set()
    for raw in project.get("capability_instances", []):
        if not isinstance(raw, Mapping):
            raise ValueError("project capability instances must be objects")
        instance_id = str(raw["instance_id"])
        outputs = list(raw.get("output_contracts", []))
        if not outputs:
            raise ValueError(f"instance {instance_id} must declare at least one output contract")
        ports = {
            ("main" if index == 0 else f"output_{index + 1}"): str(contract)
            for index, contract in enumerate(outputs)
        }
        ports_by_instance[instance_id] = ports
        inputs = raw.get("inputs", {})
        if not isinstance(inputs, Mapping):
            raise ValueError(f"instance {instance_id} inputs must be an object")
        normalized_inputs: dict[str, Any] = {}
        instance_fallbacks: set[str] = set()
        for port, binding in inputs.items():
            if not isinstance(binding, Mapping):
                raise ValueError(
                    f"instance {instance_id} input {port} must be an explicit contract binding"
                )
            item = dict(binding)
            fallbacks = item.get("permitted_native_fallbacks", [])
            if not isinstance(fallbacks, list):
                raise ValueError(f"instance {instance_id} input {port} fallbacks must be a list")
            instance_fallbacks.update(str(value) for value in fallbacks)
            permitted_project_fallbacks.update(instance_fallbacks)
            normalized_inputs[str(port)] = item
        requested = []
        for gate_id in raw.get("requested_evidence", []):
            if gate_id not in gates:
                raise ValueError(f"instance {instance_id} references unknown evidence gate {gate_id}")
            requested.append(dict(gates[gate_id]))
        context = str(raw["context"])
        instances.append(
            {
                **dict(raw),
                "inputs": normalized_inputs,
                "output_contracts": ports,
                "requested_evidence": requested,
                "parent_contract": _PARENT_CONTRACTS[context],
                "scope": {
                    "graph_edit": "planned_registered_graph",
                    "cook": "planned_bounded",
                    "cache": "planned_explicit",
                    "render": "none",
                },
                "budget": dict(stage_budgets[instance_id]),
                "approvals": [],
                "permitted_native_fallbacks": sorted(instance_fallbacks),
            }
        )
    outputs = []
    for raw in project.get("output_contracts", []):
        if not isinstance(raw, Mapping):
            raise ValueError("project output contracts must be objects")
        producer = str(raw["producer_instance_id"])
        matching = [
            port
            for port, contract in ports_by_instance.get(producer, {}).items()
            if contract == raw.get("contract_id")
        ]
        if len(matching) != 1:
            raise ValueError(
                f"project output {raw.get('contract_id')} must resolve to exactly one producer port"
            )
        outputs.append(
            {
                "contract_id": raw["contract_id"],
                "from_instance_id": producer,
                "from_port": matching[0],
                "context": raw.get("context"),
                "name": raw.get("name"),
                "artifact_path": raw.get("artifact_path"),
            }
        )
    compatibility = dict(project.get("compatibility", {}))
    optional_dependencies = compatibility.get("optional_dependencies", [])
    compatibility["optional_dependencies"] = [
        item["dependency_id"] if isinstance(item, Mapping) else item
        for item in optional_dependencies
    ]
    compatibility["permitted_native_fallbacks"] = sorted(permitted_project_fallbacks)
    aggregate = dict(project.get("budgets", {}).get("aggregate", {}))
    compiler_project = {
        **dict(project),
        "schema_version": "1.0",
        "compatibility": compatibility,
        "budgets": {"stage": aggregate, "aggregate": aggregate},
        "capability_instances": instances,
        "output_contracts": outputs,
    }
    return compiler_project, [_compiler_adapter(record) for record in adapter_records]


def build_project_plan(
    project: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any] | None = None,
    adapter_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one normalized project into a deterministic, non-executable plan."""
    selected_catalog = select_project_catalog(project, catalog=catalog)
    registry = dict(adapter_registry or load_project_adapter_registry())
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("adapter registry must contain a records list")
    compiler_project, compiler_records = adapt_project_for_compiler(
        project, adapter_records=records
    )
    return compile_project(
        compiler_project,
        capability_catalog=selected_catalog,
        adapter_records=compiler_records,
    )


def load_and_plan_project(
    path: str | Path,
    *,
    project_root: str | Path,
    adapter_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load, validate, and compile one explicitly named project file."""
    project = load_project_spec(path, project_root=project_root)
    registry = load_project_adapter_registry(adapter_root)
    plan = build_project_plan(project, adapter_registry=registry)
    return {
        "project": project,
        "project_sha256": project_spec_sha256(project),
        "adapter_registry": registry,
        "plan": plan,
    }


def observe_project(
    project: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    project_root: str | Path | None = None,
    runtime_identity: Mapping[str, Any] | None = None,
    execution_records: Iterable[Mapping[str, Any]] = (),
    artifacts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build the dry project index without discovery, execution, or inference."""
    return build_project_index(
        project,
        plan,
        project_root=project_root,
        runtime_identity=runtime_identity,
        execution_records=execution_records,
        artifacts=artifacts,
    )


__all__ = [
    "adapt_project_for_compiler",
    "build_project_plan",
    "load_and_plan_project",
    "load_project_adapter_registry",
    "observe_project",
    "select_project_catalog",
]
