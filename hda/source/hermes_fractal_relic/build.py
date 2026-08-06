"""build_hermes_relic — source-of-truth HDA builder.

Constructs `hermes::fractal_relic::1.0` by assembling native SOP nodes inside a subnet,
then wrapping it as an embedded digital asset. Run inside Houdini/hython.
"""
from __future__ import annotations

from typing import Any

from ..hermes_houdini import get_hou


def build(namespace: str = "hermes", name: str = "fractal_relic",
          version: str = "1.0", dest_dir: str = "") -> dict[str, Any]:
    hou = get_hou()
    # Build inside a temp subnet under /obj.
    obj = hou.node("/obj")
    subnet = obj.createNode("subnet", node_name="HERMES_RELIC_BUILD")
    parent = subnet

    base = parent.createNode("sphere", node_name="SRC_BASE", exact_type_name=True)
    base.parm("type").set(2)
    base.parm("radx").set(1.0)

    scatter = parent.createNode("scatter", node_name="SCATTER_PTS", exact_type_name=True)
    scatter.parm("force_total").set(1600)
    scatter.setInput(0, base)

    copy = parent.createNode("copy", node_name="COPY_INSTANCES", exact_type_name=True)
    copy.parm("pack").set(1)
    copy.setInput(0, scatter)

    out = parent.createNode("null", node_name="OUT_GEO", exact_type_name=True)
    out.setInput(0, copy)
    out.setDisplayFlag(True)
    out.setRenderFlag(True)

    type_name = f"{namespace}::{name}::{version}"
    hda_file = f"{dest_dir}/{namespace}_{name}.hdanc" if dest_dir else None
    definition = subnet.createDigitalAsset(
        name=type_name, hda_file_name=hda_file, save_as_embedded=not bool(hda_file)
    )
    definition.setUserData("hermes_license", "noncommercial")
    return {
        "type_name": type_name,
        "hda_file": hda_file,
        "noncommercial": True,
    }


__all__ = ["build"]
