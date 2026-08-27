"""Bounded Solaris look-development, USD validation, and Karma preview controls.

Validation and planning helpers remain importable without Houdini. HOM, MaterialX VOP
construction, USD stage composition, and rendering are isolated to the public entry points.
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
KARMA_CPU_DELEGATE = "BRAY_HdKarma"
APPRENTICE_RENDER_CEILING = (1280, 720)
_SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,47}\Z")
_USD_PATH = re.compile(r"/(?:[A-Za-z_][A-Za-z0-9_]*)(?:/[A-Za-z_][A-Za-z0-9_]*)*\Z")
_IMAGE_SUFFIXES = {".exr", ".png"}


def _finite(value: Any, label: str, *, minimum: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return result


def _usd_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _USD_PATH.fullmatch(value):
        raise ValueError(f"{label} must be an absolute identifier-only USD prim path")
    return value


def validate_material_specs(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate exactly three explicit, unranked MaterialX candidates."""
    if not isinstance(materials, list) or len(materials) != 3:
        raise ValueError("materials must contain exactly three candidates")
    normalized: list[dict[str, Any]] = []
    names: set[str] = set()
    paths: set[str] = set()
    for index, item in enumerate(materials):
        if not isinstance(item, dict):
            raise ValueError(f"materials[{index}] must be an object")
        required = {"id", "builder_name", "material_path", "base_color", "metalness", "roughness"}
        missing = required - set(item)
        unknown = set(item) - required
        if missing:
            raise ValueError(f"materials[{index}] missing keys: {', '.join(sorted(missing))}")
        if unknown:
            raise ValueError(f"materials[{index}] has unknown keys: {', '.join(sorted(unknown))}")
        candidate_id = item["id"]
        builder_name = item["builder_name"]
        if not isinstance(candidate_id, str) or not _SAFE_NAME.fullmatch(candidate_id):
            raise ValueError(f"materials[{index}].id must be a safe identifier")
        if not isinstance(builder_name, str) or not _SAFE_NAME.fullmatch(builder_name):
            raise ValueError(f"materials[{index}].builder_name must be a safe Houdini name")
        material_path = _usd_path(item["material_path"], f"materials[{index}].material_path")
        color = item["base_color"]
        if not isinstance(color, (list, tuple)) or len(color) != 3:
            raise ValueError(f"materials[{index}].base_color must contain three numbers")
        rgb = [_finite(channel, f"materials[{index}].base_color", minimum=0.0) for channel in color]
        if any(channel > 1.0 for channel in rgb):
            raise ValueError(f"materials[{index}].base_color channels must be <= 1")
        metalness = _finite(item["metalness"], f"materials[{index}].metalness", minimum=0.0)
        roughness = _finite(item["roughness"], f"materials[{index}].roughness", minimum=0.0)
        if metalness > 1.0 or roughness > 1.0:
            raise ValueError(f"materials[{index}] metalness and roughness must be <= 1")
        if builder_name in names or material_path in paths:
            raise ValueError("material builder names and USD paths must be unique")
        names.add(builder_name)
        paths.add(material_path)
        normalized.append(
            {
                "id": candidate_id,
                "builder_name": builder_name,
                "material_path": material_path,
                "base_color": rgb,
                "metalness": metalness,
                "roughness": roughness,
            }
        )
    return normalized


def validate_preview_spec(
    *, output_path: str, width: int, height: int, frame: float, time_limit: float, max_threads: int
) -> dict[str, Any]:
    """Validate a one-frame Apprentice-safe CPU preview specification."""
    path = Path(output_path).expanduser()
    if not path.is_absolute() or path.suffix.lower() not in _IMAGE_SUFFIXES:
        raise ValueError("output_path must be an absolute .exr or .png path")
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise ValueError("width must be a positive integer")
    if not isinstance(height, int) or isinstance(height, bool) or height < 1:
        raise ValueError("height must be a positive integer")
    ceiling_w, ceiling_h = APPRENTICE_RENDER_CEILING
    if width > ceiling_w or height > ceiling_h:
        raise ValueError(f"resolution {width}x{height} exceeds Apprentice ceiling 1280x720")
    frame_value = _finite(frame, "frame")
    limit = _finite(time_limit, "time_limit", minimum=1.0)
    if not isinstance(max_threads, int) or isinstance(max_threads, bool) or max_threads < 1:
        raise ValueError("max_threads must be a positive integer")
    return {
        "output_path": str(path),
        "width": width,
        "height": height,
        "frame": frame_value,
        "time_limit": limit,
        "max_threads": max_threads,
        "delegate": KARMA_CPU_DELEGATE,
    }


