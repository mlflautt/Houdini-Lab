"""Explicit, budgeted Houdini cook jobs.

Job contracts and state transitions are pure Python. HOM execution is isolated in
``execute_job`` and must run on Houdini's main thread.
"""

from __future__ import annotations

import json
import math
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from . import get_hou
from .schemas.command import CookInfo, Policy, Status, ToolResult

COOK_SCOPES = {"single_node", "display_chain", "one_frame", "frame_range"}
ESTIMATE_KEYS = {"points", "primitives", "memory_bytes", "seconds"}
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


def normalize_estimate(estimate: dict[str, Any]) -> dict[str, int | float]:
    """Strictly normalize the caller's pre-cook resource declaration."""
    if not isinstance(estimate, dict):
        raise ValueError("estimate must be an object")
    missing = ESTIMATE_KEYS - set(estimate)
    unknown = set(estimate) - ESTIMATE_KEYS
    if missing:
        raise ValueError(f"estimate missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"estimate has unknown keys: {', '.join(sorted(unknown))}")
    normalized: dict[str, int | float] = {}
    for key in ("points", "primitives", "memory_bytes"):
        value = estimate[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"estimate.{key} must be a non-negative integer")
        normalized[key] = value
    seconds = estimate["seconds"]
    if (
        not isinstance(seconds, (int, float))
        or isinstance(seconds, bool)
        or not math.isfinite(seconds)
        or seconds < 0
    ):
        raise ValueError("estimate.seconds must be a finite non-negative number")
    normalized["seconds"] = float(seconds)
    return normalized


def budget_violations(metrics: dict[str, Any], policy: Policy) -> list[str]:
    """Return every resource dimension that exceeds a policy ceiling."""
    limits = {
        "points": policy.max_points,
        "primitives": policy.max_primitives,
        "memory_bytes": policy.max_memory_bytes,
        "seconds": policy.max_seconds,
    }
    return [
        f"{key} {metrics.get(key, 0)} > budget {limit}"
        for key, limit in limits.items()
        if metrics.get(key, 0) > limit
    ]


def normalize_frame_range(
    frame_range: list[float] | tuple[float, ...] | None, policy: Policy
) -> list[float]:
    """Expand one inclusive, positive-step frame range under the policy ceiling."""
    if not isinstance(frame_range, (list, tuple)) or len(frame_range) not in {2, 3}:
        raise ValueError("frame_range scope requires [start, end] or [start, end, step]")
    values = list(frame_range) + ([1.0] if len(frame_range) == 2 else [])
    if any(
        not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
        for value in values
    ):
        raise ValueError("frame_range values must be finite numbers")
    start, end, step = (float(value) for value in values)
    if step <= 0:
        raise ValueError("frame_range step must be greater than zero")
    if end < start:
        raise ValueError("frame_range end must be greater than or equal to start")
    count = int(math.floor(((end - start) / step) + 1e-9)) + 1
    if count > policy.max_frames:
        raise ValueError(f"frame_range has {count} frames > policy max_frames {policy.max_frames}")
    if count < 1:
        raise ValueError("frame_range must contain at least one frame")
    return [start + (index * step) for index in range(count)]


def validate_cook_spec(
    *,
    scope: str,
    frame: float | None,
    frame_range: list[float] | tuple[float, ...] | None = None,
    estimate: dict[str, Any],
    policy: Policy,
) -> dict[str, int | float]:
    """Validate scope, frame count, and declared costs before job creation."""
    if scope not in COOK_SCOPES:
        raise ValueError(f"unsupported cook scope: {scope}")
    if scope == "one_frame":
        if (
            not isinstance(frame, (int, float))
            or isinstance(frame, bool)
            or not math.isfinite(frame)
        ):
            raise ValueError("one_frame scope requires a finite numeric frame")
        if policy.max_frames < 1:
            raise ValueError("policy does not allow any frames")
        if frame_range is not None:
            raise ValueError("frame_range is only valid for frame_range scope")
    elif scope == "frame_range":
        if frame is not None:
            raise ValueError("frame is only valid for one_frame scope, not frame_range")
        normalize_frame_range(frame_range, policy)
    elif frame is not None:
        raise ValueError(f"frame is only valid for one_frame scope, not {scope}")
    elif frame_range is not None:
        raise ValueError(f"frame_range is only valid for frame_range scope, not {scope}")
    normalized = normalize_estimate(estimate)
    violations = budget_violations(normalized, policy)
    if violations:
        raise ValueError("declared estimate exceeds policy: " + "; ".join(violations))
    return normalized


@dataclass
class CookJob:
    job_id: str
    node_path: str
    node_session_id: int
    scope: str
    frame: float | None
    frame_range: list[float] | None
    force: bool
    estimate: dict[str, int | float]
    policy: Policy
    log_path: str
    state: str = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["policy"] = self.policy.as_dict()
        return data


class CookJobManager:
    """Bounded in-process job registry with cancel-before-run semantics."""

    def __init__(self, max_jobs: int = 128) -> None:
        self.max_jobs = max_jobs
        self._jobs: dict[str, CookJob] = {}

    def submit(
        self,
        *,
        node_path: str,
        node_session_id: int,
        scope: str,
        frame: float | None,
        frame_range: list[float] | tuple[float, ...] | None = None,
        force: bool,
        estimate: dict[str, Any],
        policy: Policy,
        log_path: str,
    ) -> CookJob:
        normalized = validate_cook_spec(
            scope=scope,
            frame=frame,
            frame_range=frame_range,
            estimate=estimate,
            policy=policy,
        )
        frames = normalize_frame_range(frame_range, policy) if scope == "frame_range" else None
        self._prune()
        if len(self._jobs) >= self.max_jobs:
            raise RuntimeError("cook job registry is full")
        job = CookJob(
            job_id=f"cook-{secrets.token_hex(12)}",
            node_path=node_path,
            node_session_id=node_session_id,
            scope=scope,
            frame=float(frame) if frame is not None else None,
            frame_range=frames,
            force=bool(force),
            estimate=normalized,
            policy=Policy.from_dict(policy.as_dict()),
            log_path=log_path,
        )
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> CookJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"cook job not found: {job_id}")
        return job

    def cancel(self, job_id: str) -> CookJob:
        job = self.get(job_id)
        if job.state != "pending":
            raise ValueError(f"only pending cook jobs can be cancelled; state={job.state}")
        job.state = "cancelled"
        job.finished_at = time.time()
        return job

    def begin(self, job_id: str) -> CookJob:
        job = self.get(job_id)
        if job.state != "pending":
            raise ValueError(f"only pending cook jobs can run; state={job.state}")
        job.state = "running"
        job.started_at = time.time()
        return job

    def finish(self, job_id: str, result: ToolResult) -> CookJob:
        job = self.get(job_id)
        job.state = "succeeded" if result.status == Status.SUCCESS else "failed"
        job.finished_at = time.time()
        job.result = result.as_dict()
        job.error = "; ".join(result.errors)
        return job

    def _prune(self) -> None:
        terminal = sorted(
            (job for job in self._jobs.values() if job.state in TERMINAL_STATES),
            key=lambda item: item.finished_at or item.created_at,
        )
        while len(self._jobs) >= self.max_jobs and terminal:
            self._jobs.pop(terminal.pop(0).job_id, None)


