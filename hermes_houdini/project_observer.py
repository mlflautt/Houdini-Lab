"""Deterministic, Houdini-independent project evidence and drift indexing."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

PROJECT_INDEX_SCHEMA = "hermes.houdini.project_index.v1"
EVIDENCE_STATES = ("pass", "warn", "pending", "blocked", "not_applicable")
EVIDENCE_RUNGS = ("graph", "data", "pixel", "plugin", "model", "human", "downstream")
DRIFT_CATEGORIES = (
    "houdini_build",
    "license",
    "package",
    "optional_dependency",
    "capability_adapter_identity",
    "source_hash",
    "artifact_integrity",
)
def _json_value(value: Any, *, label: str) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item, label=f"{label}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item, label=f"{label}[]") for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} contains a non-finite number")
        return value
    raise ValueError(f"{label} contains a non-JSON value")


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return _json_value(value, label=label)


def _mapping_list(value: Any, *, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{label} must be a list of mappings")
    return [_mapping(item, label=f"{label}[{index}]") for index, item in enumerate(value)]


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            _json_value(value, label="value"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not canonical JSON: {exc}") from exc


def _sha256(value: Any, *, exclude: frozenset[str] = frozenset()) -> str:
    if isinstance(value, Mapping):
        value = {key: item for key, item in value.items() if key not in exclude}
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _declared_hash(value: Mapping[str, Any], names: tuple[str, ...], *, self_field: str) -> str:
    for name in names:
        declared = value.get(name)
        if declared is not None:
            if not _valid_sha256(declared):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
            return str(declared).lower()
    return _sha256(value, exclude=frozenset({self_field}))


def _identity(item: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _stage_id(stage: Mapping[str, Any]) -> str:
    return _identity(stage, "stage_id", "id")


def _stage_evidence(stage: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw = stage.get("evidence_gates", stage.get("evidence", []))
    entries: list[Any]
    if isinstance(raw, Mapping):
        entries = [dict(value, rung=key) if isinstance(value, Mapping) else {"rung": key} for key, value in raw.items()]
    elif isinstance(raw, (list, tuple)):
        entries = list(raw)
    elif raw is None:
        entries = []
    else:
        raise ValueError("stage evidence must be a mapping or list")
    requested: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if isinstance(entry, str):
            rung, required, reason = entry, True, "declared by the dry plan"
        elif isinstance(entry, Mapping):
            rung = _identity(entry, "rung", "evidence_type", "tier", "id")
            required = bool(entry.get("required", True))
            reason = str(entry.get("reason", "declared by the dry plan"))
        else:
            raise ValueError("stage evidence entries must be strings or mappings")
        if not rung:
            raise ValueError("stage evidence entry requires a rung")
        if rung in requested:
            raise ValueError(f"duplicate evidence rung in stage: {rung}")
        requested[rung] = {"required": required, "reason": reason}
    return requested


def _evidence_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = record.get("evidence", [])
    if isinstance(raw, Mapping):
        raw = [dict(value, rung=key) if isinstance(value, Mapping) else {"rung": key, "status": value} for key, value in raw.items()]
    return _mapping_list(raw, label="execution record evidence")


def _blocker(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, **details}


def _warning(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, **details}


def _diagnostics(value: Any, *, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{label} must be a list")
    rows = []
    for index, item in enumerate(value):
        if isinstance(item, str) and item:
            rows.append({"code": item, "source": label})
        elif isinstance(item, Mapping):
            rows.append({"source": label, **_mapping(item, label=f"{label}[{index}]")})
        else:
            raise ValueError(f"{label}[{index}] must be a string or mapping")
    return rows


def _aggregate(statuses: Iterable[str]) -> str:
    values = tuple(statuses)
    if "blocked" in values:
        return "blocked"
    if "pending" in values:
        return "pending"
    if "warn" in values:
        return "warn"
    if "pass" in values:
        return "pass"
    return "not_applicable"


def _compat_value(identity: Mapping[str, Any], category: str) -> Any:
    aliases = {
        "houdini_build": ("houdini_build", "build"),
        "license": ("license", "license_mode"),
        "package": ("package", "package_version"),
        "optional_dependency": ("optional_dependencies",),
        "capability_adapter_identity": ("capability_adapter_identity", "capabilities", "adapters"),
        "source_hash": ("source_sha256", "project_sha256"),
    }
    values = []
    for key in aliases[category]:
        if key in identity:
            values.append(identity[key])
    if category == "capability_adapter_identity" and len(values) > 1:
        return values
    return values[0] if values else None


def _normalized_identity(value: Any) -> Any:
    if isinstance(value, list):
        normalized = [_normalized_identity(item) for item in value]
        return sorted(normalized, key=_canonical_json)
    if isinstance(value, Mapping):
        return {key: _normalized_identity(item) for key, item in sorted(value.items())}
    return value


def _compatibility_drift(
    expected: Mapping[str, Any], current: Mapping[str, Any] | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for category in DRIFT_CATEGORIES[:-1]:
        expected_value = _compat_value(expected, category)
        actual_value = _compat_value(current, category) if current is not None else None
        if expected_value is None:
            status, reason = "not_applicable", "the dry plan declares no identity for this category"
        elif current is None or actual_value is None:
            status, reason = "pending", "current runtime identity was not supplied"
        else:
            left = _normalized_identity(expected_value)
            right = _normalized_identity(actual_value)
            if category == "optional_dependency" and isinstance(left, list) and isinstance(right, list):
                matches = all(item in right for item in left)
            else:
                matches = left == right
            status = "match" if matches else "drift"
            reason = "runtime identity matches the dry plan" if matches else "runtime identity differs from the dry plan"
            if not matches:
                blockers.append(_blocker(f"{category}_drift", expected=left, actual=right))
        rows.append(
            {
                "category": category,
                "status": status,
                "expected": expected_value,
                "actual": actual_value,
                "reason": reason,
            }
        )
    return rows, blockers


def _lexically_inside(root: Path, path: Path) -> bool:
    try:
        common = os.path.commonpath((os.path.normpath(str(root)), os.path.normpath(str(path))))
    except ValueError:
        return False
    return common == os.path.normpath(str(root))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_artifacts(
    supplied: Iterable[Mapping[str, Any]], project_root: str | Path | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    items = [_mapping(item, label="artifact") for item in supplied]
    items.sort(key=lambda item: (_identity(item, "path"), _canonical_json(item)))
    root: Path | None = None
    if project_root is not None:
        root = Path(project_root)
        if not root.is_absolute():
            raise ValueError("project_root must be absolute")
        root = Path(os.path.normpath(str(root)))
    normalized: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for index, source in enumerate(items):
        item = dict(source)
        path_value = item.get("path")
        expected_hash = item.get("sha256")
        durable = bool(item.get("durable", False))
        verify = item.get("verify", False) is True
        integrity = {"status": "not_checked", "reason": "verification was not explicitly requested"}
        if durable and not _valid_sha256(expected_hash):
            blockers.append(_blocker("durable_artifact_missing_sha256", artifact_index=index, path=path_value))
        elif expected_hash is not None and not _valid_sha256(expected_hash):
            blockers.append(_blocker("invalid_artifact_sha256", artifact_index=index, path=path_value))
        if root is None:
            integrity = {"status": "not_checked", "reason": "project_root was not supplied"}
        elif not isinstance(path_value, str) or not Path(path_value).is_absolute():
            blockers.append(_blocker("artifact_path_not_absolute", artifact_index=index, path=path_value))
            integrity = {"status": "blocked", "reason": "artifact path is not absolute"}
        else:
            lexical = Path(os.path.normpath(path_value))
            if not _lexically_inside(root, lexical):
                blockers.append(_blocker("artifact_outside_project_root", artifact_index=index, path=path_value))
                integrity = {"status": "blocked", "reason": "artifact path is outside project_root"}
            elif verify:
                try:
                    resolved_root = root.resolve(strict=True)
                    resolved_path = Path(path_value).resolve(strict=True)
                    if not resolved_path.is_relative_to(resolved_root):
                        raise ValueError("resolved artifact escapes project_root")
                    if not resolved_path.is_file():
                        raise FileNotFoundError(path_value)
                    actual_hash = _file_sha256(resolved_path)
                    if not _valid_sha256(expected_hash):
                        integrity = {"status": "blocked", "reason": "verification requires a claimed SHA-256", "actual_sha256": actual_hash}
                        blockers.append(_blocker("artifact_verification_missing_sha256", artifact_index=index, path=path_value))
                    elif actual_hash != str(expected_hash).lower():
                        integrity = {"status": "blocked", "reason": "artifact bytes do not match the claimed SHA-256", "actual_sha256": actual_hash}
                        blockers.append(_blocker("artifact_hash_mismatch", artifact_index=index, path=path_value, expected_sha256=expected_hash, actual_sha256=actual_hash))
                    else:
                        integrity = {"status": "pass", "reason": "artifact bytes match the claimed SHA-256", "actual_sha256": actual_hash, "size_bytes": resolved_path.stat().st_size}
                except (FileNotFoundError, OSError, ValueError) as exc:
                    integrity = {"status": "blocked", "reason": str(exc)}
                    blockers.append(_blocker("artifact_unavailable", artifact_index=index, path=path_value, reason=str(exc)))
        item["integrity"] = integrity
        normalized.append(item)
    normalized.sort(key=lambda item: (_identity(item, "path"), _canonical_json(item)))
    if len({_identity(item, "path") for item in normalized if _identity(item, "path")}) != len(
        [item for item in normalized if _identity(item, "path")]
    ):
        warnings.append(_warning("duplicate_artifact_path"))
    return normalized, blockers, warnings


def _contracts(stages: list[dict[str, Any]], plan: Mapping[str, Any]) -> dict[str, Any]:
    producers: list[dict[str, Any]] = []
    consumers: list[dict[str, Any]] = []
    for stage in stages:
        sid = stage["stage_id"]
        raw_outputs = stage.get("output_contracts", stage.get("outputs", []))
        if isinstance(raw_outputs, Mapping):
            raw_outputs = list(raw_outputs)
        for contract in raw_outputs or []:
            contract_id = contract if isinstance(contract, str) else _identity(contract, "contract_id", "id", "name")
            if contract_id:
                producers.append({"contract_id": contract_id, "stage_id": sid})
        raw_inputs = stage.get("contract_bindings", stage.get("inputs", []))
        if isinstance(raw_inputs, Mapping):
            raw_inputs = list(raw_inputs.values())
        for binding in raw_inputs or []:
            if isinstance(binding, str):
                contract_id, producer = binding, None
            elif isinstance(binding, Mapping):
                contract_id = _identity(binding, "contract_id", "contract", "source_contract")
                producer = binding.get("producer_stage_id")
            else:
                continue
            if contract_id:
                consumers.append({"contract_id": contract_id, "stage_id": sid, "producer_stage_id": producer})
    for binding in _mapping_list(plan.get("contract_bindings", []), label="plan.contract_bindings"):
        contract_id = _identity(binding, "contract_id", "contract", "source_contract")
        consumer = _identity(binding, "consumer_stage_id", "stage_id")
        if contract_id and consumer:
            consumers.append({"contract_id": contract_id, "stage_id": consumer, "producer_stage_id": binding.get("producer_stage_id"), "adapter": binding.get("adapter")})
    return {
        "producers": sorted(producers, key=lambda item: (item["contract_id"], item["stage_id"])),
        "consumers": sorted(consumers, key=lambda item: (item["contract_id"], item["stage_id"], str(item.get("producer_stage_id")))),
    }


def build_project_index(
    project: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    project_root: str | Path | None = None,
    runtime_identity: Mapping[str, Any] | None = None,
    execution_records: Iterable[Mapping[str, Any]] = (),
    artifacts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Join one dry project plan with only explicitly supplied evidence and identity."""
    source = _mapping(project, label="project")
    dry_plan = _mapping(plan, label="plan")
    runtime = _mapping(runtime_identity, label="runtime_identity") if runtime_identity is not None else None
    if source.get("schema") != "hermes.houdini.project.v1":
        raise ValueError("project schema must be hermes.houdini.project.v1")
    if dry_plan.get("schema") != "hermes.houdini.project_plan.v1":
        raise ValueError("plan schema must be hermes.houdini.project_plan.v1")
    source_hash = _declared_hash(source, ("project_sha256", "source_sha256"), self_field="project_sha256")
    plan_hash = _declared_hash(dry_plan, ("plan_sha256",), self_field="plan_sha256")

    raw_stages = _mapping_list(dry_plan.get("stages", []), label="plan.stages")
    blockers = _diagnostics(dry_plan.get("blockers", []), label="plan.blockers")
    warnings = _diagnostics(dry_plan.get("warnings", []), label="plan.warnings")
    stage_ids = [_stage_id(stage) for stage in raw_stages]
    if any(not value for value in stage_ids):
        raise ValueError("every plan stage requires stage_id")
    if len(set(stage_ids)) != len(stage_ids):
        raise ValueError("plan stage_id values must be unique")
    topological_order = dry_plan.get("topological_order")
    if topological_order is not None:
        if (
            not isinstance(topological_order, (list, tuple))
            or not all(isinstance(item, str) and item for item in topological_order)
            or len(set(topological_order)) != len(topological_order)
            or set(topological_order) != set(stage_ids)
        ):
            raise ValueError("plan.topological_order must contain every stage_id exactly once")
        by_id = {_stage_id(stage): stage for stage in raw_stages}
        raw_stages = [by_id[stage_id] for stage_id in topological_order]
        stage_ids = list(topological_order)

    record_list = [_mapping(record, label="execution_record") for record in execution_records]
    record_list.sort(key=lambda record: (_stage_id(record), _canonical_json(record)))
    records_by_stage: dict[str, list[dict[str, Any]]] = {}
    for record in record_list:
        sid = _stage_id(record)
        if not sid or sid not in set(stage_ids):
            blockers.append(_blocker("unknown_execution_stage", stage_id=sid or None))
            continue
        records_by_stage.setdefault(sid, []).append(record)
    for sid, records in sorted(records_by_stage.items()):
        if len(records) > 1:
            blockers.append(_blocker("duplicate_execution_record", stage_id=sid, count=len(records)))

    normalized_stages: list[dict[str, Any]] = []
    human_records: list[dict[str, Any]] = []
    embedded_artifacts: list[dict[str, Any]] = []
    for order, stage in enumerate(raw_stages):
        sid = stage_ids[order]
        requested = _stage_evidence(stage)
        records = records_by_stage.get(sid, [])
        record = records[0] if len(records) == 1 else None
        non_applicable_reason = stage.get("non_applicable_reason")
        declared_not_applicable = stage.get("status") == "not_applicable" or non_applicable_reason is not None
        record_valid = record is not None
        if record is not None:
            for field, expected in (("source_sha256", source_hash), ("project_sha256", source_hash), ("plan_sha256", plan_hash)):
                claimed = record.get(field)
                if claimed is not None and claimed != expected:
                    blockers.append(_blocker("execution_record_hash_mismatch", stage_id=sid, field=field, expected=expected, actual=claimed))
                    record_valid = False
            record_artifacts = _mapping_list(
                record.get("artifacts", []), label=f"execution_records[{sid}].artifacts"
            )
            embedded_artifacts.extend(
                {"stage_id": sid, **item} if "stage_id" not in item else item
                for item in record_artifacts
            )
            human = record.get("human")
            if human is not None:
                human_item = _mapping(human, label=f"execution_records[{sid}].human")
                human_records.append({"stage_id": sid, **human_item})

        supplied_evidence: dict[str, dict[str, Any]] = {}
        if record_valid and record is not None:
            for evidence in _evidence_rows(record):
                rung = _identity(evidence, "rung", "evidence_type", "tier", "id")
                status = evidence.get("status")
                if not rung:
                    raise ValueError(f"execution record {sid} evidence requires a rung")
                if status not in EVIDENCE_STATES:
                    raise ValueError(f"execution record {sid} has invalid evidence status: {status}")
                if rung in supplied_evidence:
                    blockers.append(_blocker("duplicate_evidence_rung", stage_id=sid, rung=rung))
                    continue
                supplied_evidence[rung] = evidence

        rung_names = list(EVIDENCE_RUNGS)
        rung_names.extend(sorted(set(requested).union(supplied_evidence).difference(rung_names)))
        evidence_index: list[dict[str, Any]] = []
        required_statuses: list[str] = []
        for rung in rung_names:
            gate = requested.get(rung)
            supplied = supplied_evidence.get(rung)
            if declared_not_applicable:
                status = "not_applicable"
                reason = str(non_applicable_reason or "stage is explicitly non-applicable")
                row = {"rung": rung, "required": bool(gate and gate["required"]), "status": status, "reason": reason}
            elif supplied is not None:
                row = {"rung": rung, "required": bool(gate and gate["required"]), **supplied}
                row["rung"] = rung
                status = str(row["status"])
            elif gate is not None:
                status = "pending"
                row = {"rung": rung, "required": bool(gate["required"]), "status": status, "reason": "planned evidence has not been supplied"}
            else:
                status = "not_applicable"
                row = {"rung": rung, "required": False, "status": status, "reason": "the dry plan makes no claim for this evidence rung"}
            evidence_index.append(row)
            if row["required"]:
                required_statuses.append("pending" if status == "not_applicable" else status)

        if declared_not_applicable:
            stage_status = "not_applicable"
        elif record is None or not record_valid:
            stage_status = "pending" if record is None else "blocked"
        else:
            record_status = record.get("status", "pass")
            if record_status not in EVIDENCE_STATES:
                raise ValueError(f"execution record {sid} has invalid status: {record_status}")
            if record_status == "not_applicable":
                record_status = "pending"
            stage_status = _aggregate([str(record_status), *required_statuses])
        approvals = _mapping_list(stage.get("approvals", []), label=f"stage {sid} approvals")
        normalized_stages.append(
            {
                **stage,
                "stage_id": sid,
                "order": order,
                "execution_status": stage_status,
                "execution_record": record if record_valid else None,
                "evidence": evidence_index,
                "approvals": approvals,
            }
        )

    all_artifacts, artifact_blockers, artifact_warnings = _normalize_artifacts(
        [*artifacts, *embedded_artifacts], project_root
    )
    blockers.extend(artifact_blockers)
    warnings.extend(artifact_warnings)
    expected_compatibility = _mapping(
        dry_plan.get("compatibility", source.get("compatibility", {})), label="compatibility"
    )
    expected_compatibility.setdefault("source_sha256", source_hash)
    if "capability_adapter_identity" not in expected_compatibility:
        identities: list[dict[str, Any]] = []
        for stage in raw_stages:
            capability = stage.get("capability")
            if isinstance(capability, Mapping):
                identities.append({"kind": "capability", **dict(capability)})
            elif stage.get("capability_id") or stage.get("capability_version"):
                identities.append(
                    {
                        "kind": "capability",
                        "id": stage.get("capability_id"),
                        "version": stage.get("capability_version"),
                    }
                )
            adapter = stage.get("adapter")
            if isinstance(adapter, Mapping):
                identities.append({"kind": "adapter", **dict(adapter)})
        for binding in _mapping_list(
            dry_plan.get("contract_bindings", []), label="plan.contract_bindings"
        ):
            adapter = binding.get("adapter")
            if isinstance(adapter, Mapping):
                identities.append({"kind": "adapter", **dict(adapter)})
        if identities:
            expected_compatibility["capability_adapter_identity"] = identities
    drift, drift_blockers = _compatibility_drift(expected_compatibility, runtime)
    blockers.extend(drift_blockers)
    artifact_drift_status = (
        "drift"
        if artifact_blockers
        else ("match" if any(item["integrity"]["status"] == "pass" for item in all_artifacts) else "not_checked")
    )
    drift.append(
        {
            "category": "artifact_integrity",
            "status": artifact_drift_status,
            "expected": [item.get("sha256") for item in all_artifacts],
            "actual": [item["integrity"].get("actual_sha256") for item in all_artifacts],
            "reason": "explicit artifact verification result" if all_artifacts else "no artifacts were supplied",
        }
    )

    approval_rows: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    for stage in normalized_stages:
        for approval in stage["approvals"]:
            approval_rows.append({"stage_id": stage["stage_id"], **approval})
        checkpoint = stage.get("checkpoint")
        if checkpoint:
            checkpoints.append({"stage_id": stage["stage_id"], "checkpoint": checkpoint})
    checkpoints.extend(
        _mapping_list(dry_plan.get("checkpoints", []), label="plan.checkpoints")
    )
    approval_rows.extend(_mapping_list(dry_plan.get("approvals", []), label="plan.approvals"))
    pending_approvals = [item for item in approval_rows if item.get("status", "pending") == "pending" and item.get("required", True)]

    stage_statuses = [stage["execution_status"] for stage in normalized_stages]
    identity_statuses = [
        "pending" for row in drift[:-1] if row["status"] == "pending"
    ]
    mechanical_status = "blocked" if blockers else _aggregate(
        [
            *stage_statuses,
            *identity_statuses,
            *("pending" for _ in pending_approvals),
            *("warn" for _ in warnings),
        ]
    )
    human_decisions = _mapping_list(
        dry_plan.get("human_decisions", source.get("human_decisions", [])), label="human_decisions"
    )
    variants = _mapping_list(dry_plan.get("variants", source.get("variants", [])), label="variants")
    protected_human_fields = (
        "human_rating",
        "selected_for_continuation",
        "winner",
        "feedback",
        "continuation",
    )
    for label, rows in (("variant", variants), ("human decision", human_decisions)):
        for row in rows:
            populated = [field for field in protected_human_fields if row.get(field) is not None]
            if populated:
                raise ValueError(
                    f"planned {label} human fields must remain null; use an explicit human record: {populated}"
                )
    if human_records:
        for item in human_records:
            if item.get("status", "pass") not in EVIDENCE_STATES:
                raise ValueError(f"human record has invalid status: {item.get('status')}")
        human_status = _aggregate(
            str(item.get("status", "pass"))
            for item in human_records
        )
    elif human_decisions:
        human_status = "pending"
    else:
        human_status = "not_applicable"

    index: dict[str, Any] = {
        "schema": PROJECT_INDEX_SCHEMA,
        "project_id": source.get("project_id", dry_plan.get("project_id")),
        "source_sha256": source_hash,
        "plan_sha256": plan_hash,
        "mechanical_status": mechanical_status,
        "human_status": human_status,
        "runtime_identity": runtime,
        "compatibility": expected_compatibility,
        "variants": variants,
        "stages": normalized_stages,
        "contracts": _contracts(normalized_stages, dry_plan),
        "checkpoints": checkpoints,
        "artifacts": all_artifacts,
        "evidence_by_rung": {
            rung: [
                {"stage_id": stage["stage_id"], **row}
                for stage in normalized_stages
                for row in stage["evidence"]
                if row["rung"] == rung
            ]
            for rung in sorted(
                set(EVIDENCE_RUNGS).union(
                    row["rung"] for stage in normalized_stages for row in stage["evidence"]
                )
            )
        },
        "approvals": approval_rows,
        "human_decisions": human_decisions,
        "human_records": human_records,
        "rejected_lineage": _json_value(
            dry_plan.get(
                "rejected_lineage",
                dry_plan.get(
                    "rejected_alternatives",
                    source.get("rejected_lineage", source.get("rejected_alternatives", [])),
                ),
            ),
            label="rejected_lineage",
        ),
        "warnings": warnings,
        "blockers": blockers,
        "drift": drift,
        "automatic_execution": False,
        "automatic_ranking": False,
        "winner": next((item.get("winner") for item in human_records if item.get("winner") is not None), None),
    }
    index["index_sha256"] = _sha256(index, exclude=frozenset({"index_sha256"}))
    return index


__all__ = [
    "DRIFT_CATEGORIES",
    "EVIDENCE_RUNGS",
    "EVIDENCE_STATES",
    "PROJECT_INDEX_SCHEMA",
    "build_project_index",
]
