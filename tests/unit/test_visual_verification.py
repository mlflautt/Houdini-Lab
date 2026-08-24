"""Dependency-free deterministic image gate and critique-packet tests."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

from hermes_houdini.visual_verification import (
    analyze_png,
    analyze_visual_evidence,
    build_critique_packet,
)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def _write_gray_png(path: Path, rows: list[list[int]]) -> None:
    height = len(rows)
    width = len(rows[0])
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def test_png_analyzer_rejects_black_and_accepts_three_present_panels(tmp_path):
    black = tmp_path / "black.png"
    _write_gray_png(black, [[0] * 60 for _ in range(30)])
    black_report = analyze_png(str(black), panel_count=3)
    assert black_report["status"] == "fail"
    assert "crushed_black" in black_report["flags"]

    comparison = tmp_path / "comparison.png"
    rows = [[240] * 60 for _ in range(30)]
    for panel in range(3):
        for y in range(6, 24):
            for x in range((panel * 20) + 4, (panel * 20) + 16):
                rows[y][x] = 30 + (panel * 40)
    _write_gray_png(comparison, rows)
    report = analyze_png(str(comparison), panel_count=3)
    assert report["status"] == "pass"
    assert all(panel["present"] for panel in report["panels"])
    assert report["subject_bbox"] == [4, 6, 55, 23]


def test_visual_report_detects_exact_duplicates(tmp_path):
    image = tmp_path / "image.png"
    duplicate = tmp_path / "duplicate.png"
    rows = [[255] * 20 for _ in range(20)]
    for y in range(5, 15):
        for x in range(5, 15):
            rows[y][x] = 0
    _write_gray_png(image, rows)
    duplicate.write_bytes(image.read_bytes())
    output = tmp_path / "visual.json"
    report = analyze_visual_evidence(
        image_paths=[str(image), str(duplicate)], output_path=str(output), panel_count=1
    )
    assert report["duplicate_images"] is True
    assert len(report["duplicate_sha256"]) == 1
    assert json.loads(output.read_text())["automatic_ranking"] is False


def test_critique_packet_hashes_minimum_evidence_without_inference(tmp_path):
    image = tmp_path / "image.png"
    _write_gray_png(image, [[0, 255], [255, 0]])
    graph = tmp_path / "graph.svg"
    validation = tmp_path / "validation.json"
    source = tmp_path / "skill.py"
    graph.write_text("<svg/>", encoding="utf-8")
    validation.write_text("{}", encoding="utf-8")
    source.write_text("VALUE = 1\n", encoding="utf-8")
    output = tmp_path / "packet.json"
    packet = build_critique_packet(
        image_paths=[str(image)],
        graph_path=str(graph),
        validation_paths=[str(validation)],
        code_paths=[str(source)],
        output_path=str(output),
    )
    assert packet["execution"]["performed"] is False
    assert packet["execution"]["network_transfer"] is False
    assert packet["decision_authority"] == "advisory_only"
    assert packet["winner"] is None
    assert len(packet["artifacts"]["images"][0]["sha256"]) == 64
