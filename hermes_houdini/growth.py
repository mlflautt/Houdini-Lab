"""Registered native-SOP differential-growth construction.

Pure validation remains importable without Houdini. HOM only populates the editable
feedback network inside a newly created Solver SOP; Relax, Attribute Blur, and Resample
perform all geometry computation.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from . import get_hou
from .execution import current_envelope
from .ids import make_id
from .schemas.command import ChangedNode, Status, ToolResult
from .transactions import save_checkpoint

SCHEMA_VERSION = "1.0"
_ABS_NODE_PATH = re.compile(r"/(?:[A-Za-z0-9_.-]+)(?:/[A-Za-z0-9_.-]+)*\Z")
_SAFE_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,27}\Z")


def _finite(
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{label} must be <= {maximum}")
    return result


def _integer(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return value


def validate_growth_solver_spec(
    *,
    solver_path: str,
    run_id: str,
    point_radius: float,
    relax_iterations: int,
    blur_iterations: int,
    blur_step_size: float,
    segment_length: float,
) -> dict[str, Any]:
    """Validate the exact bounded parameters accepted by the registered feedback subgraph."""
    if not isinstance(solver_path, str) or not _ABS_NODE_PATH.fullmatch(solver_path):
        raise ValueError("solver_path must be an absolute Houdini node path")
    if not isinstance(run_id, str) or not _SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError("run_id must be 1-28 filename-safe characters")
    return {
        "solver_path": solver_path,
        "run_id": run_id,
        "point_radius": _finite(point_radius, "point_radius", minimum=0.005, maximum=0.25),
        "relax_iterations": _integer(relax_iterations, "relax_iterations", minimum=1, maximum=12),
        "blur_iterations": _integer(blur_iterations, "blur_iterations", minimum=1, maximum=8),
        "blur_step_size": _finite(blur_step_size, "blur_step_size", minimum=0.0, maximum=1.0),
        "segment_length": _finite(segment_length, "segment_length", minimum=0.01, maximum=0.25),
    }


def _append_jsonl(path: str, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _record(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    hou = get_hou()
    envelope = current_envelope()
    return {
        "schema": f"hermes.houdini.{kind}",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "houdini": {
            "build": hou.applicationVersionString(),
            "license": hou.licenseCategory().name(),
        },
        "request": envelope.as_dict() if envelope is not None else None,
        **payload,
    }


def _tag(node: Any, *, role: str, created_by: str, scope: str) -> str:
    stable_id = make_id("Sop", scope)
    node.setUserData("hermes_id", stable_id)
    node.setUserData("hermes_role", role)
    node.setUserData("hermes_created_by", created_by)
    node.setUserData("hermes_manifest_version", "1")
    return stable_id


def populate_growth_solver(
    *,
    solver_path: str,
    run_id: str,
    checkpoint_dir: str,
    log_path: str,
    point_radius: float = 0.075,
    relax_iterations: int = 5,
    blur_iterations: int = 1,
    blur_step_size: float = 0.25,
    segment_length: float = 0.075,
) -> ToolResult:
    """Checkpoint, then populate one pristine Solver SOP with the registered native graph."""
    hou = get_hou()
    spec = validate_growth_solver_spec(
        solver_path=solver_path,
        run_id=run_id,
        point_radius=point_radius,
        relax_iterations=relax_iterations,
        blur_iterations=blur_iterations,
        blur_step_size=blur_step_size,
        segment_length=segment_length,
    )
    solver = hou.node(solver_path)
    if solver is None or solver.type().category().name() != "Sop":
        raise ValueError(f"Solver SOP not found: {solver_path}")
    if solver.type().name() != "solver":
        raise ValueError(f"node is not the exact native solver SOP: {solver_path}")
    feedback = solver.node("d/s")
    if feedback is None or feedback.type().category().name() != "Dop":
        raise ValueError(f"editable SOP Solver feedback network not found: {solver_path}/d/s")
    previous = feedback.node("Prev_Frame")
    output = feedback.node("OUT")
    if previous is None or output is None or output.input(0) != previous:
        raise ValueError("Solver feedback output is not pristine; refusing to replace artist work")
    managed_names = ("HERMES_POINT_SEPARATION", "HERMES_CURVE_RELAX", "HERMES_EDGE_SPACING")
    if any(feedback.node(name) is not None for name in managed_names):
        raise ValueError("managed differential-growth nodes already exist")

    checkpoint = save_checkpoint(checkpoint_dir, f"growth_{run_id}")
    created: list[Any] = []
    changed: list[ChangedNode] = []
    created_by = "tool:growth.solver.populate@1.0.0"
    result = ToolResult(status=Status.SUCCESS, checkpoint=checkpoint)
    try:
        with hou.undos.group("Hermes populate native differential-growth solver"):
            separation = feedback.createNode(
                "relax", node_name=managed_names[0], exact_type_name=True
            )
            created.append(separation)
            separation.setInput(0, previous)
            separation.parm("useradiusattrib").set(0)
            separation.parm("radius").set(spec["point_radius"])
            separation.parm("maxiterations").set(spec["relax_iterations"])
            separation.setPosition(hou.Vector2(0.0, -2.0))
            separation.setComment(
                "Native point separation force; no Python or per-point HOM computation"
            )
            separation_id = _tag(
                separation,
                role="differential_growth_separation_force",
                created_by=created_by,
                scope=f"{solver_path}:{run_id}:separation",
            )

            smoothing = feedback.createNode(
                "attribblur", node_name=managed_names[1], exact_type_name=True
            )
            created.append(smoothing)
            smoothing.setInput(0, separation)
            smoothing.parm("attributes").set("P")
            smoothing.parm("method").set("uniform")
            smoothing.parm("influencetype").set("connectivity")
            smoothing.parm("iterations").set(spec["blur_iterations"])
            smoothing.parm("stepsize").set(spec["blur_step_size"])
            smoothing.setPosition(hou.Vector2(0.0, -4.0))
            smoothing.setComment("Native connectivity blur supplies the opposing relaxation force")
            smoothing_id = _tag(
                smoothing,
                role="differential_growth_smoothing_force",
                created_by=created_by,
                scope=f"{solver_path}:{run_id}:smoothing",
            )

            spacing = feedback.createNode(
                "resample", node_name=managed_names[2], exact_type_name=True
            )
            created.append(spacing)
            spacing.setInput(0, smoothing)
            spacing.parm("method").set(0)
            spacing.parm("dolength").set(1)
            spacing.parm("length").set(spec["segment_length"])
            spacing.parm("useattribs").set(0)
            spacing.setPosition(hou.Vector2(0.0, -6.0))
            spacing.setComment("Maintains bounded, editable edge spacing after each feedback step")
            spacing_id = _tag(
                spacing,
                role="differential_growth_edge_spacing",
                created_by=created_by,
                scope=f"{solver_path}:{run_id}:spacing",
            )

            output.setInput(0, spacing)
            output.setPosition(hou.Vector2(0.0, -8.0))
            solver.setUserData("hermes_growth_algorithm", "relax_attribblur_resample_v1")
            solver.setUserData("hermes_growth_run_id", run_id)
            changed.extend(
                [
                    ChangedNode(separation_id, separation.path(), "created"),
                    ChangedNode(smoothing_id, smoothing.path(), "created"),
                    ChangedNode(spacing_id, spacing.path(), "created"),
                    ChangedNode(solver.userData("hermes_id") or "", solver.path(), "modified"),
                ]
            )
        record = _record(
            "growth_solver",
            {
                "status": "success",
                "checkpoint": checkpoint,
                "solver_path": solver_path,
                "feedback_path": feedback.path(),
                "algorithm": "native_relax_attribblur_resample",
                "parameters": spec,
                "nodes": [node.path() for node in created],
            },
        )
        _append_jsonl(log_path, record)
        result.changed_nodes = changed
        result.artifacts = [log_path]
        result.data = {
            "solver_path": solver_path,
            "feedback_path": feedback.path(),
            "algorithm": "native_relax_attribblur_resample",
            "parameters": spec,
            "node_paths": [node.path() for node in created],
        }
        return result
    except Exception as exc:
        if output.parent() is not None:
            output.setInput(0, previous)
        for node in reversed(created):
            if node.parent() is not None:
                node.destroy()
        result.status = Status.ERROR
        result.errors.append(f"{type(exc).__name__}: {exc}")
        result.data = {"rolled_back": True}
        try:
            _append_jsonl(
                log_path,
                _record(
                    "growth_solver",
                    {
                        "status": "rolled_back",
                        "checkpoint": checkpoint,
                        "solver_path": solver_path,
                        "error": result.errors[0],
                    },
                ),
            )
            result.artifacts = [log_path]
        except Exception as log_exc:
            result.status = Status.PARTIAL
            result.errors.append(f"provenance failure: {log_exc}")
        return result


__all__ = ["populate_growth_solver", "validate_growth_solver_spec"]
