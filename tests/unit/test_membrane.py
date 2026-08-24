"""Pure Sprint 13 Vellum membrane specification, recipe, and skill tests."""

from __future__ import annotations

import pytest
from hermes_houdini.membrane import validate_membrane_spec
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe


def test_membrane_spec_is_deterministic_bounded_and_resource_aware():
    values = {
        "seed": 1313,
        "start_frame": 1,
        "end_frame": 24,
        "candidate_index": 0,
        "resolution": 25,
        "sheet_size": 2.4,
        "sheet_height": 2.5,
        "noise_height": 0.035,
        "mass": 0.08,
        "thickness": 0.025,
        "substeps": 2,
        "constraint_iterations": 60,
    }
    spec = validate_membrane_spec(**values)
    assert spec["candidate_seeds"] == {"silk": 1313, "rubber": 1414, "reinforced": 1515}
    assert spec["candidate_order"] == ["silk", "rubber", "reinforced"]
    assert spec["point_count_per_candidate"] == 625
    assert spec["material_profiles"]["reinforced"]["surface_struts"] is True
    with pytest.raises(ValueError, match="limited to 48"):
        validate_membrane_spec(**{**values, "end_frame": 49})
    with pytest.raises(ValueError, match="between 9 and 41"):
        validate_membrane_spec(**{**values, "resolution": 42})
    with pytest.raises(ValueError, match="combined membrane points"):
        validate_membrane_spec(**{**values, "resolution": 41, "max_points": 5_000})


def test_membrane_recipe_exposes_three_exact_material_and_cache_branches(tmp_path):
    recipe = load_recipe("recipes/sop/vellum_membrane_lab.yaml")
    fragment = recipe.render_fragment(
        "/obj/MEMBRANE",
        run_code="UNIT_MEMBRANE",
        seed_silk=1313,
        seed_rubber=1414,
        seed_reinforced=1515,
        cache_silk=str(tmp_path / "silk.$F4.bgeo.sc"),
        cache_rubber=str(tmp_path / "rubber.$F4.bgeo.sc"),
        cache_reinforced=str(tmp_path / "reinforced.$F4.bgeo.sc"),
    )
    creates = [item for item in fragment["operations"] if item["op"] == "create"]
    types = [item["operator_type"] for item in creates]
    assert len(creates) == 49
    assert types.count("vellumsolver") == 3
    assert types.count("filecache") == 3
    assert types.count("vellumconstraints") == 7
    assert types.count("font") == 3
    surface_struts = next(item for item in creates if item["ref"] == "reinforced_struts")
    assert surface_struts["parameters"]["constrainttype"] == "surfacestruts"
    pins = [item for item in creates if item["ref"].endswith("_pin")]
    assert all(item["parameters"]["group"] == "anchors" for item in pins)
    assert all(item["parameters"]["pingroup"] == "" for item in pins)
    assert "labels" in fragment["outputs"]


def test_membrane_skill_plans_exact_validation_and_nonwriting_caches(tmp_path):
    skill = load_skill("skills/simulate.vellum_membrane_lab")
    calls = skill.plan(
        parent_node_id="/obj/MEMBRANE",
        artifact_dir=str(tmp_path),
        run_id="unit_membrane",
        end_frame=12,
        sheet_size=3.0,
    )
    assert [call["tool"] for call in calls] == [
        "recipe.instantiate",
        "simulate.membrane.validate",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    recipe_inputs = calls[0]["arguments"]["inputs"]
    assert recipe_inputs["anchor_z"] == pytest.approx(1.5)
    assert recipe_inputs["seed_reinforced"] == 1515
    assert all(path.endswith(".bgeo.sc") for path in calls[1]["arguments"]["cache_paths"].values())
    metadata = calls[3]["arguments"]["metadata"]
    assert metadata["cache_contract"]["write_implicit"] is False
    assert metadata["selection"]["winner"] is None
    assert metadata["selection"]["automatic_ranking"] is False
