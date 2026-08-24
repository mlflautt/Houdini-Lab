"""Deterministic, local-only PDG variation graphs and comparison galleries.

Pure planning and validation stay importable without Houdini. HOM is confined to the
bounded build/generate/cook/gallery entry points; native Wedge and ROP Geometry TOPs do
the variation expansion and geometry work.
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
from .schemas.command import ChangedNode, Policy, Status, ToolResult
from .transactions import save_checkpoint

PLAN_SCHEMA = "hermes.houdini.pdg_variation_plan"
RESULT_SCHEMA = "hermes.houdini.pdg_variation_result"
SCHEMA_VERSION = "1.0"
MAX_PLANNED_VARIATIONS = 100
DETAIL_LEVELS = {"draft": 0, "preview": 1, "final": 2}
_SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,47}\Z")
_ESTIMATE_KEYS = {
    "work_items",
    "seconds_per_item",
    "points_per_item",
    "primitives_per_item",
    "memory_bytes_per_item",
    "output_bytes_total",
}


def _finite_number(value: Any, label: str, *, minimum: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return result


def _range(values: list[float] | tuple[float, float], label: str) -> tuple[float, float]:
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        raise ValueError(f"{label} must contain exactly two numbers")
    start = _finite_number(values[0], f"{label}[0]", minimum=0.0)
    end = _finite_number(values[1], f"{label}[1]", minimum=0.0)
    if end < start:
        raise ValueError(f"{label} end must be >= start")
    return start, end


def _interpolate(start: float, end: float, index: int, count: int) -> float:
    ratio = index / (count - 1)
    return round(start + ((end - start) * ratio), 6)


def build_variation_plan(
    *,
    source_node_path: str,
    output_dir: str,
    base_seed: int = 1001,
    count: int = 9,
    seed_step: int = 97,
    base_radius_range: list[float] | tuple[float, float] = (0.8, 1.2),
    noise_amplitude_range: list[float] | tuple[float, float] = (0.1, 0.28),
    iterations: int = 4,
    detail_level: str = "preview",
    candidate_index: int = 0,
) -> dict[str, Any]:
    """Return a finite JSON-only plan matching a native Wedge TOP's linear ranges."""
    if not isinstance(source_node_path, str) or not source_node_path.startswith("/"):
        raise ValueError("source_node_path must be an absolute Houdini path")
    output = Path(output_dir).expanduser()
    if not output.is_absolute():
        raise ValueError("output_dir must be absolute")
    if not isinstance(count, int) or isinstance(count, bool) or not 2 <= count <= 100:
        raise ValueError("count must be between 2 and 100")
    if not isinstance(base_seed, int) or isinstance(base_seed, bool) or base_seed < 0:
        raise ValueError("base_seed must be a non-negative integer")
    if not isinstance(seed_step, int) or isinstance(seed_step, bool) or seed_step < 1:
        raise ValueError("seed_step must be a positive integer")
    last_seed = base_seed + ((count - 1) * seed_step)
    if last_seed > 2_147_483_647:
        raise ValueError("seed range exceeds Houdini's signed integer range")
    if not isinstance(iterations, int) or isinstance(iterations, bool) or not 1 <= iterations <= 8:
        raise ValueError("iterations must be between 1 and 8")
    if detail_level not in DETAIL_LEVELS:
        raise ValueError(f"detail_level must be one of {sorted(DETAIL_LEVELS)}")
    if not isinstance(candidate_index, int) or isinstance(candidate_index, bool):
        raise ValueError("candidate_index must be an integer")
    if candidate_index not in {0, 1, 2}:
        raise ValueError("candidate_index must be 0, 1, or 2")
    radius_start, radius_end = _range(base_radius_range, "base_radius_range")
    noise_start, noise_end = _range(noise_amplitude_range, "noise_amplitude_range")

    variations = []
    for index in range(count):
        seed = base_seed + (index * seed_step)
        variations.append(
            {
                "id": f"variation_{index:03d}",
                "index": index,
                "seed": seed,
                "base_radius": _interpolate(radius_start, radius_end, index, count),
                "noise_amplitude": _interpolate(noise_start, noise_end, index, count),
                "iterations": iterations,
                "detail_level": detail_level,
                "detail_level_index": DETAIL_LEVELS[detail_level],
                "candidate_index": candidate_index,
                "geometry_path": str(output / f"relic_wedge_{index}_seed_{seed}.bgeo.sc"),
                "lineage": {
                    "source_node_path": source_node_path,
                    "generator": "native Wedge TOP -> native ROP Geometry Output TOP",
                    "automatic_ranking": False,
                },
                "human_rating": {"score": None, "notes": "", "selected": False},
            }
        )
    columns = min(4, math.ceil(math.sqrt(count)))
    rows = math.ceil(count / columns)
    return {
        "schema": PLAN_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "source_node_path": source_node_path,
        "output_dir": str(output),
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "geometry_format": ".bgeo.sc",
        },
        "controls": {
            "base_seed": base_seed,
            "count": count,
            "seed_step": seed_step,
            "base_radius_range": [radius_start, radius_end],
            "noise_amplitude_range": [noise_start, noise_end],
            "iterations": iterations,
            "detail_level": detail_level,
            "candidate_index": candidate_index,
        },
        "comparison_layout": {"columns": columns, "rows": rows},
        "selection": {"method": "human", "winner": None, "automatic_ranking": False},
        "variations": variations,
    }


