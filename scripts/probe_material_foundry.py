"""Read-only-ish Houdini 22 interface probe for Sprint 18 native node contracts.

The scene is cleared and temporary nodes are created only in memory. Nothing is saved.
"""

from __future__ import annotations

import json

import hou


def parm_summary(parm: hou.Parm) -> dict:
    template = parm.parmTemplate()
    return {
        "name": parm.name(),
        "label": template.label(),
        "type": template.type().name(),
        "value": parm.evalAsString(),
        "menu_items": list(template.menuItems()) if hasattr(template, "menuItems") else [],
        "menu_labels": list(template.menuLabels()) if hasattr(template, "menuLabels") else [],
    }


def node_summary(node: hou.Node) -> dict:
    keep = (
        "signature",
        "color",
        "file",
        "image",
        "layer",
        "raw",
        "type",
        "scale",
        "normal",
        "height",
        "base",
        "rough",
        "metal",
        "res",
        "precision",
        "mat",
        "assign",
        "geo",
        "input",
        "output",
        "aov",
        "space",
        "source",
    )
    return {
        "path": node.path(),
        "type": node.type().name(),
        "inputs": list(node.inputLabels()),
        "outputs": list(node.outputLabels()),
        "parms": [
            parm_summary(parm)
            for parm in node.parms()
            if any(fragment in parm.name().lower() for fragment in keep)
        ],
    }


hou.hipFile.clear(suppress_save_prompt=True)

categories = {
    "Cop2": hou.copNodeTypeCategory(),
    "Lop": hou.lopNodeTypeCategory(),
    "Vop": hou.vopNodeTypeCategory(),
}
filters = {
    "Cop2": (
        "normal",
        "height",
        "preview",
        "usd",
        "remap",
        "math",
        "constant",
        "mono",
        "rop_image",
    ),
    "Lop": ("material", "assignmaterial"),
    "Vop": ("mtlx",),
}
for category_name, category in categories.items():
    matches = sorted(
        name
        for name in category.nodeTypes()
        if any(fragment in name.lower() for fragment in filters[category_name])
    )
    print(f"TYPES {category_name} " + json.dumps(matches))

img = hou.node("/img")
copnet = img.createNode("copnet", "SPRINT18_PROBE")
cop_candidates = [
    "constant",
    "remap",
    "monotorgb",
    "normalfromheight",
    "heighttonormal",
    "previewmaterial",
    "usdmaterial",
    "rop_image",
]
for type_name in cop_candidates:
    try:
        node = copnet.createNode(type_name, type_name.replace("::", "_"))
    except hou.OperationFailed as exc:
        print(f"CREATE_ERROR Cop2 {type_name}: {exc}")
        continue
    print("NODE Cop2 " + json.dumps(node_summary(node), sort_keys=True))

stage = hou.node("/stage")
for type_name in ("materiallibrary", "texturemateriallibrary", "assignmaterial"):
    try:
        node = stage.createNode(type_name, f"probe_{type_name}")
    except hou.OperationFailed as exc:
        print(f"CREATE_ERROR Lop {type_name}: {exc}")
        continue
    print("NODE Lop " + json.dumps(node_summary(node), sort_keys=True))

library = stage.node("probe_materiallibrary")
if library is not None:
    import voptoolutils

    builder = voptoolutils._setupMtlXBuilderSubnet(destination_node=library, name="PROBE_MAT")
    print(
        "BUILDER_CHILDREN " + json.dumps([(n.name(), n.type().name()) for n in builder.children()])
    )
    for type_name in (
        "mtlxtiledimage",
        "mtlximage",
        "mtlxnormalmap",
        "mtlxbump",
        "mtlxstandard_surface",
    ):
        try:
            node = builder.createNode(type_name, f"probe_{type_name}")
        except hou.OperationFailed as exc:
            print(f"CREATE_ERROR Vop {type_name}: {exc}")
            continue
        summary = node_summary(node)
        summary["output_names"] = list(node.outputNames())
        summary["output_types"] = list(node.outputDataTypes())
        summary["input_names"] = list(node.inputNames())
        summary["input_types"] = list(node.inputDataTypes())
        print("NODE Vop " + json.dumps(summary, sort_keys=True))
