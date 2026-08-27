"""Deterministic visual diagnostics and advisory multimodal critique packets.

The PNG analyzer is intentionally dependency-free and catches mechanical visual failures before
any model is consulted. Critique packets hash the exact image, graph, validation, and code inputs;
they do not call a network service or imply an aesthetic winner.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import time
import zlib
from collections import Counter
from pathlib import Path
from typing import Any

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SCHEMA_VERSION = "1.0"


def _new_json_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or path.suffix.lower() != ".json":
        raise ValueError("output_path must be an absolute .json path")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _existing_absolute(value: str, label: str, suffixes: set[str] | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"{label} must be an existing absolute file path")
    if suffixes is not None and path.suffix.lower() not in suffixes:
        raise ValueError(f"{label} must use one of: {', '.join(sorted(suffixes))}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unfilter(raw: bytes, width: int, height: int, channels: int) -> list[bytes]:
    stride = width * channels
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError(f"PNG scanline payload is {len(raw)} bytes; expected {expected}")
    rows: list[bytes] = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        source = raw[offset : offset + stride]
        offset += stride
        result = bytearray(stride)
        for index, value in enumerate(source):
            left = result[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                candidate = left + above - upper_left
                pa = abs(candidate - left)
                pb = abs(candidate - above)
                pc = abs(candidate - upper_left)
                predictor = left if pa <= pb and pa <= pc else (above if pb <= pc else upper_left)
            else:
                raise ValueError(f"unsupported PNG filter type: {filter_type}")
            result[index] = (value + predictor) & 0xFF
        rows.append(bytes(result))
        previous = result
    return rows


def _decode_png(path: Path) -> tuple[int, int, list[int]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"not a PNG file: {path}")
    offset = len(PNG_SIGNATURE)
    header: tuple[int, int, int, int, int, int, int] | None = None
    compressed = bytearray()
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            header = struct.unpack(">IIBBBBB", payload)
        elif chunk_type == b"IDAT":
            compressed.extend(payload)
        elif chunk_type == b"IEND":
            break
    if header is None:
        raise ValueError("PNG has no IHDR chunk")
    width, height, bit_depth, color_type, compression, filter_method, interlace = header
    if width < 1 or height < 1 or width * height > 16_777_216:
        raise ValueError("PNG dimensions are empty or exceed the 16 megapixel verification limit")
    if bit_depth != 8 or compression != 0 or filter_method != 0 or interlace != 0:
        raise ValueError("only non-interlaced 8-bit PNG images are supported")
    channels_by_type = {0: 1, 2: 3, 4: 2, 6: 4}
    if color_type not in channels_by_type:
        raise ValueError(f"unsupported PNG color type: {color_type}")
    channels = channels_by_type[color_type]
    rows = _unfilter(zlib.decompress(bytes(compressed)), width, height, channels)
    luminance: list[int] = []
    for row in rows:
        for index in range(0, len(row), channels):
            if color_type in {0, 4}:
                luminance.append(row[index])
            else:
                red, green, blue = row[index : index + 3]
                luminance.append(round((0.2126 * red) + (0.7152 * green) + (0.0722 * blue)))
    return width, height, luminance


def _entropy(values: list[int]) -> float:
    counts = Counter(value // 8 for value in values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _occupancy(
    values: list[int],
    width: int,
    height: int,
    *,
    x0: int = 0,
    x1: int | None = None,
    y0: int = 0,
    y1: int | None = None,
) -> tuple[float, tuple[int, int, int, int] | None]:
    x1 = width if x1 is None else x1
    y1 = height if y1 is None else y1
    corners = [values[0], values[width - 1], values[(height - 1) * width], values[-1]]
    background = sorted(corners)[len(corners) // 2]
    threshold = 12
    occupied: list[tuple[int, int]] = []
    region_pixels = max(1, (x1 - x0) * (y1 - y0))
    for y in range(y0, y1):
        row = y * width
        for x in range(x0, x1):
            if abs(values[row + x] - background) >= threshold:
                occupied.append((x, y))
    if not occupied:
        return 0.0, None
    xs = [item[0] for item in occupied]
    ys = [item[1] for item in occupied]
    return len(occupied) / region_pixels, (min(xs), min(ys), max(xs), max(ys))


def _panel_composition(
    bbox: tuple[int, int, int, int] | None,
    *,
    x0: int,
    x1: int,
    y0: int,
    y1: int,
) -> dict[str, Any] | None:
    if bbox is None:
        return None
    region_width = max(1, x1 - x0)
    region_height = max(1, y1 - y0)
    bbox_width = bbox[2] - bbox[0] + 1
    bbox_height = bbox[3] - bbox[1] + 1
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2
    region_center_x = (x0 + x1 - 1) / 2
    region_center_y = (y0 + y1 - 1) / 2
    left = bbox[0] - x0
    right = (x1 - 1) - bbox[2]
    top = bbox[1] - y0
    bottom = (y1 - 1) - bbox[3]
    return {
        "bbox_fill_width": round(bbox_width / region_width, 6),
        "bbox_fill_height": round(bbox_height / region_height, 6),
        "center_offset_x": round((center_x - region_center_x) / max(1.0, region_width / 2), 6),
        "center_offset_y": round((center_y - region_center_y) / max(1.0, region_height / 2), 6),
        "horizontal_margin_balance": round(abs(left - right) / region_width, 6),
        "vertical_margin_balance": round(abs(top - bottom) / region_height, 6),
        "margins": {"left": left, "right": right, "top": top, "bottom": bottom},
    }


def analyze_png(path: str, *, panel_count: int = 1, panel_rows: int = 1) -> dict[str, Any]:
    """Return deterministic exposure, occupancy, crop, entropy, edge, and panel diagnostics."""
    image = _existing_absolute(path, "path", {".png"})
    if (
        not isinstance(panel_count, int)
        or isinstance(panel_count, bool)
        or not 1 <= panel_count <= 12
    ):
        raise ValueError("panel_count must be an integer between 1 and 12")
    if (
        not isinstance(panel_rows, int)
        or isinstance(panel_rows, bool)
        or not 1 <= panel_rows <= panel_count
        or panel_count % panel_rows
    ):
        raise ValueError("panel_rows must be a positive divisor of panel_count")
    panel_columns = panel_count // panel_rows
    width, height, values = _decode_png(image)
    total = len(values)
    mean = sum(values) / total
    variance = sum((value - mean) ** 2 for value in values) / total
    standard_deviation = math.sqrt(variance)
    black_fraction = sum(value <= 5 for value in values) / total
    white_fraction = sum(value >= 250 for value in values) / total
    occupancy, bbox = _occupancy(values, width, height)
    horizontal_edges = sum(
        abs(values[(y * width) + x] - values[(y * width) + x - 1]) >= 24
        for y in range(height)
        for x in range(1, width)
    )
    vertical_edges = sum(
        abs(values[(y * width) + x] - values[((y - 1) * width) + x]) >= 24
        for y in range(1, height)
        for x in range(width)
    )
    edge_density = (horizontal_edges + vertical_edges) / max(
        1, (height * (width - 1)) + ((height - 1) * width)
    )
    panels = []
    for index in range(panel_count):
        row = index // panel_columns
        column = index % panel_columns
        x0 = round(column * width / panel_columns)
        x1 = round((column + 1) * width / panel_columns)
        y0 = round(row * height / panel_rows)
        y1 = round((row + 1) * height / panel_rows)
        panel_occupancy, panel_bbox = _occupancy(
            values, width, height, x0=x0, x1=x1, y0=y0, y1=y1
        )
        panels.append(
            {
                "index": index,
                "row": row,
                "column": column,
                "x_range": [x0, x1],
                "y_range": [y0, y1],
                "occupancy_fraction": round(panel_occupancy, 6),
                "subject_bbox": list(panel_bbox) if panel_bbox else None,
                "present": panel_occupancy >= 0.002,
                "composition": _panel_composition(
                    panel_bbox, x0=x0, x1=x1, y0=y0, y1=y1
                ),
            }
        )
    flags = []
    if standard_deviation < 2.0 or occupancy < 0.002:
        flags.append("blank_or_nearly_blank")
    if black_fraction > 0.98:
        flags.append("crushed_black")
    if white_fraction > 0.98:
        flags.append("blown_white")
    if 0.002 <= occupancy < 0.01:
        flags.append("subject_too_small")
    if standard_deviation < 8.0:
        flags.append("low_contrast")
    crop_margin = max(2, round(min(width, height) * 0.02))
    if (
        bbox
        and occupancy >= 0.01
        and (
            bbox[0] < crop_margin
            or bbox[1] < crop_margin
            or bbox[2] >= width - crop_margin
            or bbox[3] >= height - crop_margin
        )
    ):
        flags.append("possible_crop")
    if any(not panel["present"] for panel in panels):
        flags.append("missing_comparison_panel")
    if any(
        panel["composition"]
        and (
            panel["composition"]["horizontal_margin_balance"] > 0.65
            or panel["composition"]["vertical_margin_balance"] > 0.65
        )
        for panel in panels
    ):
        flags.append("severe_panel_margin_imbalance")
    hard_failures = {"blank_or_nearly_blank", "crushed_black", "blown_white"}
    status = "fail" if hard_failures.intersection(flags) else ("warn" if flags else "pass")
    return {
        "path": str(image),
        "sha256": _sha256(image),
        "width": width,
        "height": height,
        "luminance_mean": round(mean, 6),
        "luminance_stddev": round(standard_deviation, 6),
        "black_fraction": round(black_fraction, 6),
        "white_fraction": round(white_fraction, 6),
        "occupancy_fraction": round(occupancy, 6),
        "subject_bbox": list(bbox) if bbox else None,
        "crop_margin_pixels": crop_margin,
        "entropy_32_bin": round(_entropy(values), 6),
        "edge_density": round(edge_density, 6),
        "panels": panels,
        "panel_grid": {"rows": panel_rows, "columns": panel_columns},
        "flags": flags,
        "status": status,
    }


def _sequence_difference(first_path: str, second_path: str) -> dict[str, Any]:
    first_width, first_height, first = _decode_png(Path(first_path))
    second_width, second_height, second = _decode_png(Path(second_path))
    if (first_width, first_height) != (second_width, second_height):
        return {
            "from_path": first_path,
            "to_path": second_path,
            "comparable": False,
            "from_dimensions": [first_width, first_height],
            "to_dimensions": [second_width, second_height],
        }
    differences = [abs(left - right) for left, right in zip(first, second, strict=True)]
    changed = [index for index, value in enumerate(differences) if value >= 12]
    motion_bbox = None
    if changed:
        xs = [index % first_width for index in changed]
        ys = [index // first_width for index in changed]
        motion_bbox = [min(xs), min(ys), max(xs), max(ys)]
    motion_width = (motion_bbox[2] - motion_bbox[0] + 1) if motion_bbox else 0
    motion_height = (motion_bbox[3] - motion_bbox[1] + 1) if motion_bbox else 0
    return {
        "from_path": first_path,
        "to_path": second_path,
        "comparable": True,
        "dimensions": [first_width, first_height],
        "changed_fraction": round(len(changed) / len(differences), 6),
        "mean_absolute_luminance_delta": round(sum(differences) / len(differences), 6),
        "motion_bbox": motion_bbox,
        "motion_bbox_fill_width": round(motion_width / first_width, 6),
        "motion_bbox_fill_height": round(motion_height / first_height, 6),
    }


def analyze_visual_evidence(
    *,
    image_paths: list[str],
    output_path: str,
    panel_count: int = 1,
    panel_rows: int = 1,
    expect_motion: bool = False,
) -> dict[str, Any]:
    """Analyze one or more PNGs, detect exact duplicates, and write a durable report."""
    if not isinstance(image_paths, list) or not 1 <= len(image_paths) <= 24:
        raise ValueError("image_paths must contain 1-24 absolute PNG paths")
    output = _new_json_path(output_path)
    if not isinstance(expect_motion, bool):
        raise ValueError("expect_motion must be boolean")
    images = [
        analyze_png(path, panel_count=panel_count, panel_rows=panel_rows)
        for path in image_paths
    ]
    hashes = Counter(item["sha256"] for item in images)
    duplicate_hashes = sorted(digest for digest, count in hashes.items() if count > 1)
    pairs = [
        _sequence_difference(image_paths[index], image_paths[index + 1])
        for index in range(len(image_paths) - 1)
    ]
    sequence_flags = []
    if any(not pair["comparable"] for pair in pairs):
        sequence_flags.append("incompatible_sequence_dimensions")
    comparable_pairs = [pair for pair in pairs if pair["comparable"]]
    if expect_motion and len(image_paths) < 2:
        sequence_flags.append("insufficient_motion_samples")
    if expect_motion and duplicate_hashes:
        sequence_flags.append("duplicate_motion_frame")
    if expect_motion and comparable_pairs and max(
        pair["changed_fraction"] for pair in comparable_pairs
    ) < 0.005:
        sequence_flags.append("motion_too_subtle")
    if expect_motion and comparable_pairs and all(
        pair["motion_bbox_fill_width"] < 0.2 or pair["motion_bbox_fill_height"] < 0.2
        for pair in comparable_pairs
    ):
        sequence_flags.append("motion_confined_to_narrow_band")
    failed_image_indices = [
        index for index, image in enumerate(images) if image["status"] == "fail"
    ]
    if expect_motion and failed_image_indices:
        if len(failed_image_indices) == len(images):
            sequence_flags.append("all_motion_frames_mechanically_failed")
        elif failed_image_indices[-1] == len(images) - 1:
            sequence_flags.append("terminal_motion_frame_mechanically_failed")
        else:
            sequence_flags.append("sparse_or_exposure_failed_motion_frames")
    sequence_failures = {
        "all_motion_frames_mechanically_failed",
        "duplicate_motion_frame",
        "incompatible_sequence_dimensions",
        "insufficient_motion_samples",
        "motion_too_subtle",
        "terminal_motion_frame_mechanically_failed",
    }
    sequence_status = (
        "fail"
        if sequence_failures.intersection(sequence_flags)
        else ("warn" if sequence_flags else "pass")
    )
    statuses = [item["status"] for item in images]
    if expect_motion:
        overall = (
            "fail"
            if sequence_status == "fail"
            else (
                "warn"
                if "fail" in statuses or "warn" in statuses or sequence_status == "warn"
                else "pass"
            )
        )
    else:
        overall = (
            "fail"
            if "fail" in statuses or sequence_status == "fail"
            else ("warn" if "warn" in statuses or sequence_status == "warn" else "pass")
        )
    report = {
        "schema": "hermes.visual_verification",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "status": overall,
        "images": images,
        "duplicate_sha256": duplicate_hashes,
        "duplicate_images": bool(duplicate_hashes),
        "sequence": {
            "expected_motion": expect_motion,
            "pairs": pairs,
            "flags": sequence_flags,
            "status": sequence_status,
        },
        "decision_authority": "mechanical_quality_gate_only",
        "aesthetic_winner": None,
        "automatic_ranking": False,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"artifact": str(output), **report}


def build_critique_packet(
    *,
    image_paths: list[str],
    graph_path: str,
    validation_paths: list[str],
    code_paths: list[str],
    output_path: str,
    rubric: list[str] | None = None,
) -> dict[str, Any]:
    """Hash a minimum-evidence packet for an optional local or external multimodal critic."""
    if not isinstance(image_paths, list) or not 1 <= len(image_paths) <= 12:
        raise ValueError("image_paths must contain 1-12 files")
    if not isinstance(validation_paths, list) or not 1 <= len(validation_paths) <= 12:
        raise ValueError("validation_paths must contain 1-12 files")
    if not isinstance(code_paths, list) or not 1 <= len(code_paths) <= 24:
        raise ValueError("code_paths must contain 1-24 files")
    requested_rubric = rubric or [
        "mechanical_failures",
        "subject_readability",
        "composition_and_crop",
        "candidate_distinctness",
        "graph_intent_matches_render",
        "actionable_next_edit",
    ]
    if (
        not isinstance(requested_rubric, list)
        or not requested_rubric
        or any(not isinstance(item, str) or not item.strip() for item in requested_rubric)
    ):
        raise ValueError("rubric must contain non-empty strings")
    output = _new_json_path(output_path)
    groups = {
        "images": [_existing_absolute(path, "image_paths item") for path in image_paths],
        "graph": [_existing_absolute(graph_path, "graph_path")],
        "validations": [
            _existing_absolute(path, "validation_paths item") for path in validation_paths
        ],
        "code": [_existing_absolute(path, "code_paths item") for path in code_paths],
    }
    artifacts = {
        group: [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in paths
        ]
        for group, paths in groups.items()
    }
    packet = {
        "schema": "hermes.multimodal_critique_packet",
        "schema_version": SCHEMA_VERSION,
        "timestamp_unix": time.time(),
        "artifacts": artifacts,
        "rubric": requested_rubric,
        "requested_response_schema": {
            "mechanical_status": "pass|warn|fail",
            "observations": "list of evidence-linked statements",
            "suggested_edits": "list of bounded graph or parameter edits",
            "uncertainties": "list",
            "aesthetic_scores": "optional per-candidate advisory scores",
            "winner": None,
        },
        "execution": {
            "performed": False,
            "provider": None,
            "model": None,
            "network_transfer": False,
            "note": "Inference is a separate explicitly approved action",
        },
        "decision_authority": "advisory_only",
        "automatic_ranking": False,
        "winner": None,
        "human_review_trigger": "only unresolved model disagreement, policy failure, or final taste choice",
    }
    output.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with output.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"artifact": str(output), **packet}


__all__ = [
    "analyze_png",
    "analyze_visual_evidence",
    "build_critique_packet",
]
