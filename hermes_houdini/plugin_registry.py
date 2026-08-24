"""Pure-Python governance and inventory for optional Houdini packages.

This module never imports :mod:`hou` and never installs or loads plugin code.  It
validates repository records, inspects Houdini package JSON, and inventories an
already-extracted package tree without following links outside that tree.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

_BUILD = re.compile(r"\d+\.\d+\.\d+")
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._-]*")
_SHA256 = re.compile(r"sha-256=[A-Za-z0-9+/]{43}=")

PLUGIN_KINDS = {
    "tool_package",
    "hda_library",
    "python_tool",
    "viewer_state",
    "vex_library",
    "native_operator",
    "renderer",
    "engine_plugin",
}
APPRENTICE_BLOCKED_KINDS = {"renderer", "engine_plugin"}
_HDA_SUFFIXES = {".hda", ".otl", ".hdalc", ".hdanc"}
_BINARY_SUFFIXES = {".dylib", ".so", ".dll"}


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def apprentice_verdict(plugin_kind: str, *, has_native_binaries: bool) -> dict[str, str]:
    """Return the conservative Apprentice policy verdict for a plugin class."""
    if plugin_kind not in PLUGIN_KINDS:
        raise ValueError(f"unknown plugin kind: {plugin_kind}")
    if plugin_kind == "renderer":
        return {
            "status": "blocked",
            "reason": "Houdini Apprentice does not support third-party renderers",
        }
    if plugin_kind == "engine_plugin":
        return {
            "status": "blocked",
            "reason": "Apprentice-created assets cannot be used through Houdini Engine",
        }
    if has_native_binaries or plugin_kind == "native_operator":
        return {
            "status": "conditional",
            "reason": "requires exact Houdini ABI, platform, architecture, and signature checks",
        }
    return {
        "status": "allowed",
        "reason": "graph-visible tool package; node-level fixtures and license review still required",
    }


def validate_plugin_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one repository-side plugin registry record."""
    if not isinstance(data, dict):
        raise ValueError("plugin manifest must be an object")
    if data.get("schema") != "hermes.houdini.plugin":
        raise ValueError("schema must be hermes.houdini.plugin")
    if data.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")

    plugin_id = _require_string(data.get("id"), "id")
    if not _IDENTIFIER.fullmatch(plugin_id):
        raise ValueError("id must contain only lowercase letters, digits, dot, dash, or underscore")
    kind = _require_string(data.get("kind"), "kind")
    if kind not in PLUGIN_KINDS:
        raise ValueError(f"kind must be one of {sorted(PLUGIN_KINDS)}")

    source_url = _require_string(data.get("source_url"), "source_url")
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("source_url must be an https URL")

    target = data.get("target")
    if not isinstance(target, dict):
        raise ValueError("target must be an object")
    build = _require_string(target.get("houdini_build"), "target.houdini_build")
    if not _BUILD.fullmatch(build):
        raise ValueError("target.houdini_build must be a full numeric build")
    if target.get("platform") not in {"macos", "linux", "windows"}:
        raise ValueError("target.platform must be macos, linux, or windows")
    if target.get("architecture") not in {"arm64", "x86_64"}:
        raise ValueError("target.architecture must be arm64 or x86_64")
    modes = target.get("license_modes")
    if not isinstance(modes, list) or not modes or not all(isinstance(x, str) and x for x in modes):
        raise ValueError("target.license_modes must be a non-empty string list")

    package = data.get("package")
    if not isinstance(package, dict):
        raise ValueError("package must be an object")
    package_name = _require_string(package.get("name"), "package.name")
    checksum = _require_string(package.get("checksum"), "package.checksum")
    if not _SHA256.fullmatch(checksum):
        raise ValueError("package.checksum must be a base64 sha-256 checksum")

    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        raise ValueError("permissions must be an object")
    for key in ("network", "telemetry", "external_executables"):
        if not isinstance(permissions.get(key), bool):
            raise ValueError(f"permissions.{key} must be boolean")

    rollback = data.get("rollback")
    if not isinstance(rollback, dict):
        raise ValueError("rollback must be an object")
    _require_string(rollback.get("disable_environment"), "rollback.disable_environment")
    _require_string(rollback.get("uninstall_command"), "rollback.uninstall_command")

    fixtures = data.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixtures must contain at least one bounded fixture")
    seen: set[str] = set()
    for index, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict):
            raise ValueError(f"fixtures[{index}] must be an object")
        fixture_id = _require_string(fixture.get("id"), f"fixtures[{index}].id")
        if fixture_id in seen:
            raise ValueError(f"duplicate fixture id: {fixture_id}")
        seen.add(fixture_id)
        if fixture.get("context") not in {"SOP", "OBJ", "LOP", "DOP", "TOP", "COP", "CHOP"}:
            raise ValueError(f"fixtures[{index}].context is invalid")
        for budget in ("max_seconds", "max_points"):
            value = fixture.get(budget)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"fixtures[{index}].{budget} must be a positive integer")

    has_native = bool(data.get("has_native_binaries", False))
    normalized = dict(data)
    normalized["display_name"] = _require_string(data.get("display_name"), "display_name")
    normalized["vendor"] = _require_string(data.get("vendor"), "vendor")
    normalized["plugin_version"] = _require_string(data.get("plugin_version"), "plugin_version")
    normalized["license"] = _require_string(data.get("license"), "license")
    normalized["id"] = plugin_id
    normalized["kind"] = kind
    normalized["source_url"] = source_url
    normalized["package"] = {**package, "name": package_name, "checksum": checksum}
    normalized["apprentice"] = apprentice_verdict(kind, has_native_binaries=has_native)
    return normalized