def validate_variation_estimate(estimate: dict[str, Any], policy: Policy) -> dict[str, Any]:
    """Validate total and per-item PDG costs before any local jobs are scheduled."""
    if not isinstance(estimate, dict):
        raise ValueError("estimate must be an object")
    missing = _ESTIMATE_KEYS - set(estimate)
    unknown = set(estimate) - _ESTIMATE_KEYS
    if missing:
        raise ValueError(f"estimate missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"estimate has unknown keys: {', '.join(sorted(unknown))}")
    integer_keys = {
        "work_items",
        "points_per_item",
        "primitives_per_item",
        "memory_bytes_per_item",
        "output_bytes_total",
    }
    normalized: dict[str, Any] = {}
    for key in integer_keys:
        value = estimate[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"estimate.{key} must be a non-negative integer")
        normalized[key] = value
    normalized["seconds_per_item"] = _finite_number(
        estimate["seconds_per_item"], "estimate.seconds_per_item", minimum=0.0
    )
    checks = (
        ("work_items", normalized["work_items"], policy.max_work_items),
        ("points_per_item", normalized["points_per_item"], policy.max_points),
        ("primitives_per_item", normalized["primitives_per_item"], policy.max_primitives),
        ("memory_bytes_per_item", normalized["memory_bytes_per_item"], policy.max_memory_bytes),
        ("output_bytes_total", normalized["output_bytes_total"], policy.max_output_bytes),
        (
            "total_seconds",
            normalized["work_items"] * normalized["seconds_per_item"],
            policy.max_seconds,
        ),
    )
    violations = [
        f"{name} {actual} > budget {limit}" for name, actual, limit in checks if actual > limit
    ]
    if violations:
        raise ValueError("declared PDG estimate exceeds policy: " + "; ".join(violations))
    return normalized


def _tag(node: Any, *, category: str, role: str, created_by: str, stable_scope: str) -> None:
    node.setUserData("hermes_id", make_id(category, stable_scope))
    node.setUserData("hermes_role", role)
    node.setUserData("hermes_created_by", created_by)
    node.setUserData("hermes_manifest_version", "1")


def _set_parm(node: Any, name: str, value: Any) -> None:
    parm = node.parm(name)
    parm_tuple = node.parmTuple(name)
    if parm is not None:
        parm.set(value)
    elif parm_tuple is not None:
        parm_tuple.set(value)
    else:
        raise ValueError(f"node {node.path()} has no parameter {name}")


def _append_jsonl(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _write_json_exclusive(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _plan_from_topnet(topnet: Any) -> dict[str, Any]:
    raw = topnet.userData("hermes_variation_plan")
    if not raw:
        raise ValueError(f"TOP network is not a Hermes variation graph: {topnet.path()}")
    plan = json.loads(raw)
    if plan.get("schema") != PLAN_SCHEMA or plan.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported or invalid variation plan metadata")
    return plan


def build_variation_graph(
    *,
    source_node_path: str,
    output_dir: str,
    checkpoint_dir: str,
    log_path: str,
    network_name: str = "HERMES_PDG_RELIC_VARIATIONS",
    base_seed: int = 1001,
    count: int = 9,
    seed_step: int = 97,
    base_radius_range: list[float] | tuple[float, float] = (0.8, 1.2),
    noise_amplitude_range: list[float] | tuple[float, float] = (0.1, 0.28),
    iterations: int = 4,
    detail_level: str = "preview",
    candidate_index: int = 0,
    scheduler_seconds_per_item: float = 30.0,
    scheduler_memory_mb: int = 2048,
) -> ToolResult:
    """Checkpoint and build a readable Wedge -> ROP Geometry -> Wait for All graph."""
    hou = get_hou()
    if not _SAFE_NAME.fullmatch(network_name):
        raise ValueError("network_name must be a safe 1-48 character Houdini name")
    plan = build_variation_plan(
        source_node_path=source_node_path,
        output_dir=output_dir,
        base_seed=base_seed,
        count=count,
        seed_step=seed_step,
        base_radius_range=base_radius_range,
        noise_amplitude_range=noise_amplitude_range,
        iterations=iterations,
        detail_level=detail_level,
        candidate_index=candidate_index,
    )
    source = hou.node(source_node_path)
    if source is None or not hasattr(source, "geometry"):
        raise ValueError(f"source SOP node not found: {source_node_path}")
    required = (
        "seed",
        "base_radius",
        "noise_amplitude",
        "iterations",
        "detail_level",
        "preview_candidate",
        "output_mode",
    )
    missing = [name for name in required if source.parm(name) is None]
    if missing:
        raise ValueError(f"source node lacks promoted parameters: {', '.join(missing)}")
    tasks = hou.node("/tasks")
    if tasks is None:
        raise ValueError("/tasks TOP manager is unavailable")
    if tasks.node(network_name) is not None:
        raise ValueError(f"TOP network already exists: /tasks/{network_name}")
    definition = source.type().definition()
    hda_file = definition.libraryFilePath() if definition is not None else ""
    if not hda_file or hda_file == "Embedded" or not os.path.isfile(hda_file):
        raise ValueError("source must be an externally published .hdanc with a readable definition")
    seconds = _finite_number(scheduler_seconds_per_item, "scheduler_seconds_per_item", minimum=1.0)
    if not isinstance(scheduler_memory_mb, int) or not 512 <= scheduler_memory_mb <= 65_536:
        raise ValueError("scheduler_memory_mb must be between 512 and 65536")
    os.makedirs(output_dir, exist_ok=True)
    checkpoint = save_checkpoint(checkpoint_dir, f"pdg_{network_name.lower()}")
    created: list[Any] = []
    changed: list[ChangedNode] = []
    created_by = "tool:pdg.variation.build@1.0.0"
    try:
        with hou.undos.group(f"Hermes build {network_name}"):
            topnet = tasks.createNode("topnet", node_name=network_name, exact_type_name=True)
            created.append(topnet)
            _tag(
                topnet,
                category="Top",
                role="variation_network",
                created_by=created_by,
                stable_scope=f"pdg:{network_name}:network",
            )
            topnet.setUserData("hermes_variation_plan", json.dumps(plan, sort_keys=True))
            topnet.setUserData("hermes_hda_library", hda_file)
            topnet.setComment("Local-only deterministic relic variations; human selection only")
            changed.append(ChangedNode(topnet.userData("hermes_id"), topnet.path(), "created"))

            scheduler = topnet.createNode(
                "localscheduler", node_name="LOCAL_BOUNDED", exact_type_name=True
            )
            wedge = topnet.createNode("wedge", node_name="TOP_WEDGE_VARIANTS", exact_type_name=True)
            cache = topnet.createNode(
                "ropgeometry", node_name="CACHE_VARIANT_GEOMETRY", exact_type_name=True
            )
            wait = topnet.createNode(
                "waitforall", node_name="WAIT_ALL_VARIANTS", exact_type_name=True
            )
            output = topnet.createNode("null", node_name="OUT_VARIATIONS", exact_type_name=True)
            created.extend((scheduler, wedge, cache, wait, output))
            nodes = (
                (scheduler, "bounded_local_scheduler"),
                (wedge, "variation_generator"),
                (cache, "geometry_cache"),
                (wait, "variation_barrier"),
                (output, "variation_output"),
            )
            for node, role in nodes:
                _tag(
                    node,
                    category="Top",
                    role=role,
                    created_by=created_by,
                    stable_scope=f"pdg:{network_name}:{role}",
                )
                changed.append(ChangedNode(node.userData("hermes_id"), node.path(), "created"))

            _set_parm(topnet, "topscheduler", scheduler.name())
            _set_parm(scheduler, "maxprocsmenu", "1")
            _set_parm(scheduler, "maxprocs", 1)
            _set_parm(scheduler, "local_enabletimeout", 1)
            _set_parm(scheduler, "local_maxtime", seconds)
            _set_parm(scheduler, "local_handletimeout", "0")
            _set_parm(scheduler, "local_enablemaxmemory", 1)
            _set_parm(scheduler, "local_maxmemory", scheduler_memory_mb)
            _set_parm(scheduler, "local_handlememory", "0")
            _set_parm(scheduler, "local_maximumretries", 0)
            _set_parm(scheduler, "tempdirmenu", "2")
            _set_parm(scheduler, "tempdircustom", str(Path(output_dir) / "pdg_temp"))
            _set_parm(scheduler, "tempdirappendpid", 1)
            _set_parm(scheduler, "local_envmulti", 1)
            _set_parm(scheduler, "local_envname1", "HOUDINI_OTLSCAN_PATH")
            _set_parm(scheduler, "local_envvalue1", f"{Path(hda_file).parent};&")
            scheduler.setComment(
                f"One local slot; {seconds:g}s and {scheduler_memory_mb} MB per work item"
            )

            controls = plan["controls"]
            _set_parm(wedge, "wedgecount", count)
            _set_parm(wedge, "seed", base_seed)
            _set_parm(wedge, "wedgeattributes", 7)
            wedge_specs = (
                (1, "seed", 2, "range", (base_seed, plan["variations"][-1]["seed"]), "seed"),
                (2, "base_radius", 0, "range", controls["base_radius_range"], "base_radius"),
                (
                    3,
                    "noise_amplitude",
                    0,
                    "range",
                    controls["noise_amplitude_range"],
                    "noise_amplitude",
                ),
                (4, "iterations", 2, "value", iterations, "iterations"),
                (
                    5,
                    "detail_level",
                    2,
                    "value",
                    DETAIL_LEVELS[detail_level],
                    "detail_level",
                ),
                (6, "candidate_index", 2, "value", candidate_index, "preview_candidate"),
                (7, "output_mode", 2, "value", 0, "output_mode"),
            )
            for slot, attrib, type_token, wedge_type, value, target_parm in wedge_specs:
                _set_parm(wedge, f"name{slot}", attrib)
                _set_parm(wedge, f"type{slot}", type_token)
                _set_parm(wedge, f"wedgetype{slot}", 0 if wedge_type == "range" else 1)
                if wedge_type == "range":
                    parm_name = "intrange" if type_token == 2 else "floatrange"
                    _set_parm(wedge, f"{parm_name}{slot}", value)
                else:
                    parm_name = "intvalue" if type_token == 2 else "floatvalue"
                    _set_parm(wedge, f"{parm_name}{slot}", value)
                _set_parm(wedge, f"exportchannel{slot}", 1)
                _set_parm(wedge, f"channel{slot}", source.parm(target_parm).path())
                _set_parm(wedge, f"valuetype{slot}", 1)
            wedge.setComment("Deterministic linear controls; target overrides do not edit the HIP")

            _set_parm(cache, "usesoppath", 1)
            _set_parm(cache, "soppath", source_node_path)
            pattern = str(Path(output_dir) / "relic_wedge_`@wedgeindex`_seed_`@seed`.bgeo.sc")
            _set_parm(cache, "sopoutput", pattern)
            _set_parm(cache, "framegeneration", 0)
            _set_parm(cache, "mkpath", 1)
            _set_parm(cache, "savebackground", 0)
            _set_parm(cache, "usefiletag", 1)
            _set_parm(cache, "filetag", "file/geo")
            if cache.parm("local_single") is not None:
                _set_parm(cache, "local_single", 1)
            cache.setComment("Native one-frame .bgeo.sc export; no source parameter mutation")
            cache.setInput(0, wedge)
            wait.setInput(0, cache)
            output.setInput(0, wait)
            output.setDisplayFlag(True)
            wait.setComment("All local geometry work items must finish before completion")
            output.setComment("Named TOP contract for the complete variation set")

            scheduler.setPosition((-2.5, 2.0))
            wedge.setPosition((0.0, 2.0))
            cache.setPosition((0.0, 0.0))
            wait.setPosition((0.0, -2.0))
            output.setPosition((0.0, -4.0))
    except Exception:
        for node in reversed(created):
            if node.parent() is not None:
                node.destroy()
        raise

    record = {
        "schema": "hermes.houdini.pdg_graph_build",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "network_path": topnet.path(),
        "checkpoint": checkpoint,
        "plan": plan,
        "nodes": [node.path() for node in created],
    }
    _append_jsonl(log_path, record)
    return ToolResult(
        status=Status.SUCCESS,
        changed_nodes=changed,
        checkpoint=checkpoint,
        artifacts=[log_path],
        data={
            "network_path": topnet.path(),
            "wedge_path": wedge.path(),
            "cache_path": cache.path(),
            "output_path": output.path(),
            "scheduler_path": scheduler.path(),
            "plan": plan,
            "hda_file": hda_file,
        },
    )


def generate_variation_manifest(*, topnet_path: str, output_path: str) -> dict[str, Any]:
    """Generate static native Wedge work items and write an immutable human-rating manifest."""
    hou = get_hou()
    topnet = hou.node(topnet_path)
    if topnet is None:
        raise ValueError(f"TOP network not found: {topnet_path}")
    plan = _plan_from_topnet(topnet)
    wedge = topnet.node("TOP_WEDGE_VARIANTS")
    if wedge is None or wedge.type().name() != "wedge":
        raise ValueError("managed Wedge TOP is missing")
    wedge.dirtyAllWorkItems(False)
    wedge.generateStaticWorkItems(block=True)
    pdg_node = wedge.getPDGNode()
    items = list(pdg_node.workItems) if pdg_node is not None else []
    if len(items) != len(plan["variations"]):
        raise ValueError(f"Wedge generated {len(items)} items; expected {len(plan['variations'])}")
    generated = []
    for expected, item in zip(plan["variations"], items, strict=True):
        values = item.attribValues()
        actual = {
            "id": expected["id"],
            "work_item_name": item.name,
            "wedgeindex": int(values["wedgeindex"]),
            "seed": int(values["seed"]),
            "base_radius": round(float(values["base_radius"]), 6),
            "noise_amplitude": round(float(values["noise_amplitude"]), 6),
            "iterations": int(values["iterations"]),
            "detail_level_index": int(values["detail_level"]),
            "candidate_index": int(values["candidate_index"]),
            "output_mode": int(values["output_mode"]),
            "geometry_path": expected["geometry_path"],
            "human_rating": expected["human_rating"],
        }
        for key in (
            "wedgeindex",
            "seed",
            "base_radius",
            "noise_amplitude",
            "iterations",
            "detail_level_index",
            "candidate_index",
        ):
            expected_value = expected["index"] if key == "wedgeindex" else expected[key]
            if isinstance(expected_value, float):
                if not math.isclose(actual[key], expected_value, rel_tol=0.0, abs_tol=1e-5):
                    raise ValueError(f"Wedge attribute mismatch for {expected['id']}.{key}")
            elif actual[key] != expected_value:
                raise ValueError(f"Wedge attribute mismatch for {expected['id']}.{key}")
        generated.append(actual)
    manifest = {
        **plan,
        "generated_by": "tool:pdg.variation.generate@1.0.0",
        "network_path": topnet.path(),
        "generated_work_items": generated,
    }
    _write_json_exclusive(output_path, manifest)
    return {
        "artifact": output_path,
        "network_path": topnet.path(),
        "work_items": len(generated),
        "selection": manifest["selection"],
        "items": generated,
    }


def _geometry_file_metrics(path: str) -> dict[str, Any]:
    hou = get_hou()
    geometry = hou.Geometry()
    geometry.loadFromFile(path)
    bounds = geometry.boundingBox()
    values = [*bounds.minvec(), *bounds.maxvec()]
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError(f"geometry has non-finite bounds: {path}")
    memory = 0
    if "memoryusage" in geometry.intrinsicNames():
        memory = int(geometry.intrinsicValue("memoryusage"))
    return {
        "points": int(geometry.pointCount()),
        "primitives": int(geometry.primCount()),
        "vertices": int(geometry.vertexCount()),
        "memory_bytes": memory,
        "bounds": [list(bounds.minvec()), list(bounds.maxvec())],
        "file_bytes": os.path.getsize(path),
    }


def cook_variation_graph(
    *,
    topnet_path: str,
    manifest_path: str,
    result_path: str,
    scene_path: str,
    log_path: str,
    estimate: dict[str, Any],
) -> ToolResult:
    """Run the local one-slot ROP Geometry branch after explicit external-process consent."""
    hou = get_hou()
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else Policy()
    if not policy.allow_external_process:
        raise ValueError("policy.allow_external_process=true is required for local PDG hython jobs")
    normalized = validate_variation_estimate(estimate, policy)
    topnet = hou.node(topnet_path)
    if topnet is None:
        raise ValueError(f"TOP network not found: {topnet_path}")
    plan = _plan_from_topnet(topnet)
    if normalized["work_items"] != len(plan["variations"]):
        raise ValueError("estimate.work_items must equal the managed variation count")
    with open(manifest_path, encoding="utf-8") as stream:
        manifest = json.load(stream)
    if (
        manifest.get("network_path") != topnet.path()
        or manifest.get("variations") != plan["variations"]
    ):
        raise ValueError("manifest does not match the managed TOP variation plan")
    if not str(scene_path).endswith(".hipnc"):
        raise ValueError("scene_path must use the non-commercial .hipnc extension")
    for protected in (result_path, scene_path):
        if os.path.exists(protected):
            raise FileExistsError(f"refusing to overwrite existing artifact: {protected}")
    expected_files = [item["geometry_path"] for item in plan["variations"]]
    existing = [path for path in expected_files if os.path.exists(path)]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing geometry: {existing[0]}")
    cache = topnet.node("CACHE_VARIANT_GEOMETRY")
    if cache is None or cache.type().name() != "ropgeometry":
        raise ValueError("managed ROP Geometry TOP is missing")
    source = hou.node(plan["source_node_path"])
    if source is None:
        raise ValueError("variation source node was deleted")
    source_before = {
        name: source.parm(name).eval()
        for name in (
            "seed",
            "base_radius",
            "noise_amplitude",
            "iterations",
            "detail_level",
            "preview_candidate",
            "output_mode",
        )
    }
    os.makedirs(os.path.dirname(scene_path), exist_ok=True)
    started = time.monotonic()
    original_name = hou.hipFile.name()
    try:
        hou.hipFile.save(file_name=scene_path, save_to_recent_files=False)
        cache.dirtyAllWorkItems(False)
        cache.cookWorkItems(block=True, save_prompt=False)
    finally:
        hou.hipFile.setName(original_name)
    elapsed = time.monotonic() - started
    source_after = {name: source.parm(name).eval() for name in source_before}
    if source_after != source_before:
        raise RuntimeError("Wedge target overrides mutated source parameters")

    pdg_node = cache.getPDGNode()
    work_items = list(pdg_node.workItems) if pdg_node is not None else []
    actuals = []
    failures = []
    total_bytes = 0
    for item in work_items:
        values = item.attribValues()
        index = int(values["wedgeindex"])
        expected = plan["variations"][index]
        outputs = [file.path for file in item.outputFiles if file.path.endswith(".bgeo.sc")]
        state = str(item.state)
        if "CookedSuccess" not in state or outputs != [expected["geometry_path"]]:
            failures.append(
                {"work_item": item.name, "state": state, "outputs": outputs, "expected": expected}
            )
            continue
        metrics = _geometry_file_metrics(outputs[0])
        total_bytes += metrics["file_bytes"]
        if metrics["points"] > policy.max_points or metrics["primitives"] > policy.max_primitives:
            failures.append(
                {"work_item": item.name, "state": "budget_exceeded", "metrics": metrics}
            )
            continue
        actuals.append(
            {
                "id": expected["id"],
                "work_item_name": item.name,
                "state": state,
                "seed": expected["seed"],
                "base_radius": expected["base_radius"],
                "noise_amplitude": expected["noise_amplitude"],
                "geometry_path": outputs[0],
                "metrics": metrics,
                "human_rating": expected["human_rating"],
            }
        )
    if total_bytes > policy.max_output_bytes:
        failures.append(
            {
                "state": "budget_exceeded",
                "reason": f"output bytes {total_bytes} > {policy.max_output_bytes}",
            }
        )
    if len(actuals) != len(plan["variations"]):
        failures.append(
            {"state": "count_mismatch", "actual": len(actuals), "expected": len(plan["variations"])}
        )
    result_document = {
        "schema": RESULT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "source_manifest": manifest_path,
        "network_path": topnet.path(),
        "scene_path": scene_path,
        "license": plan["license"],
        "estimate": normalized,
        "elapsed_seconds": round(elapsed, 6),
        "total_output_bytes": total_bytes,
        "selection": plan["selection"],
        "variations": actuals,
        "failures": failures,
    }
    _write_json_exclusive(result_path, result_document)
    _append_jsonl(
        log_path,
        {
            "schema": "hermes.houdini.pdg_cook",
            "schema_version": SCHEMA_VERSION,
            "timestamp_unix": time.time(),
            **result_document,
        },
    )
    status = Status.SUCCESS if not failures else Status.ERROR
    tool_result = ToolResult(
        status=status,
        artifacts=[
            manifest_path,
            result_path,
            scene_path,
            log_path,
            *[item["geometry_path"] for item in actuals],
        ],
        data=result_document,
    )
    if failures:
        tool_result.errors.append(f"{len(failures)} PDG variation validation failures")
    return tool_result


def build_variation_gallery(
    *,
    result_path: str,
    checkpoint_dir: str,
    log_path: str,
    gallery_name: str = "HERMES_VARIATION_GALLERY",
    camera_name: str = "SPRINT6_GALLERY_CAMERA",
    spacing: float = 5.0,
) -> ToolResult:
    """Build a native SOP comparison grid from successful PDG geometry outputs."""
    hou = get_hou()
    if not _SAFE_NAME.fullmatch(gallery_name) or not _SAFE_NAME.fullmatch(camera_name):
        raise ValueError("gallery_name and camera_name must be safe Houdini names")
    spacing = _finite_number(spacing, "spacing", minimum=0.5)
    with open(result_path, encoding="utf-8") as stream:
        result_document = json.load(stream)
    if result_document.get("schema") != RESULT_SCHEMA or result_document.get("failures"):
        raise ValueError("gallery requires a successful Hermes PDG variation result")
    variations = result_document.get("variations", [])
    if not variations:
        raise ValueError("variation result contains no geometry")
    obj = hou.node("/obj")
    if obj.node(gallery_name) is not None or obj.node(camera_name) is not None:
        raise ValueError("gallery or camera name already exists")
    checkpoint = save_checkpoint(checkpoint_dir, f"gallery_{gallery_name.lower()}")
    created: list[Any] = []
    changed: list[ChangedNode] = []
    created_by = "tool:pdg.variation.build_gallery@1.0.0"
    columns = min(4, math.ceil(math.sqrt(len(variations))))
    rows = math.ceil(len(variations) / columns)
    try:
        with hou.undos.group(f"Hermes build {gallery_name}"):
            gallery = obj.createNode("geo", node_name=gallery_name, run_init_scripts=False)
            camera = obj.createNode("cam", node_name=camera_name)
            created.extend((gallery, camera))
            _tag(
                gallery,
                category="Object",
                role="variation_gallery",
                created_by=created_by,
                stable_scope=f"gallery:{gallery_name}",
            )
            _tag(
                camera,
                category="Object",
                role="variation_gallery_camera",
                created_by=created_by,
                stable_scope=f"gallery:{gallery_name}:camera",
            )
            gallery.setComment("Editable comparison grid; no automatic winner selection")
            camera.setComment("Explicit Sprint 6 comparison camera")
            camera.parmTuple("t").set((0.0, 0.0, max(columns, rows) * spacing * 2.1))
            camera.parm("focal").set(50.0)
            for node in (gallery, camera):
                changed.append(ChangedNode(node.userData("hermes_id"), node.path(), "created"))

            merge = gallery.createNode("merge", node_name="MERGE_VARIATIONS")
            output = gallery.createNode("null", node_name="OUT_GALLERY")
            created.extend((merge, output))
            _tag(
                merge,
                category="Sop",
                role="variation_gallery_merge",
                created_by=created_by,
                stable_scope=f"gallery:{gallery_name}:merge",
            )
            _tag(
                output,
                category="Sop",
                role="variation_gallery_output",
                created_by=created_by,
                stable_scope=f"gallery:{gallery_name}:output",
            )
            label_transforms = []
            for index, variation in enumerate(variations):
                file_node = gallery.createNode("file", node_name=f"FILE_VAR_{index:03d}")
                transform = gallery.createNode("xform", node_name=f"LAYOUT_VAR_{index:03d}")
                label = gallery.createNode("font", node_name=f"LABEL_VAR_{index:03d}")
                label_transform = gallery.createNode("xform", node_name=f"LABEL_LAYOUT_{index:03d}")
                created.extend((file_node, transform, label, label_transform))
                file_node.parm("file").set(variation["geometry_path"])
                transform.setInput(0, file_node)
                label.parm("text").set(f"V{index:03d}  seed {variation['seed']}")
                label.parm("halign").set("center")
                label.parm("valign").set("middle")
                label.parm("fontsize").set(0.28)
                label_transform.setInput(0, label)
                label_transforms.append(label_transform)
                column = index % columns
                row = index // columns
                translate_x = (column - ((columns - 1) / 2)) * spacing
                translate_y = (((rows - 1) / 2) - row) * spacing
                transform.parm("tx").set(translate_x)
                transform.parm("ty").set(translate_y)
                label_transform.parm("tx").set(translate_x)
                label_transform.parm("ty").set(translate_y - (spacing * 0.39))
                merge.setInput(index, transform)
                for node, role in (
                    (file_node, "variation_file"),
                    (transform, "variation_layout"),
                    (label, "variation_label"),
                    (label_transform, "variation_label_layout"),
                ):
                    _tag(
                        node,
                        category="Sop",
                        role=role,
                        created_by=created_by,
                        stable_scope=f"gallery:{gallery_name}:{variation['id']}:{role}",
                    )
                    node.setUserData("hermes_variation_id", variation["id"])
                    node.setUserData("hermes_seed", str(variation["seed"]))
                    node.setUserData("hermes_human_rating", json.dumps(variation["human_rating"]))
                    changed.append(ChangedNode(node.userData("hermes_id"), node.path(), "created"))
                file_node.setComment(
                    f"{variation['id']} | seed {variation['seed']} | rating unassigned"
                )
                file_node.setPosition((column * 3.0, -row * 4.0))
                transform.setPosition((column * 3.0, (-row * 4.0) - 1.5))
                label.setPosition((column * 3.0 + 1.3, -row * 4.0))
                label_transform.setPosition((column * 3.0 + 1.3, (-row * 4.0) - 1.5))
            for index, label_transform in enumerate(label_transforms, start=len(variations)):
                merge.setInput(index, label_transform)
            output.setInput(0, merge)
            output.setDisplayFlag(True)
            output.setRenderFlag(True)
            output.setComment("Named editable comparison output; human selection remains external")
            merge.setPosition((((columns - 1) * 3.0) / 2, -(rows * 4.0) - 1.0))
            output.setPosition((((columns - 1) * 3.0) / 2, -(rows * 4.0) - 3.0))
            changed.extend(
                [
                    ChangedNode(merge.userData("hermes_id"), merge.path(), "created"),
                    ChangedNode(output.userData("hermes_id"), output.path(), "created"),
                ]
            )
    except Exception:
        for node in reversed(created):
            if node.parent() is not None:
                node.destroy()
        raise
    record = {
        "schema": "hermes.houdini.pdg_gallery_build",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "result_path": result_path,
        "gallery_path": gallery.path(),
        "output_path": output.path(),
        "camera_path": camera.path(),
        "checkpoint": checkpoint,
        "variations": len(variations),
        "selection": result_document["selection"],
    }
    _append_jsonl(log_path, record)
    return ToolResult(
        status=Status.SUCCESS,
        changed_nodes=changed,
        checkpoint=checkpoint,
        artifacts=[result_path, log_path],
        data=record,
    )


__all__ = [
    "DETAIL_LEVELS",
    "MAX_PLANNED_VARIATIONS",
    "PLAN_SCHEMA",
    "RESULT_SCHEMA",
    "build_variation_gallery",
    "build_variation_graph",
    "build_variation_plan",
    "cook_variation_graph",
    "generate_variation_manifest",
    "validate_variation_estimate",
]
