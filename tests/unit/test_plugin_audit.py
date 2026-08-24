"""Optional renderer archives are inspected without loading their code."""

from __future__ import annotations

import zipfile

import pytest
from hermes_houdini.plugin_audit import audit_octane_archive


def _archive(tmp_path, name="Octane_2025.2.1.0_Houdini_Prime_macos.zip"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr(
            "Octane_2025.2.1.0_Houdini_20.5.613_Prime_macos/dso/Houdini_Octane_20.5.613.dylib",
            b"fixture",
        )
    return path


def test_octane_audit_blocks_apprentice_and_wrong_houdini_build(tmp_path):
    report = audit_octane_archive(
        str(_archive(tmp_path)),
        target_houdini_build="22.0.368",
        license_mode="houdini-apprentice-noncommercial",
    )
    assert report["packaged_houdini_builds"] == ["20.5.613"]
    assert report["octane_versions"] == ["2025.2.1.0"]
    assert report["install_ready"] is False
    assert len(report["blockers"]) == 2
    assert report["mutation_performed"] is False


def test_octane_audit_accepts_exact_build_only_for_supported_license(tmp_path):
    report = audit_octane_archive(
        str(_archive(tmp_path)),
        target_houdini_build="20.5.613",
        license_mode="houdini-indie",
    )
    assert report["install_ready"] is True
    assert report["blockers"] == []
    malicious = tmp_path / "Octane_2025.2.1.0_Houdini_Prime_macos_bad.zip"
    with zipfile.ZipFile(malicious, "w") as bundle:
        bundle.writestr("../escape", b"bad")
    with pytest.raises(ValueError, match="unsafe"):
        audit_octane_archive(
            str(malicious),
            target_houdini_build="20.5.613",
            license_mode="houdini-indie",
        )