def load_plugin_manifest(path: str | Path) -> dict[str, Any]:
    """Read and validate a JSON-compatible plugin registry record."""
    manifest_path = Path(path).expanduser()
    if not manifest_path.is_absolute() or not manifest_path.is_file():
        raise ValueError("manifest path must be an existing absolute file")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read plugin manifest: {exc}") from exc
    return validate_plugin_manifest(data)


def audit_package_json(
    package_path: str | Path, *, plugin_root: str | Path, expected_name: str
) -> dict[str, Any]:
    """Inspect a Houdini package definition without loading the referenced package."""
    package_file = Path(package_path).expanduser()
    root = Path(plugin_root).expanduser()
    if not package_file.is_absolute() or not package_file.is_file():
        raise ValueError("package_path must be an existing absolute JSON file")
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("plugin_root must be an existing absolute directory")
    try:
        data = json.loads(package_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read package JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("package JSON must contain an object")
    package_name = data.get("package_name") or data.get("name") or package_file.stem
    if package_name != expected_name:
        raise ValueError(f"package name {package_name!r} does not match {expected_name!r}")
    serialized = json.dumps(data, sort_keys=True)
    root_referenced = str(root) in serialized or "$HOUDINI_PACKAGE_PATH" in serialized
    return {
        "schema": "hermes.houdini.package_audit",
        "schema_version": "1.0",
        "package_path": str(package_file),
        "package_sha256": _sha256_file(package_file),
        "package_name": package_name,
        "enabled": data.get("enable", True) is not False,
        "plugin_root": str(root.resolve()),
        "plugin_root_referenced": root_referenced,
        "keys": sorted(data),
        "mutation_performed": False,
    }


def audit_plugin_archive(
    archive_path: str | Path, *, expected_top_levels: set[str]
) -> dict[str, Any]:
    """Inspect a ZIP package before extraction without loading its contents as code."""
    archive = Path(archive_path).expanduser()
    if not archive.is_absolute() or archive.suffix.lower() != ".zip" or not archive.is_file():
        raise ValueError("archive_path must be an existing absolute ZIP file")
    if not expected_top_levels or not all(isinstance(item, str) and item for item in expected_top_levels):
        raise ValueError("expected_top_levels must be a non-empty string set")
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
    unsafe = []
    top_levels: set[str] = set()
    total_uncompressed_bytes = 0
    for info in infos:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            unsafe.append(info.filename)
            continue
        top_levels.add(path.parts[0])
        total_uncompressed_bytes += info.file_size
    if unsafe:
        raise ValueError("archive contains unsafe absolute or traversal paths")
    unexpected = top_levels - expected_top_levels
    missing = expected_top_levels - top_levels
    if unexpected or missing:
        raise ValueError(
            f"archive top levels do not match: unexpected={sorted(unexpected)}, missing={sorted(missing)}"
        )
    return {
        "schema": "hermes.houdini.plugin_archive_audit",
        "schema_version": "1.0",
        "archive_path": str(archive),
        "archive_sha256": _sha256_file(archive),
        "archive_bytes": archive.stat().st_size,
        "uncompressed_bytes": total_uncompressed_bytes,
        "member_count": len(infos),
        "top_levels": sorted(top_levels),
        "mutation_performed": False,
    }


def inventory_plugin_tree(plugin_root: str | Path) -> dict[str, Any]:
    """Inventory files without executing code or following links outside the root."""
    root = Path(plugin_root).expanduser()
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("plugin_root must be an existing absolute directory")
    resolved_root = root.resolve()
    counts: Counter[str] = Counter()
    total_bytes = 0
    links: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            target = path.resolve()
            try:
                target.relative_to(resolved_root)
            except ValueError as exc:
                raise ValueError(f"symlink escapes plugin root: {path}") from exc
            links.append({"path": str(path), "target": str(target)})
            continue
        if not path.is_file():
            continue
        counts["files"] += 1
        total_bytes += path.stat().st_size
        suffix = path.suffix.lower()
        parts = {part.lower() for part in path.parts}
        if suffix in _HDA_SUFFIXES:
            counts["hda_libraries"] += 1
        if suffix in _BINARY_SUFFIXES:
            counts["native_binaries"] += 1
        if suffix == ".py":
            counts["python_files"] += 1
        if suffix in {".vex", ".vfl"}:
            counts["vex_files"] += 1
        if "viewer_states" in parts or "viewerstates" in parts:
            counts["viewer_state_files"] += 1
        if "toolbar" in parts or suffix == ".shelf":
            counts["shelf_files"] += 1
    return {
        "schema": "hermes.houdini.plugin_inventory",
        "schema_version": "1.0",
        "plugin_root": str(resolved_root),
        "counts": dict(sorted(counts.items())),
        "total_bytes": total_bytes,
        "symlinks": links,
        "mutation_performed": False,
    }


__all__ = [
    "APPRENTICE_BLOCKED_KINDS",
    "PLUGIN_KINDS",
    "apprentice_verdict",
    "audit_plugin_archive",
    "audit_package_json",
    "inventory_plugin_tree",
    "load_plugin_manifest",
    "validate_plugin_manifest",
]
