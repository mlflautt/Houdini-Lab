"""Pure deterministic compiler for normalized Hermes Houdini projects.

The compiler deliberately consumes plain JSON-shaped mappings. It does not load project
files, import sibling G002 lanes, call Houdini, or grant permission to execute a plan.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

PLAN_SCHEMA = "hermes.houdini.project_plan.v1"
_RISK_ORDER = {"read_only": 0, "low": 1, "medium": 2, "high": 3, "external": 4}
_SAFE_ID = re.compile(r"[^a-zA-Z0-9._-]+")


def _json_value(value: Any, path: str) -> Any:
    """Copy JSON-shaped input and report programmer errors with stable paths."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings")
            result[key] = _json_value(item, f"{path}.{key}")
        return result
    if isinstance(value, list):
        return [_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite numbers")
        return value
    raise ValueError(f"{path} must contain only JSON-shaped values")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _block(
    blockers: list[dict[str, Any]], code: str, path: str, message: str, **detail: Any
) -> None:
    item: dict[str, Any] = {"code": code, "path": path, "message": message}
    if detail:
        item["detail"] = detail
    blockers.append(item)


def _objects(
    value: Any, path: str, blockers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _block(blockers, "invalid_contract", path, "must be a list of objects")
        return []
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            _block(blockers, "invalid_contract", f"{path}[{index}]", "must be an object")
        else:
            result.append(item)
    return result


def _strings(value: Any, path: str, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        _block(blockers, "invalid_contract", path, "must be a list of non-empty strings")
        return []
    return list(value)


def _named_contracts(
    value: Any, path: str, blockers: list[dict[str, Any]]
) -> dict[str, str]:
    """Normalize a port-to-contract mapping or ordered port/contract records."""
    if isinstance(value, dict):
        if all(
            isinstance(key, str) and isinstance(item, str) and item
            for key, item in value.items()
        ):
            return dict(value)
    elif isinstance(value, list):
        result: dict[str, str] = {}
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            if not isinstance(item, dict):
                _block(blockers, "invalid_contract", item_path, "must be an object")
                continue
            port = item.get("port")
            contract = item.get("contract_id")
            if (
                not isinstance(port, str)
                or not port
                or not isinstance(contract, str)
                or not contract
            ):
                _block(
                    blockers,
                    "invalid_contract",
                    item_path,
                    "requires non-empty port and contract_id",
                )
                continue
            if port in result:
                _block(blockers, "duplicate_port", item_path, f"duplicate port {port!r}")
            result[port] = contract
        return result
    _block(blockers, "invalid_contract", path, "must name output ports and contracts")
    return {}


def _budget(
    value: Any, path: str, blockers: list[dict[str, Any]], *, required: bool = True
) -> dict[str, float | int]:
    if value is None and not required:
        return {}
    if not isinstance(value, dict):
        _block(blockers, "invalid_budget", path, "must be an object")
        return {}
    result: dict[str, float | int] = {}
    for name, amount in value.items():
        item_path = f"{path}.{name}"
        if (
            not isinstance(name, str)
            or not name
            or isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
            or amount < 0
        ):
            _block(
                blockers,
                "invalid_budget",
                item_path,
                "must be a finite non-negative number",
            )
            continue
        result[name] = amount
    return result


def _compatibility_matches(
    capability: dict[str, Any],
    compatibility: dict[str, Any],
    path: str,
    blockers: list[dict[str, Any]],
) -> None:
    build = compatibility.get("houdini_build")
    builds = capability.get("tested_builds", [])
    if not isinstance(builds, list):
        _block(blockers, "invalid_capability", f"{path}.tested_builds", "must be a list")
    elif build not in builds:
        _block(
            blockers,
            "houdini_build_mismatch",
            path,
            "capability is not tested for the exact requested Houdini build",
            requested=build,
            tested_builds=builds,
        )
    license_value = capability.get("license", {})
    license_mode = license_value.get("mode") if isinstance(license_value, dict) else license_value
    requested_license = compatibility.get("license_mode")
    if license_mode != requested_license:
        _block(
            blockers,
            "license_mismatch",
            path,
            "capability license does not match the project license",
            requested=requested_license,
            actual=license_mode,
        )


def _missing_dependencies(record: dict[str, Any], available: set[str]) -> list[str]:
    dependencies = record.get("optional_dependencies", [])
    if not isinstance(dependencies, list):
        return ["<invalid_optional_dependencies>"]
    missing = [
        item if isinstance(item, str) else f"<invalid:{item!r}>"
        for item in dependencies
        if not isinstance(item, str) or item not in available
    ]
    return sorted(missing)


def _fallback_permitted(
    record: dict[str, Any], missing: list[str], permitted: set[str]
) -> str | None:
    if not missing:
        return None
    candidates: list[str] = []
    fallback = record.get("native_fallback")
    if isinstance(fallback, str) and fallback:
        candidates.append(fallback)
    fallbacks = record.get("fallbacks", [])
    if isinstance(fallbacks, list):
        candidates.extend(item for item in fallbacks if isinstance(item, str) and item)
    matches = sorted(set(candidates).intersection(permitted))
    return matches[0] if len(matches) == 1 else None


def _stage_id(project_id: str, instance_id: str, variant_id: str | None) -> str:
    identity = {"project_id": project_id, "instance_id": instance_id, "variant_id": variant_id}
    readable = _SAFE_ID.sub("-", f"{instance_id}-{variant_id or 'shared'}").strip("-") or "stage"
    return f"stage-{readable[:48]}-{_hash(identity)[:12]}"


def _adapter_matches(
    record: dict[str, Any],
    *,
    source_contract: str,
    target_contract: str,
    binding: dict[str, Any],
) -> bool:
    if (
        record.get("from_contract") != source_contract
        or record.get("to_contract") != target_contract
    ):
        return False
    version = binding.get("adapter_version")
    adapter_id = binding.get("adapter_id")
    return record.get("version") == version and (
        adapter_id is None or record.get("adapter_id") == adapter_id
    )


def compile_project(
    spec: Mapping[str, Any],
    *,
    capability_catalog: Mapping[str, Any],
    adapter_records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compile normalized mappings into a deterministic, non-executable dry DAG.

    Project contract failures are returned as structured blockers. Inputs that are not
    JSON-shaped mappings are programmer errors and raise :class:`ValueError`.
    """
    if not isinstance(spec, Mapping):
        raise ValueError("spec must be a mapping")
    if not isinstance(capability_catalog, Mapping):
        raise ValueError("capability_catalog must be a mapping")
    try:
        raw_adapters = list(adapter_records)
    except TypeError as exc:
        raise ValueError("adapter_records must be an iterable of mappings") from exc
    if any(not isinstance(item, Mapping) for item in raw_adapters):
        raise ValueError("adapter_records items must be mappings")

    normalized_spec = _json_value(spec, "spec")
    catalog = _json_value(capability_catalog, "capability_catalog")
    adapters = [
        _json_value(item, f"adapter_records[{index}]")
        for index, item in enumerate(raw_adapters)
    ]
    adapters.sort(key=_canonical_json)
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if normalized_spec.get("schema") != "hermes.houdini.project.v1":
        _block(
            blockers,
            "unsupported_schema",
            "spec.schema",
            "expected hermes.houdini.project.v1",
        )
    if normalized_spec.get("automatic_ranking") is not False:
        _block(
            blockers,
            "automatic_ranking_forbidden",
            "spec.automatic_ranking",
            "must remain false",
        )
    if normalized_spec.get("winner") is not None:
        _block(
            blockers,
            "winner_forbidden",
            "spec.winner",
            "must remain null pending a separate human review record",
        )
    project_id = normalized_spec.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        _block(blockers, "invalid_contract", "spec.project_id", "must be a non-empty string")
        project_id = "invalid-project"
    compatibility = normalized_spec.get("compatibility")
    if not isinstance(compatibility, dict):
        _block(blockers, "invalid_contract", "spec.compatibility", "must be an object")
        compatibility = {}
    for name in ("houdini_build", "license_mode", "package_version"):
        if not isinstance(compatibility.get(name), str) or not compatibility.get(name):
            _block(
                blockers,
                "invalid_contract",
                f"spec.compatibility.{name}",
                "must be set exactly",
            )
    available_dependencies = set(
        _strings(
            compatibility.get("optional_dependencies", []),
            "spec.compatibility.optional_dependencies",
            blockers,
        )
    )
    project_fallbacks = set(
        _strings(
            compatibility.get("permitted_native_fallbacks", []),
            "spec.compatibility.permitted_native_fallbacks",
            blockers,
        )
    )

    catalog_records = _objects(
        catalog.get("records", []), "capability_catalog.records", blockers
    )
    if catalog.get("package_version") != compatibility.get("package_version"):
        _block(
            blockers,
            "package_version_mismatch",
            "capability_catalog.package_version",
            "catalog package version does not match the project compatibility identity",
            requested=compatibility.get("package_version"),
            actual=catalog.get("package_version"),
        )
    capability_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in catalog_records:
        capability_index[(record.get("capability_id"), record.get("version"))].append(record)

    budgets = normalized_spec.get("budgets")
    if not isinstance(budgets, dict):
        _block(
            blockers,
            "invalid_budget",
            "spec.budgets",
            "must contain stage and aggregate limits",
        )
        budgets = {}
    stage_limits = _budget(budgets.get("stage"), "spec.budgets.stage", blockers)
    aggregate_limits = _budget(
        budgets.get("aggregate"), "spec.budgets.aggregate", blockers
    )
    instances = _objects(
        normalized_spec.get("capability_instances", []),
        "spec.capability_instances",
        blockers,
    )
    variants = _objects(normalized_spec.get("variants", []), "spec.variants", blockers)
    for index, variant in enumerate(variants):
        for field in ("human_rating", "selected_for_continuation"):
            if variant.get(field) is not None:
                _block(
                    blockers,
                    "human_field_not_blank",
                    f"spec.variants[{index}].{field}",
                    "compiler input may not prefill human-owned fields",
                )
    variant_ids = [item.get("variant_id") for item in variants]
    instance_ids = [item.get("instance_id") for item in instances]
    duplicate_instances = sorted(
        {
            item
            for item in instance_ids
            if isinstance(item, str) and instance_ids.count(item) > 1
        }
    )
    for instance_id in duplicate_instances:
        _block(
            blockers,
            "duplicate_instance",
            "spec.capability_instances",
            f"duplicate {instance_id!r}",
        )

    stages: list[dict[str, Any]] = []
    stages_by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stage_source: dict[str, dict[str, Any]] = {}
    aggregate: dict[str, float | int] = defaultdict(int)

    for index, instance in enumerate(instances):
        path = f"spec.capability_instances[{index}]"
        instance_id = instance.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            _block(
                blockers,
                "invalid_contract",
                f"{path}.instance_id",
                "must be a non-empty string",
            )
            continue
        capability_id = instance.get("capability_id")
        capability_version = instance.get("capability_version")
        matches = capability_index.get((capability_id, capability_version), [])
        capability: dict[str, Any] | None = matches[0] if len(matches) == 1 else None
        if not matches:
            _block(
                blockers,
                "missing_capability",
                path,
                "no exact capability ID/version exists",
                capability_id=capability_id,
                version=capability_version,
            )
        elif len(matches) > 1:
            _block(
                blockers,
                "ambiguous_capability",
                path,
                "multiple exact capability records exist",
                count=len(matches),
            )
        context = instance.get("context")
        if not isinstance(context, str) or not context:
            _block(
                blockers,
                "invalid_contract",
                f"{path}.context",
                "must be a non-empty string",
            )
        if capability is not None:
            contexts = capability.get("contexts", [])
            if not isinstance(contexts, list) or context not in contexts:
                _block(
                    blockers,
                    "context_mismatch",
                    path,
                    "capability does not declare the context",
                )
            _compatibility_matches(capability, compatibility, path, blockers)

        permitted = project_fallbacks.union(
            _strings(
                instance.get("permitted_native_fallbacks", []),
                f"{path}.permitted_native_fallbacks",
                blockers,
            )
        )
        missing = _missing_dependencies(capability or {}, available_dependencies)
        fallback = _fallback_permitted(capability or {}, missing, permitted)
        if missing and fallback is None:
            _block(
                blockers,
                "unavailable_dependency",
                path,
                "capability dependencies are unavailable without one explicitly permitted "
                "native fallback",
                missing=missing,
            )
        stage_budget = _budget(instance.get("budget"), f"{path}.budget", blockers)
        for name, amount in stage_budget.items():
            if name not in stage_limits or amount > stage_limits[name]:
                _block(
                    blockers,
                    "stage_budget_overflow",
                    f"{path}.budget.{name}",
                    "stage budget exceeds or lacks a declared stage limit",
                    requested=amount,
                    limit=stage_limits.get(name),
                )

        scope = instance.get("scope")
        if not isinstance(scope, dict) or any(
            name not in scope for name in ("graph_edit", "cook", "cache", "render")
        ):
            _block(
                blockers,
                "invalid_scope",
                f"{path}.scope",
                "must explicitly declare graph_edit, cook, cache, and render",
            )
            scope = {
                "graph_edit": "none",
                "cook": "none",
                "cache": "none",
                "render": "none",
            }
        requested_variants = _strings(
            instance.get("variant_scope", []), f"{path}.variant_scope", blockers
        )
        unknown_variants = [item for item in requested_variants if item not in variant_ids]
        if unknown_variants:
            _block(
                blockers,
                "unknown_variant",
                f"{path}.variant_scope",
                "contains unknown variants",
                variants=unknown_variants,
            )
        expansions: list[str | None] = requested_variants or [None]
        outputs = _named_contracts(
            instance.get("output_contracts"), f"{path}.output_contracts", blockers
        )
        if capability is not None:
            declared_outputs = capability.get("outputs", [])
            if not isinstance(declared_outputs, list):
                _block(
                    blockers,
                    "invalid_capability",
                    f"{path}.capability.outputs",
                    "must be a list",
                )
            else:
                for port, contract_id in outputs.items():
                    if contract_id not in declared_outputs:
                        _block(
                            blockers,
                            "undeclared_output_contract",
                            f"{path}.output_contracts.{port}",
                            "capability does not declare the requested contract",
                            contract_id=contract_id,
                        )
        risk = (
            capability.get("risk")
            if capability is not None
            else instance.get("risk", "unknown")
        )
        approvals = (
            list(capability.get("approvals", []))
            if capability and isinstance(capability.get("approvals", []), list)
            else []
        )
        approvals.extend(
            _strings(instance.get("approvals", []), f"{path}.approvals", blockers)
        )
        approvals = list(dict.fromkeys(approvals))
        evidence = instance.get("requested_evidence", [])
        if not isinstance(evidence, list):
            _block(
                blockers,
                "invalid_contract",
                f"{path}.requested_evidence",
                "must be a list",
            )
            evidence = []
        needs_checkpoint = (
            _RISK_ORDER.get(str(risk), 99) >= _RISK_ORDER["medium"]
            or any(
                scope.get(name) not in (None, "none", "read_only") for name in scope
            )
        )
        parent_contract = instance.get("parent_contract")
        if not isinstance(parent_contract, str) or not parent_contract:
            _block(
                blockers,
                "undeclared_parent_contract",
                f"{path}.parent_contract",
                "must be named",
            )
        for variant_id in expansions:
            for name, amount in stage_budget.items():
                aggregate[name] += amount
            stage_id = _stage_id(project_id, instance_id, variant_id)
            stage = {
                "stage_id": stage_id,
                "instance_id": instance_id,
                "variant_id": variant_id,
                "capability": {
                    "capability_id": capability_id,
                    "version": capability_version,
                    "context": context,
                    "parent_contract": parent_contract,
                    "output_contracts": outputs,
                },
                "contract_bindings": [],
                "scope": dict(scope),
                "checkpoint": {
                    "required": needs_checkpoint,
                    "boundary": "before_stage" if needs_checkpoint else None,
                },
                "budget": dict(stage_budget),
                "risk": risk,
                "approvals": [
                    {"approval_id": item, "status": "pending"} for item in approvals
                ],
                "evidence": [
                    dict(item)
                    if isinstance(item, dict)
                    else {"gate_id": item, "status": "pending"}
                    for item in evidence
                ],
                "native_fallback": fallback,
            }
            stages.append(stage)
            stages_by_instance[instance_id].append(stage)
            stage_source[stage_id] = instance

    project_outputs = _objects(
        normalized_spec.get("output_contracts", []), "spec.output_contracts", blockers
    )
    for index, output in enumerate(project_outputs):
        path = f"spec.output_contracts[{index}]"
        contract_id = output.get("contract_id")
        source_instance_id = output.get("from_instance_id")
        source_port = output.get("from_port")
        if not all(
            isinstance(item, str) and item
            for item in (contract_id, source_instance_id, source_port)
        ):
            _block(
                blockers,
                "invalid_contract",
                path,
                "requires contract_id, from_instance_id, and from_port",
            )
            continue
        source_stages = stages_by_instance.get(source_instance_id, [])
        if not source_stages or any(
            source_port not in stage["capability"]["output_contracts"]
            for stage in source_stages
        ):
            _block(
                blockers,
                "undeclared_output",
                path,
                "project output references an undeclared instance port",
            )

    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str, str]] = set()

    def add_edge(source: str, target: str, kind: str, contract_id: str = "") -> None:
        key = (source, target, kind, contract_id)
        if key not in edge_keys:
            edge_keys.add(key)
            edges.append(
                {
                    "from_stage": source,
                    "to_stage": target,
                    "kind": kind,
                    "contract_id": contract_id or None,
                }
            )

    def compatible_sources(
        source_stages: list[dict[str, Any]], target: dict[str, Any]
    ) -> list[dict[str, Any]]:
        variant_id = target["variant_id"]
        exact = [item for item in source_stages if item["variant_id"] == variant_id]
        if exact:
            return exact
        shared = [item for item in source_stages if item["variant_id"] is None]
        return shared or (source_stages if variant_id is None else [])

    for target in stages:
        instance = stage_source[target["stage_id"]]
        path = f"spec.capability_instances[{instances.index(instance)}]"
        dependencies = _strings(
            instance.get("dependencies", []), f"{path}.dependencies", blockers
        )
        for dependency in dependencies:
            sources = compatible_sources(stages_by_instance.get(dependency, []), target)
            if not sources:
                _block(
                    blockers,
                    "missing_dependency_stage",
                    f"{path}.dependencies",
                    f"unavailable {dependency!r}",
                )
            for source in sources:
                add_edge(source["stage_id"], target["stage_id"], "dependency")

        inputs = instance.get("inputs", {})
        if not isinstance(inputs, dict):
            _block(blockers, "invalid_contract", f"{path}.inputs", "must be an object")
            continue
        for port, binding in inputs.items():
            binding_path = f"{path}.inputs.{port}"
            if not isinstance(binding, dict):
                _block(blockers, "invalid_contract", binding_path, "must be an object")
                continue
            target_contract = binding.get("contract_id")
            source_instance_id = binding.get("from_instance_id")
            source_port = binding.get("from_port")
            if not all(
                isinstance(item, str) and item for item in (target_contract, source_port)
            ):
                _block(
                    blockers,
                    "undeclared_port",
                    binding_path,
                    "requires contract_id and from_port",
                )
                continue
            candidate_instances = (
                [source_instance_id]
                if isinstance(source_instance_id, str)
                else list(stages_by_instance)
            )
            providers: list[tuple[dict[str, Any], str]] = []
            for candidate_id in candidate_instances:
                for source in compatible_sources(
                    stages_by_instance.get(candidate_id, []), target
                ):
                    outputs = source["capability"]["output_contracts"]
                    if source_port in outputs:
                        providers.append((source, outputs[source_port]))
            if not providers:
                _block(
                    blockers,
                    "undeclared_output",
                    binding_path,
                    "no provider declares the requested output port",
                )
                continue
            if len(providers) > 1:
                _block(
                    blockers,
                    "multiple_unresolved_providers",
                    binding_path,
                    "the input has multiple providers and must name from_instance_id",
                    providers=[item[0]["instance_id"] for item in providers],
                )
                continue
            source, source_contract = providers[0]
            selected_adapter = None
            if source_contract != target_contract:
                if (
                    not isinstance(binding.get("adapter_version"), str)
                    or not binding.get("adapter_version")
                ):
                    _block(
                        blockers,
                        "adapter_version_required",
                        binding_path,
                        "adaptation requires an exact adapter_version",
                    )
                else:
                    matches = [
                        record
                        for record in adapters
                        if _adapter_matches(
                            record,
                            source_contract=source_contract,
                            target_contract=target_contract,
                            binding=binding,
                        )
                    ]
                    compatible = [
                        record
                        for record in matches
                        if record.get("source_context")
                        == source["capability"]["context"]
                        and record.get("target_context")
                        == target["capability"]["context"]
                        and compatibility.get("houdini_build")
                        in record.get("tested_builds", [])
                        and (
                            record.get("license_mode")
                            or (
                                record.get("license", {}).get("mode")
                                if isinstance(record.get("license"), dict)
                                else record.get("license")
                            )
                        )
                        == compatibility.get("license_mode")
                    ]
                    if not matches:
                        _block(
                            blockers,
                            "missing_adapter",
                            binding_path,
                            "no exact adapter record exists",
                        )
                    elif len(compatible) > 1:
                        _block(
                            blockers,
                            "ambiguous_adapter",
                            binding_path,
                            "multiple compatible exact adapters exist",
                            count=len(compatible),
                        )
                    elif not compatible:
                        context_matches = [
                            record
                            for record in matches
                            if record.get("source_context")
                            == source["capability"]["context"]
                            and record.get("target_context")
                            == target["capability"]["context"]
                        ]
                        build_matches = [
                            record
                            for record in context_matches
                            if compatibility.get("houdini_build")
                            in record.get("tested_builds", [])
                        ]
                        if not context_matches:
                            code = "adapter_context_mismatch"
                        elif not build_matches:
                            code = "adapter_build_mismatch"
                        else:
                            code = "adapter_license_mismatch"
                        _block(
                            blockers,
                            code,
                            binding_path,
                            "exact adapter exists but compatibility identity does not match",
                        )
                    else:
                        selected_adapter = compatible[0]
                        missing = _missing_dependencies(
                            selected_adapter, available_dependencies
                        )
                        permitted = project_fallbacks.union(
                            _strings(
                                binding.get("permitted_native_fallbacks", []),
                                f"{binding_path}.permitted_native_fallbacks",
                                blockers,
                            )
                        )
                        fallback = _fallback_permitted(
                            selected_adapter, missing, permitted
                        )
                        if missing and fallback is None:
                            _block(
                                blockers,
                                "unavailable_dependency",
                                binding_path,
                                "adapter dependency is unavailable without an explicitly "
                                "permitted native fallback",
                                missing=missing,
                            )
                        adapter_risk = selected_adapter.get("risk")
                        if _RISK_ORDER.get(str(adapter_risk), 99) >= _RISK_ORDER["medium"]:
                            target["checkpoint"] = {
                                "required": True,
                                "boundary": "before_stage",
                            }
                        adapter_approvals = selected_adapter.get("approvals", [])
                        if isinstance(adapter_approvals, list):
                            existing = {
                                item["approval_id"] for item in target["approvals"]
                            }
                            target["approvals"].extend(
                                {"approval_id": item, "status": "pending"}
                                for item in adapter_approvals
                                if isinstance(item, str) and item not in existing
                            )
                        effect = _budget(
                            selected_adapter.get("budget_effect"),
                            f"{binding_path}.adapter.budget_effect",
                            blockers,
                            required=False,
                        )
                        for name, amount in effect.items():
                            target["budget"][name] = target["budget"].get(name, 0) + amount
                            aggregate[name] += amount
                            if (
                                name not in stage_limits
                                or target["budget"][name] > stage_limits[name]
                            ):
                                _block(
                                    blockers,
                                    "stage_budget_overflow",
                                    f"{binding_path}.adapter.budget_effect.{name}",
                                    "adapter pushes stage over its declared limit",
                                )
            target["contract_bindings"].append(
                {
                    "input_port": port,
                    "contract_id": target_contract,
                    "from_stage": source["stage_id"],
                    "from_port": source_port,
                    "from_contract": source_contract,
                    "adapter": None
                    if selected_adapter is None
                    else {
                        "record": selected_adapter,
                        "record_sha256": _hash(selected_adapter),
                    },
                }
            )
            add_edge(
                source["stage_id"], target["stage_id"], "contract", target_contract
            )

    stage_ordinal = {stage["stage_id"]: index for index, stage in enumerate(stages)}
    edges.sort(
        key=lambda item: (
            stage_ordinal[item["from_stage"]],
            stage_ordinal[item["to_stage"]],
            item["kind"],
            item["contract_id"] or "",
        )
    )
    incoming = {stage_id: 0 for stage_id in stage_ordinal}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        incoming[edge["to_stage"]] += 1
        outgoing[edge["from_stage"]].append(edge["to_stage"])
    ready = sorted(
        (item for item, count in incoming.items() if count == 0), key=stage_ordinal.get
    )
    ordered_ids: list[str] = []
    while ready:
        stage_id = ready.pop(0)
        ordered_ids.append(stage_id)
        for target_id in sorted(outgoing[stage_id], key=stage_ordinal.get):
            incoming[target_id] -= 1
            if incoming[target_id] == 0:
                ready.append(target_id)
                ready.sort(key=stage_ordinal.get)
    if len(ordered_ids) != len(stages):
        cyclic = [item for item in stage_ordinal if item not in ordered_ids]
        _block(
            blockers,
            "dependency_cycle",
            "plan.edges",
            "stage graph contains a cycle",
            stage_ids=cyclic,
        )
        ordered_ids.extend(cyclic)
    stage_lookup = {stage["stage_id"]: stage for stage in stages}
    stages = [stage_lookup[stage_id] for stage_id in ordered_ids]

    for name, amount in sorted(aggregate.items()):
        if name not in aggregate_limits or amount > aggregate_limits[name]:
            _block(
                blockers,
                "aggregate_budget_overflow",
                f"spec.budgets.aggregate.{name}",
                "aggregate request exceeds or lacks a declared limit",
                requested=amount,
                limit=aggregate_limits.get(name),
            )

    blockers.sort(key=lambda item: (item["path"], item["code"], _canonical_json(item)))
    plan = {
        "schema": PLAN_SCHEMA,
        "schema_version": "1.0",
        "status": "blocked" if blockers else "planned",
        "source_identity": {
            "spec_sha256": _hash(normalized_spec),
            "capability_catalog_sha256": _hash(catalog),
            "adapter_records_sha256": _hash(adapters),
            "adapter_record_hashes": [_hash(item) for item in adapters],
            "compatibility": dict(compatibility),
        },
        "project_id": project_id,
        "stages": stages,
        "topological_order": ordered_ids,
        "edges": edges,
        "aggregate_budget": dict(sorted(aggregate.items())),
        "budget_limits": {"stage": stage_limits, "aggregate": aggregate_limits},
        "output_contracts": project_outputs,
        "evidence_gates": normalized_spec.get("evidence_gates", []),
        "variants": variants,
        "human_decisions": normalized_spec.get("human_decisions", []),
        "blockers": blockers,
        "warnings": warnings,
        "automatic_execution": False,
        "automatic_ranking": False,
        "winner": None,
    }
    plan["plan_sha256"] = _hash(plan)
    return plan


__all__ = ["PLAN_SCHEMA", "compile_project"]
