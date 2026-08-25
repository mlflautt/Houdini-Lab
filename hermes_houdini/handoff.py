"""Hashed, path-confined handoff artifacts and dry resume planning."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .schemas.control_plane import CompatibilityIdentity, HandoffBundle, IntentPlan


def _inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_path(root: Path, value: str, *, allow_empty: bool = False) -> Path | None:
    if allow_empty and not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"handoff path must be absolute: {value}")
    resolved = path.resolve(strict=False)
    if not _inside(root, resolved):
        raise ValueError(f"handoff path outside project_root: {value}")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_artifacts(root: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            raise ValueError("each handoff artifact requires a string path")
        item = dict(artifact)
        path = _safe_path(root, item["path"])
        item["path"] = str(path)
        item["exists"] = bool(path and path.is_file())
        if path and path.is_file():
            actual_hash = _sha256_file(path)
            if item.get("sha256") and item["sha256"] != actual_hash:
                raise ValueError(f"artifact hash mismatch before handoff: {path}")
            item["sha256"] = actual_hash
            item["size_bytes"] = path.stat().st_size
        else:
            item.setdefault("sha256", "")
            item.setdefault("size_bytes", 0)
        normalized.append(item)
    return normalized


def _validate_bundle_paths(bundle: HandoffBundle) -> list[str]:
    root = Path(bundle.project_root).expanduser().resolve(strict=False)
    if not root.is_absolute():
        raise ValueError("handoff project_root must be absolute")
    referenced: list[str] = []
    checkpoint = _safe_path(root, bundle.checkpoint, allow_empty=True)
    if checkpoint:
        referenced.append(str(checkpoint))
    for value in bundle.replay_logs:
        referenced.append(str(_safe_path(root, value)))
    for artifact in bundle.artifacts:
        referenced.append(str(_safe_path(root, str(artifact.get("path", "")))))
    return referenced


def create_handoff(
    *,
    output_path: str,
    project_root: str,
    project_id: str,
    session_id: str,
    compatibility: dict[str, Any],
    intent_plan: dict[str, Any],
    checkpoint: str = "",
    replay_logs: list[str] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    stable_nodes: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    rejected_alternatives: list[dict[str, Any]] | None = None,
    human_feedback: list[dict[str, Any]] | None = None,
    pending_gates: list[str] | None = None,
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve(strict=False)
    if not Path(project_root).expanduser().is_absolute():
        raise ValueError("project_root must be absolute")
    output = _safe_path(root, output_path)
    _safe_path(root, checkpoint, allow_empty=True)
    replay = [str(_safe_path(root, value)) for value in (replay_logs or [])]
    normalized_artifacts = _normalize_artifacts(root, artifacts or [])
    bundle = HandoffBundle(
        project_id=project_id,
        session_id=session_id,
        project_root=str(root),
        compatibility=CompatibilityIdentity.from_dict(compatibility),
        intent_plan=IntentPlan.from_dict(intent_plan),
        checkpoint=str(_safe_path(root, checkpoint, allow_empty=True) or ""),
        replay_logs=tuple(replay),
        artifacts=tuple(normalized_artifacts),
        stable_nodes=tuple(dict(item) for item in (stable_nodes or [])),
        evidence=tuple(dict(item) for item in (evidence or [])),
        warnings=tuple(warnings or []),
        rejected_alternatives=tuple(dict(item) for item in (rejected_alternatives or [])),
        human_feedback=tuple(dict(item) for item in (human_feedback or [])),
        pending_gates=tuple(pending_gates or []),
    )
    data = bundle.as_dict()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {"handoff": data, "output_path": str(output), "content_sha256": data["content_sha256"]}


def inspect_handoff(file_path: str, *, allowed_roots: list[str] | None = None) -> dict[str, Any]:
    path = Path(file_path).expanduser().resolve(strict=True)
    with path.open("r", encoding="utf-8") as stream:
        raw = json.load(stream)
    bundle = HandoffBundle.from_dict(raw, verify_hash=True)
    if allowed_roots:
        project_root = Path(bundle.project_root).expanduser().resolve(strict=False)
        approved = [Path(value).expanduser().resolve(strict=False) for value in allowed_roots]
        if not any(_inside(root, project_root) for root in approved):
            raise ValueError("handoff project_root outside dispatcher-approved roots")
    referenced = _validate_bundle_paths(bundle)
    integrity: list[dict[str, Any]] = []
    for artifact in bundle.artifacts:
        artifact_path = Path(str(artifact["path"]))
        exists = artifact_path.is_file()
        actual = _sha256_file(artifact_path) if exists else ""
        expected = str(artifact.get("sha256", ""))
        integrity.append(
            {
                "path": str(artifact_path),
                "exists": exists,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "valid": exists and bool(expected) and expected == actual,
            }
        )
    return {
        "valid": True,
        "file_path": str(path),
        "content_sha256": raw["content_sha256"],
        "bundle": bundle.as_dict(),
        "referenced_paths": referenced,
        "artifact_integrity": integrity,
    }


def _major_minor(version: str) -> tuple[str, ...]:
    return tuple(version.split(".")[:2])


def plan_resume(
    *,
    file_path: str,
    current_compatibility: dict[str, Any],
    allowed_roots: list[str] | None = None,
) -> dict[str, Any]:
    inspected = inspect_handoff(file_path, allowed_roots=allowed_roots)
    bundle = HandoffBundle.from_dict(inspected["bundle"])
    current = CompatibilityIdentity.from_dict(current_compatibility)
    expected = bundle.compatibility
    blockers: list[str] = []
    warnings: list[str] = list(bundle.warnings)
    if current.protocol_version != expected.protocol_version:
        blockers.append("protocol_version_mismatch")
    if _major_minor(current.houdini_build) != _major_minor(expected.houdini_build):
        blockers.append("houdini_major_minor_mismatch")
    elif current.houdini_build != expected.houdini_build:
        warnings.append("houdini_build_differs_within_compatible_major_minor")
    if current.license_mode != expected.license_mode:
        blockers.append("license_mode_mismatch")
    if current.package_version != expected.package_version:
        blockers.append("package_version_mismatch")
    missing_dependencies = sorted(
        set(expected.optional_dependencies).difference(current.optional_dependencies)
    )
    if missing_dependencies:
        blockers.append("missing_optional_dependencies:" + ",".join(missing_dependencies))
    invalid_artifacts = [
        item["path"] for item in inspected["artifact_integrity"] if not item["valid"]
    ]
    if invalid_artifacts:
        warnings.append("missing_or_changed_artifacts")
    steps = []
    if bundle.checkpoint:
        steps.append({"action": "load_checkpoint", "path": bundle.checkpoint})
    steps.extend({"action": "review_replay_log", "path": value} for value in bundle.replay_logs)
    steps.append(
        {
            "action": "review_pending_gates",
            "items": list(bundle.pending_gates),
            "requires_human_decision": bool(bundle.pending_gates),
        }
    )
    return {
        "schema": "hermes.houdini.resume_plan",
        "schema_version": "1.0",
        "status": "blocked" if blockers else ("warn" if warnings else "ready"),
        "automatic_execution": False,
        "blockers": blockers,
        "warnings": warnings,
        "invalid_artifacts": invalid_artifacts,
        "steps": steps,
        "intent_plan": bundle.intent_plan.as_dict(),
        "rejected_alternatives": [dict(item) for item in bundle.rejected_alternatives],
        "human_feedback": [dict(item) for item in bundle.human_feedback],
    }


__all__ = ["create_handoff", "inspect_handoff", "plan_resume"]
