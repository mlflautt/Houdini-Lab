"""Bounded native particle-calligraphy contracts and temporal verification.

Pure specification and baked-envelope validation import without Houdini. HOM execution only
checks and cooks the registered graph; Particle, Time Blend, Particle Trail, Time Shift, and
PolyWire perform the geometry computation.
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
from .schemas.command import ChangedNode, Status, ToolResult
from .transactions import save_checkpoint

SCHEMA_VERSION = "1.0"
CALLIGRAPHY_ORDER = ("arc", "fan", "orbit")
SEED_OFFSETS = {"arc": 0, "fan": 101, "orbit": 211}
COMPARISON_TX = {"arc": -3.0, "fan": 0.0, "orbit": 3.0}
COMPARISON_TY = {"arc": 0.0, "fan": 0.0, "orbit": 0.6}
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


def validate_calligraphy_spec(
    *,
    seed: int,
    start_frame: int,
    end_frame: int,
    candidate_index: int,
    birth_rate: float,
    particle_life: float,
    trail_frames: float,
    trail_substeps: int,
    wire_radius: float,
    max_trail_points: int = 100_000,
) -> dict[str, Any]:
    """Validate the public deterministic controls and temporal/resource ceilings."""
    seed = _integer(seed, "seed", minimum=0, maximum=2_147_483_436)
    start_frame = _integer(start_frame, "start_frame", minimum=-100_000, maximum=100_000)
    end_frame = _integer(end_frame, "end_frame", minimum=-100_000, maximum=100_000)
    if end_frame < start_frame:
        raise ValueError("end_frame must be >= start_frame")
    frame_count = end_frame - start_frame + 1
    if frame_count > 48:
        raise ValueError("particle calligraphy is limited to 48 inclusive frames")
    candidate_index = _integer(candidate_index, "candidate_index", minimum=0, maximum=2)
    trail_substeps = _integer(trail_substeps, "trail_substeps", minimum=2, maximum=8)
    max_trail_points = _integer(max_trail_points, "max_trail_points", minimum=1, maximum=100_000)
    return {
        "seed": seed,
        "candidate_seeds": {
            candidate_id: seed + offset for candidate_id, offset in SEED_OFFSETS.items()
        },
        "start_frame": start_frame,
        "end_frame": end_frame,
        "frame_count": frame_count,
        "candidate_index": candidate_index,
        "birth_rate": _finite(birth_rate, "birth_rate", minimum=1.0, maximum=64.0),
        "particle_life": _finite(particle_life, "particle_life", minimum=0.25, maximum=8.0),
        "trail_frames": _finite(trail_frames, "trail_frames", minimum=1.0, maximum=24.0),
        "trail_substeps": trail_substeps,
        "wire_radius": _finite(wire_radius, "wire_radius", minimum=0.002, maximum=0.06),
        "max_trail_points": max_trail_points,
        "candidate_order": list(CALLIGRAPHY_ORDER),
        "integer_frame_compatibility": {
            "node": "Time Shift SOP",
            "integerframe": False,
            "expression": "$FF - 0.5",
            "reason": "Houdini 22 legacy Particle SOP produces valid Particle Trail output at intervening half-frames",
        },
    }


def load_baked_audio_envelope(
    *, project_root: str, relative_path: str, maximum_samples: int = 48
) -> dict[str, Any]:
    """Load a project-relative, finite zero-to-one envelope without touching Houdini."""
    root = Path(project_root).expanduser().resolve()
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("project_root must resolve to an existing absolute directory")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".json":
        raise ValueError("relative_path must be a project-relative .json path without traversal")
    path = (root / relative).resolve()
    if root not in path.parents:
        raise ValueError("audio envelope resolves outside project_root")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"schema", "fps", "samples"}:
        raise ValueError("audio envelope must contain exactly schema, fps, and samples")
    if payload["schema"] != "hermes.audio_envelope.v1":
        raise ValueError("unsupported audio envelope schema")
    fps = _finite(payload["fps"], "audio envelope fps", minimum=1.0, maximum=240.0)
    samples = payload["samples"]
    if not isinstance(samples, list) or not 1 <= len(samples) <= maximum_samples:
        raise ValueError(f"audio envelope samples must contain 1-{maximum_samples} values")
    normalized = [
        _finite(value, f"audio envelope samples[{index}]", minimum=0.0, maximum=1.0)
        for index, value in enumerate(samples)
    ]
    return {
        "path": str(path),
        "relative_path": relative.as_posix(),
        "schema": payload["schema"],
        "fps": fps,
        "samples": normalized,
    }


def _append_jsonl(path: str, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def apply_baked_audio_envelope(
    *,
    project_root: str,
    relative_path: str,
    particle_paths: list[str],
    start_frame: int,
    modulation_depth: float,
    checkpoint_dir: str,
    log_path: str,
) -> ToolResult:
    """Checkpoint, then keyframe native Particle wind controls from bounded baked data."""
    hou = get_hou()
    envelope = load_baked_audio_envelope(
        project_root=project_root, relative_path=relative_path, maximum_samples=48
    )
    start_frame = _integer(start_frame, "start_frame", minimum=-100_000, maximum=100_000)
    depth = _finite(modulation_depth, "modulation_depth", minimum=0.0, maximum=1.0)
    if not isinstance(particle_paths, list) or len(particle_paths) != 3:
        raise ValueError("particle_paths must contain exactly three native Particle SOPs")
    if not math.isclose(float(envelope["fps"]), float(hou.fps()), abs_tol=1e-6):
        raise ValueError("audio envelope fps must match the current Houdini scene fps")
    particles = []
    for index, path in enumerate(particle_paths):
        path = _absolute_node_path(path, f"particle_paths[{index}]")
        node = hou.node(path)
        if (
            node is None
            or node.type().category().name() != "Sop"
            or node.type().name() != "particle"
            or node.userData("hermes_role") != f"calligraphy_particles_{CALLIGRAPHY_ORDER[index]}"
        ):
            raise ValueError(f"particle_paths[{index}] is not the registered calligraphy branch")
        particles.append(node)
    tracked = [node.parm(name) for node in particles for name in ("windx", "windy", "windz")]
    if any(parm.keyframes() for parm in tracked):
        raise ValueError("refusing to replace existing authored wind animation")
    old_values = [parm.eval() for parm in tracked]
    checkpoint = save_checkpoint(checkpoint_dir, "calligraphy_audio_envelope")
    result = ToolResult(status=Status.SUCCESS, checkpoint=checkpoint)
    try:
        with hou.undos.group("Hermes apply baked calligraphy audio envelope"):
            for particle in particles:
                for parm_name in ("windx", "windy", "windz"):
                    parm = particle.parm(parm_name)
                    base_value = float(parm.eval())
                    keys = []
                    for index, sample in enumerate(envelope["samples"]):
                        key = hou.Keyframe()
                        key.setFrame(start_frame + index)
                        multiplier = 1.0 + (depth * (sample - 0.5))
                        key.setValue(base_value * multiplier)
                        keys.append(key)
                    parm.setKeyframes(keys)
        record = {
            "schema": "hermes.houdini.calligraphy_audio_envelope",
            "schema_version": SCHEMA_VERSION,
            "timestamp_unix": time.time(),
            "status": "success",
            "checkpoint": checkpoint,
            "envelope": {
                "relative_path": envelope["relative_path"],
                "fps": envelope["fps"],
                "samples": len(envelope["samples"]),
                "modulation_depth": depth,
            },
            "particle_paths": [node.path() for node in particles],
            "parameters": ["windx", "windy", "windz"],
        }
        _append_jsonl(log_path, record)
        result.changed_nodes = [
            ChangedNode(
                hermes_id=node.userData("hermes_id") or "",
                path=node.path(),
                change="modified",
            )
            for node in particles
        ]
        result.artifacts = [log_path]
        result.data = record
        return result
    except Exception as exc:
        for parm, old_value in zip(tracked, old_values, strict=True):
            parm.deleteAllKeyframes()
            parm.set(old_value)
        result.status = Status.ERROR
        result.errors.append(f"{type(exc).__name__}: {exc}")
        result.data = {"rolled_back": True}
        try:
            _append_jsonl(
                log_path,
                {
                    "schema": "hermes.houdini.calligraphy_audio_envelope",
                    "schema_version": SCHEMA_VERSION,
                    "timestamp_unix": time.time(),
                    "status": "rolled_back",
                    "checkpoint": checkpoint,
                    "error": result.errors[0],
                },
            )
            result.artifacts = [log_path]
        except Exception as log_exc:
            result.status = Status.PARTIAL
            result.errors.append(f"provenance failure: {log_exc}")
        return result


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
        raise ValueError(f"missing managed calligraphy node: {name}")
    if node.type().category().name() != "Sop" or node.type().name() != operator_type:
        raise ValueError(f"{name} must be exact Sop/{operator_type}")
    if node.userData("hermes_role") != role:
        raise ValueError(f"{name} has an invalid managed role")
    return node


def _node_messages(nodes: list[Any]) -> tuple[list[str], list[str]]:
    errors = [f"{node.path()}: {item}" for node in nodes for item in node.errors()]
    warnings = [f"{node.path()}: {item}" for node in nodes for item in node.warnings()]
    return errors, warnings


def _finite_bounds(metrics: dict[str, Any], label: str) -> None:
    bounds = metrics["bounds"]
    if bounds is None or any(
        not math.isfinite(float(value)) for vector in bounds for value in vector
    ):
        raise ValueError(f"{label} has non-finite bounds")


def cook_validate_calligraphy(
    *,
    network_path: str,
    run_code: str,
    seed: int,
    start_frame: int,
    end_frame: int,
    candidate_index: int,
    birth_rate: float,
    particle_life: float,
    trail_frames: float,
    trail_substeps: int,
    wire_radius: float,
    output_path: str,
    max_trail_points: int = 100_000,
    audio_envelope_relative_path: str = "",
) -> dict[str, Any]:
    """Cook every requested integer frame and validate the registered native graph."""
    hou = get_hou()
    spec = validate_calligraphy_spec(
        seed=seed,
        start_frame=start_frame,
        end_frame=end_frame,
        candidate_index=candidate_index,
        birth_rate=birth_rate,
        particle_life=particle_life,
        trail_frames=trail_frames,
        trail_substeps=trail_substeps,
        wire_radius=wire_radius,
        max_trail_points=max_trail_points,
    )
    network_path = _absolute_node_path(network_path, "network_path")
    if not isinstance(run_code, str) or not _RUN_CODE.fullmatch(run_code):
        raise ValueError("run_code must be a 1-32 character uppercase Houdini identifier")
    if not isinstance(audio_envelope_relative_path, str):
        raise ValueError("audio_envelope_relative_path must be a string")
    network = hou.node(network_path)
    if network is None or network.type().category().name() != "Object":
        raise ValueError(f"SOP network not found: {network_path}")

    emitter = _require_node(network, f"{run_code}_EMITTER", "circle", "calligraphy_emitter")
    if (
        emitter.parm("divs").eval() != 12
        or emitter.parm("type").evalAsString() != "poly"
        or emitter.parm("orient").evalAsString() != "zx"
    ):
        raise ValueError("calligraphy emitter is not the registered twelve-point ZX polygon")
    branches: dict[str, dict[str, Any]] = {}
    for candidate_id in CALLIGRAPHY_ORDER:
        upper = candidate_id.upper()
        nodes = {
            "particle": _require_node(
                network,
                f"{run_code}_{upper}_PARTICLES",
                "particle",
                f"calligraphy_particles_{candidate_id}",
            ),
            "points": _require_node(
                network,
                f"{run_code}_{upper}_PARTICLES_ONLY",
                "add",
                f"calligraphy_points_{candidate_id}",
            ),
            "extract": _require_node(
                network,
                f"{run_code}_{upper}_EXTRACT_AGE",
                "attribcreate::2.0",
                f"calligraphy_age_extract_{candidate_id}",
            ),
            "lifespan": _require_node(
                network,
                f"{run_code}_{upper}_EXTRACT_LIFESPAN",
                "attribcreate::2.0",
                f"calligraphy_lifespan_extract_{candidate_id}",
            ),
            "drop": _require_node(
                network,
                f"{run_code}_{upper}_DROP_LEGACY_LIFE",
                "attribdelete",
                f"calligraphy_life_cleanup_{candidate_id}",
            ),
            "scalar": _require_node(
                network,
                f"{run_code}_{upper}_SCALAR_LIFE",
                "attribcreate::2.0",
                f"calligraphy_life_scalar_{candidate_id}",
            ),
            "blend": _require_node(
                network,
                f"{run_code}_{upper}_TIME_BLEND",
                "timeblend::2.0",
                f"calligraphy_time_blend_{candidate_id}",
            ),
            "trail": _require_node(
                network,
                f"{run_code}_{upper}_PARTICLE_TRAIL",
                "particletrail",
                f"calligraphy_particle_trail_{candidate_id}",
            ),
            "compat": _require_node(
                network,
                f"OUT_{run_code}_{upper}_TRAIL",
                "timeshift",
                f"calligraphy_trail_contract_{candidate_id}",
            ),
            "wire": _require_node(
                network,
                f"OUT_{run_code}_{upper}",
                "polywire",
                f"calligraphy_tube_contract_{candidate_id}",
            ),
        }
        chain = [
            emitter,
            nodes["particle"],
            nodes["points"],
            nodes["extract"],
            nodes["lifespan"],
            nodes["drop"],
            nodes["scalar"],
            nodes["blend"],
            nodes["trail"],
            nodes["compat"],
            nodes["wire"],
        ]
        if any(target.input(0) != source for source, target in zip(chain, chain[1:], strict=False)):
            raise ValueError(f"candidate {candidate_id} graph chain is not registered")
        exact = {
            "particle": {
                "seed": spec["candidate_seeds"][candidate_id],
                "doid": 1,
                "birth": spec["birth_rate"],
                "life": spec["particle_life"],
                "lifevar": 0.0,
                "jitter": 0,
            },
            "points": {"keep": 1},
            "drop": {"ptdel": "life"},
            "blend": {"holdfirst": 1, "firstframe": 1.0, "ptidattr": "id"},
            "trail": {
                "substep": spec["trail_substeps"],
                "trailtype": 0,
                "framedur": spec["trail_frames"],
                "randattrib": "id",
                "createsplittrails": 0,
                "createparticletrails": 1,
                "tailwidth": 0.25,
                "headwidth": 1.0,
            },
            "compat": {"method": 0, "integerframe": 0},
            "wire": {
                "radius": spec["wire_radius"],
                "usescaleattrib": 1,
                "scaleattrib": "width",
                "div": 5,
            },
        }
        for stage, parameters in exact.items():
            node = nodes[stage]
            for parm_name, expected in parameters.items():
                actual = node.parm(parm_name).eval()
                if isinstance(expected, float):
                    matches = math.isclose(float(actual), expected, abs_tol=1e-6)
                else:
                    matches = actual == expected
                if not matches:
                    raise ValueError(
                        f"candidate {candidate_id} has unregistered {stage}.{parm_name}"
                    )
        compat_raw = nodes["compat"].parm("frame").rawValue().replace(" ", "")
        if compat_raw != "$FF-0.5":
            raise ValueError(
                f"candidate {candidate_id} is missing the half-frame compatibility expression"
            )
        wind_animated = all(
            nodes["particle"].parm(parm_name).keyframes()
            for parm_name in ("windx", "windy", "windz")
        )
        if wind_animated != bool(audio_envelope_relative_path):
            expected = "animated" if audio_envelope_relative_path else "unkeyed"
            raise ValueError(f"candidate {candidate_id} wind controls must be {expected}")
        branches[candidate_id] = nodes

    selector = _require_node(
        network,
        f"{run_code}_SELECT_CALLIGRAPHY",
        "switch",
        "calligraphy_human_selector",
    )
    selected = _require_node(
        network,
        f"OUT_{run_code}_SELECTED",
        "null",
        "calligraphy_selected_contract",
    )
    compare = _require_node(
        network,
        f"OUT_{run_code}_COMPARE",
        "null",
        "calligraphy_comparison_contract",
    )
    wires = [branches[candidate_id]["wire"] for candidate_id in CALLIGRAPHY_ORDER]
    if selector.parm("input").eval() != candidate_index or list(selector.inputs())[:3] != wires:
        raise ValueError("calligraphy human selector contract is invalid")
    if selected.input(0) != selector:
        raise ValueError("selected calligraphy output is disconnected")
    frame_transform = compare.input(0)
    if (
        frame_transform is None
        or frame_transform.type().name() != "xform"
        or frame_transform.userData("hermes_role") != "calligraphy_comparison_frame"
        or not math.isclose(float(frame_transform.parm("ty").eval()), -0.8, abs_tol=1e-6)
        or not math.isclose(float(frame_transform.parm("scale").eval()), 0.55, abs_tol=1e-6)
    ):
        raise ValueError(
            "calligraphy comparison output is missing its registered framing transform"
        )
    merge = frame_transform.input(0)
    if merge is None or merge.type().name() != "merge":
        raise ValueError("calligraphy comparison framing is missing its Merge SOP")
    merge_inputs = list(merge.inputs())
    transforms = merge_inputs
    if len(merge_inputs) != 3 or any(node is None for node in merge_inputs):
        raise ValueError("calligraphy comparison requires exactly three geometry inputs")
    for candidate_id, transform, wire in zip(CALLIGRAPHY_ORDER, transforms, wires, strict=True):
        if (
            transform.type().name() != "xform"
            or transform.input(0) != wire
            or transform.userData("hermes_role") != f"calligraphy_compare_{candidate_id}"
            or not math.isclose(
                float(transform.parm("tx").eval()), COMPARISON_TX[candidate_id], abs_tol=1e-6
            )
            or not math.isclose(
                float(transform.parm("ty").eval()), COMPARISON_TY[candidate_id], abs_tol=1e-6
            )
        ):
            raise ValueError(
                f"calligraphy comparison order/placement is invalid for {candidate_id}"
            )
    label_contract = _require_node(
        network,
        f"OUT_{run_code}_LABELS",
        "merge",
        "calligraphy_labels_contract",
    )
    label_inputs = list(label_contract.inputs())
    if len(label_inputs) != 3 or any(node is None for node in label_inputs):
        raise ValueError("calligraphy label contract requires exactly three inputs")
    for index, candidate_id in enumerate(CALLIGRAPHY_ORDER):
        upper = candidate_id.upper()
        label_source = _require_node(
            network,
            f"{run_code}_{upper}_LABEL",
            "font",
            f"calligraphy_label_source_{candidate_id}",
        )
        label_transform = _require_node(
            network,
            f"{run_code}_{upper}_LABEL_LAYOUT",
            "xform",
            f"calligraphy_label_{candidate_id}",
        )
        if (
            label_inputs[index] != label_transform
            or label_transform.input(0) != label_source
            or label_source.parm("text").evalAsString()
            != f"{upper}  seed {spec['candidate_seeds'][candidate_id]}"
            or not math.isclose(float(label_source.parm("fontsize").eval()), 0.22, abs_tol=1e-6)
            or not math.isclose(
                float(label_transform.parm("tx").eval()),
                COMPARISON_TX[candidate_id],
                abs_tol=1e-6,
            )
            or not math.isclose(float(label_transform.parm("ty").eval()), -0.45, abs_tol=1e-6)
        ):
            raise ValueError(f"calligraphy label contract is invalid for {candidate_id}")

    output = _prepare_new_json(output_path)
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 90.0
    max_points = min(spec["max_trail_points"], int(policy.max_points) if policy else 100_000)
    max_primitives = int(policy.max_primitives) if policy else 100_000
    started = time.monotonic()
    original_frame = hou.frame()
    frames: list[dict[str, Any]] = []
    try:
        for frame in range(spec["start_frame"], spec["end_frame"] + 1):
            hou.setFrame(frame)
            candidates = []
            frame_trail_points = 0
            for candidate_id in CALLIGRAPHY_ORDER:
                branch = branches[candidate_id]
                branch["compat"].cook(force=True)
                branch["wire"].cook(force=True)
                trail_metrics = geometry_metrics(branch["compat"])
                wire_metrics = geometry_metrics(branch["wire"])
                errors, warnings = _node_messages(list(branch.values()))
                if errors or warnings:
                    raise ValueError(
                        f"candidate {candidate_id} frame {frame} has Houdini messages: "
                        + "; ".join(errors + warnings)
                    )
                frame_trail_points += trail_metrics["points"]
                if trail_metrics["points"]:
                    _finite_bounds(trail_metrics, f"candidate {candidate_id} trail frame {frame}")
                    point_attribs = {
                        attrib.name(): attrib.size()
                        for attrib in branch["compat"].geometry().pointAttribs()
                    }
                    if any(point_attribs.get(name) != 1 for name in ("id", "age", "life")):
                        raise ValueError(
                            f"candidate {candidate_id} frame {frame} lacks scalar id/age/life"
                        )
                if wire_metrics["points"]:
                    _finite_bounds(wire_metrics, f"candidate {candidate_id} wire frame {frame}")
                if (
                    wire_metrics["points"] > max_points
                    or wire_metrics["primitives"] > max_primitives
                ):
                    raise ValueError(
                        f"candidate {candidate_id} frame {frame} exceeds topology policy"
                    )
                candidates.append(
                    {
                        "id": candidate_id,
                        "seed": spec["candidate_seeds"][candidate_id],
                        "trail": trail_metrics,
                        "tube": wire_metrics,
                        "cook_seconds": round(float(branch["wire"].lastCookTime()), 6),
                    }
                )
            if frame_trail_points > max_points:
                raise ValueError(f"frame {frame} trail points exceed the {max_points} ceiling")
            frames.append(
                {
                    "frame": frame,
                    "trail_points": frame_trail_points,
                    "candidates": candidates,
                }
            )
            if time.monotonic() - started > max_seconds:
                raise TimeoutError("particle calligraphy validation exceeded policy.max_seconds")
        selected.cook(force=True)
        compare.cook(force=True)
        selected_metrics = geometry_metrics(selected)
        comparison_metrics = geometry_metrics(compare)
    finally:
        hou.setFrame(original_frame)

    final_candidates = frames[-1]["candidates"]
    if any(item["trail"]["points"] < 2 or item["tube"]["points"] < 2 for item in final_candidates):
        raise ValueError("all final calligraphy candidates must be non-empty")
    final_bounds = {
        tuple(round(float(value), 5) for vector in item["tube"]["bounds"] for value in vector)
        for item in final_candidates
    }
    if len(final_bounds) != 3:
        raise ValueError("final calligraphy candidate bounds are not visually distinct")
    chosen = final_candidates[candidate_index]["tube"]
    if (
        selected_metrics["points"] != chosen["points"]
        or selected_metrics["primitives"] != chosen["primitives"]
    ):
        raise ValueError("selected calligraphy output does not match the human Switch input")
    if comparison_metrics["points"] != sum(item["tube"]["points"] for item in final_candidates):
        raise ValueError("calligraphy comparison does not preserve all three geometry candidates")

    elapsed = time.monotonic() - started
    document = {
        "schema": "hermes.houdini.particle_calligraphy_validation",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "status": "success",
        "network_path": network_path,
        "run_code": run_code,
        "spec": spec,
        "frames": frames,
        "selected": selected_metrics,
        "comparison": comparison_metrics,
        "peak_trail_points": max(frame["trail_points"] for frame in frames),
        "elapsed_seconds": round(elapsed, 6),
        "audio_envelope": {
            "mode": "silent_fixture" if not audio_envelope_relative_path else "baked_data",
            "relative_path": audio_envelope_relative_path or None,
            "applied": bool(audio_envelope_relative_path),
        },
        "selection": {
            "method": "human",
            "preview_input": candidate_index,
            "winner": None,
            "automatic_ranking": False,
            "human_ratings": {
                candidate_id: {"score": None, "notes": "", "selected": False}
                for candidate_id in CALLIGRAPHY_ORDER
            },
        },
        "known_compatibility": {
            "status": "verified_workaround",
            **spec["integer_frame_compatibility"],
        },
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"artifact": str(output), **document}


__all__ = [
    "CALLIGRAPHY_ORDER",
    "COMPARISON_TX",
    "COMPARISON_TY",
    "SEED_OFFSETS",
    "apply_baked_audio_envelope",
    "cook_validate_calligraphy",
    "load_baked_audio_envelope",
    "validate_calligraphy_spec",
]
