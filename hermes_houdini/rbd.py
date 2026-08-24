"""Native RBD fracture specification and transform-cache verification.

The module imports without Houdini. HOM only validates and cooks a registered graph;
Material Fracture, RBD Configure, Bullet Solver, and Transform Pieces do the work.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from . import get_hou
from .cook import geometry_metrics
from .execution import current_envelope

SCHEMA_VERSION = "1.0"
PROFILE_ORDER = ("radial", "offset", "layered")
PROFILE_SEED_OFFSETS = {"radial": 0, "offset": 101, "layered": 202}
PROFILE_POINT_COUNTS = {"radial": 8, "offset": 12, "layered": 12}
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


def validate_rbd_spec(
    *,
    seed: int,
    start_frame: int,
    end_frame: int,
    profile_index: int,
    bullet_substeps: int,
    constraint_iterations: int,
    primary_strength: float,
    chipping_strength: float,
    max_pieces: int = 5_000,
) -> dict[str, Any]:
    """Validate bounded deterministic RBD controls without importing Houdini."""
    seed = _integer(seed, "seed", minimum=0, maximum=2_147_483_445)
    start_frame = _integer(start_frame, "start_frame", minimum=1, maximum=100_000)
    end_frame = _integer(end_frame, "end_frame", minimum=1, maximum=100_000)
    if end_frame < start_frame:
        raise ValueError("end_frame must be >= start_frame")
    frame_count = end_frame - start_frame + 1
    if frame_count > 48:
        raise ValueError("RBD validation is limited to 48 inclusive frames")
    profile_index = _integer(profile_index, "profile_index", minimum=0, maximum=2)
    max_pieces = _integer(max_pieces, "max_pieces", minimum=1, maximum=5_000)
    return {
        "seed": seed,
        "profile_order": list(PROFILE_ORDER),
        "profile_index": profile_index,
        "profile": PROFILE_ORDER[profile_index],
        "profile_seeds": {
            profile: seed + PROFILE_SEED_OFFSETS[profile] for profile in PROFILE_ORDER
        },
        "profile_point_counts": PROFILE_POINT_COUNTS,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_count": frame_count,
        "bullet_substeps": _integer(bullet_substeps, "bullet_substeps", minimum=1, maximum=10),
        "constraint_iterations": _integer(
            constraint_iterations, "constraint_iterations", minimum=1, maximum=50
        ),
        "primary_strength": _finite(
            primary_strength, "primary_strength", minimum=0.01, maximum=1000.0
        ),
        "chipping_strength": _finite(
            chipping_strength, "chipping_strength", minimum=0.01, maximum=1000.0
        ),
        "max_pieces": max_pieces,
    }


def _absolute_node_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ABS_NODE_PATH.fullmatch(value):
        raise ValueError(f"{label} must be an absolute Houdini node path")
    return value


def _prepare_new_json(output_path: str) -> Path:
    path = Path(output_path).expanduser()
    if not path.is_absolute() or path.suffix.lower() != ".json":
        raise ValueError("output_path must be an absolute .json path")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _require_node(network: Any, name: str, operator_type: str, role: str) -> Any:
    node = network.node(name)
    if node is None or node.parent() != network:
        raise ValueError(f"missing managed RBD node: {name}")
    if node.type().category().name() != "Sop" or node.type().name() != operator_type:
        raise ValueError(f"{name} must be exact Sop/{operator_type}")
    if node.userData("hermes_role") != role:
        raise ValueError(f"{name} has an invalid managed role")
    return node


def _close(actual: Any, expected: float) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-6)


def _assert_parameters(node: Any, values: dict[str, Any], label: str) -> None:
    for name, expected in values.items():
        parm = node.parm(name)
        if parm is None:
            raise ValueError(f"{label} is missing parameter {name}")
        actual = parm.evalAsString() if isinstance(expected, str) else parm.eval()
        matches = actual == expected if isinstance(expected, str) else _close(actual, expected)
        if not matches:
            raise ValueError(f"{label} has unregistered {name}: {actual!r}")


def _messages(nodes: list[Any]) -> list[str]:
    return [
        f"{node.path()}: {message}"
        for node in nodes
        for message in (*node.errors(), *node.warnings())
    ]


def _finite_values(values: Any, label: str) -> list[float]:
    result = [float(value) for value in values]
    if any(not math.isfinite(value) for value in result):
        raise ValueError(f"{label} contains non-finite values")
    return result


def _point_names(geometry: Any) -> list[str]:
    if geometry.findPointAttrib("name") is None:
        raise ValueError("RBD point geometry is missing the name attribute")
    return list(geometry.pointStringAttribValues("name"))


def _piece_names(geometry: Any) -> list[str]:
    if geometry.findPrimAttrib("name") is None:
        raise ValueError("fractured geometry is missing the primitive name attribute")
    return list(geometry.primStringAttribValues("name"))


def _centroid(geometry: Any) -> list[float]:
    points = geometry.points()
    if not points:
        raise ValueError("geometry has no points")
    return [
        sum(float(point.position()[axis]) for point in points) / len(points) for axis in range(3)
    ]


def _transform_frame(geometry: Any, frame: int, expected_names: set[str]) -> dict[str, Any]:
    required = {"name", "orient", "pivot", "scale", "v", "w"}
    actual = {attribute.name() for attribute in geometry.pointAttribs()}
    if not required <= actual:
        raise ValueError(f"frame {frame} transform points are missing {sorted(required - actual)}")
    names = _point_names(geometry)
    if len(names) != len(set(names)) or set(names) != expected_names:
        raise ValueError(f"frame {frame} transform names are not stable and unique")
    records = []
    max_speed = 0.0
    for point, name in zip(geometry.points(), names, strict=True):
        position = _finite_values(point.position(), f"frame {frame} P")
        orient = _finite_values(point.attribValue("orient"), f"frame {frame} orient")
        pivot = _finite_values(point.attribValue("pivot"), f"frame {frame} pivot")
        scale = _finite_values(point.attribValue("scale"), f"frame {frame} scale")
        velocity = _finite_values(point.attribValue("v"), f"frame {frame} v")
        angular_velocity = _finite_values(point.attribValue("w"), f"frame {frame} w")
        max_speed = max(max_speed, math.sqrt(sum(value * value for value in velocity)))
        records.append(
            [
                name,
                *[round(value, 8) for value in position],
                *[round(value, 8) for value in orient],
                *[round(value, 8) for value in pivot],
                *[round(value, 8) for value in scale],
                *[round(value, 8) for value in velocity],
                *[round(value, 8) for value in angular_velocity],
            ]
        )
    records.sort(key=lambda item: item[0])
    digest = hashlib.sha256(
        json.dumps(records, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    bounds = geometry.boundingBox()
    return {
        "frame": frame,
        "piece_count": len(names),
        "centroid": [round(value, 6) for value in _centroid(geometry)],
        "bounds": [
            [round(float(value), 6) for value in bounds.minvec()],
            [round(float(value), 6) for value in bounds.maxvec()],
        ],
        "max_speed": round(max_speed, 6),
        "transform_sha256": digest,
        "memory_bytes": int(geometry.intrinsicValue("memoryusage")),
    }


def cook_validate_rbd(
    *,
    network_path: str,
    run_code: str,
    seed: int,
    start_frame: int,
    end_frame: int,
    profile_index: int,
    bullet_substeps: int,
    constraint_iterations: int,
    primary_strength: float,
    chipping_strength: float,
    transform_cache_path: str,
    output_path: str,
    max_pieces: int = 5_000,
) -> dict[str, Any]:
    """Validate the exact managed graph and every frame of its transform representation."""
    hou = get_hou()
    spec = validate_rbd_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        profile_index=profile_index,
        bullet_substeps=bullet_substeps,
        constraint_iterations=constraint_iterations,
        primary_strength=primary_strength,
        chipping_strength=chipping_strength,
        max_pieces=max_pieces,
    )
    network_path = _absolute_node_path(network_path, "network_path")
    if not isinstance(run_code, str) or not _RUN_CODE.fullmatch(run_code):
        raise ValueError("run_code must be a 1-32 character uppercase Houdini identifier")
    cache_path = Path(transform_cache_path).expanduser()
    if not cache_path.is_absolute() or "$F4" not in transform_cache_path:
        raise ValueError("transform_cache_path must be absolute and contain $F4")
    output = _prepare_new_json(output_path)
    network = hou.node(network_path)
    if network is None or network.type().category().name() != "Object":
        raise ValueError(f"SOP network not found: {network_path}")
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 120.0
    point_ceiling = int(policy.max_points) if policy and policy.max_points else 250_000
    primitive_ceiling = int(policy.max_primitives) if policy and policy.max_primitives else 250_000

    source = _require_node(network, f"OUT_{run_code}_SOURCE", "null", "rbd_source_contract")
    profiles = {
        profile: _require_node(
            network,
            f"OUT_{run_code}_IMPACT_{profile.upper()}",
            "null",
            f"rbd_impact_contract_{profile}",
        )
        for profile in PROFILE_ORDER
    }
    profile_switch = _require_node(
        network,
        f"{run_code}_SELECT_IMPACT_PROFILE",
        "switch",
        "rbd_impact_human_selector",
    )
    fracture = _require_node(
        network,
        f"{run_code}_MATERIAL_FRACTURE",
        "rbdmaterialfracture::4.0",
        "rbd_material_fracture",
    )
    rest = _require_node(network, f"OUT_{run_code}_REST_PIECES", "null", "rbd_rest_pieces_contract")
    constraints = _require_node(
        network, f"OUT_{run_code}_CONSTRAINTS", "null", "rbd_constraints_contract"
    )
    proxy = _require_node(network, f"OUT_{run_code}_PROXY", "null", "rbd_proxy_contract")
    configure = _require_node(network, f"{run_code}_CONFIGURE", "rbdconfigure", "rbd_configure")
    solver = _require_node(
        network, f"{run_code}_BULLET_SOLVER", "rbdbulletsolver", "rbd_bullet_solver"
    )
    sim_raw = _require_node(network, f"OUT_{run_code}_SIM_RAW", "null", "rbd_sim_raw_contract")
    sim_constraints = _require_node(
        network,
        f"OUT_{run_code}_SIM_CONSTRAINTS",
        "null",
        "rbd_sim_constraints_contract",
    )
    transform_raw = _require_node(
        network,
        f"OUT_{run_code}_TRANSFORMS_RAW",
        "null",
        "rbd_transform_raw_contract",
    )
    transform_cache = _require_node(
        network,
        f"{run_code}_TRANSFORM_FILE_CACHE",
        "filecache",
        "rbd_transform_cache",
    )
    transforms = _require_node(
        network,
        f"OUT_{run_code}_TRANSFORMS",
        "null",
        "rbd_transform_cache_contract",
    )
    rest_transforms = _require_node(
        network,
        f"{run_code}_REST_TRANSFORMS",
        "timeshift",
        "rbd_rest_transform_contract",
    )
    reconstruct = _require_node(
        network,
        f"{run_code}_RECONSTRUCT_PIECES",
        "xformpieces",
        "rbd_transform_reconstruction",
    )
    after_normal = _require_node(
        network,
        f"{run_code}_AFTER_NORMALS",
        "normal",
        "rbd_after_normals",
    )
    after = _require_node(network, f"OUT_{run_code}_AFTER", "null", "rbd_after_contract")
    compare = _require_node(network, f"OUT_{run_code}_COMPARE", "null", "rbd_comparison_contract")
    labels = _require_node(network, f"OUT_{run_code}_LABELS", "merge", "rbd_labels_contract")

    if list(profile_switch.inputs())[:3] != [profiles[name] for name in PROFILE_ORDER]:
        raise ValueError("RBD impact profile Switch order is invalid")
    if profile_switch.parm("input").eval() != spec["profile_index"]:
        raise ValueError("RBD impact profile Switch does not match the human preview input")
    if fracture.input(0) != source or fracture.input(3) != profile_switch:
        raise ValueError("RBD Material Fracture inputs are invalid")
    if [rest.input(0), constraints.input(0), proxy.input(0)] != [fracture, fracture, fracture]:
        raise ValueError("RBD Material Fracture output contracts are disconnected")
    if list(configure.inputs())[:3] != [rest, constraints, proxy]:
        raise ValueError("RBD Configure inputs are invalid")
    if list(solver.inputs())[:3] != [configure, configure, configure]:
        raise ValueError("RBD Bullet Solver inputs are invalid")
    if (
        sim_raw.input(0) != solver
        or sim_constraints.input(0) != solver
        or transform_raw.input(0) != solver
        or transform_cache.input(0) != transform_raw
        or transforms.input(0) != transform_cache
        or rest_transforms.input(0) != transform_raw
        or list(reconstruct.inputs())[:3] != [rest, transforms, rest_transforms]
        or after_normal.input(0) != reconstruct
        or after.input(0) != after_normal
    ):
        raise ValueError("RBD simulation, cache, or reconstruction chain is invalid")
    if labels in compare.inputAncestors():
        raise ValueError("RBD labels must remain outside comparison render geometry")

    _assert_parameters(
        fracture,
        {
            "materialtype": "concrete",
            "concrete_fracturelevel": 2,
            "constraintsenable": 1,
            "concrete_applyconstraints": 1,
            "concrete_primarystrength": spec["primary_strength"],
            "concrete_chippingstrength": spec["chipping_strength"],
        },
        "RBD Material Fracture",
    )
    _assert_parameters(
        configure,
        {"createpackedfragments": 1, "addactive1": 1, "active1": 1},
        "RBD Configure",
    )
    _assert_parameters(
        solver,
        {
            "startframe": spec["start_frame"],
            "substeps": spec["bullet_substeps"],
            "numiteration": spec["constraint_iterations"],
            "cacheenabled": 1,
            "cachemaxsize": 512,
            "useground": 1,
            "enable_constraintbreaks": 1,
            "constraint_keepbroken": 0,
        },
        "RBD Bullet Solver",
    )
    cache_contract = {
        "file": transform_cache.parm("file").unexpandedString(),
        "loadfromdisk": transform_cache.parm("loadfromdisk").eval(),
        "initsim": transform_cache.parm("initsim").eval(),
        "f1": transform_cache.parm("f1").eval(),
        "f2": transform_cache.parm("f2").eval(),
        "rest_frame": rest_transforms.parm("frame").eval(),
    }
    if cache_contract != {
        "file": transform_cache_path,
        "loadfromdisk": 0,
        "initsim": 0,
        "f1": spec["start_frame"],
        "f2": spec["end_frame"],
        "rest_frame": float(spec["start_frame"]),
    }:
        raise ValueError(f"RBD transform cache boundary is invalid: {cache_contract}")

    source.cook(force=True)
    profile_metrics = {}
    for profile, node in profiles.items():
        node.cook(force=True)
        metrics = geometry_metrics(node)
        if metrics["points"] != PROFILE_POINT_COUNTS[profile]:
            raise ValueError(f"impact profile {profile} point count is invalid")
        profile_metrics[profile] = metrics
    rest.cook(force=True)
    constraints.cook(force=True)
    proxy.cook(force=True)
    rest_geometry = rest.geometry()
    constraint_geometry = constraints.geometry()
    rest_names = set(_piece_names(rest_geometry))
    if not rest_names or len(rest_names) > spec["max_pieces"]:
        raise ValueError("RBD rest piece count is empty or over budget")
    required_constraints = {"constraint_name", "constraint_type", "strength"}
    constraint_attribs = {attribute.name() for attribute in constraint_geometry.primAttribs()}
    if not required_constraints <= constraint_attribs or not constraint_geometry.prims():
        raise ValueError("RBD material constraints are missing required attributes")
    initial_constraint_count = len(constraint_geometry.prims())
    rest_metrics = geometry_metrics(rest)
    proxy_metrics = geometry_metrics(proxy)
    if rest_metrics["points"] > point_ceiling or rest_metrics["primitives"] > primitive_ceiling:
        raise ValueError("RBD rest geometry exceeds topology policy")

    all_nodes = [
        source,
        *profiles.values(),
        profile_switch,
        fracture,
        rest,
        constraints,
        proxy,
        configure,
        solver,
        sim_raw,
        sim_constraints,
        transform_raw,
        transform_cache,
        transforms,
        rest_transforms,
        reconstruct,
        after_normal,
        after,
        compare,
    ]
    messages = _messages(all_nodes)
    if messages:
        raise ValueError("RBD graph has Houdini messages: " + "; ".join(messages))

    original_frame = hou.frame()
    started = time.monotonic()
    frames: list[dict[str, Any]] = []
    final_metrics: dict[str, Any] = {}
    try:
        for frame in range(spec["start_frame"], spec["end_frame"] + 1):
            hou.setFrame(frame)
            transforms.cook(force=True)
            sim_constraints.cook(force=True)
            after.cook(force=True)
            messages = _messages([solver, transform_cache, transforms, reconstruct, after])
            if messages:
                raise ValueError(f"RBD frame {frame} has Houdini messages: " + "; ".join(messages))
            transform_geometry = transforms.geometry()
            if len(transform_geometry.points()) > spec["max_pieces"]:
                raise ValueError(f"RBD frame {frame} exceeds the piece budget")
            frame_data = _transform_frame(transform_geometry, frame, rest_names)
            reconstructed = geometry_metrics(after)
            if (
                reconstructed["points"] != rest_metrics["points"]
                or reconstructed["primitives"] != rest_metrics["primitives"]
                or reconstructed["points"] > point_ceiling
                or reconstructed["primitives"] > primitive_ceiling
            ):
                raise ValueError(f"RBD frame {frame} reconstruction topology is invalid")
            reconstructed_names = set(_piece_names(after.geometry()))
            if reconstructed_names != rest_names:
                raise ValueError(f"RBD frame {frame} reconstruction lost piece names")
            frame_data["surviving_constraints"] = len(sim_constraints.geometry().prims())
            frame_data["reconstructed"] = reconstructed
            frames.append(frame_data)
            if time.monotonic() - started > max_seconds:
                raise TimeoutError("RBD validation exceeded policy.max_seconds")
        compare.cook(force=True)
        final_metrics = {"after": geometry_metrics(after), "comparison": geometry_metrics(compare)}
    finally:
        hou.setFrame(original_frame)

    first = frames[0]
    final = frames[-1]
    vertical_drop = first["centroid"][1] - final["centroid"][1]
    broken_constraints = initial_constraint_count - final["surviving_constraints"]
    if vertical_drop < 1.0:
        raise ValueError("RBD result did not produce a meaningful vertical drop")
    if broken_constraints <= 0:
        raise ValueError("RBD result did not break any material constraints")
    if first["transform_sha256"] == final["transform_sha256"]:
        raise ValueError("RBD transform cache did not change across the frame range")
    cache_files = sorted(cache_path.parent.glob(cache_path.name.replace("$F4", "*")))
    if cache_files:
        raise ValueError("RBD skill unexpectedly wrote transform cache files")

    document = {
        "schema": "hermes.houdini.rbd_art_directed_fracture_validation",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "status": "success",
        "network_path": network_path,
        "run_code": run_code,
        "spec": spec,
        "profiles": profile_metrics,
        "rest": rest_metrics,
        "proxy": proxy_metrics,
        "piece_count": len(rest_names),
        "initial_constraints": initial_constraint_count,
        "broken_constraints": broken_constraints,
        "vertical_drop": round(vertical_drop, 6),
        "frames": frames,
        "final": final_metrics,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "transform_cache": {
            "representation": "Bullet Simulation Points",
            "required_attributes": ["name", "P", "orient", "pivot", "scale", "v", "w"],
            "path": transform_cache_path,
            "write_implicit": False,
            "status": "configured_not_written",
            "files_written": [],
        },
        "selection": {
            "method": "human",
            "preview_input": spec["profile_index"],
            "winner": None,
            "automatic_ranking": False,
            "human_ratings": {
                profile: {"score": None, "notes": "", "selected": False}
                for profile in PROFILE_ORDER
            },
        },
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"artifact": str(output), **document}


__all__ = [
    "PROFILE_ORDER",
    "PROFILE_POINT_COUNTS",
    "PROFILE_SEED_OFFSETS",
    "cook_validate_rbd",
    "validate_rbd_spec",
]
