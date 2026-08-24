"""Pure material-foundry specification and plan tests."""

from __future__ import annotations

import os

import pytest
from hermes_houdini.material_foundry import (
    COLOR_SPACE_INTENT,
    FOUNDRY_CANDIDATES,
    PBR_CHANNELS,
    validate_foundry_spec,
)
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_foundry_spec_preserves_candidates_channels_and_color_space_intent():
    spec = validate_foundry_spec(resolution=512, candidate_index=1)
    assert spec["candidate_ids"] == list(FOUNDRY_CANDIDATES)
    assert spec["channels"] == list(PBR_CHANNELS)
    assert spec["color_space_intent"] == COLOR_SPACE_INTENT
    assert spec["automatic_ranking"] is False
    with pytest.raises(ValueError, match="resolution"):
        validate_foundry_spec(resolution=2048, candidate_index=1)
    with pytest.raises(ValueError, match="exact order"):
        validate_foundry_spec(
            resolution=512,
            candidate_index=1,
            candidate_ids=["emberglaze", "verdigris", "moonlichen"],
        )


def test_foundry_cop_recipe_has_four_named_channels_and_native_material_per_candidate():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "cop", "procedural_material_foundry.yaml"))
    fragment = recipe.render_fragment(
        "/img/UNIT_FOUNDRY",
        run_code="UNIT_FOUNDRY",
        verdigris_pattern_path="/img/UNIT_FOUNDRY/PATTERN_A",
        emberglaze_pattern_path="/img/UNIT_FOUNDRY/PATTERN_B",
        moonlichen_pattern_path="/img/UNIT_FOUNDRY/PATTERN_C",
    )
    creates = [item for item in fragment["operations"] if item["op"] == "create"]
    connects = [item for item in fragment["operations"] if item["op"] == "connect"]
    assert len([item for item in creates if item["operator_type"] == "usdmaterial"]) == 3
    assert len([item for item in creates if item["operator_type"] == "heighttonormal"]) == 3
    assert len([item for item in creates if item["operator_type"] == "null"]) == 12
    assert all(item["category"] == "Cop" for item in creates)
    for candidate in FOUNDRY_CANDIDATES:
        material_ref = f"{candidate}_material"
        material_inputs = {item["input_index"] for item in connects if item["to"] == material_ref}
        assert material_inputs == {0, 3, 12, 13}


def test_foundry_stage_is_simultaneous_and_skill_plan_has_separate_render_boundary(tmp_path):
    stage = load_recipe(
        os.path.join(ROOT, "recipes", "lop", "procedural_material_foundry_stage.yaml")
    ).render_fragment(
        "/stage",
        run_code="UNIT_FOUNDRY",
        verdigris_sop_path="/obj/SWATCHES/OUT_A",
        emberglaze_sop_path="/obj/SWATCHES/OUT_B",
        moonlichen_sop_path="/obj/SWATCHES/OUT_C",
        verdigris_material_cop="/img/FOUNDRY/MAT_A",
        emberglaze_material_cop="/img/FOUNDRY/MAT_B",
        moonlichen_material_cop="/img/FOUNDRY/MAT_C",
        render_picture="/project/render/foundry.png",
    )
    creates = [item for item in stage["operations"] if item["op"] == "create"]
    library = next(item for item in creates if item["operator_type"] == "texturemateriallibrary")
    assignment = next(item for item in creates if item["operator_type"] == "assignmaterial")
    assert library["parameters"]["materials"] == 3
    assert assignment["parameters"]["nummaterials"] == 3
    assert not any(item["operator_type"] == "switch" for item in creates)

    skill = load_skill(os.path.join(ROOT, "skills", "lookdev.procedural_material_foundry"))
    calls = skill.plan(artifact_dir=str(tmp_path), run_id="unit_foundry", render_preview=True)
    tools = [call["tool"] for call in calls]
    assert tools[:7] == [
        "graph.apply_batch",
        "recipe.instantiate",
        "recipe.instantiate",
        "cop.material_foundry.validate",
        "recipe.instantiate",
        "recipe.instantiate",
        "solaris.material_foundry.validate",
    ]
    assert tools[7:9] == ["solaris.karma_rop.build", "render.karma.preview"]
    manifest = next(call for call in calls if call["tool"] == "graph.capture_manifest")
    candidates = manifest["arguments"]["metadata"]["candidates"]
    assert [item["id"] for item in candidates] == list(FOUNDRY_CANDIDATES)
    assert all(item["automatic_rank"] is None for item in candidates)
    assert manifest["arguments"]["metadata"]["selection"]["winner"] is None
