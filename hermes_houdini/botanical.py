"""Bounded native L-System botanical grammar validation.

Pure grammar/spec validation imports without Houdini. HOM execution verifies and cooks only the
registered native SOP graph; the L-System and PolyWire nodes perform all geometry computation.
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
BOTANICAL_ORDER = ("canopy", "fern", "coral")
BOTANICAL_COMPARISON_TX = {"canopy": -2.0, "fern": 0.0, "coral": 2.0}
BOTANICAL_GRAMMARS = {
    "canopy": {
        "premise": 'a("Cd",0.12,0.65,0.22)F(0.8)A',
        "rules": ("A=F[+A][-A][/&A]",),
        "angle": 24.0,
        "step_size": 0.22,
        "step_scale": 0.82,
        "random_scale": 0.06,
        "thickness": 1.0,
        "thickness_scale": 0.82,
        "seed_offset": 0,
    },
    "fern": {
        "premise": 'a("Cd",0.10,0.35,0.08)X',
        "rules": ("X=F[+X]F[-X]+X", "F=FF"),
        "angle": 22.5,
        "step_size": 0.025,
        "step_scale": 0.78,
        "random_scale": 0.06,
        "thickness": 1.0,
        "thickness_scale": 0.78,
        "seed_offset": 101,
    },
    "coral": {
        "premise": 'a("Cd",0.75,0.25,0.12)A',
        "rules": ("A=F[+A][-A][&A][^A][/A]",),
        "angle": 28.0,
        "step_size": 0.3,
        "step_scale": 0.76,
        "random_scale": 0.06,
        "thickness": 1.0,
        "thickness_scale": 0.76,
        "seed_offset": 211,
    },
}
_ABS_NODE_PATH = re.compile(r"/(?:[A-Za-z0-9_.-]+)(?:/[A-Za-z0-9_.-]+)*\Z")


def _integer(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return value


def _fern_segments(generations: int) -> int:
    drawn_segments = 0
    nonterminals = 1
    for _ in range(generations):
        drawn_segments = (2 * drawn_segments) + (2 * nonterminals)
        nonterminals *= 3
    return drawn_segments


def validate_botanical_spec(
    *,
    generations: int,
    seed: int,
    candidate_index: int,
    wire_radius: float,
) -> dict[str, Any]:
    """Validate public controls and return conservative topology estimates."""
    generations = _integer(generations, "generations", minimum=1, maximum=6)
    seed = _integer(seed, "seed", minimum=0, maximum=2_147_483_436)
    candidate_index = _integer(candidate_index, "candidate_index", minimum=0, maximum=2)
    if (
        not isinstance(wire_radius, (int, float))
        or isinstance(wire_radius, bool)
        or not math.isfinite(wire_radius)
        or not 0.002 <= float(wire_radius) <= 0.06
    ):
        raise ValueError("wire_radius must be a finite number between 0.002 and 0.06")

    canopy_segments = sum(3**index for index in range(generations)) + 1
    fern_segments = _fern_segments(generations)
    coral_segments = sum(5**index for index in range(generations))
    skeleton_segments = {
        "canopy": canopy_segments,
        "fern": fern_segments,
        "coral": coral_segments,
    }
    estimated_wire_points = 12 * sum(skeleton_segments.values())
    estimated_wire_primitives = 24 * sum(skeleton_segments.values())
    if estimated_wire_points > 250_000 or estimated_wire_primitives > 250_000:
        raise ValueError("botanical proxy estimate exceeds the 250000 topology ceiling")
    return {
        "generations": generations,
        "seed": seed,
        "candidate_index": candidate_index,
        "wire_radius": float(wire_radius),
        "candidate_order": list(BOTANICAL_ORDER),
        "candidate_seeds": {
            grammar_id: seed + int(BOTANICAL_GRAMMARS[grammar_id]["seed_offset"])
            for grammar_id in BOTANICAL_ORDER
        },
        "estimated_skeleton_segments": skeleton_segments,
        "estimated_wire_points": estimated_wire_points,
        "estimated_wire_primitives": estimated_wire_primitives,
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


def _record(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "hermes.houdini.botanical_validation",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        **payload,
    }


def _node_messages(node: Any) -> tuple[list[str], list[str]]:
    return ([str(item) for item in node.errors()], [str(item) for item in node.warnings()])


def _validate_lsystem_contract(node: Any, grammar_id: str, spec: dict[str, Any]) -> None:
    grammar = BOTANICAL_GRAMMARS[grammar_id]
    if node.type().category().name() != "Sop" or node.type().name() != "lsystem":
        raise ValueError(f"candidate {grammar_id} is not an exact L-System SOP")
    if node.userData("hermes_role") != f"botanical_skeleton_{grammar_id}":
        raise ValueError(f"candidate {grammar_id} role is not managed")
    exact_values = {
        "type": 0,
        "generations": spec["generations"],
        "randseed": spec["candidate_seeds"][grammar_id],
        "pointwidth": 1,
        "usefile": 0,
        "premise": grammar["premise"],
        "numrules": len(grammar["rules"]),
    }
    for parm_name, expected in exact_values.items():
        actual = node.parm(parm_name).eval()
        if actual != expected:
            raise ValueError(f"candidate {grammar_id} has unregistered {parm_name}")
    numeric_values = {
        "randscale": grammar["random_scale"],
        "stepinit": grammar["step_size"],
        "stepscale": grammar["step_scale"],
        "angleinit": grammar["angle"],
        "thickinit": grammar["thickness"],
        "thickscale": grammar["thickness_scale"],
    }
    for parm_name, expected in numeric_values.items():
        if not math.isclose(float(node.parm(parm_name).eval()), float(expected), abs_tol=1e-6):
            raise ValueError(f"candidate {grammar_id} has unregistered {parm_name}")
    for index, expected_rule in enumerate(grammar["rules"], 1):
        if node.parm(f"userule{index}").eval() != 1:
            raise ValueError(f"candidate {grammar_id} disables registered rule {index}")
        if node.parm(f"rule{index}").evalAsString() != expected_rule:
            raise ValueError(f"candidate {grammar_id} has unregistered rule {index}")


def _cook_metrics(node: Any, *, required_attributes: set[str]) -> dict[str, Any]:
    node.cook(force=True)
    metrics = {"path": node.path(), **geometry_metrics(node)}
    errors, warnings = _node_messages(node)
    metrics["node_errors"] = errors
    metrics["node_warnings"] = warnings
    if errors or warnings:
        raise ValueError(f"node {node.path()} has Houdini messages")
    if metrics["points"] < 2 or metrics["primitives"] < 1:
        raise ValueError(f"node {node.path()} produced empty geometry")
    bounds = metrics["bounds"]
    if bounds is None or any(
        not math.isfinite(float(value)) for vector in bounds for value in vector
    ):
        raise ValueError(f"node {node.path()} has non-finite bounds")
    missing = required_attributes.difference(metrics["point_attributes"])
    if missing:
        raise ValueError(f"node {node.path()} is missing point attributes: {sorted(missing)}")
    return metrics


def cook_validate_botanical(
    *,
    network_path: str,
    skeleton_node_paths: list[str],
    wire_node_paths: list[str],
    selected_path: str,
    compare_path: str,
    generations: int,
    seed: int,
    candidate_index: int,
    wire_radius: float,
    output_path: str,
) -> dict[str, Any]:
    """Cook and validate one registered three-candidate native botanical graph."""
    hou = get_hou()
    spec = validate_botanical_spec(
        generations=generations,
        seed=seed,
        candidate_index=candidate_index,
        wire_radius=wire_radius,
    )
    network_path = _absolute_node_path(network_path, "network_path")
    if not isinstance(skeleton_node_paths, list) or len(skeleton_node_paths) != 3:
        raise ValueError("skeleton_node_paths must contain exactly three nodes")
    if not isinstance(wire_node_paths, list) or len(wire_node_paths) != 3:
        raise ValueError("wire_node_paths must contain exactly three nodes")
    skeleton_paths = [
        _absolute_node_path(path, f"skeleton_node_paths[{index}]")
        for index, path in enumerate(skeleton_node_paths)
    ]
    wire_paths = [
        _absolute_node_path(path, f"wire_node_paths[{index}]")
        for index, path in enumerate(wire_node_paths)
    ]
    selected_path = _absolute_node_path(selected_path, "selected_path")
    compare_path = _absolute_node_path(compare_path, "compare_path")
    network = hou.node(network_path)
    if network is None or network.type().category().name() != "Object":
        raise ValueError(f"SOP network not found: {network_path}")

    skeletons = []
    wires = []
    for index, grammar_id in enumerate(BOTANICAL_ORDER):
        skeleton = hou.node(skeleton_paths[index])
        wire = hou.node(wire_paths[index])
        if (
            skeleton is None
            or wire is None
            or skeleton.parent() != network
            or wire.parent() != network
        ):
            raise ValueError(f"candidate {grammar_id} is not inside {network_path}")
        _validate_lsystem_contract(skeleton, grammar_id, spec)
        if wire.type().name() != "null" or wire.userData("hermes_role") != (
            f"botanical_wire_contract_{grammar_id}"
        ):
            raise ValueError(f"candidate {grammar_id} wire contract is not managed")
        polywire = wire.input(0)
        if (
            polywire is None
            or polywire.type().name() != "polywire"
            or polywire.input(0) != skeleton
            or polywire.userData("hermes_role") != f"botanical_polywire_{grammar_id}"
        ):
            raise ValueError(f"candidate {grammar_id} does not use the registered PolyWire stage")
        if not math.isclose(
            float(polywire.parm("radius").eval()), spec["wire_radius"], abs_tol=1e-6
        ):
            raise ValueError(f"candidate {grammar_id} has unregistered wire radius")
        if (
            polywire.parm("div").eval() != 3
            or polywire.parm("scaleattrib").evalAsString() != "width"
        ):
            raise ValueError(f"candidate {grammar_id} has unregistered PolyWire controls")
        skeletons.append(skeleton)
        wires.append(wire)

    selected = hou.node(selected_path)
    compare = hou.node(compare_path)
    if (
        selected is None
        or selected.userData("hermes_role") != "botanical_selected_contract"
        or selected.type().name() != "null"
    ):
        raise ValueError("selected_path is not the managed botanical selection contract")
    selector = selected.input(0)
    if (
        selector is None
        or selector.type().name() != "switch"
        or selector.userData("hermes_role") != "human_botanical_selector"
        or selector.parm("input").eval() != candidate_index
        or list(selector.inputs())[:3] != wires
    ):
        raise ValueError("botanical human selector contract is invalid")
    if (
        compare is None
        or compare.userData("hermes_role") != "botanical_compare_contract"
        or compare.type().name() != "null"
        or compare.input(0) is None
        or compare.input(0).type().name() != "xform"
        or compare.input(0).userData("hermes_role") != "botanical_compare_frame"
    ):
        raise ValueError("compare_path is not the managed botanical comparison contract")
    compare_frame = compare.input(0)
    if not math.isclose(float(compare_frame.parm("ty").eval()), -0.2, abs_tol=1e-6) or not (
        math.isclose(float(compare_frame.parm("scale").eval()), 0.72, abs_tol=1e-6)
    ):
        raise ValueError("botanical comparison framing transform is unregistered")
    compare_merge = compare_frame.input(0)
    if compare_merge is None or compare_merge.type().name() != "merge":
        raise ValueError("botanical comparison framing transform is not connected to Merge")
    comparison_inputs = list(compare_merge.inputs())[:3]
    if len(comparison_inputs) != 3 or any(node is None for node in comparison_inputs):
        raise ValueError("botanical comparison requires exactly three connected inputs")
    if [node.userData("hermes_role") for node in comparison_inputs] != [
        f"botanical_compare_transform_{grammar_id}" for grammar_id in BOTANICAL_ORDER
    ] or [node.input(0) for node in comparison_inputs] != wires:
        raise ValueError("botanical comparison order is not canopy, fern, coral")
    for grammar_id, transform in zip(BOTANICAL_ORDER, comparison_inputs, strict=True):
        if not math.isclose(
            float(transform.parm("tx").eval()), BOTANICAL_COMPARISON_TX[grammar_id], abs_tol=1e-6
        ):
            raise ValueError(f"candidate {grammar_id} has unregistered comparison placement")

    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 90.0
    max_points = int(policy.max_points) if policy else 250_000
    max_primitives = int(policy.max_primitives) if policy else 250_000
    max_memory = int(policy.max_memory_bytes) if policy else 536_870_912
    output = _prepare_new_json(output_path)
    started = time.monotonic()
    skeleton_metrics = []
    wire_metrics = []
    for grammar_id, skeleton, wire in zip(BOTANICAL_ORDER, skeletons, wires, strict=True):
        skeleton_data = _cook_metrics(
            skeleton,
            required_attributes={"P", "Cd", "width", "arc", "gen", "up"},
        )
        geometry = skeleton.geometry()
        generation_values = geometry.pointFloatAttribValues("gen")
        arc_values = geometry.pointFloatAttribValues("arc")
        skeleton_data.update(
            {
                "candidate_id": grammar_id,
                "candidate_seed": spec["candidate_seeds"][grammar_id],
                "generation_range": [min(generation_values), max(generation_values)],
                "arc_range": [min(arc_values), max(arc_values)],
                "seconds": round(float(skeleton.lastCookTime()), 6),
            }
        )
        wire_data = _cook_metrics(wire, required_attributes={"P", "Cd"})
        wire_data.update(
            {
                "candidate_id": grammar_id,
                "seconds": round(float(wire.lastCookTime()), 6),
            }
        )
        skeleton_metrics.append(skeleton_data)
        wire_metrics.append(wire_data)
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("botanical validation exceeded policy.max_seconds")

    selected_metrics = _cook_metrics(selected, required_attributes={"P", "Cd"})
    compare_metrics = _cook_metrics(compare, required_attributes={"P", "Cd"})
    observed_points = sum(item["points"] for item in wire_metrics)
    observed_primitives = sum(item["primitives"] for item in wire_metrics)
    observed_memory = sum(item["memory_bytes"] for item in skeleton_metrics + wire_metrics)
    if (
        observed_points > max_points
        or selected_metrics["points"] > max_points
        or compare_metrics["points"] > max_points
    ):
        raise ValueError("botanical wire points exceed policy.max_points")
    if (
        observed_primitives > max_primitives
        or selected_metrics["primitives"] > max_primitives
        or compare_metrics["primitives"] > max_primitives
    ):
        raise ValueError("botanical wire primitives exceed policy.max_primitives")
    if observed_memory > max_memory:
        raise ValueError("botanical geometry memory exceeds policy.max_memory_bytes")
    topology = {(item["points"], item["primitives"]) for item in skeleton_metrics}
    if len(topology) != 3:
        raise ValueError("registered botanical candidates are not topologically distinct")
    elapsed = time.monotonic() - started
    if elapsed > max_seconds:
        raise TimeoutError("botanical validation exceeded policy.max_seconds")

    document = _record(
        {
            "status": "success",
            "network_path": network_path,
            "spec": spec,
            "skeletons": skeleton_metrics,
            "wires": wire_metrics,
            "selected": selected_metrics,
            "comparison": compare_metrics,
            "observed_wire_points": observed_points,
            "observed_wire_primitives": observed_primitives,
            "observed_memory_bytes": observed_memory,
            "elapsed_seconds": round(elapsed, 6),
            "selection": {
                "method": "human",
                "preview_input": candidate_index,
                "winner": None,
                "automatic_ranking": False,
            },
        }
    )
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"artifact": str(output), **document}


__all__ = [
    "BOTANICAL_GRAMMARS",
    "BOTANICAL_COMPARISON_TX",
    "BOTANICAL_ORDER",
    "cook_validate_botanical",
    "validate_botanical_spec",
]
