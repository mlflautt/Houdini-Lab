"""Cook a disposable native RBD fracture graph in the pinned Houdini build."""

from __future__ import annotations

import json

import hou

PARAM_TOKENS = (
    "scatter",
    "count",
    "piece",
    "constraint",
    "proxy",
    "pack",
    "fracture",
    "strength",
    "active",
    "velocity",
    "gravity",
    "ground",
)


def _parm_summary(node: hou.Node) -> list[dict[str, object]]:
    result = []
    for parm in node.parms():
        template = parm.parmTemplate()
        text = f"{parm.name()} {template.label()}".lower()
        if not any(token in text for token in PARAM_TOKENS):
            continue
        entry: dict[str, object] = {
            "name": parm.name(),
            "label": template.label(),
            "value": parm.eval(),
        }
        if isinstance(template, hou.MenuParmTemplate):
            entry["items"] = list(template.menuItems())
            entry["labels"] = list(template.menuLabels())
        result.append(entry)
    return result


def _geometry_summary(node: hou.SopNode, output_index: int = 0) -> dict[str, object]:
    geometry = node.geometry(output_index=output_index)
    names = []
    name_attrib = geometry.findPrimAttrib("name")
    if name_attrib is not None:
        names = sorted(set(geometry.primStringAttribValues("name")))
    elif geometry.findPointAttrib("name") is not None:
        names = sorted(set(geometry.pointStringAttribValues("name")))
    bounds = geometry.boundingBox()
    return {
        "points": geometry.intrinsicValue("pointcount"),
        "primitives": geometry.intrinsicValue("primitivecount"),
        "primitive_types": sorted(set(primitive.type().name() for primitive in geometry.prims())),
        "point_attributes": sorted(attribute.name() for attribute in geometry.pointAttribs()),
        "primitive_attributes": sorted(attribute.name() for attribute in geometry.primAttribs()),
        "piece_names": names[:12],
        "piece_name_count": len(names),
        "bounds_min": list(bounds.minvec()),
        "bounds_max": list(bounds.maxvec()),
        "centroid": list(bounds.center()),
        "memory": geometry.intrinsicValue("memoryusage"),
    }


def main() -> None:
    obj = hou.node("/obj")
    network = obj.createNode("geo", "SPRINT17_RBD_COOK_PROBE")
    for child in network.children():
        child.destroy()
    try:
        source = network.createNode("box", "SOURCE", exact_type_name=True)
        source.parmTuple("size").set((2.0, 4.0, 2.0))
        source.parm("ty").set(6.0)

        fracture = network.createNode("rbdmaterialfracture::4.0", "FRACTURE", exact_type_name=True)
        fracture.setInput(0, source, 0)
        fracture.parm("materialtype").set("concrete")
        fracture.parm("concrete_primarystrength").set(40.0)
        fracture.parm("concrete_chippingstrength").set(20.0)
        summaries = {
            "houdini": hou.applicationVersionString(),
            "license": str(hou.licenseCategory()),
            "fracture_type": fracture.type().name(),
            "fracture_inputs": list(fracture.inputLabels()),
            "fracture_outputs": list(fracture.outputLabels()),
            "fracture_parameters": _parm_summary(fracture),
        }
        fracture.cook(force=True)
        summaries["fracture_errors"] = list(fracture.errors())
        summaries["fracture_warnings"] = list(fracture.warnings())
        summaries["fracture_geometry"] = [
            _geometry_summary(fracture, index) for index in range(len(fracture.outputLabels()))
        ]

        configure = network.createNode("rbdconfigure", "CONFIGURE", exact_type_name=True)
        for index in range(min(3, len(fracture.outputLabels()))):
            configure.setInput(index, fracture, index)
        summaries["configure_parameters"] = _parm_summary(configure)
        configure.cook(force=True)
        summaries["configure_errors"] = list(configure.errors())
        summaries["configure_geometry"] = [
            _geometry_summary(configure, index) for index in range(len(configure.outputLabels()))
        ]

        solver = network.createNode("rbdbulletsolver", "SOLVER", exact_type_name=True)
        for index in range(min(3, len(configure.outputLabels()))):
            solver.setInput(index, configure, index)
        solver.parm("useground").set(1)
        solver.parm("cachemaxsize").set(512)
        summaries["solver_parameters"] = _parm_summary(solver)
        summaries["solver_outputs"] = list(solver.outputLabels())
        hou.setFrame(48)
        solver.cook(force=True)
        summaries["solver_errors"] = list(solver.errors())
        summaries["solver_warnings"] = list(solver.warnings())
        summaries["solver_geometry_frame_48"] = [
            _geometry_summary(solver, index) for index in range(len(solver.outputLabels()))
        ]

        rest_points = network.createNode("timeshift", "REST_POINTS", exact_type_name=True)
        rest_points.setInput(0, solver, 3)
        rest_points.parm("frame").deleteAllKeyframes()
        rest_points.parm("frame").set(1.0)
        reconstruct = network.createNode("xformpieces", "RECONSTRUCT", exact_type_name=True)
        reconstruct.setInput(0, fracture, 0)
        reconstruct.setInput(1, solver, 3)
        reconstruct.setInput(2, rest_points, 0)
        reconstruct.cook(force=True)
        summaries["reconstruct_errors"] = list(reconstruct.errors())
        summaries["reconstruct_warnings"] = list(reconstruct.warnings())
        summaries["reconstruct_geometry_frame_48"] = _geometry_summary(reconstruct)
        print(json.dumps(summaries, indent=2, sort_keys=True))
    finally:
        network.destroy()


if __name__ == "__main__":
    main()
