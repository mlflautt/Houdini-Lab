"""Selection-independent graph and viewport observation.

Graph SVG generation works in hython. Viewport capture is GUI-only and requires explicit
viewer, viewport, and camera identifiers; it never relies on the active pane or selection.
"""

from __future__ import annotations

import html
import json
import math
import os
from typing import Any

from . import get_hou
from .cook import metrics_for_clean_node
from .execution import current_envelope
from .graph_state import snapshot_networks
from .policy import ApprenticePolicy


def _prepare_output(output_path: str, suffix: str) -> None:
    if not isinstance(output_path, str) or not output_path:
        raise ValueError("output_path must be a non-empty path")
    if not output_path.lower().endswith(suffix):
        raise ValueError(f"output_path must end with {suffix}")
    envelope = current_envelope()
    allow_overwrite = bool(envelope and envelope.policy and envelope.policy.allow_overwrite)
    if os.path.exists(output_path) and not allow_overwrite:
        raise FileExistsError(f"output already exists and overwrite is disabled: {output_path}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)


def graph_svg(node_path: str, output_path: str, max_nodes: int = 500) -> dict[str, Any]:
    """Render a deterministic SVG of a node's direct child network."""
    hou = get_hou()
    parent = hou.node(node_path)
    if parent is None:
        raise ValueError(f"network not found: {node_path}")
    children = sorted(parent.children(), key=lambda node: node.path())
    if not isinstance(max_nodes, int) or isinstance(max_nodes, bool) or max_nodes < 1:
        raise ValueError("max_nodes must be a positive integer")
    if len(children) > max_nodes:
        raise ValueError(f"network has {len(children)} nodes; capture cap is {max_nodes}")
    _prepare_output(output_path, ".svg")

    node_width = 180.0
    node_height = 76.0
    scale_x = 105.0
    scale_y = 92.0
    margin = 55.0
    positions: dict[str, tuple[float, float]] = {}
    raw = [(float(node.position()[0]), float(node.position()[1])) for node in children]
    min_x = min((position[0] for position in raw), default=0.0)
    max_y = max((position[1] for position in raw), default=0.0)
    for node, (x, y) in zip(children, raw, strict=True):
        positions[node.path()] = (
            margin + (x - min_x) * scale_x,
            margin + (max_y - y) * scale_y,
        )
    width = max(
        640.0,
        max((x + node_width + margin for x, _ in positions.values()), default=640.0),
    )
    height = max(
        360.0,
        max((y + node_height + margin for _, y in positions.values()), default=360.0),
    )

    wires: list[str] = []
    wire_count = 0
    for target in children:
        target_position = positions[target.path()]
        for connection in target.inputConnections():
            source_path = connection.inputNode().path()
            if source_path not in positions:
                continue
            source_position = positions[source_path]
            x1 = source_position[0] + node_width / 2
            y1 = source_position[1] + node_height
            x2 = target_position[0] + node_width / 2
            y2 = target_position[1]
            middle = (y1 + y2) / 2
            wires.append(
                f'<path d="M{x1:.1f},{y1:.1f} C{x1:.1f},{middle:.1f} '
                f'{x2:.1f},{middle:.1f} {x2:.1f},{y2:.1f}" class="wire"/>'
            )
            wire_count += 1

    boxes: list[str] = []
    for node in children:
        x, y = positions[node.path()]
        role = node.userData("hermes_role") or ""
        hermes_id = node.userData("hermes_id") or "unmanaged"
        fill = "#275d80" if role else "#3f4652"
        if node.name().startswith("OUT_"):
            fill = "#2f7d5b"
        boxes.extend(
            [
                f'<g transform="translate({x:.1f},{y:.1f})">',
                f'<rect width="{node_width}" height="{node_height}" rx="9" fill="{fill}"/>',
                f'<text x="12" y="25" class="name">{html.escape(node.name())}</text>',
                f'<text x="12" y="45" class="meta">{html.escape(node.type().name())}</text>',
                f'<text x="12" y="62" class="meta">{html.escape(role or hermes_id)}</text>',
                "</g>",
            ]
        )

    title = html.escape(parent.path())
    document = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
            f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
            "<style>",
            ".background{fill:#171a20}.wire{fill:none;stroke:#8ca0b3;stroke-width:3}",
            ".title{fill:#f3f5f7;font:600 18px sans-serif}",
            ".name{fill:#fff;font:600 14px sans-serif}.meta{fill:#d9e0e7;font:11px monospace}",
            "</style>",
            f'<rect class="background" width="{width:.0f}" height="{height:.0f}"/>',
            f'<text x="20" y="28" class="title">{title}</text>',
            *wires,
            *boxes,
            "</svg>",
        ]
    )
    with open(output_path, "w", encoding="utf-8") as stream:
        stream.write(document)
        stream.flush()
        os.fsync(stream.fileno())
    return {
        "artifact": output_path,
        "network_path": parent.path(),
        "nodes": len(children),
        "wires": wire_count,
        "format": "svg",
    }


