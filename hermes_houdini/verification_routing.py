"""Deterministic routing across structural, pixel, model, and human verification gates."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
STATUS_ORDER = {"pass": 0, "warn": 1, "fail": 2}
STATUS_ALIASES = {
    "pass": "pass",
    "success": "pass",
    "ok": "pass",
    "warn": "warn",
    "warning": "warn",
    "partial": "warn",
    "fail": "fail",
    "failed": "fail",
    "error": "fail",
    "blocked": "fail",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir() or root in {Path("/"), Path.home(), Path.home().parent}:
        raise ValueError("project_root must be an existing narrow absolute directory")
    return root


def _inside_file(value: str, *, root: Path, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file() or not path.is_relative_to(root):
        raise ValueError(f"{label} must be an existing file inside project_root")
    return path


def _new_output(value: str, *, root: Path) -> Path:
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() != ".json" or not path.is_relative_to(root):
        raise ValueError("output_path must be an absolute .json path inside project_root")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite verification route: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(path: Path, *, label: str, expected_schema: str | None = None) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    if expected_schema is not None and value.get("schema") != expected_schema:
        raise ValueError(f"{label} must use schema {expected_schema}")
    return value


def _status(value: Any, *, label: str) -> str:
    normalized = STATUS_ALIASES.get(str(value).lower())
    if normalized is None:
        raise ValueError(f"{label} must declare a recognized status")
    return normalized


def _worst(statuses: list[str]) -> str:
    return max(statuses, key=STATUS_ORDER.__getitem__)


def _record(path: Path, value: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "schema": value.get("schema"),
        "status": status,
    }


def route_verification(
    *,
    project_root: str,
    structural_paths: list[str],
    visual_path: str,
    output_path: str,
    probe_path: str | None = None,
    local_critique_path: str | None = None,
    calibration_path: str | None = None,
    final_taste_review: bool = False,
    external_critic_requested: bool = False,
    allow_external: bool = False,
) -> dict[str, Any]:
    """Plan the next verification action without running a model or choosing a winner."""
    root = _project_root(project_root)
    if not isinstance(structural_paths, list) or not 1 <= len(structural_paths) <= 24:
        raise ValueError("structural_paths must contain 1-24 report paths")
    if any(not isinstance(value, bool) for value in (final_taste_review, external_critic_requested, allow_external)):
        raise ValueError("review and external policy flags must be boolean")
    if allow_external and not external_critic_requested:
        raise ValueError("allow_external is meaningful only when external_critic_requested is true")

    structural_records = []
    structural_statuses = []
    for item in structural_paths:
        path = _inside_file(item, root=root, label="structural report")
        value = _read_json(path, label="structural report")
        status = _status(value.get("status"), label="structural report")
        structural_statuses.append(status)
        structural_records.append(_record(path, value, status))
    structural_status = _worst(structural_statuses)

    visual_file = _inside_file(visual_path, root=root, label="visual report")
    visual = _read_json(
        visual_file, label="visual report", expected_schema="hermes.visual_verification"
    )
    visual_status = _status(visual.get("status"), label="visual report")
    mechanical_status = _worst([structural_status, visual_status])

    probe_record = None
    probe_status = "not_supplied"
    if probe_path is not None:
        probe_file = _inside_file(probe_path, root=root, label="local critic probe")
        probe = _read_json(
            probe_file, label="local critic probe", expected_schema="hermes.local_critic_probe"
        )
        probe_status = str(probe.get("status"))
        if probe_status not in {"available", "available_no_allowlisted_model", "unavailable"}:
            raise ValueError("local critic probe status is invalid")
        probe_record = {
            "path": str(probe_file),
            "sha256": _sha256(probe_file),
            "status": probe_status,
            "installed_allowlisted_models": probe.get("installed_allowlisted_models", []),
        }

    local_record = None
    local_status = "not_supplied"
    local_reliability = "not_calibrated"
    local_model = None
    if local_critique_path is not None:
        local_file = _inside_file(local_critique_path, root=root, label="local critique")
        local = _read_json(
            local_file, label="local critique", expected_schema="hermes.local_visual_critique"
        )
        if (
            local.get("decision_authority") != "advisory_only"
            or local.get("winner") is not None
            or not isinstance(local.get("critique"), dict)
        ):
            raise ValueError("local critique violates advisory-only policy")
        local_status = _status(local["critique"].get("mechanical_status"), label="local critique")
        local_model = local.get("model")
        if not isinstance(local_model, dict) or not local_model.get("name"):
            raise ValueError("local critique must record its model identity")
        local_record = {
            "path": str(local_file),
            "sha256": _sha256(local_file),
            "status": local_status,
            "model": local_model,
        }

    calibration_record = None
    if calibration_path is not None:
        if local_record is None:
            raise ValueError("calibration_path requires local_critique_path")
        calibration_file = _inside_file(
            calibration_path, root=root, label="local critic calibration"
        )
        calibration = _read_json(
            calibration_file,
            label="local critic calibration",
            expected_schema="hermes.local_critic_calibration",
        )
        calibration_status = _status(calibration.get("status"), label="local critic calibration")
        same_model = calibration.get("model") == local_model
        calibrated = (
            calibration_status == "pass"
            and calibration.get("model_reliability") == "calibrated"
            and same_model
        )
        local_reliability = "calibrated" if calibrated else "available_unverified"
        calibration_record = {
            "path": str(calibration_file),
            "sha256": _sha256(calibration_file),
            "status": calibration_status,
            "same_model": same_model,
        }
    elif local_record is not None:
        local_reliability = "available_unverified"

    structural_pixel_disagreement = (
        structural_status == "pass" and visual_status == "fail"
    ) or (structural_status == "fail" and visual_status == "pass")
    calibrated_critic_disagreement = (
        local_reliability == "calibrated"
        and local_status in STATUS_ORDER
        and local_status != mechanical_status
    )
    review_triggers = []
    deferred_review_triggers = []
    if structural_pixel_disagreement:
        review_triggers.append("structural_pixel_disagreement")
    if calibrated_critic_disagreement:
        review_triggers.append("calibrated_critic_disagreement")
    if final_taste_review and mechanical_status != "fail":
        review_triggers.append("final_taste_choice")
    elif final_taste_review:
        deferred_review_triggers.append("final_taste_choice_until_mechanical_pass")

    if structural_pixel_disagreement:
        next_action = "human_review_then_mechanical_repair"
    elif mechanical_status == "fail":
        next_action = "repair_mechanical_failure"
    elif calibrated_critic_disagreement:
        next_action = "human_review_model_disagreement"
    elif final_taste_review:
        next_action = "human_taste_review"
    elif mechanical_status == "warn":
        next_action = "bounded_refinement_then_reverify"
    elif local_record is not None and local_reliability != "calibrated":
        next_action = "calibrate_local_critic_or_continue_to_human_taste"
    elif probe_status in {"unavailable", "available_no_allowlisted_model"}:
        next_action = "ready_with_optional_local_critic_unavailable"
    else:
        next_action = "ready_for_human_taste_when_desired"

    if not external_critic_requested:
        external_route = "not_requested"
    elif not allow_external:
        external_route = "explicit_approval_required"
    elif mechanical_status == "fail":
        external_route = "blocked_by_mechanical_gate"
    else:
        external_route = "eligible_advisory_only"

    output = _new_output(output_path, root=root)
    result = {
        "schema": "hermes.verification_route",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "mechanical_gate": {
            "status": mechanical_status,
            "structural_status": structural_status,
            "visual_status": visual_status,
            "model_may_override": False,
        },
        "evidence": {
            "structural": structural_records,
            "visual": _record(visual_file, visual, visual_status),
            "local_probe": probe_record,
            "local_critique": local_record,
            "calibration": calibration_record,
        },
        "local_critic": {
            "status": local_status,
            "reliability": local_reliability,
            "may_reduce_human_review": local_reliability == "calibrated",
        },
        "disagreements": {
            "structural_pixel": structural_pixel_disagreement,
            "calibrated_critic": calibrated_critic_disagreement,
        },
        "human_review": {
            "required_now": bool(review_triggers),
            "triggers": review_triggers,
            "deferred_triggers": deferred_review_triggers,
            "final_taste_remains_human": True,
        },
        "external_critic": {
            "requested": external_critic_requested,
            "approved": allow_external,
            "route": external_route,
            "execution_performed": False,
        },
        "next_action": next_action,
        "decision_authority": "routing_only",
        "automatic_ranking": False,
        "winner": None,
        "human_rating": None,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"artifact": str(output), **result}


__all__ = ["route_verification"]
