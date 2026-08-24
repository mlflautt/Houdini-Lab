"""Print pinned Houdini interfaces needed by the Sprint 16 district recipes."""

from __future__ import annotations

import hou


def describe(category: hou.NodeTypeCategory, type_name: str) -> None:
    node_type = category.nodeTypes().get(type_name)
    print(f"TYPE {category.name()} {type_name} exists={node_type is not None}")
    if node_type is None:
        return
    print("PARMS", ",".join(template.name() for template in node_type.parmTemplates()))


print("HOUDINI", hou.applicationVersionString())
for name in (
    "box",
    "color",
    "polybevel::3.0",
    "normal",
    "merge",
    "null",
    "file",
    "xform",
    "font",
):
    describe(hou.sopNodeTypeCategory(), name)
for name in ("wedge", "ropgeometry", "waitforall", "null", "localscheduler"):
    describe(hou.topNodeTypeCategory(), name)

tasks = hou.node("/tasks")
probe = tasks.createNode("topnet", node_name="HERMES_DISTRICT_WEDGE_PROBE")
wedge = probe.createNode("wedge", node_name="WEDGE")
wedge.parm("wedgecount").set(12)
wedge.parm("seed").set(1601)
wedge.parm("wedgeattributes").set(2)
for slot, name, value_range in ((1, "style_index", (0, 2)), (2, "height", (4.0, 18.0))):
    wedge.parm(f"name{slot}").set(name)
    wedge.parm(f"type{slot}").set(2 if slot == 1 else 0)
    wedge.parm(f"wedgetype{slot}").set(0)
    wedge.parmTuple(f"intrange{slot}" if slot == 1 else f"floatrange{slot}").set(value_range)
    wedge.parm(f"exportchannel{slot}").set(0)
wedge.generateStaticWorkItems(block=True)
for item in wedge.getPDGNode().workItems:
    values = item.attribValues()
    print("WEDGE", int(values["wedgeindex"]), int(values["style_index"]), float(values["height"]))
probe.destroy()