COOK_JOBS = CookJobManager()


def append_cook_record(log_path: str, event: str, job: CookJob) -> None:
    """Durably append a job state transition to its JSONL provenance log."""
    parent = os.path.dirname(log_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    record = {
        "schema": "hermes.houdini.cook_job",
        "schema_version": "1.0",
        "timestamp_unix": time.time(),
        "event": event,
        "job": job.as_dict(),
    }
    with open(log_path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def geometry_metrics(node: Any) -> dict[str, Any]:
    """Collect compact structural metrics from an already-cooked SOP node."""
    geometry = node.geometry()
    if geometry is None:
        return {
            "points": 0,
            "primitives": 0,
            "vertices": 0,
            "memory_bytes": 0,
            "bounds": None,
            "point_attributes": [],
            "primitive_attributes": [],
            "point_groups": [],
            "primitive_groups": [],
        }
    memory_bytes = 0
    if "memoryusage" in geometry.intrinsicNames():
        memory_bytes = int(geometry.intrinsicValue("memoryusage"))
    bbox = geometry.boundingBox()
    return {
        "points": int(geometry.pointCount()),
        "primitives": int(geometry.primCount()),
        "vertices": int(geometry.vertexCount()),
        "memory_bytes": memory_bytes,
        "bounds": [list(bbox.minvec()), list(bbox.maxvec())],
        "point_attributes": sorted(attribute.name() for attribute in geometry.pointAttribs()),
        "primitive_attributes": sorted(attribute.name() for attribute in geometry.primAttribs()),
        "point_groups": sorted(group.name() for group in geometry.pointGroups()),
        "primitive_groups": sorted(group.name() for group in geometry.primGroups()),
    }


def metrics_for_clean_node(node_path: str) -> dict[str, Any]:
    """Read metrics without triggering an implicit cook."""
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    if not hasattr(node, "needsToCook") or not hasattr(node, "geometry"):
        raise ValueError(f"node does not expose SOP geometry: {node_path}")
    if node.needsToCook():
        raise ValueError("node is dirty; submit and run an explicit cook job first")
    return {"path": node.path(), **geometry_metrics(node)}


def execute_job(job: CookJob) -> ToolResult:
    """Execute one begun job on Houdini's main thread and restore frame state."""
    hou = get_hou()
    node = hou.node(job.node_path)
    result = ToolResult(status=Status.SUCCESS)
    if node is None or node.sessionId() != job.node_session_id:
        result.status = Status.ERROR
        result.errors.append("cook target was deleted or replaced after submission")
        return result
    if not hasattr(node, "cook") or not hasattr(node, "geometry"):
        result.status = Status.ERROR
        result.errors.append(f"node is not a cookable geometry node: {job.node_path}")
        return result

    if not node.needsToCook():
        existing = geometry_metrics(node)
        preflight_violations = budget_violations(existing, job.policy)
        if preflight_violations:
            result.status = Status.BLOCKED
            result.errors.extend(preflight_violations)
            result.data = {"phase": "clean-cache-preflight", "metrics": existing}
            return result

    original_frame = float(hou.frame())
    if job.frame_range is not None:
        frames = list(job.frame_range)
    elif job.frame is not None:
        frames = [job.frame]
    else:
        frames = [original_frame]
    started = time.monotonic()
    metrics: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []
    cook_path: list[str] = []
    frame_metrics: list[dict[str, Any]] = []
    try:
        timeout_ms = max(1, int(job.policy.max_seconds * 1000))
        with hou.InterruptableOperation(
            f"Hermes cook {job.node_path}", timeout_ms=timeout_ms
        ) as operation:
            for index, frame_value in enumerate(frames):
                if job.frame is not None or job.frame_range is not None:
                    hou.setFrame(frame_value)
                frame_started = time.monotonic()
                operation.updateProgress(index / len(frames))
                node.cook(force=job.force)
                observed = geometry_metrics(node)
                observed["frame"] = frame_value
                observed["seconds"] = time.monotonic() - frame_started
                frame_metrics.append(observed)
                frame_errors = [str(message) for message in node.errors()]
                frame_warnings = [str(message) for message in node.warnings()]
                errors.extend(f"frame {frame_value:g}: {message}" for message in frame_errors)
                warnings.extend(f"frame {frame_value:g}: {message}" for message in frame_warnings)
                if frame_errors:
                    break
            operation.updateProgress(1.0)
    except hou.OperationInterrupted:
        result.status = Status.ERROR
        result.errors.append(f"cook interrupted or timed out after {job.policy.max_seconds}s")
    except Exception as exc:
        result.status = Status.ERROR
        result.errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        # Observe the exact requested frame before restoring global timeline state.
        try:
            if frame_metrics:
                final_metrics = frame_metrics[-1]
                metrics = dict(final_metrics)
                for key in ("points", "primitives", "vertices", "memory_bytes"):
                    metrics[key] = max(int(item.get(key, 0)) for item in frame_metrics)
            elif not node.needsToCook():
                metrics = geometry_metrics(node)
            if not errors:
                errors = [str(message) for message in node.errors()]
            if not warnings:
                warnings = [str(message) for message in node.warnings()]
            if job.scope == "display_chain" and hasattr(node, "cookPathNodes"):
                cook_path = [item.path() for item in node.cookPathNodes()]
        except Exception as exc:
            result.status = Status.ERROR
            result.errors.append(f"cook observation failed: {exc}")
        if job.frame is not None or job.frame_range is not None:
            hou.setFrame(original_frame)
    seconds = time.monotonic() - started

    metrics["seconds"] = seconds
    metrics["scope"] = job.scope
    metrics["frames"] = frames
    metrics["forced"] = job.force
    metrics["node_path"] = node.path()
    if errors:
        result.status = Status.ERROR
        result.errors.extend(errors)
    result.warnings.extend(warnings)
    violations = budget_violations(metrics, job.policy)
    if violations:
        result.status = Status.ERROR
        result.errors.extend(violations)
    result.cook = CookInfo(
        node_path=node.path(),
        scope=job.scope,
        seconds=round(seconds, 6),
        points=int(metrics.get("points", 0)),
        primitives=int(metrics.get("primitives", 0)),
        vertices=int(metrics.get("vertices", 0)),
        memory_bytes=int(metrics.get("memory_bytes", 0)),
        frames=[float(value) for value in frames],
        forced=job.force,
    )
    result.data = {
        "estimate": job.estimate,
        "metrics": metrics,
        "frame_metrics": frame_metrics,
        "cook_path": cook_path,
        "node_errors": errors,
        "node_warnings": warnings,
    }
    return result


__all__ = [
    "COOK_JOBS",
    "COOK_SCOPES",
    "CookJob",
    "CookJobManager",
    "append_cook_record",
    "budget_violations",
    "execute_job",
    "geometry_metrics",
    "metrics_for_clean_node",
    "normalize_frame_range",
    "normalize_estimate",
    "validate_cook_spec",
]
