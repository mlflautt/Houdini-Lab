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


def test_png_analyzer_reports_two_by_two_grid_composition(tmp_path):
    comparison = tmp_path / "grid.png"
    rows = [[240] * 40 for _ in range(40)]
    for row in range(2):
        for column in range(2):
            for y in range((row * 20) + 5, (row * 20) + 15):
                for x in range((column * 20) + 5, (column * 20) + 15):
                    rows[y][x] = 30 + ((row * 2 + column) * 30)
    _write_gray_png(comparison, rows)
    report = analyze_png(str(comparison), panel_count=4, panel_rows=2)
    assert report["status"] == "pass"
    assert report["panel_grid"] == {"rows": 2, "columns": 2}
    assert [(panel["row"], panel["column"]) for panel in report["panels"]] == [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    ]
    assert all(panel["present"] for panel in report["panels"])
    assert all(panel["composition"]["center_offset_x"] == 0 for panel in report["panels"])
    assert all(panel["composition"]["center_offset_y"] == 0 for panel in report["panels"])


def test_motion_sequence_rejects_duplicates_and_accepts_visible_change(tmp_path):
    first = tmp_path / "first.png"
    static = tmp_path / "static.png"
    moved = tmp_path / "moved.png"
    first_rows = [[240] * 40 for _ in range(40)]
    moved_rows = [[240] * 40 for _ in range(40)]
    for y in range(12, 28):
        for x in range(8, 24):
            first_rows[y][x] = 30
            moved_rows[y][x + 5] = 30
    _write_gray_png(first, first_rows)
    static.write_bytes(first.read_bytes())
    _write_gray_png(moved, moved_rows)

    static_report = analyze_visual_evidence(
        image_paths=[str(first), str(static)],
        output_path=str(tmp_path / "static.json"),
        expect_motion=True,
    )
    assert static_report["status"] == "fail"
    assert "duplicate_motion_frame" in static_report["sequence"]["flags"]
    assert "motion_too_subtle" in static_report["sequence"]["flags"]

    moving_report = analyze_visual_evidence(
        image_paths=[str(first), str(moved)],
        output_path=str(tmp_path / "moving.json"),
        expect_motion=True,
    )
    assert moving_report["status"] == "pass"
    assert moving_report["sequence"]["flags"] == []
    assert moving_report["sequence"]["pairs"][0]["changed_fraction"] > 0.005
    assert moving_report["automatic_ranking"] is False


def test_motion_sequence_warns_when_change_is_confined_to_a_narrow_band(tmp_path):
    first = tmp_path / "band_first.png"
    second = tmp_path / "band_second.png"
    first_rows = [[240] * 80 for _ in range(80)]
    second_rows = [[240] * 80 for _ in range(80)]
    for y in range(36, 44):
        for x in range(8, 58):
            first_rows[y][x] = 30
            second_rows[y][x + 10] = 30
    _write_gray_png(first, first_rows)
    _write_gray_png(second, second_rows)
    report = analyze_visual_evidence(
        image_paths=[str(first), str(second)],
        output_path=str(tmp_path / "band.json"),
        expect_motion=True,
    )
    assert report["status"] == "warn"
    assert report["sequence"]["status"] == "warn"
    assert "motion_confined_to_narrow_band" in report["sequence"]["flags"]
    assert report["sequence"]["pairs"][0]["motion_bbox_fill_height"] < 0.2


def test_motion_sequence_allows_sparse_failed_lead_in_but_requires_visible_terminal_frame(
    tmp_path,
):
    sparse = tmp_path / "sparse.png"
    visible = tmp_path / "visible.png"
    failed_terminal = tmp_path / "failed_terminal.png"
    _write_gray_png(sparse, [[0] * 80 for _ in range(80)])
    visible_rows = [[0] * 80 for _ in range(80)]
    for y in range(20, 60):
        for x in range(20, 60):
            visible_rows[y][x] = 220
    _write_gray_png(visible, visible_rows)
    failed_terminal.write_bytes(sparse.read_bytes())

    emerging = analyze_visual_evidence(
        image_paths=[str(sparse), str(visible)],
        output_path=str(tmp_path / "emerging.json"),
        expect_motion=True,
    )
    assert emerging["status"] == "warn"
    assert emerging["sequence"]["status"] == "warn"
    assert "sparse_or_exposure_failed_motion_frames" in emerging["sequence"]["flags"]

    regressing = analyze_visual_evidence(
        image_paths=[str(visible), str(failed_terminal)],
        output_path=str(tmp_path / "regressing.json"),
        expect_motion=True,
    )
    assert regressing["status"] == "fail"
    assert "terminal_motion_frame_mechanically_failed" in regressing["sequence"]["flags"]


def test_panel_rows_must_evenly_divide_panel_count(tmp_path):
    image = tmp_path / "image.png"
    _write_gray_png(image, [[0, 255], [255, 0]])
    try:
        analyze_png(str(image), panel_count=4, panel_rows=3)
    except ValueError as exc:
        assert "positive divisor" in str(exc)
    else:
        raise AssertionError("expected invalid panel grid to fail")


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
