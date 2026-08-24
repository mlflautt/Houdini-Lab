"""Bounded native MPM matter-sculpture specification and temporal validation.

The module imports without Houdini. HOM only verifies and cooks a registered graph;
MPM Source, Collider, Container, Solver, Surface, and File Cache SOPs perform the work.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from . import get_hou
from .cook import geometry_metrics
from .execution import current_envelope

SCHEMA_VERSION = "1.0"
PROFILE_ORDER = ("granular", "elastic", "viscous")
SEED_OFFSETS = {"granular": 0, "elastic": 101, "viscous": 202}
MATERIAL_PROFILES: dict[str, dict[str, Any]] = {
    "granular": {
        "starting_point": "sand-like",
        "materialtype": "sandy",
        "density": 1500.0,
        "e": 1.2,
        "eexp": "3",
        "nu": 0.2,
        "sandfrictionangle": 34.0,
        "sandcohesion": 0.02,
    },
    "elastic": {
        "starting_point": "jello-like",
        "materialtype": "elastic",
        "density": 1050.0,
        "e": 2.5,
        "eexp": "3",
        "nu": 0.35,
    },
    "viscous": {
        "starting_point": "honey-like",
        "materialtype": "viscous",
        "density": 1250.0,
        "k": 1.0,
        "kexp": "3",
        "gamma": 1.0,
        "viscosity": 0.85,
        "viscokappa": 0.08,
    },
}
_ABS_NODE_PATH = re.compile(r"/(?:[A-Za-z0-9_.-]+)(?:/[A-Za-z0-9_.-]+)*\Z")
_RUN_CODE = re.compile(r"[A-Z0-9][A-Z0-9_]{0,31}\Z")


def _integer(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return value


def _finite(
    value: Any, label: str, *, minimum: float | None = None, maximum: float | None = None
) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{label} must be <= {maximum}")
    return result


def validate_mpm_spec(
    *,
    seed: int,
    start_frame: int,
    end_frame: int,
    particle_separation: float,
    source_radius: float,
    source_height: float,
    noise_height: float,
    substep_min: int,
    substep_max: int,
    output_mode: str,
    max_particles: int = 150_000,
) -> dict[str, Any]:
    """Validate deterministic controls and proxy-first particle/frame ceilings."""
    seed = _integer(seed, "seed", minimum=0, maximum=2_147_483_445)
    start_frame = _integer(start_frame, "start_frame", minimum=1, maximum=100_000)
    end_frame = _integer(end_frame, "end_frame", minimum=1, maximum=100_000)
    if end_frame < start_frame:
        raise ValueError("end_frame must be >= start_frame")
    frame_count = end_frame - start_frame + 1
    if frame_count > 24:
        raise ValueError("MPM proxy validation is limited to 24 inclusive frames")
    particle_separation = _finite(
        particle_separation, "particle_separation", minimum=0.06, maximum=0.25
    )
    source_radius = _finite(source_radius, "source_radius", minimum=0.3, maximum=1.1)
    source_height = _finite(source_height, "source_height", minimum=1.2, maximum=4.0)
    noise_height = _finite(noise_height, "noise_height", minimum=0.0, maximum=0.18)
    substep_min = _integer(substep_min, "substep_min", minimum=1, maximum=8)
    substep_max = _integer(substep_max, "substep_max", minimum=2, maximum=128)
    if substep_max < substep_min:
        raise ValueError("substep_max must be >= substep_min")
    if output_mode not in {"points", "surface"}:
        raise ValueError("output_mode must be points or surface")
    max_particles = _integer(max_particles, "max_particles", minimum=1, maximum=1_000_000)

    # MPM Source volume fill is implementation-dependent. This conservative envelope uses
    # two particles per separation-sized voxel across three perturbed spheres.
    source_volume = (4.0 / 3.0) * math.pi * (source_radius + noise_height) ** 3
    estimated_particles = math.ceil(
        (len(PROFILE_ORDER) * source_volume * 2.0) / (particle_separation**3)
    )
    if estimated_particles > max_particles:
        raise ValueError(
            f"estimated proxy particles {estimated_particles} exceed max_particles {max_particles}"
        )
    return {
        "seed": seed,
        "profile_seeds": {profile: seed + SEED_OFFSETS[profile] for profile in PROFILE_ORDER},
        "profile_order": list(PROFILE_ORDER),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_count": frame_count,
        "particle_separation": particle_separation,
        "source_radius": source_radius,
        "source_height": source_height,
        "noise_height": noise_height,
        "substep_min": substep_min,
        "substep_max": substep_max,
        "output_mode": output_mode,
        "output_index": 0 if output_mode == "points" else 1,
        "max_particles": max_particles,
        "estimated_particles": estimated_particles,
        "material_profiles": MATERIAL_PROFILES,
    }


def _absolute_node_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ABS_NODE_PATH.fullmatch(value):
        raise ValueError(f"{label} must be an absolute Houdini node path")
    return value


def _new_json_path(value: str, label: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or path.suffix.lower() != ".json":
        raise ValueError(f"{label} must be an absolute .json path")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _atomic_json(path: Path, document: dict[str, Any]) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temp.exists():
        raise FileExistsError(f"refusing to overwrite temporary artifact: {temp}")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _require_node(network: Any, name: str, operator_type: str, role: str) -> Any:
    node = network.node(name)
    if node is None or node.parent() != network:
        raise ValueError(f"missing managed MPM node: {name}")
    if node.type().category().name() != "Sop" or node.type().name() != operator_type:
        raise ValueError(f"{name} must be exact Sop/{operator_type}")
    if node.userData("hermes_role") != role:
        raise ValueError(f"{name} has an invalid managed role")
    return node


def _close(actual: Any, expected: float) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-6)


def _assert_parameters(node: Any, values: dict[str, Any], label: str) -> None:
    for name, expected in values.items():
        if isinstance(expected, (list, tuple)):
            parm_tuple = node.parmTuple(name)
            if parm_tuple is None:
                raise ValueError(f"{label} is missing parameter tuple {name}")
            actual = parm_tuple.eval()
            if len(actual) != len(expected) or any(
                not _close(left, right) for left, right in zip(actual, expected, strict=True)
            ):
                raise ValueError(f"{label} has unregistered {name}: {actual!r}")
            continue
        parm = node.parm(name)
        if parm is None:
            raise ValueError(f"{label} is missing parameter {name}")
        actual = parm.evalAsString() if isinstance(expected, str) else parm.eval()
        matches = actual == expected if isinstance(expected, str) else _close(actual, expected)
        if not matches:
            raise ValueError(f"{label} has unregistered {name}: {actual!r}")


def _finite_bounds(metrics: dict[str, Any], label: str) -> None:
    bounds = metrics["bounds"]
    if bounds is None or any(
        not math.isfinite(float(value)) for vector in bounds for value in vector
    ):
        raise ValueError(f"{label} has non-finite bounds")


def _sample_geometry(geometry: Any, limit: int = 256) -> dict[str, Any]:
    points = geometry.points()
    if not points:
        raise ValueError("MPM solver produced no particles")
    stride = max(1, len(points) // limit)
    sampled = points[::stride][:limit]
    velocity = geometry.findPointAttrib("v")
    positions: list[tuple[float, float, float]] = []
    speeds: list[float] = []
    for point in sampled:
        position = tuple(float(value) for value in point.position())
        if any(not math.isfinite(value) for value in position):
            raise ValueError("MPM particle sample has non-finite position")
        positions.append(position)
        if velocity is not None:
            vector = tuple(float(value) for value in point.attribValue(velocity))
            if any(not math.isfinite(value) for value in vector):
                raise ValueError("MPM particle sample has non-finite velocity")
            speeds.append(math.sqrt(sum(value * value for value in vector)))
    centroid = [sum(point[axis] for point in positions) / len(positions) for axis in range(3)]
    return {
        "sample_count": len(positions),
        "centroid": [round(value, 6) for value in centroid],
        "max_speed": round(max(speeds, default=0.0), 6),
    }


def _detail_value(geometry: Any, name: str) -> Any:
    attribute = geometry.findGlobalAttrib(name)
    if attribute is None:
        return None
    value = geometry.attribValue(attribute)
    if isinstance(value, tuple):
        return list(value)
    return value


def _source_counts(geometry: Any) -> dict[str, int]:
    for name in ("source_name", "sourcename"):
        attribute = geometry.findPointAttrib(name)
        if attribute is not None:
            values = (str(point.attribValue(attribute)) for point in geometry.points())
            return dict(sorted(Counter(values).items()))
    raise ValueError("MPM solver output is missing source_name/sourcename")


def cook_validate_mpm(
    *,
    network_path: str,
    run_code: str,
    seed: int,
    start_frame: int,
    end_frame: int,
    particle_separation: float,
    source_radius: float,
    source_height: float,
    noise_height: float,
    substep_min: int,
    substep_max: int,
    output_mode: str,
    cache_path: str,
    progress_path: str,
    output_path: str,
    max_particles: int = 150_000,
) -> dict[str, Any]:
    """Validate the exact graph and cook one bounded multi-material MPM proxy."""
    hou = get_hou()
    spec = validate_mpm_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        particle_separation=particle_separation,
        source_radius=source_radius,
        source_height=source_height,
        noise_height=noise_height,
        substep_min=substep_min,
        substep_max=substep_max,
        output_mode=output_mode,
        max_particles=max_particles,
    )
    network_path = _absolute_node_path(network_path, "network_path")
    if not isinstance(run_code, str) or not _RUN_CODE.fullmatch(run_code):
        raise ValueError("run_code must be a 1-32 character uppercase Houdini identifier")
    cache = Path(cache_path).expanduser()
    if not cache.is_absolute() or not str(cache).endswith(".bgeo.sc"):
        raise ValueError("cache_path must be an absolute .bgeo.sc path")
    output = _new_json_path(output_path, "output_path")
    progress = _new_json_path(progress_path, "progress_path")
    network = hou.node(network_path)
    if network is None or network.type().category().name() != "Object":
        raise ValueError(f"SOP network not found: {network_path}")
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 180.0
    point_ceiling = min(spec["max_particles"], int(policy.max_points) if policy else max_particles)
    memory_ceiling = int(policy.max_memory_bytes) if policy else 1_073_741_824

    container = _require_node(network, f"{run_code}_MPM_CONTAINER", "mpmcontainer", "mpm_container")
    _assert_parameters(
        container,
        {
            "startframe": start_frame,
            "particlesep": particle_separation,
            "gridscale": 2.0,
            "allboundsoverride": 1,
            "allbounds": "closed",
        },
        "MPM Container",
    )
    source_nodes = []
    for profile in PROFILE_ORDER:
        upper = profile.upper()
        shape = _require_node(
            network, f"{run_code}_{upper}_SHAPE", "sphere", f"mpm_shape_{profile}"
        )
        mountain = _require_node(
            network,
            f"{run_code}_{upper}_SEEDED_SHAPE",
            "mountain::2.0",
            f"mpm_seeded_shape_{profile}",
        )
        source = _require_node(
            network, f"{run_code}_{upper}_SOURCE", "mpmsource", f"mpm_source_{profile}"
        )
        if (
            mountain.input(0) != shape
            or source.input(0) != mountain
            or source.input(1) != container
        ):
            raise ValueError(f"{profile} MPM source branch is disconnected")
        _assert_parameters(
            mountain,
            {"height": noise_height, "offsetx": spec["profile_seeds"][profile]},
            f"{profile} seeded shape",
        )
        material = MATERIAL_PROFILES[profile]
        parameters = {
            "emissiontype": "once",
            "particlesepoverride": 0,
            "jitterscale": 0.35,
            "materialtype": material["materialtype"],
            "density": material["density"],
        }
        parameters.update(
            {
                key: value
                for key, value in material.items()
                if key not in {"starting_point", "materialtype", "density"}
            }
        )
        _assert_parameters(source, parameters, f"{profile} MPM Source")
        source_nodes.append(source)

    merge = _require_node(network, f"{run_code}_MERGE_SOURCES", "merge", "mpm_source_merge")
    if list(merge.inputs()) != source_nodes:
        raise ValueError("MPM source merge must preserve granular, elastic, viscous order")
    collider_shape = _require_node(
        network, f"{run_code}_COLLIDER_SHAPE", "box", "mpm_collider_shape"
    )
    collider = _require_node(
        network, f"OUT_{run_code}_COLLIDER", "mpmcollider", "mpm_collider_contract"
    )
    if collider.input(0) != collider_shape or collider.input(1) != container:
        raise ValueError("MPM Collider must receive explicit geometry and Container wires")
    _assert_parameters(collider, {"type": "0", "response": "bounce"}, "MPM Collider")
    solver = _require_node(network, f"{run_code}_MPM_SOLVER", "mpmsolver", "mpm_solver")
    if list(solver.inputs()) != [merge, collider, container]:
        raise ValueError("MPM Solver inputs must be Source merge, Collider, Container")
    _assert_parameters(
        solver,
        {
            "doglobalsubsteps": 0,
            "substeprange": [substep_min, substep_max],
            "groundactive": 1,
            "savecheckpoints": 0,
            "deterministic": 1,
            "cachemaxsize": 1024,
        },
        "MPM Solver",
    )
    raw = _require_node(network, f"OUT_{run_code}_POINTS_RAW", "null", "mpm_points_raw")
    file_cache = _require_node(network, f"{run_code}_FILE_CACHE", "filecache", "mpm_cache")
    cached = _require_node(network, f"OUT_{run_code}_POINTS", "null", "mpm_points_contract")
    surface = _require_node(
        network, f"OUT_{run_code}_SURFACE", "mpmsurface", "mpm_surface_contract"
    )
    selector = _require_node(network, f"{run_code}_SELECT_OUTPUT", "switch", "mpm_output_selector")
    selected = _require_node(network, f"OUT_{run_code}_SELECTED", "null", "mpm_selected_contract")
    if raw.input(0) != solver or file_cache.input(0) != raw or cached.input(0) != file_cache:
        raise ValueError("MPM point/cache output chain is disconnected")
    if (
        surface.input(0) != cached
        or list(selector.inputs()) != [cached, surface]
        or selected.input(0) != selector
    ):
        raise ValueError("MPM point/surface selector chain is disconnected")
    _assert_parameters(
        file_cache,
        {"filemode": "none", "loadfromdisk": 0, "initsim": 1},
        "MPM File Cache",
    )
    if file_cache.parm("file").unexpandedString() != str(cache):
        raise ValueError("MPM File Cache path does not match the registered cache contract")
    _assert_parameters(
        surface, {"outputtype": "polygonmesh", "surfacingmethod": "vdbfromparticles"}, "MPM Surface"
    )
    _assert_parameters(selector, {"input": spec["output_index"]}, "MPM output selector")

    status: dict[str, Any] = {
        "schema": "hermes.houdini.mpm_cache_progress",
        "schema_version": SCHEMA_VERSION,
        "status": "running",
        "cache_path": str(cache),
        "cache_write_enabled": False,
        "planned_frames": list(range(start_frame, end_frame + 1)),
        "completed_frames": [],
        "started_unix": time.time(),
    }
    _atomic_json(progress, status)
    original_frame = float(hou.frame())
    frames: list[dict[str, Any]] = []
    started = time.monotonic()
    try:
        hou.setFrame(start_frame)
        initial_sources: dict[str, Any] = {}
        total_estimated_mass = 0.0
        for profile, source in zip(PROFILE_ORDER, source_nodes, strict=True):
            source.cook(force=True)
            source_metrics = geometry_metrics(source)
            _finite_bounds(source_metrics, f"{profile} MPM source")
            if not 0 < source_metrics["points"] <= point_ceiling:
                raise ValueError(f"{profile} MPM source exceeds particle ceiling")
            source_geometry = source.geometry()
            density_attribute = source_geometry.findPointAttrib("density")
            if density_attribute is None:
                raise ValueError(f"{profile} MPM source is missing density")
            density_values = [
                float(point.attribValue(density_attribute)) for point in source_geometry.points()
            ]
            if not density_values or any(
                not math.isfinite(value) or value <= 0 for value in density_values
            ):
                raise ValueError(f"{profile} MPM source has invalid density")
            if any(
                not _close(value, MATERIAL_PROFILES[profile]["density"]) for value in density_values
            ):
                raise ValueError(f"{profile} MPM source density does not match its profile")
            estimated_mass = sum(density_values) * particle_separation**3
            total_estimated_mass += estimated_mass
            initial_sources[profile] = {
                "metrics": source_metrics,
                "density": MATERIAL_PROFILES[profile]["density"],
                "estimated_mass": round(estimated_mass, 6),
            }
        for frame in range(start_frame, end_frame + 1):
            if time.monotonic() - started > max_seconds:
                raise TimeoutError(f"MPM proxy exceeded {max_seconds:.1f} second policy")
            hou.setFrame(frame)
            frame_started = time.monotonic()
            raw.cook(force=True)
            messages = [*raw.errors(), *raw.warnings(), *solver.errors(), *solver.warnings()]
            if messages:
                raise ValueError("MPM cook messages: " + "; ".join(messages))
            metrics = geometry_metrics(raw)
            _finite_bounds(metrics, f"MPM frame {frame}")
            if not 0 < metrics["points"] <= point_ceiling:
                raise ValueError(
                    f"MPM frame {frame} particles {metrics['points']} exceed ceiling {point_ceiling}"
                )
            if metrics["memory_bytes"] > memory_ceiling:
                raise ValueError(
                    f"MPM frame {frame} memory {metrics['memory_bytes']} exceeds {memory_ceiling}"
                )
            geometry = raw.geometry()
            attributes = set(metrics["point_attributes"])
            required = {"P", "v", "id", "pscale"}
            if not required <= attributes:
                raise ValueError(
                    f"MPM frame {frame} missing attributes: {sorted(required - attributes)}"
                )
            source_counts = _source_counts(geometry)
            if len(source_counts) != len(PROFILE_ORDER):
                raise ValueError(f"MPM frame {frame} does not preserve three material sources")
            sample = _sample_geometry(geometry)
            frames.append(
                {
                    "frame": frame,
                    "metrics": metrics,
                    "sample": sample,
                    "source_counts": source_counts,
                    "estimated_mass": round(total_estimated_mass, 6),
                    "detail": {
                        name: _detail_value(geometry, name)
                        for name in ("startframe", "substepcount", "dx", "gridscale", "particlesep")
                    },
                    "cook_seconds": round(time.monotonic() - frame_started, 6),
                }
            )
            status["completed_frames"] = [item["frame"] for item in frames]
            status["last_update_unix"] = time.time()
            _atomic_json(progress, status)
        initial_centroid = frames[0]["sample"]["centroid"]
        final_centroid = frames[-1]["sample"]["centroid"]
        centroid_motion = math.sqrt(
            sum(
                (right - left) ** 2
                for left, right in zip(initial_centroid, final_centroid, strict=True)
            )
        )
        if len(frames) > 1 and centroid_motion < 0.05:
            raise ValueError("MPM proxy did not produce measurable temporal motion")
        selected.cook(force=True)
        selected_metrics = geometry_metrics(selected)
        if (
            output_mode == "points"
            and selected_metrics["points"] != frames[-1]["metrics"]["points"]
        ):
            raise ValueError("selected point output does not match final MPM particles")
        document = {
            "schema": "hermes.houdini.mpm_matter_validation",
            "schema_version": SCHEMA_VERSION,
            "timestamp_unix": time.time(),
            "status": "success",
            "network_path": network_path,
            "run_code": run_code,
            "spec": spec,
            "initial_sources": initial_sources,
            "frames": frames,
            "selected": selected_metrics,
            "centroid_motion": round(centroid_motion, 6),
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "cache": {
                "path": str(cache),
                "write_implicit": False,
                "file_mode": "none",
                "status": "configured_not_written",
                "progress_manifest": str(progress),
            },
            "selection": {
                "method": "human",
                "winner": None,
                "automatic_ranking": False,
                "human_ratings": {
                    profile: {"score": None, "notes": "", "selected": False}
                    for profile in PROFILE_ORDER
                },
            },
        }
        _atomic_json(output, document)
        status.update(
            {
                "status": "complete",
                "finished_unix": time.time(),
                "validation_path": str(output),
            }
        )
        _atomic_json(progress, status)
        return {"artifact": str(output), "progress_artifact": str(progress), **document}
    except Exception as exc:
        status.update({"status": "failed", "finished_unix": time.time(), "error": str(exc)})
        _atomic_json(progress, status)
        raise
    finally:
        hou.setFrame(original_frame)


__all__ = [
    "MATERIAL_PROFILES",
    "PROFILE_ORDER",
    "SCHEMA_VERSION",
    "SEED_OFFSETS",
    "cook_validate_mpm",
    "validate_mpm_spec",
]