def _set_parm(node: Any, name: str, value: Any) -> None:
    parm = node.parm(name)
    parm_tuple = node.parmTuple(name)
    if parm is not None:
        parm.set(value)
    elif parm_tuple is not None:
        parm_tuple.set(value)
    else:
        raise ValueError(f"node {node.path()} has no parameter {name}")


def _tag(node: Any, *, category: str, role: str, created_by: str, scope: str) -> str:
    stable_id = make_id(category, scope)
    node.setUserData("hermes_id", stable_id)
    node.setUserData("hermes_role", role)
    node.setUserData("hermes_created_by", created_by)
    node.setUserData("hermes_manifest_version", "1")
    return stable_id


def _append_jsonl(path: str, payload: dict[str, Any]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
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


def populate_materialx_library(
    *,
    material_library_path: str,
    materials: list[dict[str, Any]],
    checkpoint_dir: str,
    log_path: str,
) -> ToolResult:
    """Checkpoint, then add three native MaterialX builder subnets to a Material Library LOP."""
    hou = get_hou()
    import voptoolutils

    specs = validate_material_specs(materials)
    library = hou.node(material_library_path)
    if library is None or library.type().category().name() != "Lop":
        raise ValueError(f"Material Library LOP not found: {material_library_path}")
    if library.type().name() != "materiallibrary":
        raise ValueError(f"node is not materiallibrary: {material_library_path}")
    existing = [item["builder_name"] for item in specs if library.node(item["builder_name"])]
    if existing:
        raise ValueError(f"material builders already exist: {', '.join(existing)}")

    checkpoint = save_checkpoint(checkpoint_dir, "solaris_materialx")
    created: list[Any] = []
    changed: list[ChangedNode] = []
    old_values: dict[str, Any] = {}
    result = ToolResult(status=Status.SUCCESS, checkpoint=checkpoint)
    created_by = "tool:solaris.materialx.populate@1.0.0"
    try:
        old_count = int(library.parm("materials").eval())
        old_values["materials"] = old_count
        for index in range(1, old_count + 1):
            for name in (f"matnode{index}", f"matpath{index}"):
                old_values[name] = library.parm(name).eval()
        with hou.undos.group("Hermes populate MaterialX lookdev candidates"):
            _set_parm(library, "materials", 3)
            for index, spec in enumerate(specs, start=1):
                builder = voptoolutils._setupMtlXBuilderSubnet(
                    destination_node=library, name=spec["builder_name"]
                )
                created.append(builder)
                builder_id = _tag(
                    builder,
                    category="Vop",
                    role=f"material_candidate_{spec['id']}",
                    created_by=created_by,
                    scope=f"{material_library_path}:{spec['builder_name']}",
                )
                surface = next(
                    child
                    for child in builder.children()
                    if child.type().name() == "mtlxstandard_surface"
                )
                _tag(
                    surface,
                    category="Vop",
                    role=f"material_surface_{spec['id']}",
                    created_by=created_by,
                    scope=f"{surface.path()}:surface",
                )
                _set_parm(surface, "base_color", spec["base_color"])
                _set_parm(surface, "metalness", spec["metalness"])
                _set_parm(surface, "specular_roughness", spec["roughness"])
                _set_parm(library, f"matnode{index}", builder.path())
                _set_parm(library, f"matpath{index}", spec["material_path"])
                changed.append(ChangedNode(builder_id, builder.path(), "created"))
            changed.append(
                ChangedNode(library.userData("hermes_id") or "", library.path(), "modified")
            )
        record = _record(
            "solaris_materialx",
            {
                "status": "success",
                "checkpoint": checkpoint,
                "material_library_path": material_library_path,
                "materials": specs,
                "automatic_ranking": False,
            },
        )
        _append_jsonl(log_path, record)
        result.changed_nodes = changed
        result.artifacts = [log_path]
        result.data = {
            "material_library_path": material_library_path,
            "materials": specs,
            "selection": {"method": "human", "winner": None, "automatic_ranking": False},
        }
        return result
    except Exception as exc:
        for node in reversed(created):
            if node.parent() is not None:
                node.destroy()
        library.parm("materials").set(old_values["materials"])
        for name, value in old_values.items():
            if name != "materials" and library.parm(name) is not None:
                library.parm(name).set(value)
        result.status = Status.ERROR
        result.errors.append(f"{type(exc).__name__}: {exc}")
        result.data = {"rolled_back": True}
        try:
            _append_jsonl(
                log_path,
                _record(
                    "solaris_materialx",
                    {
                        "status": "rolled_back",
                        "checkpoint": checkpoint,
                        "material_library_path": material_library_path,
                        "error": result.errors[0],
                    },
                ),
            )
            result.artifacts = [log_path]
        except Exception as log_exc:
            result.status = Status.PARTIAL
            result.errors.append(f"provenance failure: {log_exc}")
        return result


def _managed_sop_import(stage_node: Any, source_sop_path: str) -> Any:
    matching = []
    for ancestor in stage_node.inputAncestors():
        sop_path_parm = ancestor.parm("soppath")
        if (
            ancestor.type().name().split("::", 1)[0] == "sopimport"
            and sop_path_parm is not None
            and sop_path_parm.evalAsString() == source_sop_path
        ):
            matching.append(ancestor)
    if len(matching) != 1:
        raise RuntimeError(
            "expected exactly one upstream SOP Import for "
            f"{source_sop_path}, found {len(matching)}"
        )
    return matching[0]


def validate_stage(
    *,
    stage_node_path: str,
    source_sop_path: str,
    expected_paths: list[str],
    binding_prim_path: str,
    max_prims: int = 10000,
    source_start_frame: float = 1.0,
    frame: float | None = None,
) -> dict[str, Any]:
    """Compose one bounded USD stage at an explicit frame and verify its contracts."""
    hou = get_hou()
    from pxr import UsdShade

    if not isinstance(max_prims, int) or isinstance(max_prims, bool) or max_prims < 1:
        raise ValueError("max_prims must be a positive integer")
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    if policy is not None and max_prims > policy.max_primitives:
        raise ValueError("max_prims exceeds command policy.max_primitives")
    frame_value = None if frame is None else _finite(frame, "frame")
    source_start_value = _finite(source_start_frame, "source_start_frame")
    evaluation_frame = hou.frame() if frame_value is None else frame_value
    if not source_start_value.is_integer() or not evaluation_frame.is_integer():
        raise ValueError("source_start_frame and frame must be integer frames")
    source_start = int(source_start_value)
    source_end = int(evaluation_frame)
    if source_start > source_end:
        raise ValueError("source_start_frame must be <= frame")
    source_frames = tuple(range(source_start, source_end + 1))
    if policy is not None and len(source_frames) > policy.max_frames:
        raise ValueError(
            f"source warm-up needs {len(source_frames)} frames > policy {policy.max_frames}"
        )
    paths = [_usd_path(path, "expected_paths item") for path in expected_paths]
    binding_path = _usd_path(binding_prim_path, "binding_prim_path")
    node = hou.node(stage_node_path)
    if node is None or node.type().category().name() != "Lop":
        raise ValueError(f"LOP stage node not found: {stage_node_path}")
    source = hou.node(source_sop_path)
    if source is None or source.type().category().name() != "Sop":
        raise ValueError(f"source SOP node not found: {source_sop_path}")
    original_frame = hou.frame()
    started = time.monotonic()
    try:
        with hou.InterruptableOperation(
            "Hermes bounded USD stage composition",
            "Composing one LOP stage",
            open_interrupt_dialog=False,
        ):
            # A SOP Import LOP can retain an empty external-SOP result after a
            # temporal validation call. Evaluate the declared source in the
            # same explicit global-frame context used by SOP Import, force its
            # output, then dirty and force the managed LOP output.
            for source_frame in source_frames:
                hou.setFrame(source_frame)
                source.cook(force=True)
            source_geometry = source.geometry()
            if source_geometry is None:
                raise RuntimeError(f"source SOP produced no geometry handle: {source_sop_path}")
            source_points = len(source_geometry.points())
            source_primitives = len(source_geometry.prims())
            if policy is not None and source_points > policy.max_points:
                raise RuntimeError(
                    f"source SOP exceeds policy.max_points={policy.max_points}: {source_points}"
                )
            if policy is not None and source_primitives > policy.max_primitives:
                raise RuntimeError(
                    "source SOP exceeds "
                    f"policy.max_primitives={policy.max_primitives}: {source_primitives}"
                )
            source_errors = list(source.errors())
            if source_errors:
                raise RuntimeError("source SOP errors: " + "; ".join(source_errors))
            source_import = _managed_sop_import(node, source_sop_path)
            source_import.invalidateOutput()
            source_import.cook(force=True)
            node.cook(force=True)
            stage = node.stage()
        elapsed = time.monotonic() - started
        if policy is not None and elapsed > policy.max_seconds:
            raise RuntimeError(
                f"USD stage composition took {elapsed:.3f}s > policy {policy.max_seconds:.3f}s"
            )
        if stage is None:
            raise RuntimeError(f"LOP did not produce a USD stage: {stage_node_path}")
        prims: list[Any] = []
        type_counts: dict[str, int] = {}
        for prim in stage.Traverse():
            prims.append(prim)
            if len(prims) > max_prims:
                raise RuntimeError(f"USD stage exceeds max_prims={max_prims}")
            type_name = prim.GetTypeName() or "untyped"
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        missing = [path for path in paths if not stage.GetPrimAtPath(path).IsValid()]
        if missing:
            raise RuntimeError(f"USD stage missing expected prims: {', '.join(missing)}")
        binding_prim = stage.GetPrimAtPath(binding_path)
        if not binding_prim.IsValid():
            raise RuntimeError(f"USD binding prim missing: {binding_path}")
        material, relationship = UsdShade.MaterialBindingAPI(binding_prim).ComputeBoundMaterial()
        material_path = str(material.GetPath()) if material else ""
        relationship_path = str(relationship.GetPath()) if relationship else ""
        if not material_path:
            raise RuntimeError(f"USD prim has no computed material binding: {binding_path}")
        errors = list(node.errors())
        if errors:
            raise RuntimeError("LOP stage errors: " + "; ".join(errors))
        warnings = list(node.warnings())
    finally:
        if hou.frame() != original_frame:
            hou.setFrame(original_frame)
    return {
        "stage_node_path": stage_node_path,
        "source_import_lop_path": source_import.path(),
        "source_sop_path": source_sop_path,
        "source_geometry": {
            "points": source_points,
            "primitives": source_primitives,
        },
        "source_frames_cooked": list(source_frames),
        "frame": frame_value if frame_value is not None else original_frame,
        "restored_frame": original_frame,
        "seconds": round(elapsed, 6),
        "prim_count": len(prims),
        "type_counts": dict(sorted(type_counts.items())),
        "expected_paths": paths,
        "binding": {
            "prim_path": binding_path,
            "material_path": material_path,
            "relationship": relationship_path,
        },
        "warnings": warnings,
        "errors": errors,
    }


def build_karma_render_rop(
    *,
    stage_node_path: str,
    render_settings_path: str,
    output_path: str,
    checkpoint_dir: str,
    log_path: str,
    node_name: str,
    width: int = 640,
    height: int = 360,
    frame: float = 1.0,
    time_limit: float = 30.0,
    max_threads: int = 4,
) -> ToolResult:
    """Checkpoint and create an editable USD Render ROP configured for Karma CPU."""
    hou = get_hou()
    spec = validate_preview_spec(
        output_path=output_path,
        width=width,
        height=height,
        frame=frame,
        time_limit=time_limit,
        max_threads=max_threads,
    )
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    if policy is not None:
        policy_w, policy_h = policy.max_resolution
        if spec["width"] > policy_w or spec["height"] > policy_h:
            raise ValueError("render resolution exceeds command policy.max_resolution")
        if spec["time_limit"] > policy.max_seconds:
            raise ValueError("render time limit exceeds policy.max_seconds")
    if Path(spec["output_path"]).exists():
        raise FileExistsError(f"refusing to configure overwrite: {spec['output_path']}")
    _usd_path(render_settings_path, "render_settings_path")
    if not _SAFE_NAME.fullmatch(node_name):
        raise ValueError("node_name must be a safe Houdini node name")
    stage_node = hou.node(stage_node_path)
    if stage_node is None or stage_node.type().category().name() != "Lop":
        raise ValueError(f"LOP stage node not found: {stage_node_path}")
    out = hou.node("/out")
    if out is None:
        raise ValueError("/out Driver network is unavailable")
    if out.node(node_name) is not None:
        raise ValueError(f"render ROP already exists: /out/{node_name}")
    checkpoint = save_checkpoint(checkpoint_dir, "solaris_karma_rop")
    created_by = "tool:solaris.karma_rop.build@1.0.0"
    rop = None
    result = ToolResult(status=Status.SUCCESS, checkpoint=checkpoint)
    try:
        with hou.undos.group("Hermes build bounded Karma CPU render ROP"):
            rop = out.createNode("usdrender", node_name=node_name, exact_type_name=True)
            stable_id = _tag(
                rop,
                category="Driver",
                role="karma_cpu_preview",
                created_by=created_by,
                scope=f"karma_preview:{node_name}",
            )
            values = {
                "trange": 0,
                "renderer": KARMA_CPU_DELEGATE,
                "loppath": stage_node_path,
                "rendersettings": render_settings_path,
                "outputimage": spec["output_path"],
                "override_res": "specific",
                "res_user1": spec["width"],
                "res_user2": spec["height"],
                "husk_dotimelimit": 1,
                "husk_timelimit": spec["time_limit"],
                "husk_timelimitperimage": 1,
                "domaxthreads": 1,
                "maxthreads": spec["max_threads"],
                "runcommand": 1,
                "soho_foreground": 1,
            }
            for name, value in values.items():
                _set_parm(rop, name, value)
            rop.setComment(
                "Hermes bounded Karma CPU preview. One frame only; external husk launch requires approval."
            )
        record = _record(
            "solaris_karma_rop",
            {"status": "success", "checkpoint": checkpoint, "rop_path": rop.path(), **spec},
        )
        _append_jsonl(log_path, record)
        result.changed_nodes = [ChangedNode(stable_id, rop.path(), "created")]
        result.artifacts = [log_path]
        result.data = {"rop_path": rop.path(), "render_settings_path": render_settings_path, **spec}
        return result
    except Exception as exc:
        if rop is not None and rop.parent() is not None:
            rop.destroy()
        result.status = Status.ERROR
        result.errors.append(f"{type(exc).__name__}: {exc}")
        result.data = {"rolled_back": True}
        return result


def render_karma_preview(
    *,
    rop_path: str,
    output_path: str,
    log_path: str,
    frame: float = 1.0,
    source_sop_path: str | None = None,
    source_start_frame: float | None = None,
) -> ToolResult:
    """Launch one explicitly approved, bounded Karma CPU preview via a managed USD Render ROP."""
    hou = get_hou()
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    if policy is None or not policy.allow_external_process:
        raise ValueError("policy.allow_external_process=true is required for husk rendering")
    rop = hou.node(rop_path)
    if rop is None or rop.type().category().name() != "Driver" or rop.type().name() != "usdrender":
        raise ValueError(f"USD Render ROP not found: {rop_path}")
    if rop.userData("hermes_role") != "karma_cpu_preview":
        raise ValueError("render tool only accepts a Hermes-managed karma_cpu_preview ROP")
    width = int(rop.parm("res_user1").eval())
    height = int(rop.parm("res_user2").eval())
    time_limit = float(rop.parm("husk_timelimit").eval())
    max_threads = int(rop.parm("maxthreads").eval())
    spec = validate_preview_spec(
        output_path=output_path,
        width=width,
        height=height,
        frame=frame,
        time_limit=time_limit,
        max_threads=max_threads,
    )
    if rop.parm("renderer").evalAsString() != KARMA_CPU_DELEGATE:
        raise ValueError("USD Render ROP must use the Karma CPU delegate")
    if rop.parm("outputimage").evalAsString() != spec["output_path"]:
        raise ValueError("output_path does not match the managed USD Render ROP")
    if rop.parm("override_res").evalAsString() != "specific":
        raise ValueError("USD Render ROP must use an explicit resolution override")
    if spec["time_limit"] > policy.max_seconds:
        raise ValueError("render time limit exceeds policy.max_seconds")
    policy_w, policy_h = policy.max_resolution
    if width > policy_w or height > policy_h:
        raise ValueError("render resolution exceeds command policy.max_resolution")
    if (source_sop_path is None) != (source_start_frame is None):
        raise ValueError("source_sop_path and source_start_frame must be provided together")
    source = None
    source_frames: tuple[int, ...] = ()
    source_import = None
    if source_sop_path is not None and source_start_frame is not None:
        source = hou.node(source_sop_path)
        if source is None or source.type().category().name() != "Sop":
            raise ValueError(f"source SOP node not found: {source_sop_path}")
        start_value = _finite(source_start_frame, "source_start_frame")
        if not start_value.is_integer() or not spec["frame"].is_integer():
            raise ValueError("source_start_frame and frame must be integer frames")
        start_frame = int(start_value)
        end_frame = int(spec["frame"])
        if start_frame > end_frame:
            raise ValueError("source_start_frame must be <= frame")
        source_frames = tuple(range(start_frame, end_frame + 1))
        stage_node = hou.node(rop.parm("loppath").evalAsString())
        if stage_node is None or stage_node.type().category().name() != "Lop":
            raise ValueError("managed USD Render ROP has no valid LOP stage")
        source_import = _managed_sop_import(stage_node, source_sop_path)
    required_frames = max(1, len(source_frames))
    if policy.max_frames < required_frames:
        raise ValueError(
            f"render warm-up needs {required_frames} frames > policy {policy.max_frames}"
        )
    output = Path(spec["output_path"])
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing render: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    original_frame = hou.frame()
    try:
        if source is not None and source_import is not None:
            for source_frame in source_frames:
                hou.setFrame(source_frame)
                source.cook(force=True)
            source_geometry = source.geometry()
            source_points = len(source_geometry.points())
            source_primitives = len(source_geometry.prims())
            if source_points > policy.max_points or source_primitives > policy.max_primitives:
                raise RuntimeError("render source geometry exceeds command topology policy")
            source_errors = list(source.errors())
            if source_errors:
                raise RuntimeError("render source SOP errors: " + "; ".join(source_errors))
            source_import.invalidateOutput()
            source_import.cook(force=True)
        rop.render(
            frame_range=(spec["frame"], spec["frame"], 1.0),
            verbose=True,
            output_progress=True,
        )
        elapsed = time.monotonic() - started
        if elapsed > policy.max_seconds:
            raise RuntimeError(
                f"render plus source warm-up took {elapsed:.3f}s > policy {policy.max_seconds:.3f}s"
            )
    finally:
        if hou.frame() != original_frame:
            hou.setFrame(original_frame)
    if not output.is_file():
        raise RuntimeError(f"Karma render completed without expected artifact: {output}")
    size = output.stat().st_size
    if size > policy.max_output_bytes:
        raise RuntimeError(f"render output {size} bytes exceeds policy limit")
    payload = {
        "status": "success",
        "rop_path": rop_path,
        "seconds": round(elapsed, 6),
        "bytes": size,
        "source_sop_path": source_sop_path,
        "source_frames_cooked": list(source_frames),
        "source_geometry": (
            {"points": source_points, "primitives": source_primitives}
            if source is not None
            else None
        ),
        **spec,
    }
    _append_jsonl(log_path, _record("karma_preview", payload))
    return ToolResult(
        status=Status.SUCCESS,
        artifacts=[str(output), log_path],
        data=payload,
    )


__all__ = [
    "APPRENTICE_RENDER_CEILING",
    "KARMA_CPU_DELEGATE",
    "build_karma_render_rop",
    "populate_materialx_library",
    "render_karma_preview",
    "validate_material_specs",
    "validate_preview_spec",
    "validate_stage",
]
