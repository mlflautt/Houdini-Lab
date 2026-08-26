"""Plain-mapping Hython tier adapters for Grinder G001-B."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hermes_houdini import get_hou
from hermes_houdini.cook import geometry_metrics
from hermes_houdini.execution import reset_current_envelope, set_current_envelope
from hermes_houdini.observation import viewport_capture
from hermes_houdini.schemas.command import CommandEnvelope, Policy, RiskClass
from hermes_houdini.solaris import render_karma_preview

from .fixtures import build_acceptance_fixtures

TINY_CEILINGS = {
    "max_points": 10_000,
    "max_frames": 8,
    "max_memory_bytes": 256 * 1024 * 1024,
    "max_artifact_bytes": 256 * 1024 * 1024,
    "width": 640,
    "height": 360,
    "samples": 16,
    "max_seconds": 120.0,
    "max_work_items": 1,
}


def _budget(value: dict[str, Any]) -> dict[str, int | float]:
    if not isinstance(value, dict):
        raise ValueError("budget must be an explicit mapping")
    missing = set(TINY_CEILINGS) - set(value)
    unknown = set(value) - set(TINY_CEILINGS)
    if missing:
        raise ValueError("budget missing keys: " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError("budget has unknown keys: " + ", ".join(sorted(unknown)))
    normalized: dict[str, int | float] = {}
    for key, ceiling in TINY_CEILINGS.items():
        raw = value[key]
        if isinstance(ceiling, int):
            if not isinstance(raw, int) or isinstance(raw, bool) or raw < 1:
                raise ValueError(f"budget.{key} must be a positive integer")
            normalized[key] = raw
        else:
            if not isinstance(raw, (int, float)) or isinstance(raw, bool) or raw <= 0:
                raise ValueError(f"budget.{key} must be positive")
            normalized[key] = float(raw)
        if normalized[key] > ceiling:
            raise ValueError(f"budget.{key} {normalized[key]} exceeds frozen ceiling {ceiling}")
    if normalized["width"] > 1280 or normalized["height"] > 720:
        raise ValueError("resolution exceeds Apprentice ceiling 1280x720")
    return normalized


def _started() -> tuple[str, float]:
    return datetime.now(UTC).isoformat(), time.monotonic()


def _result(
    tier: str,
    command: str,
    started_at: str,
    started: float,
    budget: dict[str, Any],
    *,
    status: str = "pass",
    observed: dict[str, Any] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "tier": tier,
        "status": status,
        "command": command,
        "started_at": started_at,
        "duration_seconds": round(time.monotonic() - started, 6),
        "budget": dict(budget),
        "observed": observed or {},
        "artifacts": artifacts or [],
        "warnings": warnings or [],
        "errors": errors or [],
    }


def _artifact(path: str) -> dict[str, Any]:
    item = Path(path)
    return {"path": str(item), "bytes": item.stat().st_size, "kind": item.suffix.lstrip(".")}


def _guarded(tier: str, command: str, raw_budget: dict[str, Any], call: Callable) -> dict[str, Any]:
    started_at, started = _started()
    try:
        budget = _budget(raw_budget)
        return call(started_at, started, budget)
    except (ValueError, FileExistsError) as exc:
        return _result(
            tier,
            command,
            started_at,
            started,
            raw_budget if isinstance(raw_budget, dict) else {},
            status="blocked",
            errors=[f"{type(exc).__name__}: {exc}"],
        )
    except Exception as exc:
        return _result(
            tier,
            command,
            started_at,
            started,
            raw_budget if isinstance(raw_budget, dict) else {},
            status="blocked",
            errors=[f"{type(exc).__name__}: {exc}"],
        )


def run_hython_read_tier(*, node_path: str, budget: dict[str, Any]) -> dict[str, Any]:
    """Inspect node identity and dirty state without cooking it."""
    command = f"hython-read node={node_path} cook=none"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        hou = get_hou()
        frame_before = float(hou.frame())
        node = hou.node(node_path)
        if node is None:
            raise ValueError(f"node not found: {node_path}")
        dirty_before = bool(node.needsToCook()) if hasattr(node, "needsToCook") else None
        observed = {
            "node_path": node.path(),
            "category": node.type().category().name(),
            "operator_type": node.type().name(),
            "hermes_id": node.userData("hermes_id"),
            "hermes_role": node.userData("hermes_role"),
            "needs_to_cook_before": dirty_before,
            "needs_to_cook_after": bool(node.needsToCook()) if hasattr(node, "needsToCook") else None,
            "frame_before": frame_before,
            "frame_after": float(hou.frame()),
            "cook_scope": "none",
        }
        return _result("hython-read", command, started_at, started, normalized, observed=observed)

    return _guarded("hython-read", command, budget, execute)


def run_graph_edit_tier(
    *, artifact_root: str, budget: dict[str, Any], fixture_name: str = "HERMES_ACCEPTANCE_G001B"
) -> dict[str, Any]:
    """Build and save the source fixtures without forcing a display-chain cook."""
    command = f"graph-edit build_acceptance_fixtures artifact_root={artifact_root}"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        fixture = build_acceptance_fixtures(artifact_root, fixture_name=fixture_name)
        scene = _artifact(fixture["scene_path"])
        if scene["bytes"] > normalized["max_artifact_bytes"]:
            raise ValueError("fixture scene exceeds budget.max_artifact_bytes")
        observed = {
            **fixture,
            "managed_node_count": len(fixture["managed_nodes"]),
            "cook_scope": "none",
            "forced_cook": False,
        }
        return _result(
            "graph-edit", command, started_at, started, normalized, observed=observed, artifacts=[scene]
        )

    return _guarded("graph-edit", command, budget, execute)


def _cook_frames(
    *, node_path: str, frames: list[float], budget: dict[str, Any], force: bool = True
) -> dict[str, Any]:
    hou = get_hou()
    node = hou.node(node_path)
    if node is None or not hasattr(node, "geometry"):
        raise ValueError(f"cookable SOP node not found: {node_path}")
    if len(frames) > budget["max_frames"]:
        raise ValueError(f"requested {len(frames)} frames exceeds budget.max_frames")
    original_frame = float(hou.frame())
    frame_metrics = []
    try:
        for frame in frames:
            frame_started = time.monotonic()
            hou.setFrame(frame)
            node.cook(force=force)
            metrics = geometry_metrics(node)
            metrics.update({"frame": float(frame), "seconds": time.monotonic() - frame_started})
            if metrics["points"] > budget["max_points"]:
                raise ValueError("observed points exceed budget.max_points")
            if metrics["memory_bytes"] > budget["max_memory_bytes"]:
                raise ValueError("observed memory exceeds budget.max_memory_bytes")
            errors = [str(item) for item in node.errors()]
            if errors:
                raise RuntimeError("; ".join(errors))
            frame_metrics.append(metrics)
    finally:
        hou.setFrame(original_frame)
    return {
        "node_path": node.path(),
        "frames": [float(item) for item in frames],
        "frame_metrics": frame_metrics,
        "frame_before": original_frame,
        "frame_after": float(hou.frame()),
        "forced": force,
    }


def run_single_frame_tier(
    *, node_path: str, frame: float, budget: dict[str, Any]
) -> dict[str, Any]:
    command = f"single-frame node={node_path} frame={frame}"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        observed = _cook_frames(node_path=node_path, frames=[float(frame)], budget=normalized)
        observed["cook_scope"] = "one_frame"
        return _result("single-frame", command, started_at, started, normalized, observed=observed)

    return _guarded("single-frame", command, budget, execute)


def run_frame_range_tier(
    *, node_path: str, frames: list[float], budget: dict[str, Any]
) -> dict[str, Any]:
    command = f"frame-range node={node_path} frames={frames}"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(frames, list) or not frames:
            raise ValueError("frames must be a non-empty explicit list")
        observed = _cook_frames(
            node_path=node_path, frames=[float(item) for item in frames], budget=normalized
        )
        observed["cook_scope"] = "frame_range"
        return _result("frame-range", command, started_at, started, normalized, observed=observed)

    return _guarded("frame-range", command, budget, execute)


def run_pdg_child_tier(
    *, pdg_node_path: str, output_path: str, budget: dict[str, Any], authorized: bool
) -> dict[str, Any]:
    command = f"pdg-child node={pdg_node_path} output={output_path}"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        if not authorized:
            return _result(
                "pdg-child", command, started_at, started, normalized, status="blocked",
                errors=["explicit external-process policy approval is required"],
            )
        output = Path(output_path)
        if output.exists():
            raise FileExistsError(f"refusing to overwrite PDG artifact: {output}")
        hou = get_hou()
        node = hou.node(pdg_node_path)
        if node is None or node.type().name() != "ropgeometry":
            raise ValueError("managed ROP Geometry TOP not found")
        if node.userData("hermes_role") != "approved_external_pdg_child":
            raise ValueError("PDG tier only accepts the managed child fixture")
        before = float(hou.frame())
        try:
            node.dirtyAllWorkItems(False)
            node.cookWorkItems(block=True, save_prompt=False)
        finally:
            hou.setFrame(before)
        elapsed = time.monotonic() - started
        if elapsed > normalized["max_seconds"]:
            raise RuntimeError("PDG child exceeded budget.max_seconds")
        if not output.is_file():
            raise RuntimeError("PDG child completed without the declared artifact")
        artifact = _artifact(str(output))
        if artifact["bytes"] > normalized["max_artifact_bytes"]:
            raise RuntimeError("PDG output exceeds budget.max_artifact_bytes")
        return _result(
            "pdg-child", command, started_at, started, normalized,
            observed={"work_items": 1, "frame_before": before, "frame_after": float(hou.frame())},
            artifacts=[artifact],
        )

    return _guarded("pdg-child", command, budget, execute)


def run_simulation_tier(
    *, node_path: str, frames: list[float], budget: dict[str, Any], authorized: bool
) -> dict[str, Any]:
    command = f"simulation node={node_path} frames={frames}"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        if not authorized:
            return _result(
                "simulation", command, started_at, started, normalized, status="blocked",
                errors=["explicit simulation authorization is required"],
            )
        if not isinstance(frames, list) or not frames:
            raise ValueError("simulation frames must be a non-empty explicit list")
        node = get_hou().node(node_path)
        if node is None or node.userData("hermes_role") != "simulation_output_contract":
            raise ValueError("simulation tier only accepts the managed Solver SOP output")
        observed = _cook_frames(
            node_path=node_path, frames=[float(item) for item in frames], budget=normalized
        )
        observed["cook_scope"] = "simulation_frame_range"
        return _result("simulation", command, started_at, started, normalized, observed=observed)

    return _guarded("simulation", command, budget, execute)


def run_viewport_tier(
    *, viewer_name: str, viewport_name: str, camera_path: str, output_path: str,
    frame: float, budget: dict[str, Any]
) -> dict[str, Any]:
    command = f"viewport viewer={viewer_name} viewport={viewport_name} camera={camera_path}"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        hou = get_hou()
        if not hou.isUIAvailable():
            return _result(
                "viewport", command, started_at, started, normalized, status="pending",
                warnings=["interactive Houdini is required for authentic viewport pixels"],
            )
        if Path(output_path).exists():
            raise FileExistsError(f"refusing to overwrite viewport artifact: {output_path}")
        observed = viewport_capture(
            viewer_name=viewer_name, viewport_name=viewport_name, camera_path=camera_path,
            output_path=output_path, frame=frame, width=int(normalized["width"]),
            height=int(normalized["height"]),
        )
        return _result(
            "viewport", command, started_at, started, normalized, observed=observed,
            artifacts=[_artifact(output_path)],
        )

    return _guarded("viewport", command, budget, execute)


def run_karma_tier(
    *, rop_path: str, output_path: str, log_path: str, frame: float,
    budget: dict[str, Any], authorized: bool
) -> dict[str, Any]:
    command = f"karma rop={rop_path} frame={frame} output={output_path}"

    def execute(started_at: str, started: float, normalized: dict[str, Any]) -> dict[str, Any]:
        if not authorized:
            return _result(
                "karma", command, started_at, started, normalized, status="blocked",
                errors=["explicit render and external-process authorization is required"],
            )
        if Path(output_path).exists() or Path(log_path).exists():
            raise FileExistsError("refusing to overwrite Karma output or provenance log")
        hou = get_hou()
        rop = hou.node(rop_path)
        if rop is None or rop.userData("hermes_role") != "karma_cpu_preview":
            raise ValueError("Karma tier only accepts the managed preview ROP")
        stage_node = hou.node(rop.parm("loppath").evalAsString())
        settings = stage_node
        while settings is not None and settings.type().name() != "karmarendersettings":
            settings = settings.input(0)
        if settings is None:
            raise ValueError("managed Karma render-settings LOP is unavailable")
        fixture_samples = max(
            int(settings.parm("samplesperpixel").eval()),
            int(settings.parm("pathtracedsamples").eval()),
        )
        if fixture_samples > normalized["samples"]:
            raise ValueError(
                f"fixture samples {fixture_samples} exceeds budget.samples {normalized['samples']}"
            )
        policy = Policy(
            allow_external_process=True, max_seconds=float(normalized["max_seconds"]),
            max_points=int(normalized["max_points"]),
            max_memory_bytes=int(normalized["max_memory_bytes"]), max_frames=1,
            max_output_bytes=int(normalized["max_artifact_bytes"]),
            max_resolution=(int(normalized["width"]), int(normalized["height"])),
            risk=RiskClass.EXTERNAL,
        )
        envelope = CommandEnvelope(tool="acceptance.karma", policy=policy)
        token = set_current_envelope(envelope)
        original_frame = float(hou.frame())
        try:
            rendered = render_karma_preview(
                rop_path=rop_path, output_path=output_path, log_path=log_path, frame=frame
            )
        finally:
            hou.setFrame(original_frame)
            reset_current_envelope(token)
        if rendered.status.value != "success":
            raise RuntimeError("; ".join(rendered.errors))
        return _result(
            "karma", command, started_at, started, normalized,
            observed={**rendered.data, "frame_before": original_frame, "frame_after": float(hou.frame())},
            artifacts=[_artifact(output_path), _artifact(log_path)],
        )

    return _guarded("karma", command, budget, execute)


__all__ = [
    "TINY_CEILINGS", "run_frame_range_tier", "run_graph_edit_tier", "run_hython_read_tier",
    "run_karma_tier", "run_pdg_child_tier", "run_simulation_tier", "run_single_frame_tier",
    "run_viewport_tier",
]
