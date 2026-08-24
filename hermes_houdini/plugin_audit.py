"""Pure, non-installing compatibility audit for optional Houdini plugin archives."""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

_HOUDINI_BUILD = re.compile(r"Houdini_(\d+\.\d+\.\d+)")
_OCTANE_VERSION = re.compile(r"Octane_(\d+(?:\.\d+){3})")
_THIRD_PARTY_LICENSES = {
    "houdini-indie",
    "houdini-education",
    "houdini-core",
    "houdini-fx",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_octane_archive(
    archive_path: str, *, target_houdini_build: str, license_mode: str
) -> dict[str, Any]:
    """Inspect filenames and hashes without extracting or loading plugin code."""
    archive = Path(archive_path).expanduser()
    if not archive.is_absolute() or archive.suffix.lower() != ".zip" or not archive.is_file():
        raise ValueError("archive_path must be an existing absolute .zip file")
    if not re.fullmatch(r"\d+\.\d+\.\d+", target_houdini_build):
        raise ValueError("target_houdini_build must be a full numeric Houdini build")
    if not isinstance(license_mode, str) or not license_mode:
        raise ValueError("license_mode must be a non-empty string")

    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
    unsafe = [
        name
        for name in names
        if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
    ]
    if unsafe:
        raise ValueError("archive contains unsafe absolute or traversal paths")
    builds = sorted({match for name in names for match in _HOUDINI_BUILD.findall(name)})
    versions = sorted({match for name in names for match in _OCTANE_VERSION.findall(name)})
    lower_name = archive.name.lower()
    edition = next(
        (value for value in ("prime", "studio+", "demo") if value.replace("+", "") in lower_name),
        "unknown",
    )
    third_party_allowed = license_mode in _THIRD_PARTY_LICENSES
    exact_build = target_houdini_build in builds
    reasons: list[str] = []
    if not exact_build:
        reasons.append(f"archive has no binary compiled for Houdini {target_houdini_build}")
    if not third_party_allowed:
        reasons.append(f"license mode {license_mode} does not allow third-party renderers")
    if "macos" not in lower_name:
        reasons.append("archive filename does not declare macOS")
    return {
        "schema": "hermes.houdini.optional_plugin_audit",
        "schema_version": "1.0",
        "plugin": "OctaneRender for Houdini",
        "archive": str(archive),
        "archive_sha256": _sha256(archive),
        "octane_versions": versions,
        "edition": edition,
        "packaged_houdini_builds": builds,
        "target": {
            "houdini_build": target_houdini_build,
            "license_mode": license_mode,
            "third_party_renderer_allowed": third_party_allowed,
        },
        "install_ready": exact_build and third_party_allowed and not reasons,
        "blockers": reasons,
        "mutation_performed": False,
    }


__all__ = ["audit_octane_archive"]
