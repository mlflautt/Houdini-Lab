"""Print the installed Houdini MPM SOP surface as JSON.

Run with the pinned build's ``hython``. The probe creates an unsaved temporary
network, never cooks it, and exists so recipes can target observed operator and
parameter tokens instead of tutorial-era guesses.
"""

from __future__ import annotations

import argparse
import json

import hou

OPERATOR_TYPES = (
    "mpmsource",
    "mpmcollider",
    "mpmcontainer",
    "mpmsolver",
    "mpmsurface",
    "filecache",
)

RELEVANT_LABEL_TERMS = {
    "mpmsource": (
        "mpm container",
        "emission type",
        "activation",
        "point separation",
        "jitter",
        "seed",
        "material preset",
        "behavior",
        "density",
        "critical compression",
        "critical stretch",
        "compression hardening",
        "stiffness",
        "young",
        "volume preservation",
        "incompressibility",
        "viscosity",
        "plasticity",
        "friction angle",
        "cohesion",
        "velocity",
        "point scale",
    ),
    "mpmcollider": ("mpm container", "collider type", "collision response", "friction", "sticky"),
    "mpmcontainer": ("start frame", "particle separation", "grid scale", "size", "center", "all"),
    "mpmsolver": (
        "start frame",
        "global substeps",
        "substeps min",
        "substeps max",
        "gravity",
        "ground",
        "friction",
        "opencl",
        "checkpoint",
        "point attributes",
        "detail attributes",
    ),
    "mpmsurface": ("output type", "voxel scale", "particle scale", "method", "adaptivity"),
    "filecache": (
        "load from disk",
        "file mode",
        "geometry file",
        "valid frame range",
        "start/end/inc",
        "initialize simulation",
    ),
}


def _parameter(parm_tuple: hou.ParmTuple) -> dict[str, object]:
    template = parm_tuple.parmTemplate()
    result: dict[str, object] = {
        "name": template.name(),
        "label": template.label(),
        "type": template.type().name(),
    }
    if hasattr(template, "defaultValue"):
        defaults = template.defaultValue()
        if defaults is not None:
            result["default"] = list(defaults) if isinstance(defaults, tuple) else defaults
    if isinstance(template, hou.MenuParmTemplate):
        try:
            result["menu_items"] = list(parm_tuple[0].menuItems())
            result["menu_labels"] = list(parm_tuple[0].menuLabels())
        except hou.OperationFailed:
            result["menu_items"] = list(template.menuItems())
            result["menu_labels"] = list(template.menuLabels())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="include every parameter template")
    parser.add_argument("--operator", choices=OPERATOR_TYPES, help="report one exact SOP type")
    arguments = parser.parse_args()
    obj = hou.node("/obj")
    network = obj.createNode("geo", node_name="HERMES_MPM_PROBE")
    for child in network.children():
        child.destroy()

    sop_types = hou.sopNodeTypeCategory().nodeTypes()
    report: dict[str, object] = {
        "application_version": hou.applicationVersionString(),
        "license_category": str(hou.licenseCategory()),
        "operators": {},
    }
    operators: dict[str, object] = report["operators"]  # type: ignore[assignment]
    selected_types = (arguments.operator,) if arguments.operator else OPERATOR_TYPES
    for operator_type in selected_types:
        node_type = sop_types.get(operator_type)
        if node_type is None:
            operators[operator_type] = {"available": False}
            continue
        node = network.createNode(operator_type, exact_type_name=True)
        parameters = [_parameter(parm) for parm in node.parmTuples()]
        if not arguments.all:
            terms = RELEVANT_LABEL_TERMS[operator_type]
            parameters = [
                parameter
                for parameter in parameters
                if any(term in str(parameter["label"]).lower() for term in terms)
            ]
        operators[operator_type] = {
            "available": True,
            "exact_type": node.type().name(),
            "input_names": list(node.inputNames()),
            "input_labels": list(node.inputLabels()),
            "output_names": list(node.outputNames()),
            "parameters": parameters,
        }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
