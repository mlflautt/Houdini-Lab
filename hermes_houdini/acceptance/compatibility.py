"""Pure compatibility diffing plus narrow, read-only Houdini introspection."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

COMPATIBILITY_SCHEMA = "hermes.houdini.acceptance.compatibility.v1"
_VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)*$")


def _version(value: object, *, label: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not _VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be a dotted numeric build string")
    return tuple(int(part) for part in value.split("."))


def _json_value(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    return str(value)


def _parameter_specs(value: object, *, label: str) -> dict[str, dict[str, object]]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    result: dict[str, dict[str, object]] = {}
    for name, raw_spec in value.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{label} names must be non-empty strings")
        if not isinstance(raw_spec, Mapping):
            raise ValueError(f"{label}.{name} must be a mapping")
        unknown = sorted(set(raw_spec) - {"type", "default"})
        if unknown:
            raise ValueError(f"{label}.{name} has unknown fields: {', '.join(unknown)}")
        spec: dict[str, object] = {}
        if "type" in raw_spec:
            if not isinstance(raw_spec["type"], str) or not raw_spec["type"]:
                raise ValueError(f"{label}.{name}.type must be a non-empty string")
            spec["type"] = raw_spec["type"]
        if "default" in raw_spec:
            spec["default"] = _json_value(raw_spec["default"])
        result[name] = spec
    return {name: result[name] for name in sorted(result)}


def normalize_expectation(expectation: Mapping[str, object]) -> dict[str, Any]:
    """Validate and normalize a complete operator compatibility expectation."""

    if not isinstance(expectation, Mapping):
        raise ValueError("expectation must be a mapping")
    for field in ("expectation_id", "context", "category", "operator_type"):
        if not isinstance(expectation.get(field), str) or not expectation[field]:
            raise ValueError(f"{field} must be a non-empty string")
    required = _parameter_specs(expectation.get("required_parameters"), label="required_parameters")
    optional = _parameter_specs(expectation.get("optional_parameters"), label="optional_parameters")
    overlap = sorted(set(required) & set(optional))
    if overlap:
        raise ValueError(f"parameters cannot be both required and optional: {', '.join(overlap)}")

    raw_range = expectation.get("tested_build_range")
    if not isinstance(raw_range, Mapping):
        raise ValueError("tested_build_range must be a mapping")
    minimum = raw_range.get("minimum")
    maximum = raw_range.get("maximum")
    minimum_tuple = _version(minimum, label="tested build minimum")
    maximum_tuple = _version(maximum, label="tested build maximum")
    if minimum_tuple > maximum_tuple:
        raise ValueError("tested build minimum must not exceed maximum")
    return {
        "expectation_id": expectation["expectation_id"],
        "context": expectation["context"],
        "category": expectation["category"],
        "operator_type": expectation["operator_type"],
        "required_parameters": required,
        "optional_parameters": optional,
        "tested_build_range": {"minimum": minimum, "maximum": maximum},
    }


def _diff(code: str, path: str, expected: object, observed: object, message: str) -> dict[str, object]:
    return {
        "code": code,
        "path": path,
        "expected": expected,
        "observed": observed,
        "message": message,
    }


def _spec_text(spec: Mapping[str, object]) -> str:
    parts = []
    if "type" in spec:
        parts.append(str(spec["type"]))
    if "default" in spec:
        parts.append(f"default {spec['default']}")
    return " ".join(parts) or "declared"


def compare_compatibility(
    expectation: Mapping[str, object], observation: Mapping[str, object]
) -> dict[str, Any]:
    """Return deterministic, human-readable operator and parameter drift."""

    expected = normalize_expectation(expectation)
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    live_build = observation.get("live_build")
    license_mode = observation.get("license")
    if not isinstance(live_build, str) or not isinstance(license_mode, str):
        raise ValueError("observation must name live_build and license")
    live_version = _version(live_build, label="live build")
    diffs: list[dict[str, object]] = []

    build_range = expected["tested_build_range"]
    if not (_version(build_range["minimum"], label="minimum") <= live_version <= _version(build_range["maximum"], label="maximum")):
        diffs.append(
            _diff(
                "build_outside_tested_range",
                "live_build",
                f"{build_range['minimum']}..{build_range['maximum']}",
                live_build,
                f"live Houdini build {live_build} is outside tested range "
                f"{build_range['minimum']}..{build_range['maximum']}",
            )
        )
    for field in ("context", "category", "operator_type"):
        if observation.get(field) != expected[field]:
            diffs.append(
                _diff(
                    f"{field}_drift",
                    field,
                    expected[field],
                    observation.get(field),
                    f"{field} drift: expected {expected[field]}, observed {observation.get(field)}",
                )
            )

    operator_path = f"{expected['context']}/{expected['category']}/{expected['operator_type']}"
    if observation.get("available") is not True:
        diffs.append(
            _diff(
                "missing_operator",
                operator_path,
                "available",
                "missing",
                f"missing operator {operator_path} on Houdini {live_build} ({license_mode})",
            )
        )
    else:
        raw_parameters = observation.get("parameters")
        if not isinstance(raw_parameters, Mapping):
            raise ValueError("available operator observation must include parameter mappings")
        parameters = {
            str(name): dict(spec) if isinstance(spec, Mapping) else {}
            for name, spec in raw_parameters.items()
        }
        declared = {**expected["required_parameters"], **expected["optional_parameters"]}
        for name, spec in expected["required_parameters"].items():
            if name not in parameters:
                diffs.append(
                    _diff(
                        "missing_parameter",
                        f"parameters.{name}",
                        spec,
                        "missing",
                        f"{expected['operator_type']} is missing required parameter {name} "
                        f"(expected {_spec_text(spec)})",
                    )
                )
        for name in sorted(set(parameters) & set(declared)):
            spec = declared[name]
            actual = parameters[name]
            if "type" in spec and actual.get("type") != spec["type"]:
                diffs.append(
                    _diff(
                        "parameter_type_drift",
                        f"parameters.{name}",
                        spec["type"],
                        actual.get("type"),
                        f"{expected['operator_type']}.{name} type drift: expected "
                        f"{spec['type']}, observed {actual.get('type')}",
                    )
                )
            actual_default = _json_value(actual.get("default"))
            if "default" in spec and actual_default != spec["default"]:
                diffs.append(
                    _diff(
                        "parameter_default_drift",
                        f"parameters.{name}",
                        spec["default"],
                        actual_default,
                        f"{expected['operator_type']}.{name} default drift: expected "
                        f"{spec['default']}, observed {actual_default}",
                    )
                )
        for name in sorted(set(parameters) - set(declared)):
            diffs.append(
                _diff(
                    "unexpected_parameter",
                    f"parameters.{name}",
                    "not declared",
                    parameters[name],
                    f"{expected['operator_type']} has unexpected parameter {name}",
                )
            )

    priority = {
        "missing_parameter": 0,
        "parameter_type_drift": 1,
        "parameter_default_drift": 2,
        "unexpected_parameter": 3,
    }
    diffs.sort(key=lambda item: (str(item["path"]), priority.get(str(item["code"]), 0)))
    return {
        "schema": COMPATIBILITY_SCHEMA,
        "expectation_id": expected["expectation_id"],
        "status": "pass" if not diffs else "blocked",
        "compatible": not diffs,
        "live_build": live_build,
        "license": license_mode,
        "context": observation.get("context"),
        "category": observation.get("category"),
        "operator_type": observation.get("operator_type"),
        "diffs": diffs,
    }


def _hou_category(hou: Any, context: str) -> Any:
    factories = {
        "SOP": "sopNodeTypeCategory",
        "OBJ": "objNodeTypeCategory",
        "LOP": "lopNodeTypeCategory",
        "DOP": "dopNodeTypeCategory",
        "TOP": "topNodeTypeCategory",
        "COP": "copNodeTypeCategory",
        "CHOP": "chopNodeTypeCategory",
        "APEX": "apexNodeTypeCategory",
    }
    factory_name = factories.get(context)
    factory = getattr(hou, factory_name, None) if factory_name else None
    if factory is None:
        raise ValueError(f"unsupported Houdini context: {context}")
    return factory()


def _template_default(template: Any, hou: Any) -> object:
    try:
        return _json_value(template.defaultValue())
    except (AttributeError, hou.OperationFailed):
        return None


def validate_compatibility_output_path(output_path: str | os.PathLike[str]) -> Path:
    """Resolve an explicit compatibility artifact path under an allowed narrow parent."""
    from .schema import validate_artifact_root

    destination = Path(output_path).expanduser()
    if not destination.is_absolute():
        raise ValueError("compatibility output_path must be absolute")
    validate_artifact_root(str(destination.parent))
    return destination.resolve(strict=False)


def probe_compatibility(
    expectation: Mapping[str, object], *, output_path: str | os.PathLike[str] | None = None
) -> dict[str, Any]:
    """Inspect operator definitions without creating nodes, cooking, or changing Houdini state.

    ``hou`` is imported lazily.  The result is returned in memory and is written only when
    ``output_path`` is explicitly supplied; existing files are never overwritten.
    """

    import hou  # type: ignore[import-not-found]  # noqa: PLC0415

    expected = normalize_expectation(expectation)
    category = _hou_category(hou, expected["context"])
    node_type = category.nodeTypes().get(expected["operator_type"])
    parameters = {}
    if node_type is not None:
        parameters = {
            template.name(): {
                "type": template.type().name(),
                "default": _template_default(template, hou),
            }
            for template in node_type.parmTemplates()
        }
    license_category = hou.licenseCategory()
    license_mode = (
        license_category.name()
        if callable(getattr(license_category, "name", None))
        else str(license_category)
    )
    observation = {
        "live_build": hou.applicationVersionString(),
        "license": license_mode,
        "context": expected["context"],
        "category": category.name(),
        "operator_type": expected["operator_type"],
        "available": node_type is not None,
        "parameters": parameters,
    }
    result = compare_compatibility(expected, observation)
    result["mutation_performed"] = False
    if output_path is not None:
        destination = validate_compatibility_output_path(output_path)
        rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    return result


__all__ = [
    "COMPATIBILITY_SCHEMA",
    "compare_compatibility",
    "normalize_expectation",
    "probe_compatibility",
    "validate_compatibility_output_path",
]
