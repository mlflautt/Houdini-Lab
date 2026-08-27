from __future__ import annotations

from pathlib import Path

import pytest
from hermes_houdini.g003_visual_audition import (
    PRESENTATION_ORDER,
    SAMPLE_FRAMES,
    build_visual_audition_manifest,
    visual_audition_manifest_sha256,
)

ACCEPTED = "df476c1af5db0cda4b80d8cc7ff5bd384cb51389"


def _manifest(tmp_path: Path) -> dict[str, object]:
    return build_visual_audition_manifest(
        project_root=tmp_path,
        artifact_root=tmp_path / ".hermes" / "g003" / "gate-v" / "test-run",
        source_identity={"commit": ACCEPTED, "branch": "test", "dirty": False},
        runtime_observation={
            "status": "blocked",
            "detail": "not logged into SideFX license server",
            "mutation_performed": False,
        },
    )


def test_manifest_is_stable_nonexecuting_and_does_not_create_artifact_root(tmp_path: Path) -> None:
    first = _manifest(tmp_path)
    second = _manifest(tmp_path)
    assert first == second
    assert visual_audition_manifest_sha256(first) == visual_audition_manifest_sha256(second)
    assert first["automatic_execution"] is False
    assert first["approval"]["karma_external_process"] is False
    assert first["review"]["winner"] is None
    assert first["review"]["human_rating"] is None
    assert not (tmp_path / ".hermes").exists()
    digest = visual_audition_manifest_sha256(first)
    first["approval"]["manifest_sha256_subject"] = digest
    assert visual_audition_manifest_sha256(first) == digest


def test_manifest_preserves_three_methods_and_exact_temporal_render_contract(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    assert manifest["presentation_order"] == list(PRESENTATION_ORDER)
    assert manifest["timeline"]["sample_frames"] == list(SAMPLE_FRAMES)
    assert manifest["render"]["total_frames"] == 36
    methods = manifest["methods"]
    assert [method["capability"] for method in methods] == list(PRESENTATION_ORDER)
    assert [method["presentation_index"] for method in methods] == [0, 1, 2]
    for method in methods:
        render_calls = [call for call in method["calls"] if call["tool"] == "render.karma.preview"]
        assert len(render_calls) == 12
        assert [int(call["arguments"]["frame"]) for call in render_calls] == list(SAMPLE_FRAMES)
        assert all(call["arguments"]["source_sop_path"] == method["source_sop_path"] for call in render_calls)
        assert all(call["arguments"]["source_start_frame"] == 1.0 for call in render_calls)
        assert [call["policy"]["max_frames"] for call in render_calls] == list(SAMPLE_FRAMES)
        assert all(call["policy"]["allow_external_process"] for call in render_calls)
        assert len(method["render_paths"]) == 12
    calligraphy_stage = next(
        call for call in methods[0]["calls"] if call["tool"] == "solaris.stage.validate"
    )
    differential_stage = next(
        call for call in methods[1]["calls"] if call["tool"] == "solaris.stage.validate"
    )
    assert calligraphy_stage["arguments"]["frame"] == 24
    assert differential_stage["arguments"]["frame"] == 24
    calligraphy_recipe = next(
        call for call in methods[0]["calls"] if call["tool"] == "recipe.instantiate"
        and call["arguments"]["recipe_id"] == "lop.relic_lookdev_stage"
    )
    differential_recipe = next(
        call for call in methods[1]["calls"] if call["tool"] == "recipe.instantiate"
        and call["arguments"]["recipe_id"] == "lop.relic_lookdev_stage"
    )
    assert calligraphy_recipe["arguments"]["inputs"]["camera_tz"] == 6.4
    assert differential_recipe["arguments"]["inputs"]["camera_tx"] == -2.0
    assert differential_recipe["arguments"]["inputs"]["camera_tz"] == 20.0
    assert calligraphy_recipe["arguments"]["inputs"]["dome_exposure"] == 1.0
    assert methods[2]["mode"] == "native_only_mops_false"
    assert manifest["postprocess"][0]["kind"] == "stable_order_contact_sheet"
    assert manifest["postprocess"][0]["labels"] == [
        "Particle Calligraphy",
        "Differential Growth",
        "Kinetic Instances",
    ]
    assert manifest["postprocess"][1]["kind"] == "write_static_review_index"


def test_manifest_refuses_drift_dirty_source_existing_or_outside_root(tmp_path: Path) -> None:
    kwargs = {
        "project_root": tmp_path,
        "artifact_root": tmp_path / "artifacts",
        "runtime_observation": {"status": "pending"},
    }
    with pytest.raises(ValueError, match="dirty=false"):
        build_visual_audition_manifest(
            **kwargs,
            source_identity={"commit": ACCEPTED, "branch": "test", "dirty": True},
        )
    with pytest.raises(ValueError, match="accepted G003"):
        build_visual_audition_manifest(
            **kwargs,
            source_identity={"commit": "0" * 40, "branch": "test", "dirty": False},
        )
    (tmp_path / "artifacts").mkdir()
    with pytest.raises(FileExistsError, match="existing Gate V"):
        build_visual_audition_manifest(
            **kwargs,
            source_identity={"commit": ACCEPTED, "branch": "test", "dirty": False},
        )
    with pytest.raises(ValueError, match="inside project_root"):
        build_visual_audition_manifest(
            project_root=tmp_path,
            artifact_root=tmp_path.parent / "outside",
            source_identity={"commit": ACCEPTED, "branch": "test", "dirty": False},
            runtime_observation={"status": "pending"},
        )
