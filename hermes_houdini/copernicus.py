"""Bounded Copernicus reaction-diffusion observation and image export.

Pure validation is importable without Houdini. HOM execution cooks registered native COP
graphs, reads their image layers for numeric validation, and renders only managed ROP Image
nodes to new PNG artifacts.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import struct
import time
from pathlib import Path
from typing import Any

from . import get_hou
from .execution import current_envelope
from .schemas.command import Status, ToolResult

SCHEMA_VERSION = "1.0"
REACTION_PRESETS = ("smallwaves", "bigwaves", "spots")
REACTION_PRESET_COEFFICIENTS = {
    "smallwaves": {"kill": 0.3865, "killraw": 0.051, "feed": 0.0899, "feedraw": 0.018},
    "bigwaves": {"kill": 0.0, "killraw": 0.045, "feed": 0.0444, "feedraw": 0.014},
    "spots": {"kill": 0.8045, "killraw": 0.062, "feed": 0.2222, "feedraw": 0.03},
}
REACTION_RESOLUTIONS = (64, 128, 256, 512)
_ABS_NODE_PATH = re.compile(r"/(?:[A-Za-z0-9_.-]+)(?:/[A-Za-z0-9_.-]+)*\Z")


def _integer(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return value


def validate_reaction_spec(
    *,
    resolution: int,
    iterations: int,
    iterations_per_step: int,
    candidate_index: int,
    presets: list[str] | tuple[str, ...] = REACTION_PRESETS,
) -> dict[str, Any]:
    """Validate one deterministic three-candidate Reaction-Diffusion specification."""
    if resolution not in REACTION_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {list(REACTION_RESOLUTIONS)}")
    iteration_count = _integer(iterations, "iterations", minimum=1, maximum=12)
    per_step = _integer(iterations_per_step, "iterations_per_step", minimum=1, maximum=12)
    total_steps = iteration_count * per_step
    if total_steps > 48:
        raise ValueError("iterations * iterations_per_step must be <= 48")
    selected = _integer(candidate_index, "candidate_index", minimum=0, maximum=2)
    if not isinstance(presets, (list, tuple)) or tuple(presets) != REACTION_PRESETS:
        raise ValueError(f"presets must preserve exact order {list(REACTION_PRESETS)}")
    contact_scale = 1.0 if resolution <= 256 else 0.5
    contact_resolution = (round(resolution * 3 * contact_scale), round(resolution * contact_scale))
    return {
        "resolution": resolution,
        "iterations": iteration_count,
        "iterations_per_step": per_step,
        "total_steps": total_steps,
        "candidate_index": selected,
        "presets": list(REACTION_PRESETS),
        "contact_scale": contact_scale,
        "contact_resolution": list(contact_resolution),
    }


def _absolute_node_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ABS_NODE_PATH.fullmatch(value):
        raise ValueError(f"{label} must be an absolute Houdini node path")
    return value


def _append_jsonl(path: str, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _record(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    hou = get_hou()
    envelope = current_envelope()
    return {
        "schema": f"hermes.houdini.{kind}",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "houdini": {
            "build": hou.applicationVersionString(),
            "license": hou.licenseCategory().name(),
        },
        "request": envelope.as_dict() if envelope is not None else None,
        **payload,
    }


def _prepare_new_file(path: str, suffix: str) -> Path:
    output = Path(path).expanduser()
    if not output.is_absolute() or output.suffix.lower() != suffix:
        raise ValueError(f"output path must be an absolute {suffix} file")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _layer_metrics(node: Any, *, expected_resolution: tuple[int, int]) -> dict[str, Any]:
    layer = node.layer(0)
    width, height = (int(value) for value in layer.bufferResolution())
    if (width, height) != expected_resolution:
        raise ValueError(
            f"node {node.path()} resolution {width}x{height} does not match "
            f"expected {expected_resolution[0]}x{expected_resolution[1]}"
        )
    storage = str(layer.storageType())
    if not storage.endswith("Float32"):
        raise ValueError(f"node {node.path()} must use Float32 image storage, got {storage}")
    raw = layer.allBufferElements()
    pixel_count = width * height
    if pixel_count < 1 or len(raw) % (pixel_count * 4) != 0:
        raise ValueError(f"node {node.path()} returned an invalid image buffer")
    components = len(raw) // (pixel_count * 4)
    if components not in {1, 2, 3, 4}:
        raise ValueError(f"node {node.path()} returned {components} components per pixel")
    values = memoryview(raw).cast("f")
    minimum = math.inf
    maximum = -math.inf
    total = 0.0
    total_squared = 0.0
    nonfinite = 0
    for value in values:
        numeric = float(value)
        if not math.isfinite(numeric):
            nonfinite += 1
            continue
        minimum = min(minimum, numeric)
        maximum = max(maximum, numeric)
        total += numeric
        total_squared += numeric * numeric
    finite_count = len(values) - nonfinite
    if finite_count < 1:
        raise ValueError(f"node {node.path()} image contains no finite values")
    mean = total / finite_count
    variance = max(0.0, (total_squared / finite_count) - (mean * mean))
    sample_step = max(1, len(values) // 4096)
    sampled_unique = len(
        {round(float(values[index]), 5) for index in range(0, len(values), sample_step)}
    )
    return {
        "path": node.path(),
        "resolution": [width, height],
        "pixels": pixel_count,
        "components": components,
        "values": len(values),
        "memory_bytes": len(raw),
        "storage": storage,
        "buffer_sha256": hashlib.sha256(raw).hexdigest(),
        "minimum": minimum,
        "maximum": maximum,
        "dynamic_range": maximum - minimum,
        "mean": mean,
        "standard_deviation": math.sqrt(variance),
        "nonfinite_values": nonfinite,
        "sampled_unique_values": sampled_unique,
        "node_errors": [str(message) for message in node.errors()],
        "node_warnings": [str(message) for message in node.warnings()],
    }


def cook_validate_reaction(
    *,
    network_path: str,
    pattern_node_paths: list[str],
    contact_sheet_path: str,
    resolution: int,
    iterations: int,
    iterations_per_step: int,
    candidate_index: int,
    output_path: str,
    minimum_dynamic_range: float = 0.02,
    minimum_standard_deviation: float = 0.005,
) -> dict[str, Any]:
    """Cook three deterministic native patterns and record bounded pixel evidence."""
    hou = get_hou()
    spec = validate_reaction_spec(
        resolution=resolution,
        iterations=iterations,
        iterations_per_step=iterations_per_step,
        candidate_index=candidate_index,
    )
    network_path = _absolute_node_path(network_path, "network_path")
    if not isinstance(pattern_node_paths, list) or len(pattern_node_paths) != 3:
        raise ValueError("pattern_node_paths must contain exactly three nodes")
    normalized_paths = [
        _absolute_node_path(path, f"pattern_node_paths[{index}]")
        for index, path in enumerate(pattern_node_paths)
    ]
    contact_sheet_path = _absolute_node_path(contact_sheet_path, "contact_sheet_path")
    network = hou.node(network_path)
    if network is None or network.type().category().name() != "CopNet":
        raise ValueError(f"Copernicus network not found: {network_path}")
    if int(network.parm("setres").eval()) != 1 or tuple(
        int(value) for value in network.parmTuple("res").eval()
    ) != (resolution, resolution):
        raise ValueError("Copernicus network does not match the explicit square resolution")
    patterns = []
    for index, path in enumerate(normalized_paths):
        node = hou.node(path)
        if node is None or node.parent() != network:
            raise ValueError(f"pattern node is not inside {network_path}: {path}")
        if (
            node.type().category().name() != "Cop"
            or node.type().name() != "reactiondiffusion_block_end"
        ):
            raise ValueError(
                f"pattern node is not an exact Reaction-Diffusion Block End COP: {path}"
            )
        if node.userData("hermes_role") != f"reaction_pattern_{REACTION_PRESETS[index]}":
            raise ValueError(f"pattern node role does not match candidate order: {path}")
        if int(node.parm("simulate").eval()) != 0 or int(node.parm("continuouscook").eval()) != 0:
            raise ValueError("deterministic validation refuses simulation or Live Simulation mode")
        if int(node.parm("iterations").eval()) * int(node.parm("iterationsperstep").eval()) > 48:
            raise ValueError("managed Reaction-Diffusion node exceeds 48 integration steps")
        preset = REACTION_PRESETS[index]
        if node.parm("presetsgs").evalAsString() != preset:
            raise ValueError(f"pattern node preset token does not match candidate order: {path}")
        for parm_name, expected in REACTION_PRESET_COEFFICIENTS[preset].items():
            if not math.isclose(float(node.parm(parm_name).eval()), expected, abs_tol=1e-6):
                raise ValueError(
                    f"pattern {preset} has stale callback-driven coefficient {parm_name}"
                )
        patterns.append(node)
    contact = hou.node(contact_sheet_path)
    if (
        contact is None
        or contact.parent() != network
        or contact.userData("hermes_role") != "reaction_contact_sheet_contract"
    ):
        raise ValueError("contact_sheet_path is not the managed contact-sheet contract")

    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 90.0
    max_memory = int(policy.max_memory_bytes) if policy else 536_870_912
    policy_resolution = tuple(policy.max_resolution) if policy else (1280, 720)
    output = _prepare_new_file(output_path, ".json")
    started = time.monotonic()
    pattern_metrics: list[dict[str, Any]] = []
    for index, node in enumerate(patterns):
        node.cook(force=True)
        metrics = _layer_metrics(node, expected_resolution=(resolution, resolution))
        metrics["candidate_id"] = REACTION_PRESETS[index]
        metrics["preset"] = node.parm("presetsgs").evalAsString()
        metrics["seconds"] = round(float(node.lastCookTime()), 6)
        if metrics["nonfinite_values"]:
            raise ValueError(f"pattern {REACTION_PRESETS[index]} contains non-finite values")
        if metrics["dynamic_range"] < minimum_dynamic_range:
            raise ValueError(f"pattern {REACTION_PRESETS[index]} has insufficient dynamic range")
        if metrics["standard_deviation"] < minimum_standard_deviation:
            raise ValueError(f"pattern {REACTION_PRESETS[index]} has insufficient variation")
        if metrics["node_errors"] or metrics["node_warnings"]:
            raise ValueError(f"pattern {REACTION_PRESETS[index]} has Houdini messages")
        pattern_metrics.append(metrics)
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("Reaction-Diffusion validation exceeded policy.max_seconds")

    pattern_hashes = [item["buffer_sha256"] for item in pattern_metrics]
    if len(set(pattern_hashes)) != len(pattern_hashes):
        raise ValueError("Reaction-Diffusion candidates are not visually distinct")

    contact.cook(force=True)
    contact_resolution = tuple(spec["contact_resolution"])
    contact_metrics = _layer_metrics(contact, expected_resolution=contact_resolution)
    contact_metrics["seconds"] = round(float(contact.lastCookTime()), 6)
    total_memory = (
        sum(item["memory_bytes"] for item in pattern_metrics) + contact_metrics["memory_bytes"]
    )
    elapsed = time.monotonic() - started
    max_width, max_height = policy_resolution
    if contact_resolution[0] > max_width or contact_resolution[1] > max_height:
        raise ValueError("contact-sheet resolution exceeds policy.max_resolution")
    if total_memory > max_memory:
        raise ValueError("observed image buffers exceed policy.max_memory_bytes")
    if elapsed > max_seconds:
        raise TimeoutError("Reaction-Diffusion validation exceeded policy.max_seconds")
    if contact_metrics["node_errors"] or contact_metrics["node_warnings"]:
        raise ValueError("contact sheet has Houdini messages")

    document = _record(
        "reaction_diffusion_validation",
        {
            "status": "success",
            "network_path": network_path,
            "spec": spec,
            "patterns": pattern_metrics,
            "contact_sheet": contact_metrics,
            "elapsed_seconds": round(elapsed, 6),
            "total_buffer_memory_bytes": total_memory,
            "selection": {
                "method": "human",
                "preview_input": candidate_index,
                "winner": None,
                "automatic_ranking": False,
            },
        },
    )
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "artifact": str(output),
        "network_path": network_path,
        "spec": spec,
        "patterns": pattern_metrics,
        "contact_sheet": contact_metrics,
        "elapsed_seconds": round(elapsed, 6),
        "total_buffer_memory_bytes": total_memory,
        "selection": document["selection"],
    }


def _png_resolution(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"output is not a valid PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def export_managed_image(
    *,
    rop_path: str,
    output_path: str,
    log_path: str,
    expected_resolution: list[int],
    frame: float = 1.0,
) -> ToolResult:
    """Render one managed native ROP Image node to a new bounded PNG artifact."""
    hou = get_hou()
    rop_path = _absolute_node_path(rop_path, "rop_path")
    output = _prepare_new_file(output_path, ".png")
    if (
        not isinstance(expected_resolution, list)
        or len(expected_resolution) != 2
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in expected_resolution
        )
    ):
        raise ValueError("expected_resolution must contain two positive integers")
    if not isinstance(frame, (int, float)) or isinstance(frame, bool) or not math.isfinite(frame):
        raise ValueError("frame must be finite")
    rop = hou.node(rop_path)
    if rop is None or rop.type().category().name() != "Cop" or rop.type().name() != "rop_image":
        raise ValueError(f"ROP Image COP not found: {rop_path}")
    if rop.userData("hermes_role") not in {
        "reaction_contact_sheet_export",
        "reaction_selected_export",
    }:
        raise ValueError("image export accepts only a managed reaction-diffusion ROP")
    if rop.parm("copoutput").evalAsString() != str(output):
        raise ValueError("output_path does not match the managed ROP Image node")
    if rop.input(0) is None:
        raise ValueError("managed ROP Image has no explicit input")
    if rop.parm("trange").evalAsString() != "off":
        raise ValueError("managed ROP Image must render only the current frame")
    if int(rop.parm("docompile").eval()) != 0:
        raise ValueError("compiled COP cooks do not support Reaction-Diffusion simulation")
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_seconds = float(policy.max_seconds) if policy else 90.0
    max_output_bytes = int(policy.max_output_bytes) if policy else 536_870_912
    max_width, max_height = tuple(policy.max_resolution) if policy else (1280, 720)
    expected_width, expected_height = expected_resolution
    if expected_width > max_width or expected_height > max_height:
        raise ValueError("expected image resolution exceeds policy.max_resolution")
    original_frame = float(hou.frame())
    started = time.monotonic()
    try:
        hou.setFrame(float(frame))
        rop.render(
            frame_range=(float(frame), float(frame), 1.0), verbose=True, output_progress=True
        )
    finally:
        hou.setFrame(original_frame)
    elapsed = time.monotonic() - started
    if not output.is_file():
        raise RuntimeError(f"ROP Image completed without expected artifact: {output}")
    size = output.stat().st_size
    actual_resolution = _png_resolution(output)
    if actual_resolution != (expected_width, expected_height):
        raise RuntimeError(
            f"PNG resolution {actual_resolution} does not match expected "
            f"{(expected_width, expected_height)}"
        )
    if elapsed > max_seconds:
        raise TimeoutError("ROP Image export exceeded policy.max_seconds")
    if size > max_output_bytes:
        raise RuntimeError(f"image output {size} bytes exceeds policy.max_output_bytes")
    payload = {
        "status": "success",
        "rop_path": rop_path,
        "output_path": str(output),
        "resolution": list(actual_resolution),
        "frame": float(frame),
        "seconds": round(elapsed, 6),
        "bytes": size,
        "compiled_cook": False,
        "background": False,
    }
    _append_jsonl(log_path, _record("cop_image_export", payload))
    return ToolResult(status=Status.SUCCESS, artifacts=[str(output), log_path], data=payload)


__all__ = [
    "REACTION_PRESETS",
    "REACTION_RESOLUTIONS",
    "cook_validate_reaction",
    "REACTION_PRESET_COEFFICIENTS",
    "export_managed_image",
    "validate_reaction_spec",
]
