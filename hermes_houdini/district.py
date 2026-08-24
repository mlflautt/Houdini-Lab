"""Bounded native-SOP and PDG procedural district generation.

Pure planning is available without Houdini. HOM only constructs readable recipe graphs,
configures native Wedge channel overrides, executes an explicitly approved one-slot ROP
Geometry cook, and assembles immutable lot caches into editable SOP outputs.
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

from recipes.catalog import register_bundled_recipes

from . import get_hou
from .execution import current_envelope
from .graph_batch import apply_batch
from .ids import make_id
from .pdg_variations import validate_variation_estimate
from .registry import REGISTRY
from .schemas.command import ChangedNode, Policy, Status, ToolResult
from .transactions import save_checkpoint

PLAN_SCHEMA = "hermes.houdini.procedural_district_plan"
RESULT_SCHEMA = "hermes.houdini.procedural_district_result"
ASSEMBLY_SCHEMA = "hermes.houdini.procedural_district_assembly"
VALIDATION_SCHEMA = "hermes.houdini.procedural_district_validation"
SCHEMA_VERSION = "1.0"
MAX_LOTS = 16
DEFAULT_COLUMNS = 4
PROFILE_NAMES = {0: "block", 1: "terrace", 2: "needle"}
PROFILE_COLORS = {
    "block": (0.24, 0.48, 0.72),
    "terrace": (0.78, 0.42, 0.18),
    "needle": (0.34, 0.64, 0.39),
}
_SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,47}\Z")

_FLOAT_RANGES = {
    "block_width": (3.4, 4.4),
    "block_depth": (3.2, 4.2),
    "block_height": (4.0, 8.0),
    "block_center": (2.8, 4.8),
    "terrace_width": (2.6, 3.4),
    "terrace_depth": (2.2, 3.0),
    "terrace_height": (7.0, 14.0),
    "terrace_center": (4.3, 7.8),
    "needle_width": (1.5, 2.4),
    "needle_depth": (1.5, 2.4),
    "needle_height": (12.0, 20.0),
    "needle_center": (6.8, 10.8),
}


def _finite(value: Any, label: str, *, minimum: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return result


def _interpolate(start: float, end: float, index: int, count: int) -> float:
    if count == 1:
        return round(start, 6)
    return round(start + ((end - start) * (index / (count - 1))), 6)


def _round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def _append_jsonl(path: str, payload: dict[str, Any]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _write_json_exclusive(path: str, payload: dict[str, Any]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _tag(node: Any, *, category: str, role: str, created_by: str, scope: str) -> str:
    stable_id = make_id(category, scope)
    node.setUserData("hermes_id", stable_id)
    node.setUserData("hermes_role", role)
    node.setUserData("hermes_created_by", created_by)
    node.setUserData("hermes_manifest_version", "1")
    return stable_id


def _set_parm(node: Any, name: str, value: Any) -> None:
    parm = node.parm(name)
    parm_tuple = node.parmTuple(name)
    if parm is not None:
        parm.set(value)
    elif parm_tuple is not None:
        parm_tuple.set(value)
    else:
        raise ValueError(f"node {node.path()} has no parameter {name}")


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "sha256": _sha256(path),
    }


def _geometry_node_metrics(node: Any) -> dict[str, Any]:
    geometry = node.geometry()
    bounds = geometry.boundingBox()
    values = [*bounds.minvec(), *bounds.maxvec()]
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError(f"node has non-finite bounds: {node.path()}")
    return {
        "points": int(geometry.pointCount()),
        "primitives": int(geometry.primCount()),
        "vertices": int(geometry.vertexCount()),
        "bounds": [list(bounds.minvec()), list(bounds.maxvec())],
    }


def build_district_plan(
    *,
    source_node_path: str,
    output_dir: str,
    base_seed: int = 1601,
    count: int = 12,
    seed_step: int = 53,
    columns: int = DEFAULT_COLUMNS,
    lot_spacing: float = 6.0,
) -> dict[str, Any]:
    """Return a deterministic JSON-only plan for bounded lot generation and placement."""
    if not isinstance(source_node_path, str) or not source_node_path.startswith("/"):
        raise ValueError("source_node_path must be an absolute Houdini path")
    output = Path(output_dir).expanduser()
    if not output.is_absolute():
        raise ValueError("output_dir must be absolute")
    if not isinstance(count, int) or isinstance(count, bool) or not 4 <= count <= MAX_LOTS:
        raise ValueError(f"count must be between 4 and {MAX_LOTS}")
    if not isinstance(base_seed, int) or isinstance(base_seed, bool) or base_seed < 0:
        raise ValueError("base_seed must be a non-negative integer")
    if not isinstance(seed_step, int) or isinstance(seed_step, bool) or seed_step < 1:
        raise ValueError("seed_step must be a positive integer")
    last_seed = base_seed + ((count - 1) * seed_step)
    if last_seed > 2_147_483_647:
        raise ValueError("seed range exceeds Houdini's signed integer range")
    if not isinstance(columns, int) or isinstance(columns, bool) or not 2 <= columns <= 4:
        raise ValueError("columns must be between 2 and 4")
    spacing = _finite(lot_spacing, "lot_spacing", minimum=5.5)
    if spacing > 20.0:
        raise ValueError("lot_spacing must be <= 20")

    rows = math.ceil(count / columns)
    candidates: list[dict[str, Any]] = []
    for index in range(count):
        ratio = index / (count - 1)
        style_index = _round_half_up(2.0 * ratio)
        seed = base_seed + (index * seed_step)
        column = index % columns
        row = index // columns
        x = round((column - ((columns - 1) / 2.0)) * spacing, 6)
        z = round((((rows - 1) / 2.0) - row) * spacing, 6)
        controls = {
            name: _interpolate(value_range[0], value_range[1], index, count)
            for name, value_range in _FLOAT_RANGES.items()
        }
        candidates.append(
            {
                "id": f"lot_{index:03d}",
                "index": index,
                "seed": seed,
                "style_index": style_index,
                "style": PROFILE_NAMES[style_index],
                "controls": controls,
                "placement": {
                    "x": x,
                    "y": 0.0,
                    "z": z,
                    "rotation_y": float((seed % 4) * 90),
                },
                "geometry_path": str(output / f"district_lot_{index}_seed_{seed}.bgeo.sc"),
                "lineage": {
                    "source_recipe": "sop.procedural_building_lot@1.0.0",
                    "generator": "native Wedge TOP -> native ROP Geometry Output TOP",
                    "automatic_ranking": False,
                },
                "human_rating": {"score": None, "notes": "", "selected": False},
            }
        )
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
        "recipes": {
            "source": {"id": "sop.procedural_building_lot", "version": "1.0.0"},
            "top": {"id": "top.procedural_district", "version": "1.0.0"},
        },
        "controls": {
            "base_seed": base_seed,
            "count": count,
            "seed_step": seed_step,
            "columns": columns,
            "rows": rows,
            "lot_spacing": spacing,
            "float_ranges": {key: list(value) for key, value in _FLOAT_RANGES.items()},
        },
        "profiles": [PROFILE_NAMES[index] for index in sorted(PROFILE_NAMES)],
        "selection": {"method": "human", "winner": None, "automatic_ranking": False},
        "candidates": candidates,
    }


def _plan_from_topnet(topnet: Any) -> dict[str, Any]:
    raw = topnet.userData("hermes_district_plan")
    if not raw:
        raise ValueError(f"TOP network is not a Hermes district graph: {topnet.path()}")
    plan = json.loads(raw)
    if plan.get("schema") != PLAN_SCHEMA or plan.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported or invalid district plan metadata")
    return plan


def _recipe_fragment(
    recipe_id: str, parent_path: str, inputs: dict[str, Any], ref_prefix: str
) -> dict[str, Any]:
    register_bundled_recipes()
    entry = REGISTRY.resolve(recipe_id, "1.0.0")
    if entry is None or entry.kind != "recipe":
        raise ValueError(f"registered recipe not found: {recipe_id}@1.0.0")
    return entry.handler(
        parent_path=parent_path,
        inputs=inputs,
        ref_prefix=ref_prefix,
        position_offset=[0.0, 0.0],
    )


def _wedge_specs(source: Any, plan: dict[str, Any]) -> list[dict[str, Any]]:
    source_path = source.path()
    controls = plan["controls"]
    last_seed = plan["candidates"][-1]["seed"]
    target = {
        "style_index": f"{source_path}/DISTRICT_PROFILE_SWITCH/input",
        "block_width": f"{source_path}/DISTRICT_BLOCK_TOWER/sizex",
        "block_depth": f"{source_path}/DISTRICT_BLOCK_TOWER/sizez",
        "block_height": f"{source_path}/DISTRICT_BLOCK_TOWER/sizey",
        "block_center": f"{source_path}/DISTRICT_BLOCK_TOWER/ty",
        "terrace_width": f"{source_path}/DISTRICT_TERRACE_TOWER/sizex",
        "terrace_depth": f"{source_path}/DISTRICT_TERRACE_TOWER/sizez",
        "terrace_height": f"{source_path}/DISTRICT_TERRACE_TOWER/sizey",
        "terrace_center": f"{source_path}/DISTRICT_TERRACE_TOWER/ty",
        "needle_width": f"{source_path}/DISTRICT_NEEDLE_TOWER/sizex",
        "needle_depth": f"{source_path}/DISTRICT_NEEDLE_TOWER/sizez",
        "needle_height": f"{source_path}/DISTRICT_NEEDLE_TOWER/sizey",
        "needle_center": f"{source_path}/DISTRICT_NEEDLE_TOWER/ty",
    }
    specs = [
        {"name": "seed", "type": 2, "range": [controls["base_seed"], last_seed]},
        {"name": "style_index", "type": 2, "range": [0, 2], "target": target["style_index"]},
    ]
    specs.extend(
        {
            "name": name,
            "type": 0,
            "range": list(controls["float_ranges"][name]),
            "target": target[name],
        }
        for name in _FLOAT_RANGES
    )
    return specs


def build_district_graph(
    *,
    output_dir: str,
    checkpoint_dir: str,
    log_path: str,
    source_name: str = "HERMES_DISTRICT_SOURCE",
    network_name: str = "HERMES_PDG_DISTRICT",
    base_seed: int = 1601,
    count: int = 12,
    seed_step: int = 53,
    columns: int = DEFAULT_COLUMNS,
    lot_spacing: float = 6.0,
    scheduler_seconds_per_item: float = 30.0,
    scheduler_memory_mb: int = 2048,
) -> ToolResult:
    """Checkpoint and build the registered native SOP source plus TOP work-item graph."""
    hou = get_hou()
    if not _SAFE_NAME.fullmatch(source_name) or not _SAFE_NAME.fullmatch(network_name):
        raise ValueError("source_name and network_name must be safe Houdini names")
    seconds = _finite(scheduler_seconds_per_item, "scheduler_seconds_per_item", minimum=1.0)
    if seconds > 120.0:
        raise ValueError("scheduler_seconds_per_item must be <= 120")
    if (
        not isinstance(scheduler_memory_mb, int)
        or isinstance(scheduler_memory_mb, bool)
        or not 512 <= scheduler_memory_mb <= 8192
    ):
        raise ValueError("scheduler_memory_mb must be between 512 and 8192")
    obj = hou.node("/obj")
    tasks = hou.node("/tasks")
    if obj is None or tasks is None:
        raise ValueError("/obj and /tasks contexts are required")
    if obj.node(source_name) is not None or tasks.node(network_name) is not None:
        raise ValueError("district source or TOP network already exists")
    source_path = f"/obj/{source_name}/OUT_BUILDING"
    plan = build_district_plan(
        source_node_path=source_path,
        output_dir=output_dir,
        base_seed=base_seed,
        count=count,
        seed_step=seed_step,
        columns=columns,
        lot_spacing=lot_spacing,
    )
    output_pattern = str(Path(output_dir) / "district_lot_`@wedgeindex`_seed_`@seed`.bgeo.sc")
    protected = [candidate["geometry_path"] for candidate in plan["candidates"]]
    existing = [path for path in protected if os.path.exists(path)]
    if existing:
        raise FileExistsError(f"refusing existing district geometry: {existing[0]}")
    os.makedirs(output_dir, exist_ok=True)
    checkpoint = save_checkpoint(checkpoint_dir, f"district_{network_name.lower()}")
    source = None
    topnet = None
    changed: list[ChangedNode] = []
    created_by = "tool:district.build@1.0.0"
    try:
        with hou.undos.group(f"Hermes build {network_name}"):
            source = obj.createNode("geo", node_name=source_name, run_init_scripts=False)
            topnet = tasks.createNode("topnet", node_name=network_name, exact_type_name=True)
            source_id = _tag(
                source,
                category="Object",
                role="district_source_network",
                created_by=created_by,
                scope=f"district:{network_name}:source",
            )
            topnet_id = _tag(
                topnet,
                category="Top",
                role="district_work_item_network",
                created_by=created_by,
                scope=f"district:{network_name}:topnet",
            )
            changed.extend(
                [
                    ChangedNode(source_id, source.path(), "created"),
                    ChangedNode(topnet_id, topnet.path(), "created"),
                ]
            )
            source.setComment(
                "Three editable native-SOP massing profiles; lot placement happens downstream"
            )
            topnet.setComment(
                "One-slot local PDG district generation; no Python TOP and no automatic ranking"
            )

        source_fragment = _recipe_fragment(
            "sop.procedural_building_lot",
            source.path(),
            {"run_code": "DISTRICT", "candidate_index": 0, "bevel_offset": 0.08},
            "src_",
        )
        source_batch = apply_batch(
            batch_id=f"district-source-{source_name.lower()}",
            operations=source_fragment["operations"],
            checkpoint_dir=checkpoint_dir,
            log_path=log_path,
            label="Hermes instantiate district building source",
            checkpoint_stem="district_source_recipe",
        )
        changed.extend(source_batch.changed_nodes)
        top_fragment = _recipe_fragment(
            "top.procedural_district",
            topnet.path(),
            {
                "source_sop_path": source_path,
                "output_pattern": output_pattern,
                "temp_dir": str(Path(output_dir) / "pdg_temp"),
                "lot_count": count,
                "seconds_per_item": seconds,
                "memory_mb": scheduler_memory_mb,
            },
            "top_",
        )
        top_batch = apply_batch(
            batch_id=f"district-top-{network_name.lower()}",
            operations=top_fragment["operations"],
            checkpoint_dir=checkpoint_dir,
            log_path=log_path,
            label="Hermes instantiate district TOP recipe",
            checkpoint_stem="district_top_recipe",
        )
        changed.extend(top_batch.changed_nodes)

        scheduler = topnet.node("LOCAL_BOUNDED")
        wedge = topnet.node("TOP_WEDGE_LOTS")
        cache = topnet.node("CACHE_LOT_GEOMETRY")
        output = topnet.node("OUT_LOTS")
        if None in (scheduler, wedge, cache, output):
            raise RuntimeError("district TOP recipe did not create its named contracts")
        _set_parm(topnet, "topscheduler", scheduler.name())
        specs = _wedge_specs(source, plan)
        _set_parm(wedge, "wedgecount", count)
        _set_parm(wedge, "seed", base_seed)
        _set_parm(wedge, "wedgeattributes", len(specs))
        for slot, spec in enumerate(specs, start=1):
            _set_parm(wedge, f"name{slot}", spec["name"])
            _set_parm(wedge, f"type{slot}", spec["type"])
            _set_parm(wedge, f"wedgetype{slot}", 0)
            range_name = "intrange" if spec["type"] == 2 else "floatrange"
            _set_parm(wedge, f"{range_name}{slot}", spec["range"])
            _set_parm(wedge, f"exportchannel{slot}", int("target" in spec))
            if "target" in spec:
                if hou.parm(spec["target"]) is None:
                    raise ValueError(f"district Wedge target parameter missing: {spec['target']}")
                _set_parm(wedge, f"channel{slot}", spec["target"])
                _set_parm(wedge, f"valuetype{slot}", 1)
        topnet.setUserData("hermes_district_plan", json.dumps(plan, sort_keys=True))
        topnet.setUserData("hermes_source_recipe", "sop.procedural_building_lot@1.0.0")
        topnet.setUserData("hermes_top_recipe", "top.procedural_district@1.0.0")
        scheduler.setComment(f"One local slot; {seconds:g}s and {scheduler_memory_mb} MB per item")
        wedge.setComment("Fourteen declared numeric attributes; channel targets never edit the HIP")
        cache.setComment("Foreground one-frame .bgeo.sc cache; immutable paths; no background save")
        output.setDisplayFlag(True)
    except Exception:
        for node in (topnet, source):
            if node is not None and node.parent() is not None:
                node.destroy()
        raise

    record = {
        "schema": "hermes.houdini.procedural_district_build",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "checkpoint": checkpoint,
        "source_path": source.path(),
        "source_output_path": source_path,
        "network_path": topnet.path(),
        "plan": plan,
    }
    _append_jsonl(log_path, record)
    return ToolResult(
        status=Status.SUCCESS,
        changed_nodes=changed,
        checkpoint=checkpoint,
        artifacts=[log_path],
        data={
            "source_path": source.path(),
            "source_output_path": source_path,
            "network_path": topnet.path(),
            "scheduler_path": scheduler.path(),
            "wedge_path": wedge.path(),
            "cache_path": cache.path(),
            "output_path": output.path(),
            "plan": plan,
        },
    )


def generate_district_manifest(*, topnet_path: str, output_path: str) -> dict[str, Any]:
    """Generate static native Wedge work items and freeze their exact values to new JSON."""
    hou = get_hou()
    topnet = hou.node(topnet_path)
    if topnet is None:
        raise ValueError(f"TOP network not found: {topnet_path}")
    plan = _plan_from_topnet(topnet)
    wedge = topnet.node("TOP_WEDGE_LOTS")
    if wedge is None or wedge.type().name() != "wedge":
        raise ValueError("managed district Wedge TOP is missing")
    wedge.dirtyAllWorkItems(False)
    wedge.generateStaticWorkItems(block=True)
    pdg_node = wedge.getPDGNode()
    items = list(pdg_node.workItems) if pdg_node is not None else []
    if len(items) != len(plan["candidates"]):
        raise ValueError(f"Wedge generated {len(items)} items; expected {len(plan['candidates'])}")
    generated: list[dict[str, Any]] = []
    for expected, item in zip(plan["candidates"], items, strict=True):
        values = item.attribValues()
        controls = {name: round(float(values[name]), 6) for name in _FLOAT_RANGES}
        actual = {
            "id": expected["id"],
            "work_item_name": item.name,
            "wedgeindex": int(values["wedgeindex"]),
            "seed": int(values["seed"]),
            "style_index": int(values["style_index"]),
            "style": PROFILE_NAMES[int(values["style_index"])],
            "controls": controls,
            "placement": expected["placement"],
            "geometry_path": expected["geometry_path"],
            "human_rating": expected["human_rating"],
        }
        if actual["wedgeindex"] != expected["index"] or actual["seed"] != expected["seed"]:
            raise ValueError(f"Wedge identity mismatch for {expected['id']}")
        if actual["style_index"] != expected["style_index"]:
            raise ValueError(f"Wedge style mismatch for {expected['id']}")
        for name, value in controls.items():
            if not math.isclose(value, expected["controls"][name], rel_tol=0.0, abs_tol=1e-5):
                raise ValueError(f"Wedge attribute mismatch for {expected['id']}.{name}")
        generated.append(actual)
    manifest = {
        **plan,
        "generated_by": "tool:district.generate@1.0.0",
        "network_path": topnet.path(),
        "generated_work_items": generated,
    }
    _write_json_exclusive(output_path, manifest)
    return {
        "artifact": output_path,
        "network_path": topnet.path(),
        "work_items": len(generated),
        "items": generated,
        "selection": plan["selection"],
    }


def _target_parms(source: Any, plan: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for spec in _wedge_specs(source, plan):
        target = spec.get("target")
        if target:
            parm = get_hou().parm(target)
            if parm is None:
                raise ValueError(f"district target parameter missing: {target}")
            values[target] = parm.eval()
    return values


def cook_district_graph(
    *,
    topnet_path: str,
    manifest_path: str,
    result_path: str,
    scene_path: str,
    log_path: str,
    estimate: dict[str, Any],
) -> ToolResult:
    """Run the foreground one-slot lot cache after explicit local-process consent."""
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
    if normalized["work_items"] != len(plan["candidates"]):
        raise ValueError("estimate.work_items must equal the managed district lot count")
    with open(manifest_path, encoding="utf-8") as stream:
        manifest = json.load(stream)
    if (
        manifest.get("schema") != PLAN_SCHEMA
        or manifest.get("network_path") != topnet.path()
        or manifest.get("candidates") != plan["candidates"]
    ):
        raise ValueError("manifest does not match the managed district plan")
    if not scene_path.endswith(".hipnc"):
        raise ValueError("scene_path must use the non-commercial .hipnc extension")
    for protected in (result_path, scene_path):
        if os.path.exists(protected):
            raise FileExistsError(f"refusing to overwrite existing artifact: {protected}")
    existing = [
        item["geometry_path"]
        for item in plan["candidates"]
        if os.path.exists(item["geometry_path"])
    ]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing geometry: {existing[0]}")
    cache = topnet.node("CACHE_LOT_GEOMETRY")
    if cache is None or cache.type().name() != "ropgeometry":
        raise ValueError("managed district ROP Geometry TOP is missing")
    source = hou.node(plan["source_node_path"]).parent()
    if source is None:
        raise ValueError("district source network was deleted")
    source_before = _target_parms(source, plan)
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
    if _target_parms(source, plan) != source_before:
        raise RuntimeError("Wedge target overrides mutated source parameters")

    pdg_node = cache.getPDGNode()
    work_items = list(pdg_node.workItems) if pdg_node is not None else []
    actuals: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    total_bytes = 0
    for item in work_items:
        values = item.attribValues()
        index = int(values["wedgeindex"])
        expected = plan["candidates"][index]
        outputs = [file.path for file in item.outputFiles if file.path.endswith(".bgeo.sc")]
        state = str(item.state)
        if "CookedSuccess" not in state or outputs != [expected["geometry_path"]]:
            failures.append(
                {"work_item": item.name, "state": state, "outputs": outputs, "expected": expected}
            )
            continue
        metrics = _geometry_file_metrics(outputs[0])
        total_bytes += metrics["file_bytes"]
        height = metrics["bounds"][1][1] - metrics["bounds"][0][1]
        if (
            metrics["points"] < 8
            or metrics["primitives"] < 6
            or metrics["points"] > policy.max_points
            or metrics["primitives"] > policy.max_primitives
            or height <= 1.0
            or height > 25.0
        ):
            failures.append(
                {"work_item": item.name, "state": "geometry_contract_failed", "metrics": metrics}
            )
            continue
        actuals.append(
            {
                "id": expected["id"],
                "work_item_name": item.name,
                "state": state,
                "seed": expected["seed"],
                "style_index": expected["style_index"],
                "style": expected["style"],
                "controls": expected["controls"],
                "placement": expected["placement"],
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
    if len(actuals) != len(plan["candidates"]):
        failures.append(
            {"state": "count_mismatch", "actual": len(actuals), "expected": len(plan["candidates"])}
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
        "candidates": actuals,
        "failures": failures,
    }
    _write_json_exclusive(result_path, result_document)
    _append_jsonl(
        log_path,
        {
            "schema": "hermes.houdini.procedural_district_cook",
            "schema_version": SCHEMA_VERSION,
            "timestamp_unix": time.time(),
            **result_document,
        },
    )
    status = Status.SUCCESS if not failures else Status.ERROR
    result = ToolResult(
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
        result.errors.append(f"{len(failures)} procedural district validation failures")
    return result


def build_district_assembly(
    *,
    result_path: str,
    checkpoint_dir: str,
    log_path: str,
    manifest_path: str,
    assembly_name: str = "HERMES_DISTRICT_ASSEMBLY",
    camera_name: str = "HERMES_DISTRICT_CAMERA",
    gallery_spacing: float = 6.0,
) -> ToolResult:
    """Build editable district and no-winner gallery branches from successful lot caches."""
    hou = get_hou()
    if not _SAFE_NAME.fullmatch(assembly_name) or not _SAFE_NAME.fullmatch(camera_name):
        raise ValueError("assembly_name and camera_name must be safe Houdini names")
    spacing = _finite(gallery_spacing, "gallery_spacing", minimum=5.5)
    with open(result_path, encoding="utf-8") as stream:
        result_document = json.load(stream)
    if result_document.get("schema") != RESULT_SCHEMA or result_document.get("failures"):
        raise ValueError("assembly requires a successful procedural district result")
    candidates = result_document.get("candidates", [])
    if not candidates:
        raise ValueError("district result contains no candidates")
    obj = hou.node("/obj")
    if obj.node(assembly_name) is not None or obj.node(camera_name) is not None:
        raise ValueError("district assembly or camera already exists")
    checkpoint = save_checkpoint(checkpoint_dir, f"district_assembly_{assembly_name.lower()}")
    created: list[Any] = []
    changed: list[ChangedNode] = []
    created_by = "tool:district.assemble@1.0.0"
    columns = min(DEFAULT_COLUMNS, math.ceil(math.sqrt(len(candidates))))
    rows = math.ceil(len(candidates) / columns)
    try:
        with hou.undos.group(f"Hermes build {assembly_name}"):
            assembly = obj.createNode("geo", node_name=assembly_name, run_init_scripts=False)
            camera = obj.createNode("cam", node_name=camera_name)
            created.extend((assembly, camera))
            assembly_id = _tag(
                assembly,
                category="Object",
                role="procedural_district_assembly",
                created_by=created_by,
                scope=f"district:{assembly_name}:assembly",
            )
            camera_id = _tag(
                camera,
                category="Object",
                role="procedural_district_camera",
                created_by=created_by,
                scope=f"district:{assembly_name}:camera",
            )
            changed.extend(
                [
                    ChangedNode(assembly_id, assembly.path(), "created"),
                    ChangedNode(camera_id, camera.path(), "created"),
                ]
            )
            assembly.setComment(
                "Editable cached lot assembly plus a separate equal-scale no-winner gallery"
            )
            camera.setComment("Explicit perspective camera for bounded district previews")
            camera.parmTuple("t").set((24.0, 22.0, 30.0))
            camera.parmTuple("r").set((-24.0, 38.0, 0.0))
            camera.parm("focal").set(52.0)

            district_merge = assembly.createNode("merge", node_name="MERGE_DISTRICT_LOTS")
            gallery_merge = assembly.createNode("merge", node_name="MERGE_GALLERY_CANDIDATES")
            district_out = assembly.createNode("null", node_name="OUT_DISTRICT")
            gallery_out = assembly.createNode("null", node_name="OUT_GALLERY")
            created.extend((district_merge, gallery_merge, district_out, gallery_out))
            for node, role in (
                (district_merge, "district_lot_merge"),
                (gallery_merge, "district_gallery_merge"),
                (district_out, "district_output"),
                (gallery_out, "district_gallery_output"),
            ):
                stable_id = _tag(
                    node,
                    category="Sop",
                    role=role,
                    created_by=created_by,
                    scope=f"district:{assembly_name}:{role}",
                )
                changed.append(ChangedNode(stable_id, node.path(), "created"))

            gallery_labels: list[Any] = []
            for index, candidate in enumerate(candidates):
                file_node = assembly.createNode("file", node_name=f"FILE_LOT_{index:03d}")
                color = assembly.createNode("color", node_name=f"COLOR_LOT_{index:03d}")
                district_xform = assembly.createNode("xform", node_name=f"PLACE_LOT_{index:03d}")
                gallery_xform = assembly.createNode("xform", node_name=f"GALLERY_LOT_{index:03d}")
                label = assembly.createNode("font", node_name=f"LABEL_LOT_{index:03d}")
                label_xform = assembly.createNode("xform", node_name=f"LABEL_LAYOUT_{index:03d}")
                created.extend(
                    (file_node, color, district_xform, gallery_xform, label, label_xform)
                )
                file_node.parm("file").set(candidate["geometry_path"])
                color.setInput(0, file_node)
                color.parmTuple("color").set(PROFILE_COLORS[candidate["style"]])
                district_xform.setInput(0, color)
                placement = candidate["placement"]
                district_xform.parmTuple("t").set((placement["x"], placement["y"], placement["z"]))
                district_xform.parm("ry").set(placement["rotation_y"])
                district_merge.setInput(index, district_xform)

                gallery_xform.setInput(0, color)
                column = index % columns
                row = index // columns
                gallery_x = (column - ((columns - 1) / 2.0)) * spacing
                gallery_y = (((rows - 1) / 2.0) - row) * spacing * 1.35
                gallery_xform.parm("tx").set(gallery_x)
                gallery_xform.parm("ty").set(gallery_y)
                gallery_merge.setInput(index, gallery_xform)
                label.parm("text").set(
                    f"L{index:02d} {candidate['style']} seed {candidate['seed']}"
                )
                label.parm("halign").set("center")
                label.parm("valign").set("middle")
                label.parm("fontsize").set(0.3)
                label_xform.setInput(0, label)
                label_xform.parm("tx").set(gallery_x)
                label_xform.parm("ty").set(gallery_y - 0.85)
                gallery_labels.append(label_xform)

                for node, role in (
                    (file_node, "district_cache_reader"),
                    (color, "district_profile_color"),
                    (district_xform, "district_lot_placement"),
                    (gallery_xform, "district_gallery_placement"),
                    (label, "district_gallery_label"),
                    (label_xform, "district_gallery_label_layout"),
                ):
                    stable_id = _tag(
                        node,
                        category="Sop",
                        role=role,
                        created_by=created_by,
                        scope=f"district:{assembly_name}:{candidate['id']}:{role}",
                    )
                    node.setUserData("hermes_candidate_id", candidate["id"])
                    node.setUserData("hermes_seed", str(candidate["seed"]))
                    node.setUserData("hermes_profile", candidate["style"])
                    node.setUserData(
                        "hermes_human_rating", json.dumps(candidate["human_rating"], sort_keys=True)
                    )
                    changed.append(ChangedNode(stable_id, node.path(), "created"))
                file_node.setComment(
                    f"{candidate['id']} | {candidate['style']} | seed {candidate['seed']} | rating unassigned"
                )
                file_node.setPosition((column * 4.0, 10.0 - (row * 7.0)))
                color.setPosition((column * 4.0, 8.5 - (row * 7.0)))
                district_xform.setPosition((column * 4.0 - 0.8, 7.0 - (row * 7.0)))
                gallery_xform.setPosition((column * 4.0 + 0.8, 7.0 - (row * 7.0)))
                label.setPosition((column * 4.0 + 2.0, 8.5 - (row * 7.0)))
                label_xform.setPosition((column * 4.0 + 2.0, 7.0 - (row * 7.0)))

            for index, label_xform in enumerate(gallery_labels, start=len(candidates)):
                gallery_merge.setInput(index, label_xform)
            ground = assembly.createNode("box", node_name="DISTRICT_GROUND")
            ground_color = assembly.createNode("color", node_name="DISTRICT_GROUND_COLOR")
            created.extend((ground, ground_color))
            plan_columns = max(1, len({candidate["placement"]["x"] for candidate in candidates}))
            plan_rows = max(1, len({candidate["placement"]["z"] for candidate in candidates}))
            ground.parmTuple("size").set(
                (plan_columns * spacing + 1.5, 0.1, plan_rows * spacing + 1.5)
            )
            ground.parm("ty").set(-0.05)
            ground_color.setInput(0, ground)
            ground_color.parmTuple("color").set((0.08, 0.09, 0.11))
            district_merge.setInput(len(candidates), ground_color)
            for node, role in (
                (ground, "district_ground"),
                (ground_color, "district_ground_color"),
            ):
                stable_id = _tag(
                    node,
                    category="Sop",
                    role=role,
                    created_by=created_by,
                    scope=f"district:{assembly_name}:{role}",
                )
                changed.append(ChangedNode(stable_id, node.path(), "created"))

            district_out.setInput(0, district_merge)
            gallery_out.setInput(0, gallery_merge)
            district_out.setDisplayFlag(True)
            district_out.setRenderFlag(True)
            district_out.setComment("Named editable district contract from immutable lot caches")
            gallery_out.setComment(
                "All candidates at equal scale with labels; no automatic winner or ranking"
            )
            district_merge.setPosition((2.0, -15.0))
            gallery_merge.setPosition((8.0, -15.0))
            district_out.setPosition((2.0, -17.0))
            gallery_out.setPosition((8.0, -17.0))
    except Exception:
        for node in reversed(created):
            if node.parent() is not None:
                node.destroy()
        raise

    assembly_document = {
        "schema": ASSEMBLY_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "source_result": result_path,
        "assembly_path": assembly.path(),
        "district_output_path": district_out.path(),
        "gallery_output_path": gallery_out.path(),
        "camera_path": camera.path(),
        "candidate_count": len(candidates),
        "district_merge_inputs": len(candidates) + 1,
        "gallery_merge_inputs": len(candidates) * 2,
        "selection": result_document["selection"],
        "candidates": [
            {
                "id": candidate["id"],
                "seed": candidate["seed"],
                "style": candidate["style"],
                "placement": candidate["placement"],
                "geometry_path": candidate["geometry_path"],
                "sha256": candidate["metrics"]["sha256"],
                "human_rating": candidate["human_rating"],
            }
            for candidate in candidates
        ],
    }
    _write_json_exclusive(manifest_path, assembly_document)
    record = {
        "schema": "hermes.houdini.procedural_district_assembly_build",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "checkpoint": checkpoint,
        **assembly_document,
    }
    _append_jsonl(log_path, record)
    return ToolResult(
        status=Status.SUCCESS,
        changed_nodes=changed,
        checkpoint=checkpoint,
        artifacts=[result_path, manifest_path, log_path],
        data=assembly_document,
    )


def validate_district(
    *,
    topnet_path: str,
    assembly_path: str,
    result_path: str,
    assembly_manifest_path: str,
    output_path: str,
) -> dict[str, Any]:
    """Cook and validate scheduler, caches, assembly, gallery order, and selection invariants."""
    hou = get_hou()
    topnet = hou.node(topnet_path)
    assembly = hou.node(assembly_path)
    if topnet is None or assembly is None:
        raise ValueError("managed TOP network and district assembly must exist")
    plan = _plan_from_topnet(topnet)
    with open(result_path, encoding="utf-8") as stream:
        result = json.load(stream)
    with open(assembly_manifest_path, encoding="utf-8") as stream:
        assembly_manifest = json.load(stream)
    if result.get("schema") != RESULT_SCHEMA or result.get("failures"):
        raise ValueError("district result is missing or contains failures")
    if (
        assembly_manifest.get("schema") != ASSEMBLY_SCHEMA
        or assembly_manifest.get("source_result") != result_path
    ):
        raise ValueError("assembly manifest does not match the district result")
    scheduler = topnet.node("LOCAL_BOUNDED")
    wedge = topnet.node("TOP_WEDGE_LOTS")
    cache = topnet.node("CACHE_LOT_GEOMETRY")
    wait = topnet.node("WAIT_ALL_LOTS")
    output = topnet.node("OUT_LOTS")
    required = {
        "LOCAL_BOUNDED": (scheduler, "localscheduler"),
        "TOP_WEDGE_LOTS": (wedge, "wedge"),
        "CACHE_LOT_GEOMETRY": (cache, "ropgeometry"),
        "WAIT_ALL_LOTS": (wait, "waitforall"),
        "OUT_LOTS": (output, "null"),
    }
    for name, (node, type_name) in required.items():
        if node is None or node.type().name() != type_name:
            raise ValueError(f"managed TOP contract missing or wrong type: {name}")
    if int(scheduler.parm("maxprocs").eval()) != 1:
        raise ValueError("district scheduler must remain at one local slot")
    if int(cache.parm("savebackground").eval()) != 0:
        raise ValueError("district ROP Geometry must not save in the background")
    if any(node.type().name() in {"pythonprocessor", "pythonscript"} for node in topnet.children()):
        raise ValueError("district TOP graph must not contain Python work-item nodes")

    candidates = result["candidates"]
    if len(candidates) != len(plan["candidates"]):
        raise ValueError("district candidate count differs from the immutable plan")
    current_caches = []
    for candidate in candidates:
        metrics = _geometry_file_metrics(candidate["geometry_path"])
        if metrics["sha256"] != candidate["metrics"]["sha256"]:
            raise ValueError(f"district cache changed after validation: {candidate['id']}")
        current_caches.append(
            {"id": candidate["id"], "style": candidate["style"], "metrics": metrics}
        )
    if set(item["style"] for item in current_caches) != set(PROFILE_NAMES.values()):
        raise ValueError("district must preserve block, terrace, and needle profiles")

    district_out = assembly.node("OUT_DISTRICT")
    gallery_out = assembly.node("OUT_GALLERY")
    district_merge = assembly.node("MERGE_DISTRICT_LOTS")
    gallery_merge = assembly.node("MERGE_GALLERY_CANDIDATES")
    if None in (district_out, gallery_out, district_merge, gallery_merge):
        raise ValueError("district assembly contracts are incomplete")
    district_metrics = _geometry_node_metrics(district_out)
    gallery_metrics = _geometry_node_metrics(gallery_out)
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else Policy()
    for label, metrics in (
        ("district", district_metrics),
        ("gallery", gallery_metrics),
    ):
        if metrics["points"] > policy.max_points:
            raise ValueError(
                f"{label} points {metrics['points']} exceed policy {policy.max_points}"
            )
        if metrics["primitives"] > policy.max_primitives:
            raise ValueError(
                f"{label} primitives {metrics['primitives']} exceed policy {policy.max_primitives}"
            )
    if len(district_merge.inputs()) != len(candidates) + 1:
        raise ValueError("district merge input order/count is invalid")
    if len(gallery_merge.inputs()) != len(candidates) * 2:
        raise ValueError("gallery merge must connect every candidate before every label")
    if district_metrics["points"] <= sum(item["metrics"]["points"] for item in current_caches):
        raise ValueError("district output is missing its ground context")
    if gallery_metrics["points"] <= sum(item["metrics"]["points"] for item in current_caches):
        raise ValueError("no-winner gallery is missing its labels")
    if result["selection"] != {"method": "human", "winner": None, "automatic_ranking": False}:
        raise ValueError("district result must preserve unfilled human selection")
    messages = {
        node.path(): {"errors": list(node.errors()), "warnings": list(node.warnings())}
        for node in (topnet, cache, assembly, district_out, gallery_out)
    }
    if any(value["errors"] or value["warnings"] for value in messages.values()):
        raise ValueError(f"managed district nodes report messages: {messages}")
    document = {
        "schema": VALIDATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "houdini": {
            "build": hou.applicationVersionString(),
            "license": hou.licenseCategory().name(),
        },
        "topnet_path": topnet.path(),
        "assembly_path": assembly.path(),
        "candidate_count": len(candidates),
        "profiles": sorted({item["style"] for item in current_caches}),
        "scheduler_slots": 1,
        "background_save": False,
        "cache_total_bytes": sum(item["metrics"]["file_bytes"] for item in current_caches),
        "caches": current_caches,
        "district_metrics": district_metrics,
        "gallery_metrics": gallery_metrics,
        "messages": messages,
        "selection": result["selection"],
        "passed": True,
    }
    _write_json_exclusive(output_path, document)
    return {"artifact": output_path, **document}


__all__ = [
    "ASSEMBLY_SCHEMA",
    "MAX_LOTS",
    "PLAN_SCHEMA",
    "PROFILE_NAMES",
    "RESULT_SCHEMA",
    "VALIDATION_SCHEMA",
    "build_district_assembly",
    "build_district_graph",
    "build_district_plan",
    "cook_district_graph",
    "generate_district_manifest",
    "validate_district",
]
