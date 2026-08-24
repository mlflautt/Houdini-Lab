"""Inspect pinned Houdini RBD SOP interfaces without mutating project files.

Run with the Houdini 22.0.368 hython binary.  The output is deliberately JSON so
the exact operator/parameter contract can be retained with Sprint 17 evidence.
"""

from __future__ import annotations

import json

import hou

INTERESTING_TOKENS = (
    "material",
    "fracture",
    "piece",
    "constraint",
    "bullet",
    "collision",
    "active",
    "frame",
    "substep",
    "cache",
    "transform",
    "name",
    "seed",
    "impact",
)


def _default(template: hou.ParmTemplate):
    try:
        value = template.defaultValue()
    except (AttributeError, hou.OperationFailed):
        return None
    if isinstance(value, tuple):
        return list(value)
    return value


def _flatten_templates(templates):
    for template in templates:
        yield template
        if isinstance(template, hou.FolderParmTemplate):
            yield from _flatten_templates(template.parmTemplates())


def _describe(node_type: hou.NodeType) -> dict[str, object]:
    definition = node_type.definition()
    templates: list[dict[str, object]] = []
    for template in _flatten_templates(node_type.parmTemplateGroup().parmTemplates()):
        name = template.name()
        label = template.label()
        if not any(token in f"{name} {label}".lower() for token in INTERESTING_TOKENS):
            continue
        entry: dict[str, object] = {
            "name": name,
            "label": label,
            "type": template.type().name(),
            "default": _default(template),
        }
        if isinstance(template, hou.MenuParmTemplate):
            entry["menu_items"] = list(template.menuItems())
            entry["menu_labels"] = list(template.menuLabels())
        templates.append(entry)
    return {
        "name": node_type.name(),
        "description": node_type.description(),
        "min_inputs": node_type.minNumInputs(),
        "max_inputs": node_type.maxNumInputs(),
        "source": definition.libraryFilePath() if definition else "builtin",
        "parameters": templates,
    }


def main() -> None:
    category = hou.sopNodeTypeCategory()
    all_types = category.nodeTypes()
    matching = sorted(
        name
        for name in all_types
        if "rbd" in name.lower()
        or "bullet" in name.lower()
        or "transform" in name.lower()
        or "xform" in name.lower()
    )
    requested = [
        "rbdmaterialfracture",
        "rbdmaterialfracture::4.0",
        "rbdconfigure",
        "rbdconstraintsfromrules",
        "rbdbulletsolver",
        "rbdpack",
        "rbdunpack",
        "transformpieces",
        "transformbyattrib",
        "xformpieces",
        "rbddeformpieces",
        "rbdxform",
        "filecache",
        "scatter::2.0",
    ]
    descriptions = {name: _describe(all_types[name]) for name in requested if name in all_types}

    obj = hou.node("/obj")
    probe = obj.createNode("geo", "SPRINT17_RBD_PROBE")
    for child in probe.children():
        child.destroy()
    try:
        for name, description in descriptions.items():
            node = probe.createNode(name, f"PROBE_{name.replace(':', '_')}", exact_type_name=True)
            description["input_labels"] = list(node.inputLabels())
            description["output_labels"] = list(node.outputLabels())
    finally:
        probe.destroy()

    print(
        json.dumps(
            {
                "houdini": hou.applicationVersionString(),
                "license": str(hou.licenseCategory()),
                "matching_types": matching,
                "requested": descriptions,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
