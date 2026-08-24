"""Pure Sprint 21 capability, recipe, and skill planning tests."""

from __future__ import annotations

from pathlib import Path

from hermes_houdini.labs_atlas import (
    LABS_ATLAS_NODE_TYPES,
    detect_labs_atlas_capability,
    validate_labs_atlas_spec,
)
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe

ROOT = Path(__file__).resolve().parents[2]


def test_labs_atlas_capability_is_exact_and_spec_never_ranks():
    absent = detect_labs_atlas_capability({LABS_ATLAS_NODE_TYPES[0]})
    assert absent["available"] is False
    assert absent["missing_node_types"] == list(LABS_ATLAS_NODE_TYPES[1:])
    present = detect_labs_atlas_capability(LABS_ATLAS_NODE_TYPES)
    assert present["available"] is True
    spec = validate_labs_atlas_spec(
        base_seed=19019, terrain_samples=96, world_size=9.0, labs_available=True
    )
    assert spec["selection"]["winner"] is None
    assert spec["selection"]["automatic_ranking"] is False
    assert [branch["id"] for branch in spec["candidates"][0]["branches"]] == [
        "native",
        "labs",
    ]
    assert all(
        branch["human_rating"]["score"] is None
        for candidate in spec["candidates"]
        for branch in candidate["branches"]
    )


def test_labs_overlay_uses_only_certified_types_and_native_default():
    recipe = load_recipe(ROOT / "recipes" / "sop" / "world_seed_labs_enhancement.yaml")
    fragment = recipe.render_fragment(
        "/obj/UNIT",
        run_code="UNIT",
        labs_translation_x=2.25,
        attribute_seed=19420,
    )
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    plugin_types = [
        operation["operator_type"]
        for operation in creates
        if operation["operator_type"].startswith("labs::")
    ]
    assert plugin_types == [
        "labs::terrain_analysis::1.0",
        "labs::instance_attributes::1.0",
        "labs::measure_curvature::3.1",
    ]
    selector = next(operation for operation in creates if operation["role"] == "labs_atlas_human_selector")
    assert selector["parameters"]["input"] == 0


def test_labs_atlas_skill_explicitly_selects_plugin_or_fallback(tmp_path):
    skill = load_skill(ROOT / "skills" / "world.world_seed_atlas_labs")
    enhanced = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="unit_labs",
        labs_available=True,
        render_preview=False,
    )
    enhanced_recipes = [
        call["arguments"]["recipe_id"]
        for call in enhanced
        if call["tool"] == "recipe.instantiate"
    ]
    assert enhanced_recipes.count("sop.world_seed_labs_enhancement") == 3
    assert enhanced_recipes[-1] == "lop.world_seed_atlas_stage"
    validation = next(call for call in enhanced if call["tool"] == "world_seed.labs.validate")
    assert validation["arguments"]["labs_available"] is True

    fallback = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="unit_native",
        labs_available=False,
        render_preview=False,
    )
    fallback_recipes = [
        call["arguments"]["recipe_id"]
        for call in fallback
        if call["tool"] == "recipe.instantiate"
    ]
    assert fallback_recipes.count("sop.world_seed_labs_unavailable") == 3
    assert "sop.world_seed_labs_enhancement" not in fallback_recipes