def graph_manifest(
    *,
    node_path: str,
    output_path: str,
    public_parameters: dict[str, list[str]] | None = None,
    metric_node_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a deterministic graph/provenance manifest without implicitly cooking nodes."""
    hou = get_hou()
    parent = hou.node(node_path)
    if parent is None:
        raise ValueError(f"network not found: {node_path}")
    tracked = public_parameters or {}
    if not isinstance(tracked, dict) or any(
        not isinstance(path, str)
        or not path.startswith("/")
        or not isinstance(names, list)
        or any(not isinstance(name, str) or not name for name in names)
        for path, names in tracked.items()
    ):
        raise ValueError("public_parameters must map absolute node paths to parameter-name lists")
    metric_paths = metric_node_paths or []
    if not isinstance(metric_paths, list) or any(
        not isinstance(path, str) or not path.startswith("/") for path in metric_paths
    ):
        raise ValueError("metric_node_paths must be a list of absolute node paths")
    extra = metadata or {}
    if not isinstance(extra, dict):
        raise ValueError("metadata must be an object")
    try:
        normalized_metadata = json.loads(json.dumps(extra, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"metadata must be finite JSON data: {exc}") from exc
    if len(json.dumps(normalized_metadata, separators=(",", ":"))) > 262_144:
        raise ValueError("metadata exceeds 256 KiB")

    _prepare_output(output_path, ".json")
    envelope = current_envelope()
    document = {
        "schema": "hermes.houdini.graph_manifest",
        "schema_version": "1.0",
        "houdini": {
            "build": hou.applicationVersionString(),
            "license": (
                hou.licenseCategory().name() if hasattr(hou, "licenseCategory") else "unknown"
            ),
        },
        "network_path": parent.path(),
        "graph": snapshot_networks(
            [parent.path()], {path: set(names) for path, names in tracked.items()}
        ),
        "metrics": {path: metrics_for_clean_node(path) for path in metric_paths},
        "metadata": normalized_metadata,
        "request": envelope.as_dict() if envelope is not None else None,
    }
    with open(output_path, "w", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {
        "artifact": output_path,
        "network_path": parent.path(),
        "nodes": len(parent.children()),
        "metric_nodes": metric_paths,
        "schema": document["schema"],
    }


def list_viewers() -> dict[str, Any]:
    """List stable viewer and viewport names available on the current desktop."""
    hou = get_hou()
    if not hou.isUIAvailable() or not hasattr(hou, "ui"):
        return {"available": False, "viewers": []}
    desktop = hou.ui.curDesktop()
    viewers = []
    for tab in desktop.paneTabs():
        if tab.type() != hou.paneTabType.SceneViewer:
            continue
        viewers.append(
            {
                "name": tab.name(),
                "full_name": tab.fullName(),
                "viewports": [
                    {
                        "name": viewport.name(),
                        "camera_path": viewport.cameraPath(),
                    }
                    for viewport in tab.viewports()
                ],
            }
        )
    return {"available": True, "desktop": desktop.name(), "viewers": viewers}


def validate_viewport_capture(*, width: int, height: int, frame: float, output_path: str) -> None:
    """Pure validation for a one-frame Apprentice-safe capture."""
    if not isinstance(width, int) or isinstance(width, bool) or width < 2:
        raise ValueError("width must be an integer >= 2")
    if not isinstance(height, int) or isinstance(height, bool) or height < 2:
        raise ValueError("height must be an integer >= 2")
    ok, message = ApprenticePolicy().validate_render_resolution(width, height)
    if not ok:
        raise ValueError(message)
    if not isinstance(frame, int) or isinstance(frame, bool) or not math.isfinite(float(frame)):
        raise ValueError("viewport frame must be a finite integer")
    if not output_path.lower().endswith(".png"):
        raise ValueError("viewport output_path must end with .png")
    if "$" in output_path or "`" in output_path:
        raise ValueError("viewport output_path must name one literal PNG, not a sequence")
    envelope = current_envelope()
    if envelope and envelope.policy:
        max_width, max_height = envelope.policy.max_resolution
        if width > max_width or height > max_height:
            raise ValueError(
                f"resolution {width}x{height} exceeds command budget {max_width}x{max_height}"
            )


def viewport_capture(
    *,
    viewer_name: str,
    viewport_name: str,
    camera_path: str,
    output_path: str,
    frame: float,
    width: int = 1280,
    height: int = 720,
) -> dict[str, Any]:
    """Capture one named GUI viewport through one explicit camera to a PNG."""
    validate_viewport_capture(width=width, height=height, frame=frame, output_path=output_path)
    _prepare_output(output_path, ".png")
    hou = get_hou()
    if not hou.isUIAvailable() or not hasattr(hou, "ui"):
        raise RuntimeError("viewport capture requires interactive Houdini")
    viewer = hou.ui.curDesktop().findPaneTab(viewer_name)
    if viewer is None or viewer.type() != hou.paneTabType.SceneViewer:
        raise ValueError(f"named scene viewer not found: {viewer_name}")
    viewport = viewer.findViewport(viewport_name)
    if viewport is None:
        raise ValueError(f"viewport {viewport_name!r} not found in {viewer_name!r}")
    camera = hou.node(camera_path)
    if camera is None or camera.type().category().name() != "Object":
        raise ValueError(f"object camera not found: {camera_path}")

    old_camera = viewport.camera()
    old_default = viewport.defaultCamera().stash()
    settings = viewer.flipbookSettings().stash()
    settings.outputToMPlay(False)
    settings.output(output_path)
    settings.frameRange((frame, frame))
    settings.frameIncrement(1)
    settings.useResolution(True)
    settings.resolution((width, height))
    settings.appendFramesToCurrent(False)
    try:
        viewport.setCamera(camera)
        viewer.flipbook(viewport, settings, open_dialog=False)
    finally:
        if old_camera is not None:
            viewport.setCamera(old_camera)
        else:
            viewport.useDefaultCamera()
            viewport.setDefaultCamera(old_default)
    if not os.path.isfile(output_path):
        raise RuntimeError("flipbook returned without creating the requested image")
    return {
        "artifact": output_path,
        "viewer_name": viewer_name,
        "viewport_name": viewport_name,
        "camera_path": camera_path,
        "frame": float(frame),
        "resolution": [width, height],
    }


__all__ = [
    "graph_manifest",
    "graph_svg",
    "list_viewers",
    "validate_viewport_capture",
    "viewport_capture",
]
