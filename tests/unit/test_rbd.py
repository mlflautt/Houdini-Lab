"""Pure Sprint 17 RBD recipe, specification, and skill tests."""

from __future__ import annotations

import os

import pytest
from hermes_houdini.rbd import PROFILE_ORDER, validate_rbd_spec
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_rbd_spec_is_deterministic_and_bounded():
    spec = validate_rbd_spec(
        seed=1717,
        start_frame=1,
        end_frame=48,
        profile_index=2,
        bullet_substeps=5,
        constraint_iterations=10,
        primary_strength=40.0,
        chipping_strength=20.0,
    )
    assert spec["profile_order"] == list(PROFILE_ORDER)
    assert spec["profile"] == "layered"
    assert spec["profile_seeds"] == {"radial": 1717, "offset": 1818, "layered": 1919}
    assert spec["profile_point_counts"] == {"radial": 8, "offset": 12, "layered": 12}
    assert spec["frame_count"] == 48
    assert spec["max_pieces"] == 5_000
    with pytest.raises(ValueError, match="48 inclusive frames"):
        validate_rbd_spec(
            seed=1,
            start_frame=1,
            end_frame=49,
            profile_index=0,
            bullet_substeps=5,
            constraint_iterations=10,
            primary_strength=40.0,
            chipping_strength=20.0,
        )
    with pytest.raises(ValueError, match="between 1 and 5000"):
        validate_rbd_spec(
            seed=1,
            start_frame=1,
            end_frame=48,
            profile_index=0,
            bullet_substeps=5,
            constraint_iterations=10,
            primary_strength=40.0,
            chipping_strength=20.0,
            max_pieces=5_001,
        )


def test_rbd_recipe_preserves_pinned_native_outputs_and_transform_reconstruction():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "sop", "rbd_art_directed_fracture.yaml"))
    fragment = recipe.render_fragment(
        "/obj/RBD",
        run_code="UNIT_RBD",
        profile_index=1,
        start_frame=3,
        end_frame=24,
        transform_cache="/project/cache/rbd/transforms.$F4.bgeo.sc",
    )
    creates = [item for item in fragment["operations"] if item["op"] == "create"]
    connects = [item for item in fragment["operations"] if item["op"] == "connect"]
    by_ref = {item["ref"]: item for item in creates}
    assert fragment["recipe"] == {
        "id": "sop.rbd_art_directed_fracture",
        "version": "1.0.0",
    }
    assert by_ref["fracture"]["operator_type"] == "rbdmaterialfracture::4.0"
    assert by_ref["fracture"]["parameters"]["materialtype"] == "concrete"
    assert by_ref["solver"]["operator_type"] == "rbdbulletsolver"
    assert by_ref["solver"]["parameters"]["cachemaxsize"] == 512
    assert by_ref["transform_cache"]["parameters"]["loadfromdisk"] == 0
    assert by_ref["transform_cache"]["parameters"]["initsim"] == 0
    assert by_ref["transform_cache"]["expressions"] == {"f1": "3 + 0", "f2": "24 + 0"}
    assert by_ref["rest_transforms"]["expressions"] == {"frame": "3 + 0"}
    assert by_ref["reconstruct"]["operator_type"] == "xformpieces"
    switch_inputs = [item for item in connects if item["to"] == "profile_switch"]
    assert [(item["from"], item["input_index"]) for item in switch_inputs] == [
        ("radial", 0),
        ("offset", 1),
        ("layered", 2),
    ]
    reconstruct_inputs = [item for item in connects if item["to"] == "reconstruct"]
    assert [
        (item["from"], item["output_index"], item["input_index"]) for item in reconstruct_inputs
    ] == [
        ("rest", 0, 0),
        ("transforms", 0, 1),
        ("rest_transforms", 0, 2),
    ]
    assert set(fragment["outputs"]) >= {
        "source",
        "rest",
        "constraints",
        "proxy",
        "transforms",
        "after",
        "compare",
    }


def test_rbd_skill_plans_checkpointed_validation_and_no_implicit_cache_write(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "simulate.rbd_art_directed_fracture"))
    calls = skill.plan(
        parent_node_id="/obj/RBD",
        artifact_dir=str(tmp_path),
        run_id="unit_rbd",
        seed=200,
        start_frame=1,
        end_frame=48,
        profile_index=1,
    )
    assert [call["tool"] for call in calls] == [
        "recipe.instantiate",
        "simulate.rbd.validate",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    assert calls[0]["arguments"]["recipe_id"] == "sop.rbd_art_directed_fracture"
    assert calls[1]["arguments"]["max_pieces"] == 5_000
    assert calls[1]["policy"]["max_frames"] == 48
    assert calls[1]["arguments"]["transform_cache_path"].endswith(
        "/cache/unit_rbd/v001/transforms.$F4.bgeo.sc"
    )
    metadata = calls[3]["arguments"]["metadata"]
    assert [profile["seed"] for profile in metadata["profiles"]] == [200, 301, 402]
    assert all(profile["automatic_rank"] is None for profile in metadata["profiles"])
    assert metadata["transform_cache"]["write_implicit"] is False
    assert metadata["selection"] == {
        "method": "human",
        "preview_input": 1,
        "winner": None,
        "automatic_ranking": False,
    }
    with pytest.raises(ValueError, match="48 inclusive frames"):
        skill.plan(
            parent_node_id="/obj/RBD",
            artifact_dir=str(tmp_path),
            start_frame=1,
            end_frame=49,
        )
    with pytest.raises(ValueError, match="provided together"):
        skill.plan(
            parent_node_id="/obj/RBD",
            artifact_dir=str(tmp_path),
            viewer_name="sceneviewer1",
        )
