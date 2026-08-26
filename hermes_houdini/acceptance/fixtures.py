"""Tiny source-built fixtures for the v0.35 live acceptance tiers.

The builders in this module only edit native Houdini graphs and save a rebuildable
non-commercial scene.  They do not cook, render, inspect geometry, or rely on UI state.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from hermes_houdini import get_hou

CREATED_BY = "grinder:G001-B@1.0"
_SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,47}\Z")


def _unused_artifact_root(value: str | os.PathLike[str]) -> Path:
    root = Path(value).expanduser()
    if not root.is_absolute():
        raise ValueError("artifact_root must be absolute")
    if root.exists():
        raise FileExistsError(f"artifact_root must be unused: {root}")
    root.mkdir(parents=True, exist_ok=False)
    return root


def _tag(node: Any, *, stable_id: str, role: str) -> None:
    node.setUserData("hermes_id", stable_id)
    node.setUserData("hermes_role", role)
    node.setUserData("hermes_created_by", CREATED_BY)


def _set(node: Any, name: str, value: Any) -> None:
    parm = node.parm(name)
    if parm is None:
        raise ValueError(f"{node.type().nameWithCategory()} has no parameter {name}")
    parm.set(value)


def _record(node: Any) -> dict[str, Any]:
    return {
        "path": node.path(),
        "category": node.type().category().name(),
        "operator_type": node.type().name(),
        "hermes_id": node.userData("hermes_id"),
        "hermes_role": node.userData("hermes_role"),
        "hermes_created_by": node.userData("hermes_created_by"),
        "needs_to_cook": bool(node.needsToCook()) if hasattr(node, "needsToCook") else None,
    }


def build_acceptance_fixtures(
    artifact_root: str | os.PathLike[str],
    *,
    fixture_name: str = "HERMES_ACCEPTANCE_G001B",
) -> dict[str, Any]:
    """Build native SOP, Solver SOP, PDG-child, viewport, and Karma fixtures.

    ``artifact_root`` must be a caller-supplied unused absolute path.  The scene is
    saved as ``.hipnc`` without changing the caller's current HIP name.
    """
    if not isinstance(fixture_name, str) or not _SAFE_NAME.fullmatch(fixture_name):
        raise ValueError("fixture_name must be a safe Houdini identifier")
    root = _unused_artifact_root(artifact_root)
    hou = get_hou()
    obj = hou.node("/obj")
    tasks = hou.node("/tasks")
    stage = hou.node("/stage")
    out = hou.node("/out")
    if any(network is None for network in (obj, tasks, stage, out)):
        raise RuntimeError("required /obj, /tasks, /stage, and /out networks are unavailable")

    protected = [
        f"/obj/{fixture_name}",
        f"/obj/{fixture_name}_SIM",
        f"/obj/{fixture_name}_CAMERA",
        f"/tasks/{fixture_name}_PDG",
        f"/stage/{fixture_name}_IMPORT",
        f"/out/{fixture_name}_KARMA",
    ]
    collision = next((path for path in protected if hou.node(path) is not None), None)
    if collision:
        raise ValueError(f"fixture node path already exists: {collision}")

    render_path = root / "renders" / "karma.png"
    pdg_output = root / "cache" / "pdg_child.bgeo.sc"
    scene_path = root / "scenes" / "acceptance_fixture.hipnc"
    created: list[Any] = []
    try:
        with hou.undos.group("Build G001-B bounded acceptance fixtures"):
            geo = obj.createNode("geo", node_name=fixture_name, run_init_scripts=False)
            created.append(geo)
            _tag(geo, stable_id="HOU-OBJ-G001B-FIXTURE", role="acceptance_fixture_container")
            source = geo.createNode("box", node_name="SOURCE_BOX", run_init_scripts=False)
            _tag(source, stable_id="HOU-SOP-G001B-SOURCE", role="acceptance_source")
            _set(source, "sizex", 1.0)
            _set(source, "sizey", 1.0)
            _set(source, "sizez", 1.0)
            animated = geo.createNode("xform", node_name="ANIMATED_TRANSFORM", run_init_scripts=False)
            _tag(animated, stable_id="HOU-SOP-G001B-ANIMATED", role="frame_range_fixture")
            animated.setInput(0, source)
            animated.parm("tx").setExpression("$F * 0.01", language=hou.exprLanguage.Hscript)
            output = geo.createNode("null", node_name="OUT_GEO", run_init_scripts=False)
            _tag(output, stable_id="HOU-SOP-G001B-OUT", role="geometry_output_contract")
            output.setInput(0, animated)
            source.setPosition(hou.Vector2(0, 2))
            animated.setPosition(hou.Vector2(0, 1))
            output.setPosition(hou.Vector2(0, 0))

            sim_geo = obj.createNode("geo", node_name=f"{fixture_name}_SIM", run_init_scripts=False)
            created.append(sim_geo)
            _tag(sim_geo, stable_id="HOU-OBJ-G001B-SIM", role="simulation_fixture_container")
            sim_source = sim_geo.createNode("box", node_name="SOURCE_BOX", run_init_scripts=False)
            _tag(sim_source, stable_id="HOU-SOP-G001B-SIM-SOURCE", role="simulation_source")
            solver = sim_geo.createNode("solver", node_name="BOUNDED_SOLVER")
            _tag(solver, stable_id="HOU-SOP-G001B-SOLVER", role="bounded_native_simulation")
            solver.setInput(0, sim_source)
            for index, child in enumerate(sorted(solver.allSubChildren(), key=lambda item: item.path())):
                _tag(
                    child,
                    stable_id=f"HOU-SOP-G001B-SOLVER-INTERNAL-{index:02d}",
                    role="native_solver_internal",
                )
            sim_output = sim_geo.createNode("null", node_name="OUT_SIM", run_init_scripts=False)
            _tag(sim_output, stable_id="HOU-SOP-G001B-SIM-OUT", role="simulation_output_contract")
            sim_output.setInput(0, solver)
            sim_source.setPosition(hou.Vector2(0, 2))
            solver.setPosition(hou.Vector2(0, 1))
            sim_output.setPosition(hou.Vector2(0, 0))

            camera = obj.createNode("cam", node_name=f"{fixture_name}_CAMERA", run_init_scripts=False)
            created.append(camera)
            _tag(camera, stable_id="HOU-OBJ-G001B-CAMERA", role="explicit_viewport_camera")
            _set(camera, "tx", 3.0)
            _set(camera, "ty", 2.5)
            _set(camera, "tz", 4.0)
            _set(camera, "rx", -20.0)
            _set(camera, "ry", 36.0)

            topnet = tasks.createNode("topnet", node_name=f"{fixture_name}_PDG", run_init_scripts=False)
            created.append(topnet)
            _tag(topnet, stable_id="HOU-TOP-G001B-NET", role="pdg_child_fixture_container")
            pdg = topnet.createNode("ropgeometry", node_name="CACHE_ONE_CHILD", run_init_scripts=False)
            _tag(pdg, stable_id="HOU-TOP-G001B-CHILD", role="approved_external_pdg_child")
            _set(pdg, "usesoppath", 1)
            _set(pdg, "soppath", output.path())
            _set(pdg, "sopoutput", str(pdg_output))
            _set(pdg, "trange", 0)

            sop_import = stage.createNode("sopimport", node_name=f"{fixture_name}_IMPORT", run_init_scripts=False)
            created.append(sop_import)
            _tag(sop_import, stable_id="HOU-LOP-G001B-IMPORT", role="karma_fixture_import")
            _set(sop_import, "soppath", output.path())
            _set(sop_import, "primpath", "/World/AcceptanceBox")
            dome = stage.createNode("domelight", node_name=f"{fixture_name}_DOME", run_init_scripts=False)
            created.append(dome)
            _tag(dome, stable_id="HOU-LOP-G001B-LIGHT", role="neutral_karma_light")
            dome.setInput(0, sop_import)
            lop_camera = stage.createNode("camera", node_name=f"{fixture_name}_CAMERA", run_init_scripts=False)
            created.append(lop_camera)
            _tag(lop_camera, stable_id="HOU-LOP-G001B-CAMERA", role="explicit_karma_camera")
            lop_camera.setInput(0, dome)
            for name, value in {
                "primpath": "/cameras/G001B_Camera",
                "tx": 3.0,
                "ty": 2.5,
                "tz": 4.0,
                "rx": -20.0,
                "ry": 36.0,
            }.items():
                _set(lop_camera, name, value)
            settings = stage.createNode(
                "karmarendersettings", node_name=f"{fixture_name}_SETTINGS", run_init_scripts=False
            )
            created.append(settings)
            _tag(settings, stable_id="HOU-LOP-G001B-SETTINGS", role="karma_cpu_settings")
            settings.setInput(0, lop_camera)
            for name, value in {
                "primpath": "/Render/G001B_Settings",
                "picture": str(render_path),
                "camera": "/cameras/G001B_Camera",
                "res_mode": "manual",
                "resolutionx": 640,
                "resolutiony": 360,
                "samplesperpixel": 4,
                "pathtracedsamples": 8,
                "setlayerrendersettings": 1,
            }.items():
                _set(settings, name, value)
            stage_output = stage.createNode("null", node_name=f"OUT_{fixture_name}_STAGE", run_init_scripts=False)
            created.append(stage_output)
            _tag(stage_output, stable_id="HOU-LOP-G001B-OUT", role="usd_stage_output_contract")
            stage_output.setInput(0, settings)

            rop = out.createNode("usdrender", node_name=f"{fixture_name}_KARMA", run_init_scripts=False)
            created.append(rop)
            _tag(rop, stable_id="HOU-ROP-G001B-KARMA", role="karma_cpu_preview")
            for name, value in {
                "trange": 0,
                "renderer": "BRAY_HdKarma",
                "loppath": stage_output.path(),
                "rendersettings": "/Render/G001B_Settings",
                "outputimage": str(render_path),
                "override_res": "specific",
                "res_user1": 640,
                "res_user2": 360,
                "husk_dotimelimit": 1,
                "husk_timelimit": 120,
                "husk_timelimitperimage": 1,
                "domaxthreads": 1,
                "maxthreads": 4,
                "runcommand": 1,
                "soho_foreground": 1,
            }.items():
                _set(rop, name, value)
            rop.setComment("One-frame bounded Karma CPU fixture; execution requires explicit approval.")

        managed = [geo, *geo.allSubChildren(), sim_geo, *sim_geo.allSubChildren(), camera, topnet,
                   *topnet.allSubChildren(), sop_import, dome, lop_camera, settings, stage_output, rop]
        for index, node in enumerate(managed):
            if not node.userData("hermes_id"):
                _tag(
                    node,
                    stable_id=f"HOU-{node.type().category().name().upper()}-G001B-AUTO-{index:02d}",
                    role="native_fixture_internal",
                )
        dirty_before_save = {node.path(): bool(node.needsToCook()) for node in managed if hasattr(node, "needsToCook")}
        scene_path.parent.mkdir(parents=True, exist_ok=False)
        original_hip = hou.hipFile.name()
        try:
            hou.hipFile.save(file_name=str(scene_path), save_to_recent_files=False)
        finally:
            hou.hipFile.setName(original_hip)
        return {
            "artifact_root": str(root),
            "scene_path": str(scene_path),
            "fixture_name": fixture_name,
            "source_node_path": source.path(),
            "output_node_path": output.path(),
            "simulation_node_path": sim_output.path(),
            "pdg_node_path": pdg.path(),
            "viewport_camera_path": camera.path(),
            "stage_node_path": stage_output.path(),
            "render_settings_path": "/Render/G001B_Settings",
            "karma_rop_path": rop.path(),
            "pdg_output_path": str(pdg_output),
            "render_output_path": str(render_path),
            "dirty_before_save": dirty_before_save,
            "managed_nodes": [_record(node) for node in managed],
        }
    except Exception:
        for node in reversed(created):
            if node is not None and node.parent() is not None:
                node.destroy()
        raise


__all__ = ["CREATED_BY", "build_acceptance_fixtures"]
