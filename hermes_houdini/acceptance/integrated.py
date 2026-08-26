"""Integrated adapters for the G001 tiered acceptance entry point.

The module imports without Houdini. Live calls import the Hython adapters lazily and
share one source-built fixture only inside the current acceptance process.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hermes_houdini import __version__, has_hou

from .baselines import evaluate_baseline
from .compatibility import probe_compatibility


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _artifact(path: Path, *, kind: str) -> dict[str, Any]:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "kind": kind,
        "sha256": digest,
    }


class IntegratedAcceptanceAdapter:
    """Dispatch pure and live tiers through one stateful, bounded adapter seam."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        fixture_name: str = "HERMES_ACCEPTANCE_G001I",
        allow_pdg_child: bool = False,
        allow_simulation: bool = False,
        allow_viewport: bool = False,
        allow_karma: bool = False,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        if not (self.repository_root / "pyproject.toml").is_file():
            raise ValueError("repository_root must contain pyproject.toml")
        self.fixture_name = fixture_name
        self.allow_pdg_child = bool(allow_pdg_child)
        self.allow_simulation = bool(allow_simulation)
        self.allow_viewport = bool(allow_viewport)
        self.allow_karma = bool(allow_karma)
        fixture_root = self.repository_root / "tests" / "fixtures" / "acceptance"
        self._baseline = _load_json(fixture_root / "g001-small-baseline.json")
        self._expectation = _load_json(fixture_root / "g001-h22-box-expectation.json")
        self._fixture: dict[str, Any] | None = None

    def run(
        self, *, tier: str, artifact_root: str, budget: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        handlers = {
            "pure": self._run_pure,
            "hython-read": self._run_hython_read,
            "graph-edit": self._run_graph_edit,
            "single-frame": self._run_single_frame,
            "frame-range": self._run_frame_range,
            "pdg-child": self._run_pdg_child,
            "simulation": self._run_simulation,
            "viewport": self._run_viewport,
            "karma": self._run_karma,
        }
        handler = handlers.get(tier)
        if handler is None:
            raise ValueError(f"unsupported integrated tier: {tier}")
        result = dict(handler(Path(artifact_root), dict(budget)))
        if tier in {"single-frame", "frame-range", "simulation", "viewport", "karma"}:
            result = self._attach_baseline(result)
        return result

    def _run_pure(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        output_dir = root / "pure"
        output_dir.mkdir(parents=True, exist_ok=False)
        log_path = output_dir / "pytest.log"
        python = self.repository_root / ".venv" / "bin" / "python"
        if not python.is_file():
            raise FileNotFoundError("pure tier requires repository .venv/bin/python")
        command = [
            str(python),
            "-m",
            "pytest",
            "tests/unit",
            "-o",
            "addopts=",
            "-q",
        ]
        timeout = float(budget["seconds"])
        started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=self.repository_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            transcript = completed.stdout + completed.stderr
            log_path.write_text(transcript, encoding="utf-8")
            status = "pass" if completed.returncode == 0 else "blocked"
            errors = [] if status == "pass" else [f"pure tests exited {completed.returncode}"]
            observed = {
                "exit_code": completed.returncode,
                "python": str(python),
                "package_version": __version__,
                "test_output_tail": transcript.strip().splitlines()[-1:] or [],
            }
        except subprocess.TimeoutExpired as exc:
            transcript = (exc.stdout or "") + (exc.stderr or "")
            log_path.write_text(transcript, encoding="utf-8")
            status = "blocked"
            errors = [f"pure tests exceeded budget.seconds {timeout}"]
            observed = {"timeout_seconds": timeout, "package_version": __version__}
        return {
            "tier": "pure",
            "status": status,
            "command": command,
            "started_at": started_at,
            "duration_seconds": round(time.monotonic() - started, 6),
            "budget": budget,
            "observed": observed,
            "artifacts": [_artifact(log_path, kind="pytest-log")],
            "warnings": [],
            "errors": errors,
        }

    def _live_functions(self) -> dict[str, Any]:
        if not has_hou():
            raise RuntimeError("live acceptance tiers require Houdini or Hython")
        from .hython_tiers import (
            run_frame_range_tier,
            run_graph_edit_tier,
            run_hython_read_tier,
            run_karma_tier,
            run_pdg_child_tier,
            run_simulation_tier,
            run_single_frame_tier,
            run_viewport_tier,
        )

        return {
            "frame-range": run_frame_range_tier,
            "graph-edit": run_graph_edit_tier,
            "hython-read": run_hython_read_tier,
            "karma": run_karma_tier,
            "pdg-child": run_pdg_child_tier,
            "simulation": run_simulation_tier,
            "single-frame": run_single_frame_tier,
            "viewport": run_viewport_tier,
        }

    def _require_fixture(self) -> dict[str, Any]:
        if self._fixture is None:
            raise RuntimeError("graph-edit must pass before this live tier")
        return self._fixture

    def _run_hython_read(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        result = dict(self._live_functions()["hython-read"](node_path="/obj", budget=budget))
        compatibility = probe_compatibility(self._expectation)
        result["observed"] = {**result.get("observed", {}), "compatibility": compatibility}
        if compatibility["status"] != "pass":
            result["status"] = "blocked"
            result["errors"] = [
                *result.get("errors", []),
                "current-build compatibility probe failed",
            ]
        return result

    def _run_graph_edit(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        result = dict(
            self._live_functions()["graph-edit"](
                artifact_root=str(root / "graph"),
                budget=budget,
                fixture_name=self.fixture_name,
            )
        )
        if result["status"] == "pass":
            self._fixture = dict(result["observed"])
        return result

    def _run_single_frame(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        fixture = self._require_fixture()
        return dict(
            self._live_functions()["single-frame"](
                node_path=fixture["output_node_path"], frame=1, budget=budget
            )
        )

    def _run_frame_range(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        fixture = self._require_fixture()
        return dict(
            self._live_functions()["frame-range"](
                node_path=fixture["output_node_path"], frames=[1, 2, 3], budget=budget
            )
        )

    def _run_pdg_child(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        fixture = self._require_fixture()
        output = Path(fixture["pdg_output_path"])
        output.parent.mkdir(parents=True, exist_ok=True)
        return dict(
            self._live_functions()["pdg-child"](
                pdg_node_path=fixture["pdg_node_path"],
                output_path=str(output),
                budget=budget,
                authorized=self.allow_pdg_child,
            )
        )

    def _run_simulation(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        fixture = self._require_fixture()
        return dict(
            self._live_functions()["simulation"](
                node_path=fixture["simulation_node_path"],
                frames=[1, 2, 3],
                budget=budget,
                authorized=self.allow_simulation,
            )
        )

    def _run_viewport(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        if not self.allow_viewport:
            started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            return {
                "tier": "viewport",
                "status": "blocked",
                "command": ["viewport", "authorized=False"],
                "started_at": started_at,
                "duration_seconds": 0.0,
                "budget": budget,
                "observed": {},
                "artifacts": [],
                "warnings": [],
                "errors": ["explicit interactive-viewer authorization is required"],
            }
        fixture = self._require_fixture()
        output_dir = root / "viewport"
        output_dir.mkdir(parents=True, exist_ok=False)
        return dict(
            self._live_functions()["viewport"](
                viewer_name="sceneviewer1",
                viewport_name="persp1",
                camera_path=fixture["viewport_camera_path"],
                output_path=str(output_dir / "viewport.png"),
                frame=1,
                budget=budget,
            )
        )

    def _run_karma(self, root: Path, budget: dict[str, Any]) -> dict[str, Any]:
        fixture = self._require_fixture()
        output = Path(fixture["render_output_path"])
        log_path = root / "graph" / "logs" / "karma.jsonl"
        return dict(
            self._live_functions()["karma"](
                rop_path=fixture["karma_rop_path"],
                output_path=str(output),
                log_path=str(log_path),
                frame=1,
                budget=budget,
                authorized=self.allow_karma,
            )
        )

    def _attach_baseline(self, result: dict[str, Any]) -> dict[str, Any]:
        observed = dict(result.get("observed", {}))
        frame_metrics = observed.get("frame_metrics", [])
        points = max((item.get("points", 0) for item in frame_metrics), default=0)
        primitives = max((item.get("primitives", 0) for item in frame_metrics), default=0)
        memory = max((item.get("memory_bytes", 0) for item in frame_metrics), default=0)
        seconds = sum(item.get("seconds", 0.0) for item in frame_metrics)
        artifacts = result.get("artifacts", [])
        resources = {
            "points": points,
            "primitives": primitives,
            "peak_memory_bytes": memory,
            "cook_seconds": seconds,
            "cache_bytes": sum(item.get("bytes", 0) for item in artifacts),
            "frames": len(observed.get("frames", [])),
            "width": result["budget"]["width"] if result["tier"] in {"viewport", "karma"} else 0,
            "height": result["budget"]["height"] if result["tier"] in {"viewport", "karma"} else 0,
            "render_samples": result["budget"]["samples"] if result["tier"] == "karma" else 0,
        }
        baseline = evaluate_baseline(self._baseline, resources)
        observed["resource_baseline"] = baseline
        result["observed"] = observed
        if baseline["status"] == "blocked" and result["status"] in {"pass", "warn"}:
            result["status"] = "blocked"
            result["errors"] = [*result.get("errors", []), "resource baseline blocked tier"]
        elif baseline["status"] == "warn" and result["status"] == "pass":
            result["status"] = "warn"
            result["warnings"] = [*result.get("warnings", []), "resource baseline warning"]
        return result


def _repository_identity(repository_root: Path) -> dict[str, Any]:
    """Bind evidence to the local Git source without mutating the checkout."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repository_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {"kind": "repository", "commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"kind": "repository", "commit": "unavailable", "dirty": None}


def runtime_identity(
    repository_root: str | Path | None = None,
) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    """Return truthful build/license/package identity without cooking."""
    root = Path(repository_root).resolve() if repository_root else Path(__file__).parents[2]
    inventory: list[dict[str, Any]] = [
        _repository_identity(root),
        {"kind": "python", "version": sys.version.split()[0]},
        {"kind": "houdini-creative-dev", "version": __version__},
    ]
    if not has_hou():
        return "not_applicable", "not_applicable", tuple(inventory)
    from hermes_houdini.session import describe_session

    session = describe_session(max_nodes_scanned=5_000, max_managed_nodes=256)
    compatibility = session["compatibility"]
    inventory.append({"kind": "houdini-packages", **session["packages"]})
    return (
        str(compatibility["houdini_build"]),
        str(compatibility["license_mode"]),
        tuple(inventory),
    )


__all__ = ["IntegratedAcceptanceAdapter", "runtime_identity"]
