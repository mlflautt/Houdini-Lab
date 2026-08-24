"""Native Vellum membrane specification and exact temporal verification.

The module imports without Houdini. HOM only inspects and cooks the registered SOP graph; Grid,
Mountain, Vellum Constraints, Vellum Solver, and File Cache nodes perform the computation.
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
from .cook import geometry_metrics
from .execution import current_envelope

SCHEMA_VERSION = "1.0"
MEMBRANE_ORDER = ("silk", "rubber", "reinforced")
SEED_OFFSETS = {"silk": 0, "rubber": 101, "reinforced": 202}
COMPARISON_TX = {"silk": -3.2, "rubber": 0.0, "reinforced": 3.2}
MATERIAL_PROFILES = {
    "silk": {"stretch": (1.0, 5), "bend": (1.0, -3), "surface_struts": False},
    "rubber": {"stretch": (2.0, 4), "bend": (1.0, -1), "surface_struts": False},
    "reinforced": {"stretch": (1.0, 5), "bend": (1.0, -2), "surface_struts": True},
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


def validate_membrane_spec(
    *,
    seed: int,
    start_frame: int,
    end_frame: int,
    candidate_index: int,
    resolution: int,
    sheet_size: float,
    sheet_height: float,
    noise_height: float,
    mass: float,
    thickness: float,
    substeps: int,
    constraint_iterations: int,
    max_points: int = 75_000,
) -> dict[str, Any]:
    """Validate deterministic controls and conservative frame/topology ceilings."""
    seed = _integer(seed, "seed", minimum=0, maximum=2_147_483_445)
    start_frame = _integer(start_frame, "start_frame", minimum=1, maximum=100_000)
    end_frame = _integer(end_frame, "end_frame", minimum=1, maximum=100_000)
    if end_frame < start_frame:
        raise ValueError("end_frame must be >= start_frame")
    frame_count = end_frame - start_frame + 1
    if frame_count > 48:
        raise ValueError("Vellum membrane validation is limited to 48 inclusive frames")
    candidate_index = _integer(candidate_index, "candidate_index", minimum=0, maximum=2)
    resolution = _integer(resolution, "resolution", minimum=9, maximum=41)
    substeps = _integer(substeps, "substeps", minimum=1, maximum=5)
    constraint_iterations = _integer(
        constraint_iterations, "constraint_iterations", minimum=10, maximum=150
    )
    max_points = _integer(max_points, "max_points", minimum=1, maximum=75_000)
    point_count = resolution * resolution
    if point_count * len(MEMBRANE_ORDER) > max_points:
        raise ValueError("combined membrane points exceed max_points")
    return {
        "seed": seed,
        "candidate_seeds": {
            candidate: seed + SEED_OFFSETS[candidate] for candidate in MEMBRANE_ORDER
        },
        "candidate_order": list(MEMBRANE_ORDER),
        "candidate_index": candidate_index,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_count": frame_count,
        "resolution": resolution,
        "point_count_per_candidate": point_count,
        "sheet_size": _finite(sheet_size, "sheet_size", minimum=1.0, maximum=5.0),
        "sheet_height": _finite(sheet_height, "sheet_height", minimum=1.5, maximum=6.0),
        "noise_height": _finite(noise_height, "noise_height", minimum=0.0, maximum=0.12),
        "mass": _finite(mass, "mass", minimum=0.001, maximum=2.0),
        "thickness": _finite(thickness, "thickness", minimum=0.002, maximum=0.1),
        "substeps": substeps,
        "constraint_iterations": constraint_iterations,
        "max_points": max_points,
        "material_profiles": MATERIAL_PROFILES,
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
        raise ValueError(f"missing managed membrane node: {name}")
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


def _finite_bounds(metrics: dict[str, Any], label: str) -> None:
    bounds = metrics["bounds"]
    if bounds is None or any(
        not math.isfinite(float(value)) for vector in bounds for value in vector
    ):
        raise ValueError(f"{label} has non-finite bounds")


def _point_positions(geometry: Any) -> list[tuple[float, float, float]]:
    return [tuple(float(value) for value in point.position()) for point in geometry.points()]


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)))


def cook_validate_membranes(
    *,
    network_path: str,
    run_code: str,
    seed: int,
    start_frame: int,
    end_frame: int,
    candidate_index: int,
    resolution: int,
    sheet_size: float,
    sheet_height: float,
    noise_height: float,
    mass: float,
    thickness: float,
    substeps: int,
    constraint_iterations: int,
    cache_paths: dict[str, str],
    output_path: str,
    max_points: int = 75_000,
) -> dict[str, Any]:
    """Validate the exact graph and cook all membrane candidates across the requested range."""
    hou = get_hou()
    spec = validate_membrane_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        candidate_index=candidate_index,
        resolution=resolution,
        sheet_size=sheet_size,
        sheet_height=sheet_height,
        noise_height=noise_height,
        mass=mass,
        thickness=thickness,
        substeps=substeps,
        constraint_iterations=constraint_iterations,
        max_points=max_points,
    )
    network_path = _absolute_node_path(network_path, "network_path")
    if not isinstance(run_code, str) or not _RUN_CODE.fullmatch(run_code):
        raise ValueError("run_code must be a 1-32 character uppercase Houdini identifier")
    if not isinstance(cache_paths, dict) or set(cache_paths) != set(MEMBRANE_ORDER):
        raise ValueError("cache_paths must map exactly silk, rubber, and reinforced")
    network = hou.node(network_path)
    if network is None or network.type().category().name() != "Object":
        raise ValueError(f"SOP network not found: {network_path}")
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 90.0
    point_ceiling = min(spec["max_points"], int(policy.max_points) if policy else 75_000)
    primitive_ceiling = int(policy.max_primitives) if policy else 75_000

    grid = _require_node(network, f"{run_code}_MEMBRANE_GRID", "grid", "membrane_shared_grid")
    anchors = _require_node(
        network, f"{run_code}_ANCHOR_EDGE", "groupcreate", "membrane_anchor_group"
    )
    if anchors.input(0) != grid:
        raise ValueError("membrane anchor group is disconnected from the shared Grid")
    _assert_parameters(
        grid,
        {
            "orient": "zx",
            "sizex": spec["sheet_size"],
            "sizey": spec["sheet_size"],
            "rows": spec["resolution"],
            "cols": spec["resolution"],
            "ty": spec["sheet_height"],
        },
        "shared Grid",
    )
    _assert_parameters(
        anchors,
        {
            "groupname": "anchors",
            "grouptype": "point",
            "groupbase": 0,
            "groupbounding": 1,
            "boundtype": "usebbox",
            "tz": spec["sheet_size"] / 2.0,
        },
        "anchor Group Create",
    )

    collider = _require_node(
        network, f"OUT_{run_code}_COLLIDER", "null", "membrane_collider_contract"
    )
    collider_merge = collider.input(0)
    if (
        collider_merge is None
        or collider_merge.type().name() != "merge"
        or len(collider_merge.inputs()) != 2
        or [node.type().name() for node in collider_merge.inputs()] != ["sphere", "box"]
    ):
        raise ValueError("membrane collider must be the registered Sphere plus Box merge")
    collider.cook(force=True)
    collider_metrics = geometry_metrics(collider)
    _finite_bounds(collider_metrics, "membrane collider")

    branches: dict[str, dict[str, Any]] = {}
    constraint_counts: dict[str, int] = {}
    rest_positions: dict[str, list[tuple[float, float, float]]] = {}
    anchor_numbers: dict[str, list[int]] = {}
    for candidate in MEMBRANE_ORDER:
        upper = candidate.upper()
        profile = MATERIAL_PROFILES[candidate]
        nodes = {
            "noise": _require_node(
                network,
                f"{run_code}_{upper}_SEEDED_REST",
                "mountain::2.0",
                f"membrane_seeded_rest_{candidate}",
            ),
            "rest": _require_node(
                network,
                f"OUT_{run_code}_{upper}_REST",
                "null",
                f"membrane_rest_{candidate}",
            ),
            "cloth": _require_node(
                network,
                f"{run_code}_{upper}_CLOTH",
                "vellumconstraints",
                f"membrane_cloth_{candidate}",
            ),
            "pin": _require_node(
                network,
                f"{run_code}_{upper}_PIN",
                "vellumconstraints",
                f"membrane_pin_{candidate}",
            ),
            "constraints": _require_node(
                network,
                f"OUT_{run_code}_{upper}_CONSTRAINTS",
                "null",
                f"membrane_constraints_{candidate}",
            ),
            "solver": _require_node(
                network,
                f"{run_code}_{upper}_SOLVER",
                "vellumsolver",
                f"membrane_solver_{candidate}",
            ),
            "raw": _require_node(
                network,
                f"OUT_{run_code}_{upper}_SIM_RAW",
                "null",
                f"membrane_raw_{candidate}",
            ),
            "cache": _require_node(
                network,
                f"{run_code}_{upper}_FILE_CACHE",
                "filecache",
                f"membrane_cache_{candidate}",
            ),
            "out": _require_node(
                network,
                f"OUT_{run_code}_{upper}",
                "null",
                f"membrane_candidate_{candidate}",
            ),
        }
        terminal = nodes["pin"]
        if profile["surface_struts"]:
            nodes["struts"] = _require_node(
                network,
                f"{run_code}_REINFORCED_SURFACE_STRUTS",
                "vellumconstraints",
                "membrane_surface_struts_reinforced",
            )
            terminal = nodes["struts"]
            if list(terminal.inputs())[:2] != [nodes["pin"], nodes["pin"]]:
                raise ValueError("reinforced Surface Struts inputs are invalid")
            _assert_parameters(
                terminal,
                {
                    "constrainttype": "surfacestruts",
                    "strut_maxlen": 0.8,
                    "strut_constraintsperpt": 2,
                    "strut_jitter": 0.15,
                    "strut_seed": spec["candidate_seeds"][candidate],
                    "stretchstiffness": 1.0,
                    "stretchstiffnessexp": 4,
                },
                "reinforced Surface Struts",
            )
        if (
            nodes["noise"].input(0) != anchors
            or nodes["rest"].input(0) != nodes["noise"]
            or nodes["cloth"].input(0) != nodes["rest"]
            or list(nodes["pin"].inputs())[:2] != [nodes["cloth"], nodes["cloth"]]
            or nodes["constraints"].input(0) != terminal
            or list(nodes["solver"].inputs())[:3] != [terminal, nodes["constraints"], collider]
            or nodes["raw"].input(0) != nodes["solver"]
            or nodes["cache"].input(0) != nodes["raw"]
            or nodes["out"].input(0) != nodes["cache"]
        ):
            raise ValueError(f"candidate {candidate} graph chain is not registered")
        _assert_parameters(
            nodes["noise"],
            {
                "height": spec["noise_height"],
                "offsetx": spec["candidate_seeds"][candidate],
                "updatenmls": 0,
            },
            f"candidate {candidate} rest noise",
        )
        _assert_parameters(
            nodes["cloth"],
            {
                "constrainttype": "cloth",
                "domass": "on",
                "mass": spec["mass"],
                "dothickness": "on",
                "thickness": spec["thickness"],
                "stretchstiffness": profile["stretch"][0],
                "stretchstiffnessexp": profile["stretch"][1],
                "bendstiffness": profile["bend"][0],
                "bendstiffnessexp": profile["bend"][1],
            },
            f"candidate {candidate} Cloth",
        )
        _assert_parameters(
            nodes["pin"],
            {
                "constrainttype": "pin",
                "grouptype": "points",
                "group": "anchors",
                "pingroup": "",
                "pintype": "hard",
                "matchanimation": 0,
            },
            f"candidate {candidate} Pin",
        )
        _assert_parameters(
            nodes["solver"],
            {
                "startframe": spec["start_frame"],
                "simulationtype": "dynamic",
                "substeps": spec["substeps"],
                "niter": spec["constraint_iterations"],
                "enablecollisions": 1,
                "doselfcollisions": 1,
                "autoresim": 1,
            },
            f"candidate {candidate} Solver",
        )
        expected_cache = cache_paths[candidate]
        if not isinstance(expected_cache, str) or not Path(expected_cache).is_absolute():
            raise ValueError(f"cache_paths.{candidate} must be absolute")
        if (
            nodes["cache"].parm("file").unexpandedString() != expected_cache
            or nodes["cache"].parm("loadfromdisk").eval() != 0
            or nodes["cache"].parm("initsim").eval() != 1
        ):
            raise ValueError(f"candidate {candidate} cache boundary is invalid")

        rest_geometry = nodes["rest"].geometryAtFrame(start_frame)
        rest_metric = geometry_metrics(nodes["rest"])
        _finite_bounds(rest_metric, f"candidate {candidate} rest")
        if (
            rest_metric["points"] != spec["point_count_per_candidate"]
            or rest_metric["primitives"] != (resolution - 1) ** 2
        ):
            raise ValueError(f"candidate {candidate} rest topology is invalid")
        anchor_group = rest_geometry.findPointGroup("anchors")
        if anchor_group is None or len(anchor_group.points()) != resolution:
            raise ValueError(f"candidate {candidate} must retain exactly one anchored edge")
        rest_positions[candidate] = _point_positions(rest_geometry)
        anchor_numbers[candidate] = [point.number() for point in anchor_group.points()]

        source_geometry = terminal.geometryAtFrame(start_frame, output_index=0)
        masses = source_geometry.pointFloatAttribValues("mass")
        zero_mass = sum(_close(value, 0.0) for value in masses)
        dynamic_mass = sum(_close(value, spec["mass"]) for value in masses)
        if zero_mass != resolution or dynamic_mass != len(masses) - resolution:
            raise ValueError(f"candidate {candidate} pin mass contract is invalid")
        constraint_geometry = terminal.geometryAtFrame(start_frame, output_index=1)
        constraint_counts[candidate] = len(constraint_geometry.prims())
        required_prim_attribs = {"type", "stiffness", "dampingratio"}
        actual_prim_attribs = {attrib.name() for attrib in constraint_geometry.primAttribs()}
        if (
            constraint_counts[candidate] <= rest_metric["points"]
            or constraint_counts[candidate] > primitive_ceiling
            or not required_prim_attribs <= actual_prim_attribs
        ):
            raise ValueError(f"candidate {candidate} constraint geometry is invalid")
        messages = _messages(list(nodes.values()))
        if messages:
            raise ValueError(f"candidate {candidate} has Houdini messages: {'; '.join(messages)}")
        branches[candidate] = nodes

    if not (
        constraint_counts["reinforced"]
        > max(constraint_counts["silk"], constraint_counts["rubber"]) * 1.2
    ):
        raise ValueError("reinforced membrane did not add a material Surface Struts layer")

    outputs = [branches[candidate]["out"] for candidate in MEMBRANE_ORDER]
    selector = _require_node(
        network, f"{run_code}_SELECT_MEMBRANE", "switch", "membrane_human_selector"
    )
    selected = _require_node(
        network, f"OUT_{run_code}_SELECTED", "null", "membrane_selected_contract"
    )
    compare = _require_node(
        network, f"OUT_{run_code}_COMPARE", "null", "membrane_comparison_contract"
    )
    if selector.parm("input").eval() != candidate_index or list(selector.inputs())[:3] != outputs:
        raise ValueError("membrane human selector contract is invalid")
    if selected.input(0) != selector:
        raise ValueError("selected membrane output is disconnected")
    frame_transform = compare.input(0)
    if (
        frame_transform is None
        or frame_transform.type().name() != "xform"
        or frame_transform.userData("hermes_role") != "membrane_comparison_frame"
        or not _close(frame_transform.parm("ty").eval(), -0.7)
        or not _close(frame_transform.parm("scale").eval(), 0.58)
    ):
        raise ValueError("membrane comparison framing contract is invalid")
    comparison_merge = frame_transform.input(0)
    if comparison_merge is None or comparison_merge.type().name() != "merge":
        raise ValueError("membrane comparison Merge is missing")
    comparison_inputs = list(comparison_merge.inputs())
    if len(comparison_inputs) != 3:
        raise ValueError("membrane comparison requires exactly three inputs")
    for candidate, transform, output in zip(
        MEMBRANE_ORDER, comparison_inputs, outputs, strict=True
    ):
        if (
            transform is None
            or transform.type().name() != "xform"
            or transform.input(0) != output
            or transform.userData("hermes_role") != f"membrane_compare_{candidate}"
            or not _close(transform.parm("tx").eval(), COMPARISON_TX[candidate])
        ):
            raise ValueError(f"membrane comparison placement is invalid for {candidate}")
    labels = _require_node(network, f"OUT_{run_code}_LABELS", "merge", "membrane_labels_contract")
    if len(labels.inputs()) != 3 or labels in compare.inputAncestors():
        raise ValueError("membrane labels must be a separate three-input contract")

    output = _prepare_new_json(output_path)
    original_frame = hou.frame()
    started = time.monotonic()
    frames: list[dict[str, Any]] = []
    final_geometries: dict[str, Any] = {}
    try:
        for frame in range(start_frame, end_frame + 1):
            hou.setFrame(frame)
            candidates = []
            total_points = 0
            total_primitives = 0
            for candidate in MEMBRANE_ORDER:
                branch = branches[candidate]
                branch["out"].cook(force=True)
                messages = _messages(list(branch.values()))
                if messages:
                    raise ValueError(
                        f"candidate {candidate} frame {frame} has Houdini messages: "
                        + "; ".join(messages)
                    )
                metrics = geometry_metrics(branch["out"])
                _finite_bounds(metrics, f"candidate {candidate} frame {frame}")
                if metrics["points"] > point_ceiling or metrics["primitives"] > primitive_ceiling:
                    raise ValueError(f"candidate {candidate} frame {frame} exceeds topology policy")
                total_points += metrics["points"]
                total_primitives += metrics["primitives"]
                geometry = branch["out"].geometry()
                positions = _point_positions(geometry)
                centroid = [
                    sum(point[axis] for point in positions) / len(positions) for axis in range(3)
                ]
                candidates.append(
                    {
                        "id": candidate,
                        "seed": spec["candidate_seeds"][candidate],
                        "metrics": metrics,
                        "centroid": [round(value, 6) for value in centroid],
                        "cook_seconds": round(float(branch["out"].lastCookTime()), 6),
                    }
                )
                if frame == end_frame:
                    final_geometries[candidate] = geometry.freeze()
            if total_points > point_ceiling or total_primitives > primitive_ceiling:
                raise ValueError(f"frame {frame} combined topology exceeds policy")
            frames.append(
                {
                    "frame": frame,
                    "points": total_points,
                    "primitives": total_primitives,
                    "candidates": candidates,
                }
            )
            if time.monotonic() - started > max_seconds:
                raise TimeoutError("Vellum membrane validation exceeded policy.max_seconds")
        selected.cook(force=True)
        compare.cook(force=True)
        selected_metrics = geometry_metrics(selected)
        comparison_metrics = geometry_metrics(compare)
    finally:
        hou.setFrame(original_frame)

    final_checks: dict[str, Any] = {}
    centroids = []
    for candidate in MEMBRANE_ORDER:
        final_geometry = final_geometries[candidate]
        final_positions = _point_positions(final_geometry)
        rest = rest_positions[candidate]
        anchored_drift = max(
            _distance(final_positions[number], rest[number]) for number in anchor_numbers[candidate]
        )
        dynamic_numbers = set(range(len(final_positions))).difference(anchor_numbers[candidate])
        mean_dynamic_displacement = sum(
            _distance(final_positions[number], rest[number]) for number in dynamic_numbers
        ) / len(dynamic_numbers)
        if anchored_drift > 0.02:
            raise ValueError(f"candidate {candidate} anchored edge drifted")
        if mean_dynamic_displacement < 0.25:
            raise ValueError(
                f"candidate {candidate} did not produce a dynamic membrane deformation"
            )
        centroid = tuple(
            sum(point[axis] for point in final_positions) / len(final_positions)
            for axis in range(3)
        )
        centroids.append(centroid)
        final_checks[candidate] = {
            "anchored_max_drift": round(anchored_drift, 8),
            "mean_dynamic_displacement": round(mean_dynamic_displacement, 6),
            "constraint_primitives": constraint_counts[candidate],
        }
    if (
        min(
            _distance(left, right)
            for index, left in enumerate(centroids)
            for right in centroids[index + 1 :]
        )
        < 0.005
    ):
        raise ValueError("final membrane material candidates are not spatially distinct")
    chosen = frames[-1]["candidates"][candidate_index]["metrics"]
    if (
        selected_metrics["points"] != chosen["points"]
        or selected_metrics["primitives"] != chosen["primitives"]
    ):
        raise ValueError("selected membrane output does not match the human Switch")
    if comparison_metrics["points"] != sum(
        item["metrics"]["points"] for item in frames[-1]["candidates"]
    ):
        raise ValueError("membrane comparison does not preserve all three candidates")

    document = {
        "schema": "hermes.houdini.vellum_membrane_validation",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "status": "success",
        "network_path": network_path,
        "run_code": run_code,
        "spec": spec,
        "collider": collider_metrics,
        "frames": frames,
        "final_checks": final_checks,
        "selected": selected_metrics,
        "comparison": comparison_metrics,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "cache": {
            "write_implicit": False,
            "status": "configured_not_written",
            "paths": cache_paths,
        },
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
            "human_ratings": {
                candidate: {"score": None, "notes": "", "selected": False}
                for candidate in MEMBRANE_ORDER
            },
        },
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"artifact": str(output), **document}


__all__ = [
    "COMPARISON_TX",
    "MATERIAL_PROFILES",
    "MEMBRANE_ORDER",
    "SEED_OFFSETS",
    "cook_validate_membranes",
    "validate_membrane_spec",
]
