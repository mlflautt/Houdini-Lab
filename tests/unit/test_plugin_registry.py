"""Plugin governance stays pure and conservative outside Houdini."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from hermes_houdini.plugin_registry import (
    apprentice_verdict,
    audit_package_json,
    audit_plugin_archive,
    inventory_plugin_tree,
    load_plugin_manifest,
    validate_plugin_manifest,
)


def _manifest():
    return {
        "schema": "hermes.houdini.plugin",
        "schema_version": "1.0",
        "id": "sidefx-labs-22.0.368",
        "display_name": "SideFX Labs",
        "vendor": "SideFX",
        "plugin_version": "22.0.368",
        "kind": "tool_package",
        "source_url": "https://www.sidefx.com/download/download-labs/packages/",
        "license": "SideFX Labs LICENSE.md (permissive BSD-like terms)",
        "has_native_binaries": False,
        "target": {
            "houdini_build": "22.0.368",
            "platform": "macos",
            "architecture": "arm64",
            "license_modes": ["houdini-apprentice-noncommercial"],
        },
        "package": {
            "name": "SideFXLabs22.0",
            "checksum": "sha-256=mkoIk692DUaxIis/+6UUhGETyoSB5Hpl2lO1s8dOh9U=",
        },
        "permissions": {"network": False, "telemetry": False, "external_executables": False},
        "rollback": {
            "disable_environment": "HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json",
            "uninstall_command": "houdini_installer uninstall-package --package-name SideFXLabs22.0",
        },
        "fixtures": [
            {"id": "mesh", "context": "SOP", "max_seconds": 30, "max_points": 100000}
        ],
    }


def test_manifest_is_strict_and_adds_apprentice_verdict():
    validated = validate_plugin_manifest(_manifest())
    assert validated["apprentice"]["status"] == "allowed"
    broken = _manifest()
    broken["permissions"]["network"] = "unknown"
    with pytest.raises(ValueError, match="permissions.network"):
        validate_plugin_manifest(broken)


def test_apprentice_blocks_renderers_and_conditions_native_binaries():
    assert apprentice_verdict("renderer", has_native_binaries=True)["status"] == "blocked"
    assert apprentice_verdict("engine_plugin", has_native_binaries=False)["status"] == "blocked"
    assert apprentice_verdict("tool_package", has_native_binaries=True)["status"] == "conditional"


def test_package_json_audit_and_tree_inventory(tmp_path):
    root = tmp_path / "labs"
    root.mkdir()
    (root / "otls").mkdir()
    (root / "python3.11libs").mkdir()
    (root / "otls" / "tool.hdalc").write_bytes(b"hda")
    (root / "python3.11libs" / "tool.py").write_text("VALUE = 1\n", encoding="utf-8")
    package = tmp_path / "SideFXLabs22.0.json"
    package.write_text(
        json.dumps({"package_name": "SideFXLabs22.0", "enable": False, "path": str(root)}),
        encoding="utf-8",
    )
    audit = audit_package_json(package, plugin_root=root, expected_name="SideFXLabs22.0")
    assert audit["enabled"] is False
    assert audit["plugin_root_referenced"] is True
    inventory = inventory_plugin_tree(root)
    assert inventory["counts"] == {"files": 2, "hda_libraries": 1, "python_files": 1}
    assert inventory["total_bytes"] > 0
    assert inventory["mutation_performed"] is False


def test_inventory_rejects_symlink_escape(tmp_path):
    root = tmp_path / "plugin"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (root / "escape").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink escapes"):
        inventory_plugin_tree(root)


def test_archive_audit_requires_exact_safe_top_levels(tmp_path):
    archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("Plugin.json", "{}")
        bundle.writestr("Plugin/tool.hda", "fixture")
    report = audit_plugin_archive(
        archive.resolve(), expected_top_levels={"Plugin.json", "Plugin"}
    )
    assert report["top_levels"] == ["Plugin", "Plugin.json"]
    assert report["member_count"] == 2
    malicious = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious, "w") as bundle:
        bundle.writestr("../escape", "bad")
    with pytest.raises(ValueError, match="unsafe"):
        audit_plugin_archive(malicious.resolve(), expected_top_levels={"Plugin"})


def test_committed_labs_record_uses_verified_filename_skiplist():
    root = Path(__file__).resolve().parents[2]
    record = load_plugin_manifest((root / "plugins" / "sidefx-labs-22.0.368.json").resolve())
    assert record["plugin_version"] == "22.0.368"
    assert record["rollback"]["disable_environment"].endswith("SideFXLabs22.0.json")
    assert record["certified_node_types"] == [
        "labs::measure_curvature::3.1",
        "labs::terrain_analysis::1.0",
        "labs::instance_attributes::1.0",
    ]
