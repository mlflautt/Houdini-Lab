"""Visual observer (inside Houdini, needs `hou`).

Captures viewport screenshots, network-editor images, and low-cost Karma CPU previews
(docs §4.10). On Apprentice, render ceiling is enforced by policy.
"""
from __future__ import annotations

import os

from . import get_hou


def viewport_capture(pane_path: str | None = None,
                     output: str = "/tmp/hermes_viewport.png",
                     mode: str = "shaded") -> str:
    """Capture the viewport (or a specific pane) to `output`."""
    hou = get_hou()
    os.makedirs(os.path.dirname(output), exist_ok=True)
    vport = hou.ui.currentViewer()
    if vport is None:
        raise RuntimeError("no active viewer to capture")
    vport.saveViewportSnapshotToFile(output)
    return output


def capture_graph(node_path: str, output: str = "/tmp/hermes_graph.png") -> str:
    """Screenshot a network editor showing `node_path`."""
    hou = get_hou()
    os.makedirs(os.path.dirname(output), exist_ok=True)
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    # frame the node then capture the editor it lives in
    node.setCurrent(True, True)
    editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    if editor is None:
        raise RuntimeError("no network editor open")
    editor.saveSnapshot(output)
    return output


__all__ = ["viewport_capture", "capture_graph"]
