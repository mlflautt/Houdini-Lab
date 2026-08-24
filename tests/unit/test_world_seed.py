"""Pure World Seed Atlas specification, recipe, and skill-plan tests."""

from __future__ import annotations

import os

import pytest
from hermes_houdini.skill_loader import load_skill
from hermes_houdini.world_seed import WORLD_SEED_IDS, validate_world_seed_spec
from recipes.parser import load_recipe

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_world_seed_spec_is_bounded_reproducible_and_never_ranks():
    first = validate_world_seed_spec(base_seed=19019, terrain_samples=128, world_size=9.0)
    assert first == validate_world_seed_spec(base_seed=19019, terrain_samples=128, world_size=9.0)
    assert first["candidate_order"] == list(WORLD_SEED_IDS)
    assert [item["seed"] for item in first["candidates"]] == [19019, 19156, 19290]
    assert [item["translation_x"] for item in first["candidates"]] == [-9.5, 0.0, 9.5]
    assert first["estimated_terrain_points"] == 49_152
    assert first["selection"] == {
        "method": "human",
        "winner": None,
        "automatic_ranking": False,
    }
    assert all(item["human_rating"]["score"] is None for item in first["candidates"])
    assert all(item["automatic_rank"] is None for item in first["candidates"])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"base_seed": -1}, "base_seed"),
        ({"base_seed": 2_147_483_377}, "base_seed"),
        ({"terrain_samples": 512}, "terrain_samples"),
        ({"terrain_samples": 100}, "terrain_samples"),
        ({"world_size": 7.9}, "world_size"),
        ({"world_size": 10.1}, "world_size"),
    ],
)
def test_world_seed_spec_rejects_invalid_or_unbounded_controls(overrides, message):
    arguments = {"base_seed": 19019, "terrain_samples": 128, "world_size": 9.0}
    arguments.update(overrides)
    with pytest.raises(ValueError, match=message):
        validate_world_seed_spec(**arguments)


def test_world_seed_recipe_is_native_readable_and_preserves_named_contracts():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "sop", "world_seed_biome.yaml"))
    fragment = recipe.render_fragment(
        "/obj/UNIT_WORLD",
        run_code="UNIT_WORLD",
        seed=19019,
        offset_x=1.0,
        offset_y=2.0,
        noise_amplitude=2.4,
        noise_element_size=2.6,
        terrace_step_size=0.55,
        scatter_count=54,
        scatter_radius=0.14,
        hero_radius=1.05,
        platonic_type=3,
        translation_x=-11.0,
        terrain_r=0.33,
        terrain_g=0.075,
        terrain_b=0.025,
        accent_r=1.0,
        accent_g=0.31,
        accent_b=0.025,
    )
    creates = [item for item in fragment["operations"] if item["op"] == "create"]
    types = [item["operator_type"] for item in creates]
    assert "heightfield" in types
    assert "heightfield_noise" in types
    assert "heightfield_terrace::2.0" in types
    assert "convertheightfield" in types
    assert "scatter" in types
    assert "copytopoints::2.0" in types
    assert "python" not in " ".join(types).lower()
    output_roles = {item["role"] for item in creates if item["role"].endswith("_contract")}
    assert output_roles == {
        "world_seed_terrain_contract",
        "world_seed_biome_points_contract",
        "world_seed_biome_forms_contract",
        "world_seed_hero_contract",
        "world_seed_world_contract",
    }


def test_world_seed_skill_has_three_recipes_separate_render_and_no_winner(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "world.world_seed_atlas"))
    calls = skill.plan(artifact_dir=str(tmp_path), run_id="unit_world_seed", render_preview=True)
    tools = [call["tool"] for call in calls]
    assert tools[:7] == [
        "graph.apply_batch",
        "recipe.instantiate",
        "recipe.instantiate",
        "recipe.instantiate",
        "world_seed.validate",
        "recipe.instantiate",
        "solaris.world_seed.validate",
    ]
    assert tools[7:9] == ["solaris.karma_rop.build", "render.karma.preview"]
    recipes = [
        call["arguments"]["recipe_id"] for call in calls if call["tool"] == "recipe.instantiate"
    ]
    assert recipes == [
        "sop.world_seed_biome",
        "sop.world_seed_biome",
        "sop.world_seed_biome",
        "lop.world_seed_atlas_stage",
    ]
    manifest = next(call for call in calls if call["tool"] == "graph.capture_manifest")
    metadata = manifest["arguments"]["metadata"]
    assert [item["id"] for item in metadata["candidates"]] == list(WORLD_SEED_IDS)
    assert metadata["selection"]["winner"] is None
    assert metadata["selection"]["automatic_ranking"] is False
