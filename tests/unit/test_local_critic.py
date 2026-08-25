"""Loopback transport, advisory policy, and calibration tests for the local critic."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import hermes_houdini.local_critic as local_critic
import pytest
from hermes_houdini.local_critic import (
    materialize_calibration_corpus,
    probe_ollama,
    run_local_critique,
    score_calibration,
)
from hermes_houdini.visual_verification import build_critique_packet


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def _write_gray_png(path: Path) -> None:
    rows = [[240] * 8 for _ in range(8)]
    for y in range(2, 6):
        for x in range(2, 6):
            rows[y][x] = 30
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack(">IIBBBBB", 8, 8, 8, 0, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def _packet(tmp_path: Path) -> Path:
    image = tmp_path / "image.png"
    graph = tmp_path / "graph.svg"
    validation = tmp_path / "validation.json"
    source = tmp_path / "skill.py"
    packet = tmp_path / "packet.json"
    _write_gray_png(image)
    graph.write_text("<svg/>", encoding="utf-8")
    validation.write_text('{"status": "pass"}', encoding="utf-8")
    source.write_text("VALUE = 1\n", encoding="utf-8")
    build_critique_packet(
        image_paths=[str(image)],
        graph_path=str(graph),
        validation_paths=[str(validation)],
        code_paths=[str(source)],
        output_path=str(packet),
    )
    return packet


def test_probe_rejects_non_loopback_endpoint():
    with pytest.raises(ValueError, match="127.0.0.1"):
        probe_ollama(endpoint="http://example.com:11434")
    with pytest.raises(ValueError, match="no path"):
        probe_ollama(endpoint="http://127.0.0.1:11434/api")


def test_probe_reports_unavailable_without_mutating(monkeypatch, tmp_path):
    def unavailable(**_kwargs):
        raise OSError("service is down")

    monkeypatch.setattr(local_critic, "_request_json", unavailable)
    output = tmp_path / "probe.json"
    result = probe_ollama(output_path=str(output))
    assert result["status"] == "unavailable"
    assert result["mutations_performed"] is False
    assert result["model_downloaded"] is False
    assert result["service_started"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "unavailable"


def test_local_critique_is_off_by_default_and_rejects_unlisted_model(tmp_path):
    packet = _packet(tmp_path)
    with pytest.raises(PermissionError, match="disabled"):
        run_local_critique(packet_path=str(packet), output_path=str(tmp_path / "off.json"))
    with pytest.raises(ValueError, match="model must be"):
        run_local_critique(
            packet_path=str(packet),
            output_path=str(tmp_path / "bad-model.json"),
            enabled=True,
            model="untrusted:latest",
        )


def test_local_critique_writes_advisory_provenance(monkeypatch, tmp_path):
    packet = _packet(tmp_path)
    monkeypatch.setattr(
        local_critic,
        "probe_ollama",
        lambda **_kwargs: {
            "status": "available",
            "installed_allowlisted_models": ["qwen3-vl:8b"],
            "allowlisted_model_records": [
                {"name": "qwen3-vl:8b", "digest": "a" * 64, "size": 1}
            ],
        },
    )

    def fake_request(**kwargs):
        assert kwargs["url"] == "http://127.0.0.1:11434/api/chat"
        assert kwargs["payload"]["stream"] is False
        assert kwargs["payload"]["format"] == local_critic.CRITIQUE_SCHEMA
        return {
            "model": "qwen3-vl:8b",
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "mechanical_status": "warn",
                        "mechanical_labels": ["low_contrast"],
                        "observations": ["The subject and background have limited separation."],
                        "suggested_edits": ["Increase key-to-fill ratio, then rerender one frame."],
                        "uncertainties": ["Only one frame was supplied."],
                        "aesthetic_scores": None,
                        "winner": None,
                    }
                ),
            },
        }

    monkeypatch.setattr(local_critic, "_request_json", fake_request)
    result = run_local_critique(
        packet_path=str(packet),
        output_path=str(tmp_path / "critique.json"),
        enabled=True,
    )
    assert result["status"] == "available_unverified"
    assert result["execution"]["network_transfer"] == "ipv4_loopback_only"
    assert result["winner"] is None
    assert result["human_rating"] is None
    assert result["automatic_ranking"] is False
    assert len(result["artifact_hashes"]) == 4


def test_local_critique_rejects_changed_packet_artifact(monkeypatch, tmp_path):
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    Path(payload["artifacts"]["images"][0]["path"]).write_bytes(b"changed")
    monkeypatch.setattr(
        local_critic,
        "probe_ollama",
        lambda **_kwargs: {
            "status": "available",
            "installed_allowlisted_models": ["qwen3-vl:8b"],
            "allowlisted_model_records": [{"name": "qwen3-vl:8b"}],
        },
    )
    with pytest.raises(ValueError, match="changed after packet creation"):
        run_local_critique(
            packet_path=str(packet),
            output_path=str(tmp_path / "changed.json"),
            enabled=True,
        )


def test_calibration_requires_every_known_mechanical_case(tmp_path):
    source = Path(__file__).parents[1] / "fixtures" / "local_critic_calibration.json"
    corpus = tmp_path / "corpus.json"
    corpus.write_bytes(source.read_bytes())
    cases = json.loads(corpus.read_text(encoding="utf-8"))["cases"]
    responses = []
    for case in cases:
        response = tmp_path / f"{case['id']}.json"
        response.write_text(
            json.dumps(
                {
                    "schema": "hermes.local_visual_critique",
                    "calibration_case_id": case["id"],
                    "model": {"name": "qwen3-vl:8b", "digest": "a" * 64},
                    "critique": {"mechanical_labels": case["expected_labels"]},
                    "decision_authority": "advisory_only",
                    "winner": None,
                }
            ),
            encoding="utf-8",
        )
        responses.append(str(response))
    result = score_calibration(
        corpus_path=str(corpus),
        response_paths=responses,
        output_path=str(tmp_path / "calibration.json"),
    )
    assert result["status"] == "pass"
    assert result["model_reliability"] == "calibrated"
    assert result["metrics"]["recall"] == 1.0
    assert result["winner"] is None

    failed = score_calibration(
        corpus_path=str(corpus),
        response_paths=responses[:-1],
        output_path=str(tmp_path / "failed-calibration.json"),
    )
    assert failed["status"] == "fail"
    assert failed["model_reliability"] == "available_unverified"
    assert failed["missing_cases"] == [cases[-1]["id"]]


def test_materialized_calibration_corpus_has_real_bad_images_and_packets(tmp_path):
    source = Path(__file__).parents[1] / "fixtures" / "local_critic_calibration.json"
    corpus = tmp_path / "corpus.json"
    corpus.write_bytes(source.read_bytes())
    result = materialize_calibration_corpus(
        corpus_path=str(corpus), output_directory=str(tmp_path / "materialized")
    )
    assert [case["id"] for case in result["cases"]] == [
        "crushed_black",
        "blown_white",
        "missing_panel",
        "duplicate_motion",
    ]
    by_id = {case["id"]: case for case in result["cases"]}
    assert "crushed_black" in by_id["crushed_black"]["visual_flags"]
    assert "blown_white" in by_id["blown_white"]["visual_flags"]
    assert "missing_comparison_panel" in by_id["missing_panel"]["visual_flags"]
    assert "duplicate_motion_frame" in by_id["duplicate_motion"]["visual_flags"]
    assert all(Path(case["packet_path"]).is_file() for case in result["cases"])
    with pytest.raises(FileExistsError, match="refusing to reuse"):
        materialize_calibration_corpus(
            corpus_path=str(corpus), output_directory=str(tmp_path / "materialized")
        )
