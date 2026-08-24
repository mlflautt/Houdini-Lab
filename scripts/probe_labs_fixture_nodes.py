#!/usr/bin/env hython
"""Cook three disposable Labs fixture candidates and report their live H22 interfaces."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import hou

NODE_TYPES = (
    "labs::measure_curvature::3.1",
    "labs::terrain_analysis::1.0",
    "labs::instance_attributes::1.0",
)


def _parm_summary(node: hou.Node) -> list[dict[str, object]]:
    result = []
    for parm in node.parms():
        template = parm.parmTemplate()
        value = parm.eval()
        if isinstance(value, (str, int, float)):
            entry: dict[str, object] = {
                "name": parm.name(),
                "label": template.label(),
                "value": value,
            }
            if isinstance(template, hou.MenuParmTemplate):
                entry["items"] = list(template.menuItems())
                entry["labels"] = list(template.menuLabels())
            result.append(entry)
    return result


def _geometry_summary(node: hou.SopNode) -> dict[str, object]:
    geometry = node.geometry()
    bounds = geometry.boundingBox()
    return {
        "points": geometry.intrinsicValue("pointcount"),
        "primitives": geometry.intrinsicValue("primitivecount"),
        "memory": geometry.intrinsicValue("memoryusage"),
        "point_attributes": sorted(attribute.name() for attribute in geometry.pointAttribs()),
        "primitive_attributes": sorted(attribute.name() for attribute in geometry.primAttribs()),
        "detail_attributes": sorted(attribute.name() for attribute in geometry.globalAttribs()),
        "bounds_min": list(bounds.minvec()),
        "bounds_max": list(bounds.maxvec()),
    }


def _tag(node: hou.Node, fixture_id: str, role: str) -> None:
    node.setUserData("hermes_id", f"sprint20:{fixture_id}:{role}")
    node.setUserData("hermes_role", role)
    node.setUserData("hermes_created_by", "scripts/probe_labs_fixture_nodes.py")


def _cook(node: hou.SopNode) -> dict[str, object]:
    started = time.monotonic()
    node.cook(force=True)
    elapsed = time.monotonic() - started
    return {
        "type": node.type().name(),
        "path": node.path(),
        "seconds": elapsed,
        "errors": list(node.errors()),
        "warnings": list(node.warnings()),
        "geometry": _geometry_summary(node),
        "parameters": _parm_summary(node),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    missing = [name for name in NODE_TYPES if name not in hou.sopNodeTypeCategory().nodeTypes()]
    if missing:
        raise RuntimeError(f"required Labs node types are missing: {missing}")
    obj = hou.node("/obj")
    network = obj.createNode("geo", "SPRINT20_LABS_FIXTURE_PROBE")
    for child in network.children():
        child.destroy()
    try:
        sphere = network.createNode("sphere", "ARTIFACT_SOURCE", exact_type_name=True)
        sphere.parm("type").set(1)
        sphere.parm("freq").set(24)
        curvature = network.createNode(NODE_TYPES[0], "LABS_CURVATURE", exact_type_name=True)
        curvature.setInput(0, sphere)
        _tag(curvature, "artifact_mesh_utility", "labs_measure_curvature")

        heightfield = network.createNode("heightfield", "TERRAIN_SOURCE", exact_type_name=True)
        heightfield.parm("divisionmode").set(0)
        heightfield.parm("gridsamples").set(64)
        heightfield.parmTuple("size").set((8.0, 8.0))
        noise = network.createNode("heightfield_noise", "TERRAIN_NOISE", exact_type_name=True)
        noise.setInput(0, heightfield)
        noise.parm("amp").set(1.5)
        noise.parm("elementsize").set(2.5)
        terrain = network.createNode(NODE_TYPES[1], "LABS_TERRAIN_ANALYSIS", exact_type_name=True)
        terrain.setInput(0, noise)
        terrain.parm("slope").set(1)
        terrain.parm("horizontalcurvature").set(1)
        terrain.parm("enablevisualization").set(1)
        terrain.parm("visualizemenu").set(1)
        terrain.parm("visualizeattribute").set("slope")
        _tag(terrain, "terrain_cartography_utility", "labs_terrain_analysis")

        grid = network.createNode("grid", "INSTANCE_DOMAIN", exact_type_name=True)
        grid.parmTuple("size").set((6.0, 6.0))
        scatter = network.createNode("scatter::2.0", "INSTANCE_POINTS", exact_type_name=True)
        scatter.setInput(0, grid)
        scatter.parm("npts").set(64)
        instance = network.createNode(NODE_TYPES[2], "LABS_INSTANCE_ATTRIBUTES", exact_type_name=True)
        instance.setInput(0, scatter)
        instance.parm("pscalemin").set(0.25)
        instance.parm("pscalemax").set(0.75)
        instance.parm("spinamountmode").set(1)
        instance.parm("spin_min").set(0.0)
        instance.parm("spin_max").set(360.0)
        instance.parm("rand3drot").set(1)
        _tag(instance, "motion_instancing_utility", "labs_instance_attributes")

        fixtures = {
            "artifact_mesh_utility": _cook(curvature),
            "terrain_cartography_utility": _cook(terrain),
            "motion_instancing_utility": _cook(instance),
        }
        report = {
            "schema": "hermes.houdini.sidefx_labs_fixture_probe",
            "schema_version": "1.0",
            "houdini_version": hou.applicationVersionString(),
            "license_mode": str(hou.licenseCategory()),
            "fixtures": fixtures,
            "total_seconds": sum(float(value["seconds"]) for value in fixtures.values()),
            "mutation_scope": "disposable_unsaved_hip_session",
        }
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        output = args.out.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
        print(rendered, end="")
    finally:
        network.destroy()
    hou.exit(exit_code=0, suppress_save_prompt=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
