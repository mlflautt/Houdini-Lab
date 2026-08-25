"""Deterministic capability catalog assembled from every bounded registry."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, get_args, get_origin

from . import __version__
from .registry import REGISTRY, Entry
from .schemas.control_plane import CapabilityRecord, content_hash
from .skill_loader import discover_skills

_ROOT = Path(__file__).resolve().parent.parent
_RISK_ORDER = {"read_only": 0, "low": 1, "medium": 2, "high": 3, "external": 4}
_PINNED_TESTED_BUILDS = ("22.0.368",)


def _annotation_name(value: Any) -> str:
    if value is inspect.Parameter.empty:
        return "any"
    origin = get_origin(value)
    if origin is not None:
        args = [_annotation_name(item) for item in get_args(value) if item is not type(None)]
        return " | ".join(args) or str(origin)
    return getattr(value, "__name__", str(value).replace("typing.", ""))


def _handler_inputs(entry: Entry) -> dict[str, Any]:
    described: dict[str, Any] = {}
    try:
        parameters = inspect.signature(entry.handler).parameters.values()
    except (TypeError, ValueError):
        return described
    for parameter in parameters:
        if parameter.name.startswith("_"):
            continue
        item: dict[str, Any] = {"type": _annotation_name(parameter.annotation)}
        if parameter.default is not inspect.Parameter.empty:
            item["required"] = False
            if parameter.default is not None and isinstance(
                parameter.default, (str, int, float, bool, list, dict)
            ):
                item["default"] = parameter.default
        else:
            item["required"] = True
        described[parameter.name] = item
    return described


def _infer_contexts(entry: Entry) -> tuple[str, ...]:
    contexts = entry.meta.get("contexts")
    if isinstance(contexts, list) and contexts:
        return tuple(sorted({str(item).upper() for item in contexts}))
    prefix = entry.name.split(".", 1)[0]
    mapping = {
        "cop": ("COP",),
        "hda": ("SOP",),
        "karma": ("LOP", "ROP"),
        "lookdev": ("LOP",),
        "material": ("LOP",),
        "node": ("OBJ", "SOP", "LOP", "DOP", "TOP", "COP", "CHOP", "APEX"),
        "pdg": ("TOP",),
        "render": ("LOP", "ROP"),
        "solaris": ("LOP",),
        "stage": ("LOP",),
        "viewport": ("VIEWPORT",),
    }
    return mapping.get(prefix, ("SYSTEM",))


def _license_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value:
        return {"mode": value}
    return {"mode": "houdini-apprentice-noncommercial"}


def _source_path(value: Any) -> str:
    path = Path(str(value or "hermes_houdini/tools/__init__.py"))
    if path.is_absolute():
        try:
            return str(path.resolve().relative_to(_ROOT))
        except ValueError:
            return f"external:{path.name}"
    return str(path)


def _entry_record(entry: Entry) -> CapabilityRecord:
    risk = entry.risk
    outputs = entry.meta.get("outputs", [])
    if isinstance(outputs, dict):
        outputs = list(outputs)
    dependencies = entry.meta.get("optional_dependencies", entry.meta.get("dependencies", []))
    return CapabilityRecord(
        capability_id=entry.name,
        version=entry.version,
        kind=entry.kind,
        summary=entry.doc or f"Registered {entry.kind} {entry.name}",
        contexts=_infer_contexts(entry),
        risk=risk,
        inputs=dict(entry.meta.get("inputs", {})) or _handler_inputs(entry),
        outputs=tuple(str(item) for item in outputs),
        approvals=(f"explicit_{risk}_risk_approval",) if _RISK_ORDER.get(risk, 9) >= 2 else (),
        cook_budget=dict(entry.meta.get("cook_budget", {})),
        license=_license_dict(entry.meta.get("license")),
        tested_builds=tuple(
            str(item) for item in entry.meta.get("tested_builds", _PINNED_TESTED_BUILDS)
        ),
        optional_dependencies=tuple(str(item) for item in dependencies),
        fallbacks=tuple(str(item) for item in entry.meta.get("fallbacks", [])),
        evidence_status=str(entry.meta.get("evidence_status", "pending")),
        source=_source_path(entry.meta.get("source", "hermes_houdini/tools/__init__.py")),
    )


def _skill_records(skills_root: Path) -> list[CapabilityRecord]:
    records: list[CapabilityRecord] = []
    for skill in discover_skills(skills_root):
        manifest = skill.manifest
        houdini = manifest.get("houdini", {})
        dependencies = manifest.get("optional_dependencies", manifest.get("dependencies", []))
        if isinstance(dependencies, dict):
            dependencies = list(dependencies)
        records.append(
            CapabilityRecord(
                capability_id=skill.id,
                version=skill.version,
                kind="skill",
                summary=str(manifest["summary"]),
                contexts=tuple(str(item).upper() for item in manifest["contexts"]),
                risk=str(manifest["risk"]),
                inputs=dict(manifest["inputs"]),
                outputs=tuple(str(item) for item in manifest.get("outputs", [])),
                approvals=(
                    f"explicit_{manifest['risk']}_risk_approval",
                )
                if _RISK_ORDER.get(str(manifest["risk"]), 9) >= 2
                else (),
                cook_budget=dict(manifest.get("cook_budget", {})),
                license=_license_dict(manifest.get("license")),
                tested_builds=tuple(str(item) for item in houdini.get("tested_builds", [])),
                optional_dependencies=tuple(str(item) for item in dependencies),
                fallbacks=tuple(str(item) for item in manifest.get("fallbacks", [])),
                evidence_status=str(manifest.get("evidence_status", "pending")),
                source=str(skill.root.relative_to(_ROOT) / "skill.yaml"),
            )
        )
    return records


def build_catalog(
    *,
    context: str = "",
    risk: str = "",
    kind: str = "",
    license_mode: str = "",
    houdini_build: str = "",
    dependency: str = "",
    skills_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build and filter a stable catalog without importing ``hou``."""
    if risk and risk not in _RISK_ORDER:
        raise ValueError(f"unsupported risk filter: {risk}")
    if kind and kind not in {"tool", "recipe", "hda", "skill"}:
        raise ValueError(f"unsupported capability kind filter: {kind}")
    context = context.upper()
    records = [_entry_record(entry) for entry in REGISTRY.list()]
    records.extend(_skill_records(Path(skills_root or (_ROOT / "skills"))))
    records = sorted(records, key=lambda item: (item.kind, item.capability_id, item.version))
    filtered = []
    for record in records:
        if context and context not in record.contexts:
            continue
        if risk and record.risk != risk:
            continue
        if kind and record.kind != kind:
            continue
        if license_mode and record.license.get("mode") != license_mode:
            continue
        if houdini_build and houdini_build not in record.tested_builds:
            continue
        if dependency and dependency not in record.optional_dependencies:
            continue
        filtered.append(record.as_dict())
    payload = {
        "schema": "hermes.houdini.capability_catalog",
        "schema_version": "1.0",
        "package_version": __version__,
        "filters": {
            "context": context,
            "risk": risk,
            "kind": kind,
            "license_mode": license_mode,
            "houdini_build": houdini_build,
            "dependency": dependency,
        },
        "record_count": len(filtered),
        "records": filtered,
    }
    payload["catalog_sha256"] = content_hash(payload)
    return payload


__all__ = ["build_catalog"]
