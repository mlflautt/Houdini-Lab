"""Pure Sprint 14 MPM specification, recipe, and skill tests."""

from __future__ import annotations

import pytest
from hermes_houdini.mpm import MATERIAL_PROFILES, validate_mpm_spec
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe


def _values() -> dict[str, object]:
    return {
        "seed": 1414,
        "start_frame": 1,
        "end_frame": 24,
        "particle_separation": 0.12,
        "source_radius": 0.62,
        "source_height": 2.4,
        "noise_height": 0.08,
        "substep_min": 1,
        "substep_max": 32,
        "output_mode": "points",
        "max_particles": 150_000,
    }


def test_mpm_spec_is_deterministic_proxy_first_and_resource_bounded():
    values = _values()
    spec = validate_mpm_spec(**values)
    assert spec["profile_seeds"] == {"granular": 1414, "elastic": 1515, "viscous": 1616}
    assert spec["profile_order"] == ["granular", "elastic", "viscous"]
    assert 0 < spec["estimated_particles"] < 150_000
    assert spec["output_index"] == 0
    assert MATERIAL_PROFILES["granular"]["materialtype"] == "sandy"
    assert MATERIAL_PROFILES["elastic"]["eexp"] == "3"
    with pytest.raises(ValueError, match="limited to 24"):
        validate_mpm_spec(**{**values, "end_frame": 25})
    with pytest.raises(ValueError, match="estimated proxy particles"):
        validate_mpm_spec(**{**values, "max_particles": 100})
    with pytest.raises(ValueError, match="points or surface"):
        validate_mpm_spec(**{**values, "output_mode": "mesh"})


def test_mpm_recipe_exposes_exact_four_part_graph_and_nonwriting_cache(tmp_path):
    recipe = load_recipe("recipes/sop/mpm_matter_sculpture.yaml")
    fragment = recipe.render_fragment(
        "/obj/MPM",
        run_code="UNIT_MPM",
        cache_path=str(tmp_path / "matter.$F4.bgeo.sc"),
    )
    creates = [item for item in fragment["operations"] if item["op"] == "create"]
    connects = [item for item in fragment["operations"] if item["op"] == "connect"]
    types = [item["operator_type"] for item in creates]
    assert len(creates) == 20
    assert types.count("mpmsource") == 3
    assert types.count("mpmcontainer") == 1
    assert types.count("mpmcollider") == 1
    assert types.count("mpmsolver") == 1
    assert types.count("mpmsurface") == 1
    assert types.count("filecache") == 1
    cache = next(item for item in creates if item["ref"] == "cache")
    assert cache["parameters"]["filemode"] == "none"
    assert cache["parameters"]["loadfromdisk"] == 0
    solver_inputs = [item for item in connects if item["to"] == "solver"]
    assert [(item["from"], item["input_index"]) for item in solver_inputs] == [
        ("source_merge", 0),
        ("collider", 1),
        ("container", 2),
    ]
    source_inputs = [item for item in connects if item["to"] == "granular_source"]
    assert [(item["from"], item["input_index"]) for item in source_inputs] == [
        ("granular_mountain", 0),
        ("container", 1),
    ]


def test_mpm_skill_plans_durable_progress_and_no_implicit_cache(tmp_path):
    skill = load_skill("skills/simulate.mpm_matter_sculpture")
    calls = skill.plan(
        parent_node_id="/obj/MPM",
        artifact_dir=str(tmp_path),
        run_id="unit_mpm",
        end_frame=8,
        output_mode="surface",
    )
    assert [call["tool"] for call in calls] == [
        "recipe.instantiate",
        "simulate.mpm.validate",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    recipe_inputs = calls[0]["arguments"]["inputs"]
    assert recipe_inputs["seed_viscous"] == 1616
    assert recipe_inputs["output_index"] == 1
    assert recipe_inputs["cache_path"].endswith("unit_mpm.$F4.bgeo.sc")
    validation = calls[1]["arguments"]
    assert validation["progress_path"].endswith("unit_mpm_cache_progress.json")
    assert validation["max_particles"] == 150_000
    metadata = calls[3]["arguments"]["metadata"]
    assert metadata["cache_contract"]["file_mode"] == "none"
    assert metadata["cache_contract"]["write_implicit"] is False
    assert metadata["selection"]["winner"] is None
    assert metadata["selection"]["automatic_ranking"] is False
    assert metadata["resource_contract"]["roadmap_ceiling_requires_separate_approval"] == 1_000_000
