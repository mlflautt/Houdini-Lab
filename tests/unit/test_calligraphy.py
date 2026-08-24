"""Pure Sprint 12 particle-calligraphy and baked-envelope contract tests."""

from __future__ import annotations

import json

import pytest
from hermes_houdini.calligraphy import load_baked_audio_envelope, validate_calligraphy_spec
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe


def test_calligraphy_spec_is_deterministic_and_bounded():
    values = dict(
        seed=5201,
        start_frame=1,
        end_frame=48,
        candidate_index=1,
        birth_rate=8,
        particle_life=3,
        trail_frames=12,
        trail_substeps=4,
        wire_radius=0.014,
    )
    spec = validate_calligraphy_spec(**values)
    assert spec["candidate_seeds"] == {"arc": 5201, "fan": 5302, "orbit": 5412}
    assert spec["frame_count"] == 48
    assert spec["candidate_order"] == ["arc", "fan", "orbit"]
    assert spec["integer_frame_compatibility"]["expression"] == "$FF - 0.5"
    with pytest.raises(ValueError, match="limited to 48"):
        validate_calligraphy_spec(**{**values, "start_frame": 1, "end_frame": 49})
    with pytest.raises(ValueError, match="between 0 and 2"):
        validate_calligraphy_spec(**{**values, "candidate_index": 3})
    with pytest.raises(ValueError, match="max_trail_points must be between"):
        validate_calligraphy_spec(**{**values, "max_trail_points": 100_001})


def test_project_relative_baked_audio_envelope(tmp_path):
    envelope_dir = tmp_path / "audio"
    envelope_dir.mkdir()
    path = envelope_dir / "silent.json"
    path.write_text(
        json.dumps({"schema": "hermes.audio_envelope.v1", "fps": 24, "samples": [0, 0.5, 1]}),
        encoding="utf-8",
    )
    loaded = load_baked_audio_envelope(
        project_root=str(tmp_path), relative_path="audio/silent.json"
    )
    assert loaded["relative_path"] == "audio/silent.json"
    assert loaded["samples"] == [0.0, 0.5, 1.0]
    with pytest.raises(ValueError, match="without traversal"):
        load_baked_audio_envelope(project_root=str(tmp_path), relative_path="../escape.json")
    path.write_text(
        json.dumps({"schema": "hermes.audio_envelope.v1", "fps": 24, "samples": [1.2]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be <= 1.0"):
        load_baked_audio_envelope(project_root=str(tmp_path), relative_path="audio/silent.json")


def test_particle_calligraphy_recipe_has_visible_compatibility_boundaries():
    recipe = load_recipe("recipes/sop/particle_calligraphy.yaml")
    fragment = recipe.render_fragment(
        "/obj/CALLIGRAPHY",
        run_code="UNIT_CALLIGRAPHY",
        seed_arc=5201,
        seed_fan=5302,
        seed_orbit=5412,
    )
    creates = [item for item in fragment["operations"] if item["op"] == "create"]
    types = [item["operator_type"] for item in creates]
    assert types.count("particle") == 3
    assert types.count("particletrail") == 3
    assert types.count("timeblend::2.0") == 3
    assert types.count("timeshift") == 3
    assert types.count("font") == 3
    assert any(
        item["name"] == "OUT_UNIT_CALLIGRAPHY_LABELS"
        and item["role"] == "calligraphy_labels_contract"
        for item in creates
    )
    compatibility = [item for item in creates if item["operator_type"] == "timeshift"]
    assert all(item["expressions"]["frame"] == "$FF - 0.5" for item in compatibility)
    assert all(item["parameters"]["integerframe"] == 0 for item in compatibility)


def test_particle_calligraphy_skill_plans_silent_verification_lane(tmp_path):
    skill = load_skill("skills/motion.particle_calligraphy")
    calls = skill.plan(
        parent_node_id="/obj/CALLIGRAPHY",
        artifact_dir=str(tmp_path),
        run_id="unit_calligraphy",
        end_frame=12,
    )
    tools = [call["tool"] for call in calls]
    assert tools[:2] == ["recipe.instantiate", "motion.calligraphy.validate"]
    assert "motion.calligraphy.apply_audio_envelope" not in tools
    assert tools[-1] == "hip.save_snapshot"
    validation = next(call for call in calls if call["tool"] == "motion.calligraphy.validate")
    assert validation["arguments"]["audio_envelope_relative_path"] == ""
    assert validation["policy"]["max_frames"] == 48
