"""Manifest and path-based skill loading tests (no Houdini)."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from hermes_houdini.skill_loader import SkillError, discover_skills, load_skill  # noqa: E402


def test_all_bundled_skills_load_and_plan(tmp_path):
    definitions = discover_skills(os.path.join(ROOT, "skills"))
    assert {skill.id for skill in definitions} == {
        "generate.differential_growth",
        "generate.fractal_relic_variations",
        "generate.reaction_diffusion_pattern",
        "grow.botanical_grammar",
        "lookdev.relic_stage",
        "lookdev.procedural_material_foundry",
        "model.fractal_relic",
        "motion.particle_calligraphy",
        "motion.kinetic_reliquary",
        "simulate.vellum_relic_drop",
        "simulate.vellum_membrane_lab",
        "simulate.mpm_matter_sculpture",
        "simulate.rbd_art_directed_fracture",
        "world.biobloom_cluster",
        "world.procedural_district",
        "world.world_seed_atlas",
        "world.world_seed_atlas_labs",
    }
    for skill in definitions:
        if skill.id == "world.procedural_district":
            arguments = {"artifact_dir": str(tmp_path)}
        elif skill.id in {
            "world.world_seed_atlas",
            "world.world_seed_atlas_labs",
            "motion.kinetic_reliquary",
        }:
            arguments = {"artifact_dir": str(tmp_path), "render_preview": False}
        elif skill.id == "generate.fractal_relic_variations":
            arguments = {
                "source_node_path": "/obj/HERMES_ASSET_TEST/RELIC",
                "artifact_dir": str(tmp_path),
            }
        elif skill.id == "lookdev.relic_stage":
            arguments = {
                "source_sop_path": "/obj/HERMES_ASSET_TEST/OUT_GEO",
                "artifact_dir": str(tmp_path),
            }
        elif skill.id == "lookdev.procedural_material_foundry":
            arguments = {"artifact_dir": str(tmp_path), "render_preview": False}
        elif skill.id == "generate.reaction_diffusion_pattern":
            arguments = {"artifact_dir": str(tmp_path)}
        else:
            arguments = {"parent_node_id": "/obj/HERMES_ASSET_TEST"}
        if skill.id in {
            "generate.differential_growth",
            "grow.botanical_grammar",
            "model.fractal_relic",
            "motion.particle_calligraphy",
            "simulate.vellum_relic_drop",
            "simulate.vellum_membrane_lab",
            "simulate.mpm_matter_sculpture",
            "simulate.rbd_art_directed_fracture",
        }:
            arguments["artifact_dir"] = str(tmp_path)
        calls = skill.plan(**arguments)
        assert calls
        assert all("tool" in call and "arguments" in call for call in calls)


def test_skill_inputs_are_validated(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "model.fractal_relic"))
    try:
        skill.plan(parent_node_id="/obj/TEST", artifact_dir=str(tmp_path), iterations=99)
    except SkillError as exc:
        assert "<= 8" in str(exc)
    else:
        raise AssertionError("expected SkillError")


def test_fractal_relic_plan_is_connected_bounded_and_human_rated(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "model.fractal_relic"))
    calls = skill.plan(
        parent_node_id="/obj/HERMES_RELIC",
        artifact_dir=str(tmp_path),
        run_id="unit_relic",
        seed=100,
    )
    assert [call["tool"] for call in calls] == [
        "graph.apply_batch",
        "cook.node",
        "geometry.validate",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    graph_call = calls[0]
    operations = graph_call["arguments"]["operations"]
    creates = [operation for operation in operations if operation["op"] == "create"]
    assert len(creates) == 28
    assert all(operation["exact_name"] for operation in creates)
    assert all(len(operation["position"]) == 2 for operation in creates)
    names = {operation["name"] for operation in creates}
    assert {"OUT_CAND_A", "OUT_CAND_B", "OUT_CAND_C", "OUT_COMPARISON", "OUT_GEO"} <= names
    assert graph_call["policy"]["max_points"] == 3_000_000

    manifest = calls[4]["arguments"]["metadata"]
    candidates = manifest["candidates"]
    assert [candidate["seed"] for candidate in candidates] == [100, 8019, 15938]
    assert all(
        candidate["human_rating"] == {"score": None, "notes": "", "selected": False}
        for candidate in candidates
    )
    assert all(candidate["automatic_rank"] is None for candidate in candidates)
    assert all(
        candidate["recipe"] == {"id": "sop.fractal_relic_candidate", "version": "2.0.0"}
        for candidate in candidates
    )
    assert manifest["selection"] == {
        "method": "human",
        "preview_input": 0,
        "winner": None,
        "automatic_ranking": False,
    }


def test_fractal_relic_plan_requires_safe_artifact_and_viewport_identity(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "model.fractal_relic"))
    with pytest.raises(ValueError, match="artifact_dir must be absolute"):
        skill.plan(parent_node_id="/obj/TEST", artifact_dir="relative")
    with pytest.raises(ValueError, match="must be provided together"):
        skill.plan(
            parent_node_id="/obj/TEST",
            artifact_dir=str(tmp_path),
            viewer_name="sceneviewer1",
        )


def test_pdg_variation_skill_is_bounded_local_and_preserves_human_selection(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "generate.fractal_relic_variations"))
    calls = skill.plan(
        source_node_path="/obj/RELIC/ASSET",
        artifact_dir=str(tmp_path),
        run_id="unit_variations",
        base_seed=400,
        count=4,
        seed_step=17,
    )
    assert [call["tool"] for call in calls] == [
        "pdg.variation.build",
        "pdg.variation.generate",
        "pdg.variation.cook",
        "pdg.variation.build_gallery",
        "cook.node",
        "geometry.validate",
        "graph.capture_svg",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    build = calls[0]
    assert build["arguments"]["count"] == 4
    assert build["arguments"]["scheduler_memory_mb"] == 2048
    cook = calls[2]
    assert cook["policy"]["allow_external_process"] is True
    assert cook["policy"]["max_work_items"] == 4
    assert cook["arguments"]["estimate"]["work_items"] == 4
    manifest = calls[8]["arguments"]["metadata"]
    assert manifest["selection"] == {
        "method": "human",
        "winner": None,
        "automatic_ranking": False,
    }

    with pytest.raises(SkillError, match="<= 16"):
        skill.plan(
            source_node_path="/obj/RELIC/ASSET",
            artifact_dir=str(tmp_path),
            count=17,
        )


def test_procedural_district_skill_is_bounded_manifested_and_human_selected(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "world.procedural_district"))
    calls = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="unit_district",
        base_seed=700,
        lot_count=12,
        seed_step=17,
    )
    assert [call["tool"] for call in calls] == [
        "district.build",
        "district.generate",
        "district.cook",
        "district.assemble",
        "district.validate",
        "graph.capture_svg",
        "graph.capture_svg",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    build = calls[0]
    assert build["arguments"]["count"] == 12
    assert build["arguments"]["scheduler_memory_mb"] == 1024
    cook = calls[2]
    assert cook["policy"]["allow_external_process"] is True
    assert cook["policy"]["max_work_items"] == 12
    assert cook["arguments"]["estimate"]["work_items"] == 12
    assert calls[4]["policy"]["max_points"] == 150_000
    assert calls[4]["policy"]["max_primitives"] == 100_000
    metadata = calls[8]["arguments"]["metadata"]
    assert metadata["selection"] == {
        "method": "human",
        "winner": None,
        "automatic_ranking": False,
    }
    assert metadata["scheduler"] == {"slots": 1, "background": False}

    with pytest.raises(ValueError, match="<= 16"):
        skill.plan(artifact_dir=str(tmp_path), lot_count=17)
    with pytest.raises(ValueError, match="supplied together"):
        skill.plan(artifact_dir=str(tmp_path), viewer_name="sceneviewer1")


def test_vellum_simulation_skill_has_bounded_temporal_and_nonwriting_cache_contract(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "simulate.vellum_relic_drop"))
    calls = skill.plan(
        parent_node_id="/obj/HERMES_SIM",
        artifact_dir=str(tmp_path),
        run_id="unit_drop",
        start_frame=1,
        end_frame=12,
    )
    assert [call["tool"] for call in calls] == [
        "recipe.instantiate",
        "cook.node",
        "geometry.validate",
        "geometry.validate",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    recipe = calls[0]
    assert recipe["arguments"]["recipe_id"] == "sop.vellum_relic_drop"
    assert recipe["arguments"]["version"] == "1.0.0"
    assert recipe["arguments"]["inputs"]["cache_path"].endswith(
        "/cache/unit_drop/v001/unit_drop.$F4.bgeo.sc"
    )
    cook = calls[1]
    assert cook["arguments"]["scope"] == "frame_range"
    assert cook["arguments"]["frame_range"] == [1, 12, 1.0]
    assert cook["policy"]["max_frames"] == 12
    manifest = calls[5]["arguments"]["metadata"]
    assert manifest["cache_contract"]["write_implicit"] is False
    assert manifest["cache_contract"]["status"] == "configured_not_written"
    assert manifest["selection"] == {
        "method": "human",
        "winner": None,
        "automatic_ranking": False,
    }

    with pytest.raises(ValueError, match="at most 48"):
        skill.plan(
            parent_node_id="/obj/HERMES_SIM",
            artifact_dir=str(tmp_path),
            start_frame=1,
            end_frame=49,
        )
    with pytest.raises(ValueError, match="provided together"):
        skill.plan(
            parent_node_id="/obj/HERMES_SIM",
            artifact_dir=str(tmp_path),
            viewer_name="sceneviewer1",
        )


def test_differential_growth_skill_is_native_bounded_and_human_selected(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "generate.differential_growth"))
    calls = skill.plan(
        parent_node_id="/obj/HERMES_GROWTH",
        artifact_dir=str(tmp_path),
        run_id="unit_growth",
        seed=101,
        candidate_index=2,
        end_frame=18,
    )
    assert [call["tool"] for call in calls] == [
        "recipe.instantiate",
        "growth.solver.populate",
        "cook.node",
        "geometry.validate",
        "graph.capture_svg",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    recipe = calls[0]
    assert recipe["arguments"]["recipe_id"] == "sop.differential_growth_loop"
    assert recipe["arguments"]["inputs"]["candidate_index"] == 2
    populate = calls[1]
    assert populate["arguments"]["point_radius"] == pytest.approx(0.075)
    assert populate["arguments"]["solver_path"].endswith("/UNIT_GROWTH_SOLVER")
    temporal = calls[2]
    assert temporal["arguments"]["scope"] == "frame_range"
    assert temporal["arguments"]["frame_range"] == [1.0, 18, 1.0]
    assert temporal["policy"]["max_frames"] == 18
    metadata = calls[6]["arguments"]["metadata"]
    assert [item["id"] for item in metadata["candidates"]] == [
        "circle",
        "ellipse",
        "spiral",
    ]
    assert all(item["seed"] == 101 for item in metadata["candidates"])
    assert all(item["human_rating"]["score"] is None for item in metadata["candidates"])
    assert metadata["selection"] == {
        "method": "human",
        "preview_input": 2,
        "winner": None,
        "automatic_ranking": False,
    }
    assert metadata["algorithm"]["python_geometry_compute"] is False

    with pytest.raises(ValueError, match="at most 24"):
        skill.plan(
            parent_node_id="/obj/HERMES_GROWTH",
            artifact_dir=str(tmp_path),
            start_frame=1,
            end_frame=25,
        )
    with pytest.raises(ValueError, match="provided together"):
        skill.plan(
            parent_node_id="/obj/HERMES_GROWTH",
            artifact_dir=str(tmp_path),
            viewer_name="sceneviewer1",
        )


def test_reaction_diffusion_skill_preserves_three_native_patterns_and_explicit_exports(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "generate.reaction_diffusion_pattern"))
    calls = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="unit_reaction",
        seed=77,
        resolution=128,
        candidate_index=2,
        iterations=4,
        iterations_per_step=6,
    )
    assert [call["tool"] for call in calls] == [
        "graph.apply_batch",
        "recipe.instantiate",
        "cop.reaction.validate",
        "cop.image.export",
        "cop.image.export",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    network = calls[0]
    create = network["arguments"]["operations"][0]
    assert create["category"] == "CopNet"
    assert create["operator_type"] == "copnet"
    assert create["parameters"]["res"] == [128, 128]
    recipe = calls[1]
    assert recipe["arguments"]["recipe_id"] == "cop.reaction_diffusion_pattern"
    assert recipe["arguments"]["inputs"]["candidate_index"] == 2
    validation = calls[2]
    assert validation["arguments"]["pattern_node_paths"] == [
        "/img/UNIT_REACTION_COPNET/UNIT_REACTION_SMALL_WAVES",
        "/img/UNIT_REACTION_COPNET/UNIT_REACTION_LARGE_WAVES",
        "/img/UNIT_REACTION_COPNET/UNIT_REACTION_SPOTS",
    ]
    assert (
        validation["arguments"]["iterations"] * validation["arguments"]["iterations_per_step"] == 24
    )
    assert calls[3]["arguments"]["expected_resolution"] == [384, 128]
    assert calls[4]["arguments"]["expected_resolution"] == [128, 128]
    metadata = calls[6]["arguments"]["metadata"]
    assert [item["preset"] for item in metadata["candidates"]] == [
        "smallwaves",
        "bigwaves",
        "spots",
    ]
    assert all(item["human_rating"]["score"] is None for item in metadata["candidates"])
    assert metadata["selection"] == {
        "method": "human",
        "preview_input": 2,
        "winner": None,
        "automatic_ranking": False,
        "contact_order": ["smallwaves", "bigwaves", "spots"],
    }
    assert metadata["algorithm"]["python_image_compute"] is False

    with pytest.raises(ValueError, match="must be <= 48"):
        skill.plan(
            artifact_dir=str(tmp_path),
            iterations=9,
            iterations_per_step=6,
        )
    with pytest.raises(ValueError, match="explicit /img"):
        skill.plan(artifact_dir=str(tmp_path), network_parent_path="/stage")


def test_botanical_grammar_skill_uses_registered_templates_and_human_comparison(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "grow.botanical_grammar"))
    calls = skill.plan(
        parent_node_id="/obj/BOTANICAL",
        artifact_dir=str(tmp_path),
        run_id="unit_botanical",
        seed=4103,
        generations=5,
        candidate_index=2,
        wire_radius=0.02,
    )
    assert [call["tool"] for call in calls] == [
        "recipe.instantiate",
        "botanical.validate",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    recipe = calls[0]
    assert recipe["arguments"]["recipe_id"] == "sop.lsystem_botanical"
    assert recipe["arguments"]["inputs"]["seed_canopy"] == 4103
    assert recipe["arguments"]["inputs"]["seed_fern"] == 4204
    assert recipe["arguments"]["inputs"]["seed_coral"] == 4314
    validation = calls[1]
    assert validation["arguments"]["skeleton_node_paths"] == [
        "/obj/BOTANICAL/UNIT_BOTANICAL_CANOPY_SKELETON",
        "/obj/BOTANICAL/UNIT_BOTANICAL_FERN_SKELETON",
        "/obj/BOTANICAL/UNIT_BOTANICAL_CORAL_SKELETON",
    ]
    metadata = calls[3]["arguments"]["metadata"]
    assert [candidate["id"] for candidate in metadata["candidates"]] == [
        "canopy",
        "fern",
        "coral",
    ]
    assert all(candidate["human_rating"]["score"] is None for candidate in metadata["candidates"])
    assert metadata["selection"] == {
        "method": "human",
        "preview_input": 2,
        "winner": None,
        "automatic_ranking": False,
        "comparison_order": ["canopy", "fern", "coral"],
    }
    assert metadata["algorithm"]["safe_registered_grammars_only"] is True
    assert metadata["algorithm"]["python_geometry_compute"] is False

    with pytest.raises(ValueError, match="must be <= 6"):
        skill.plan(
            parent_node_id="/obj/BOTANICAL",
            artifact_dir=str(tmp_path),
            generations=7,
        )
    with pytest.raises(ValueError, match="absolute /obj"):
        skill.plan(parent_node_id="/stage", artifact_dir=str(tmp_path))


def test_relic_lookdev_skill_separates_stage_validation_and_external_render(tmp_path):
    skill = load_skill(os.path.join(ROOT, "skills", "lookdev.relic_stage"))
    calls = skill.plan(
        source_sop_path="/obj/RELIC/OUT_GEO",
        artifact_dir=str(tmp_path),
        run_id="unit_lookdev",
        candidate_index=1,
        width=480,
        height=270,
    )
    assert [call["tool"] for call in calls] == [
        "recipe.instantiate",
        "solaris.materialx.populate",
        "solaris.stage.validate",
        "solaris.karma_rop.build",
        "render.karma.preview",
        "graph.capture_svg",
        "graph.capture_manifest",
        "hip.save_snapshot",
    ]
    recipe = calls[0]
    assert recipe["arguments"]["recipe_id"] == "lop.relic_lookdev_stage"
    assert recipe["arguments"]["version"] == "1.1.0"
    assert recipe["arguments"]["inputs"]["candidate_index"] == 1
    assert recipe["arguments"]["inputs"]["dome_intensity"] == 1.0
    assert recipe["arguments"]["inputs"]["camera_focal_length"] == 45.0
    materials = calls[1]["arguments"]["materials"]
    assert [item["id"] for item in materials] == ["oxide", "amber", "ivory"]
    stage = calls[2]
    assert stage["arguments"]["binding_prim_path"] == "/World/Asset"
    assert stage["arguments"]["source_sop_path"] == "/obj/RELIC/OUT_GEO"
    assert stage["arguments"]["source_start_frame"] == 1.0
    assert stage["arguments"]["frame"] == 1.0
    render = calls[4]
    assert render["policy"]["allow_external_process"] is True
    assert render["policy"]["max_frames"] == 1
    assert render["policy"]["max_resolution"] == [480, 270]
    metadata = calls[6]["arguments"]["metadata"]
    assert metadata["selection"] == {
        "method": "human",
        "preview_input": 1,
        "winner": None,
        "automatic_ranking": False,
    }
    assert all(item["human_rating"]["score"] is None for item in metadata["materials"])
    assert metadata["presentation"]["camera_translate"] == [6.0, 4.0, 8.0]

    with pytest.raises(ValueError, match="camera_focal_length"):
        skill.plan(
            source_sop_path="/obj/RELIC/OUT_GEO",
            artifact_dir=str(tmp_path),
            camera_focal_length=0.0,
        )

    no_render = skill.plan(
        source_sop_path="/obj/RELIC/OUT_GEO",
        artifact_dir=str(tmp_path),
        render_preview=False,
    )
    assert "solaris.karma_rop.build" not in [call["tool"] for call in no_render]
    assert "render.karma.preview" not in [call["tool"] for call in no_render]


def test_skill_directory_matches_manifest_id(tmp_path):
    root = tmp_path / "wrong_name"
    root.mkdir()
    (root / "skill.py").write_text("def plan(**kwargs): return []\n")
    (root / "skill.yaml").write_text(
        """id: model.example
version: 1.0.0
summary: example
contexts: [SOP]
houdini: {tested_builds: [\"22.0.368\"]}
license: {mode: houdini-apprentice-noncommercial}
inputs: {}
risk: low
checkpoint: none
cook_budget: {}
steps: []
verification: {}
outputs: []
rollback: none
"""
    )
    try:
        load_skill(root)
    except SkillError as exc:
        assert "must match id" in str(exc)
    else:
        raise AssertionError("expected SkillError")
