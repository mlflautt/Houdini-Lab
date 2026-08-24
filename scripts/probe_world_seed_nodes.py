"""Print the pinned H22 operator contracts considered for World Seed Atlas.

Run with Houdini's hython. This script is read-only and does not save a scene.
"""

from __future__ import annotations

import json

import hou


def _describe(category: hou.NodeTypeCategory, names: tuple[str, ...]) -> dict[str, object]:
    result: dict[str, object] = {}
    available = category.nodeTypes()
    for name in names:
        node_type = available.get(name)
        if node_type is None:
            result[name] = None
            continue
        result[name] = {
            "description": node_type.description(),
            "min_inputs": node_type.minNumInputs(),
            "max_inputs": node_type.maxNumInputs(),
            "parameters": [template.name() for template in node_type.parmTemplates()],
        }
    return result


print(
    json.dumps(
        {
            "houdini": hou.applicationVersionString(),
            "license": str(hou.licenseCategory()),
            "cop": _describe(
                hou.copNodeTypeCategory(),
                (
                    "heightfield",
                    "heightfield_noise",
                    "heightfield_strata",
                    "heightfield_terrace",
                    "heightfield_erode",
                    "heightfield_maskbyfeature",
                    "heightfield_visualize",
                    "heightfield_xform2d",
                    "monotorgb",
                    "null",
                ),
            ),
            "sop": _describe(
                hou.sopNodeTypeCategory(),
                (
                    "copnet",
                    "grid",
                    "mountain",
                    "heightfield",
                    "heightfield_noise",
                    "heightfield_erode::3.0",
                    "heightfield_convert",
                    "scatter",
                    "copytopoints::2.0",
                    "sphere",
                    "platonic",
                    "merge",
                    "xform",
                    "null",
                ),
            ),
        },
        indent=2,
        sort_keys=True,
    )
)
