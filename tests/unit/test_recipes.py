"""Recipe parser unit tests (no Houdini; uses a tiny inline YAML fallback if pyyaml missing)."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from recipes.parser import Recipe, RecipeError, load_recipe  # noqa: E402

RECIPE_YAML = """
id: sop.scatter_cluster_points
version: 1.0.0
summary: test
contexts: [SOP]
inputs:
  parent_path: {type: string}
  count: {type: integer, default: 100}
nodes:
  - id: src
    type: scatter
    name: SCATTER_PTS
    params: {force_total: "{{count}}"}
connections:
  - [src, 0, src, 0]
outputs: [src]
"""


def _recipe_from_text(tmp_path) -> Recipe:
    p = tmp_path / "r.yaml"
    p.write_text(RECIPE_YAML)
    return load_recipe(p)


def test_load_and_render(tmp_path):
    r = _recipe_from_text(tmp_path)
    assert r.id == "sop.scatter_cluster_points"
    calls = r.render("/obj/ASSET", count=500)
    # 1 create + 1 connect
    assert len(calls) == 2
    create = [c for c in calls if c["tool"] == "node.create"][0]
    assert create["arguments"]["parameters"]["force_total"] == 500


def test_template_substitution(tmp_path):
    r = _recipe_from_text(tmp_path)
    calls = r.render("/obj/ASSET", count=10)
    create = [c for c in calls if c["tool"] == "node.create"][0]
    assert create["arguments"]["parameters"]["force_total"] == 10


def test_defaults_and_bounds_are_enforced(tmp_path):
    r = _recipe_from_text(tmp_path)
    calls = r.render("/obj/ASSET")
    create = [c for c in calls if c["tool"] == "node.create"][0]
    assert create["arguments"]["parameters"]["force_total"] == 100
    try:
        r.render("/obj/ASSET", count="bad")
    except RecipeError as exc:
        assert "integer" in str(exc)
    else:
        raise AssertionError("expected RecipeError")


def test_all_bundled_recipes_validate_and_render():
    rendered = {}
    recipes_root = os.path.join(ROOT, "recipes")
    for context in ("cop", "lop", "sop", "top"):
        context_root = os.path.join(recipes_root, context)
        parent = {
            "cop": "/img/HERMES_COP",
            "lop": "/stage",
            "top": "/tasks/HERMES_PDG",
        }.get(context, "/obj/HERMES_ASSET")
        for filename in sorted(os.listdir(context_root)):
            if not filename.endswith(".yaml"):
                continue
            recipe = load_recipe(os.path.join(context_root, filename))
            overrides = {}
            if recipe.id == "lop.relic_lookdev_stage":
                overrides = {
                    "source_sop_path": "/obj/HERMES_ASSET/OUT_GEO",
                    "render_picture": "/project/render/lookdev.png",
                }
            elif recipe.id == "cop.reaction_diffusion_pattern":
                overrides = {
                    "end_small_path": f"{parent}/REACTION_DIFFUSION_SMALL_WAVES",
                    "end_large_path": f"{parent}/REACTION_DIFFUSION_LARGE_WAVES",
                    "end_spots_path": f"{parent}/REACTION_DIFFUSION_SPOTS",
                    "contact_output": "/project/reaction_contact.png",
                    "selected_output": "/project/reaction_selected.png",
                }
            elif recipe.id == "cop.procedural_material_foundry":
                overrides = {
                    "verdigris_pattern_path": f"{parent}/VERDIGRIS_PATTERN",
                    "emberglaze_pattern_path": f"{parent}/EMBERGLAZE_PATTERN",
                    "moonlichen_pattern_path": f"{parent}/MOONLICHEN_PATTERN",
                }
            elif recipe.id == "lop.procedural_material_foundry_stage":
                overrides = {
                    "verdigris_sop_path": "/obj/SWATCHES/OUT_VERDIGRIS",
                    "emberglaze_sop_path": "/obj/SWATCHES/OUT_EMBERGLAZE",
                    "moonlichen_sop_path": "/obj/SWATCHES/OUT_MOONLICHEN",
                    "verdigris_material_cop": "/img/FOUNDRY/OUT_VERDIGRIS_MATERIAL",
                    "emberglaze_material_cop": "/img/FOUNDRY/OUT_EMBERGLAZE_MATERIAL",
                    "moonlichen_material_cop": "/img/FOUNDRY/OUT_MOONLICHEN_MATERIAL",
                    "render_picture": "/project/render/material_foundry.png",
                }
            elif recipe.id == "lop.world_seed_atlas_stage":
                overrides = {
                    "amber_sop_path": "/obj/AMBER/OUT_WORLD",
                    "verdant_sop_path": "/obj/VERDANT/OUT_WORLD",
                    "lunar_sop_path": "/obj/LUNAR/OUT_WORLD",
                    "render_picture": "/project/render/world_seed.png",
                }
            elif recipe.id == "lop.sidefx_labs_acceptance_stage":
                overrides = {
                    "gallery_sop_path": "/obj/LABS/OUT_LABS_GALLERY",
                    "render_picture": "/project/render/sidefx_labs_acceptance.png",
                }
            elif recipe.id == "lop.kinetic_reliquary_stage":
                overrides = {
                    "gallery_sop_path": "/obj/KINETIC/OUT_KINETIC_COMPARE",
                    "render_picture": "/project/render/kinetic_reliquary.png",
                }
            elif recipe.id == "sop.world_seed_biome":
                overrides = {
                    "seed": 19019,
                    "offset_x": 1.0,
                    "offset_y": 2.0,
                    "noise_amplitude": 2.4,
                    "noise_element_size": 2.6,
                    "terrace_step_size": 0.55,
                    "scatter_count": 54,
                    "scatter_radius": 0.14,
                    "hero_radius": 1.05,
                    "platonic_type": 3,
                    "translation_x": -9.5,
                    "terrain_r": 0.33,
                    "terrain_g": 0.075,
                    "terrain_b": 0.025,
                    "accent_r": 1.0,
                    "accent_g": 0.31,
                    "accent_b": 0.025,
                }
            rendered[recipe.id] = recipe.render(parent, **overrides)
    assert set(rendered) == {
        "lop.relic_lookdev_stage",
        "lop.procedural_material_foundry_stage",
        "lop.world_seed_atlas_stage",
        "lop.sidefx_labs_acceptance_stage",
        "lop.kinetic_reliquary_stage",
        "cop.reaction_diffusion_pattern",
        "cop.procedural_material_foundry",
        "sop.differential_growth_loop",
        "sop.fractal_relic_candidate",
        "sop.lsystem_botanical",
        "sop.particle_calligraphy",
        "sop.scatter_cluster_points",
        "sop.sweep_petals",
        "sop.vellum_relic_drop",
        "sop.vellum_membrane_lab",
        "sop.mpm_matter_sculpture",
        "sop.procedural_building_lot",
        "sop.rbd_art_directed_fracture",
        "sop.material_swatch_gallery",
        "sop.world_seed_biome",
        "sop.sidefx_labs_acceptance_gallery",
        "sop.kinetic_reliquary_native",
        "sop.kinetic_reliquary_mops",
        "sop.kinetic_reliquary_mops_unavailable",
        "sop.world_seed_labs_enhancement",
        "sop.world_seed_labs_unavailable",
        "top.procedural_district",
    }
    sweep_connects = [
        call for call in rendered["sop.sweep_petals"] if call["tool"] == "node.connect"
    ]
    assert sweep_connects[0]["arguments"]["from_path"].endswith("SECTION_CURVE")
    assert sweep_connects[1]["arguments"]["input_index"] == 1


def test_procedural_district_recipes_preserve_native_profiles_and_one_slot_top_contract():
    source = load_recipe(os.path.join(ROOT, "recipes", "sop", "procedural_building_lot.yaml"))
    source_fragment = source.render_fragment("/obj/DISTRICT", run_code="UNIT_DISTRICT")
    source_creates = [
        operation for operation in source_fragment["operations"] if operation["op"] == "create"
    ]
    source_connects = [
        operation for operation in source_fragment["operations"] if operation["op"] == "connect"
    ]
    assert source_fragment["recipe"] == {
        "id": "sop.procedural_building_lot",
        "version": "1.0.0",
    }
    assert len(source_creates) == 14
    assert len(source_connects) == 17
    assert {item["operator_type"] for item in source_creates} >= {
        "box",
        "merge",
        "switch",
        "polybevel::3.0",
        "normal",
        "null",
    }
    selector = next(item for item in source_creates if item["ref"] == "profile_switch")
    assert selector["parameters"]["input"] == 0
    assert source_fragment["outputs"] == {"out": "out"}

    top = load_recipe(os.path.join(ROOT, "recipes", "top", "procedural_district.yaml"))
    top_fragment = top.render_fragment(
        "/tasks/DISTRICT",
        source_sop_path="/obj/DISTRICT/OUT_BUILDING",
        output_pattern="/project/lot_`@wedgeindex`.bgeo.sc",
        temp_dir="/project/pdg_temp",
        lot_count=12,
    )
    top_creates = [
        operation for operation in top_fragment["operations"] if operation["op"] == "create"
    ]
    assert [item["operator_type"] for item in top_creates] == [
        "localscheduler",
        "wedge",
        "ropgeometry",
        "waitforall",
        "null",
    ]
    scheduler = next(item for item in top_creates if item["ref"] == "scheduler")
    cache = next(item for item in top_creates if item["ref"] == "cache")
    assert scheduler["parameters"]["maxprocs"] == 1
    assert cache["parameters"]["savebackground"] == 0
    assert all(
        item["operator_type"] not in {"pythonprocessor", "pythonscript"} for item in top_creates
    )


def test_lop_lookdev_recipe_preserves_three_assignments_and_human_switch():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "lop", "relic_lookdev_stage.yaml"))
    fragment = recipe.render_fragment(
        "/stage",
        source_sop_path="/obj/RELIC/OUT_GEO",
        render_picture="/project/render/relic.png",
        run_code="UNIT_LOOKDEV",
        candidate_index=2,
    )
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    connects = [operation for operation in fragment["operations"] if operation["op"] == "connect"]
    assert fragment["recipe"] == {"id": "lop.relic_lookdev_stage", "version": "1.0.0"}
    assert len(creates) == 10
    assert len(connects) == 11
    assert all(operation["category"] == "Lop" for operation in creates)
    assignments = [item for item in creates if item["operator_type"] == "assignmaterial"]
    assert [item["parameters"]["matspecpath1"] for item in assignments] == [
        "/materials/UNIT_LOOKDEV_oxide",
        "/materials/UNIT_LOOKDEV_amber",
        "/materials/UNIT_LOOKDEV_ivory",
    ]
    selector = next(item for item in creates if item["operator_type"] == "switch")
    assert selector["parameters"]["input"] == 2
    selector_inputs = [item for item in connects if item["to"] == "select"]
    assert [(item["from"], item["input_index"]) for item in selector_inputs] == [
        ("assign_a", 0),
        ("assign_b", 1),
        ("assign_c", 2),
    ]


def test_vellum_recipe_exposes_native_temporal_and_cache_contracts():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "sop", "vellum_relic_drop.yaml"))
    fragment = recipe.render_fragment(
        "/obj/SIM",
        run_code="UNIT_DROP",
        start_frame=1,
        end_frame=12,
        cache_path="/project/cache/unit_drop.$F4.bgeo.sc",
    )
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    connects = [operation for operation in fragment["operations"] if operation["op"] == "connect"]
    assert fragment["recipe"] == {"id": "sop.vellum_relic_drop", "version": "1.0.0"}
    assert len(creates) == 15
    assert len(connects) == 18
    assert {operation["operator_type"] for operation in creates} >= {
        "sphere",
        "vellumconstraints",
        "vellumsolver",
        "box",
        "filecache",
    }
    assert fragment["outputs"] == {
        "rest": "rest",
        "constraints": "constraints",
        "collider": "collider",
        "sim_raw": "sim_raw",
        "sim_cache": "sim_cache",
        "compare": "compare",
    }
    cache = next(operation for operation in creates if operation["operator_type"] == "filecache")
    assert cache["parameters"]["file"] == "/project/cache/unit_drop.$F4.bgeo.sc"
    assert cache["parameters"]["initsim"] == 1
    solver_connections = [item for item in connects if item["to"] == "solver"]
    assert [
        (item["from"], item["output_index"], item["input_index"]) for item in solver_connections
    ] == [
        ("pressure", 0, 0),
        ("pressure", 1, 1),
        ("collider", 0, 2),
    ]


def test_differential_growth_recipe_preserves_sources_feedback_boundary_and_outputs():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "sop", "differential_growth_loop.yaml"))
    fragment = recipe.render_fragment(
        "/obj/GROWTH",
        run_code="UNIT_GROWTH",
        candidate_index=1,
        noise_offset_x=2.5,
        start_frame=3,
    )
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    connects = [operation for operation in fragment["operations"] if operation["op"] == "connect"]
    assert fragment["recipe"] == {"id": "sop.differential_growth_loop", "version": "1.0.0"}
    assert len(creates) == 15
    assert len(connects) == 15
    assert {operation["operator_type"] for operation in creates} >= {
        "circle",
        "spiral",
        "switch",
        "mountain::2.0",
        "resample",
        "solver",
        "polywire",
    }
    selector = next(operation for operation in creates if operation["ref"] == "source_select")
    assert selector["parameters"]["input"] == 1
    solver = next(operation for operation in creates if operation["ref"] == "solver")
    assert solver["parameters"]["startframe"] == 3
    assert solver["parameters"]["cachetodisk"] == 0
    assert fragment["outputs"] == {
        "rest_curve": "rest_curve",
        "growth_curve": "growth_curve",
        "growth_wire": "growth_wire",
        "compare": "compare",
    }


def test_reaction_diffusion_recipe_uses_native_cop_blocks_and_preserves_contact_order():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "cop", "reaction_diffusion_pattern.yaml"))
    fragment = recipe.render_fragment(
        "/img/UNIT_REACTION",
        run_code="UNIT_REACTION",
        end_small_path="/img/UNIT_REACTION/UNIT_REACTION_SMALL_WAVES",
        end_large_path="/img/UNIT_REACTION/UNIT_REACTION_LARGE_WAVES",
        end_spots_path="/img/UNIT_REACTION/UNIT_REACTION_SPOTS",
        candidate_index=1,
        iterations=4,
        iterations_per_step=5,
        contact_output="/project/contact.png",
        selected_output="/project/selected.png",
    )
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    connects = [operation for operation in fragment["operations"] if operation["op"] == "connect"]
    assert fragment["recipe"] == {"id": "cop.reaction_diffusion_pattern", "version": "1.0.0"}
    assert len(creates) == 17
    assert len(connects) == 20
    assert all(operation["category"] == "Cop" for operation in creates)
    assert (
        sum(operation["operator_type"] == "reactiondiffusion_block_begin" for operation in creates)
        == 3
    )
    assert (
        sum(operation["operator_type"] == "reactiondiffusion_block_end" for operation in creates)
        == 3
    )
    end_nodes = [
        next(operation for operation in creates if operation["ref"] == ref)
        for ref in ("end_small", "end_large", "end_spots")
    ]
    assert [node["parameters"]["presetsgs"] for node in end_nodes] == [
        "smallwaves",
        "bigwaves",
        "spots",
    ]
    assert [(node["parameters"]["kill"], node["parameters"]["feed"]) for node in end_nodes] == [
        (0.3865, 0.0899),
        (0.0, 0.0444),
        (0.8045, 0.2222),
    ]
    assert all(node["parameters"]["simulate"] == 0 for node in end_nodes)
    assert all(node["parameters"]["continuouscook"] == 0 for node in end_nodes)
    contact_inputs = [item for item in connects if item["to"] == "contactsheet"]
    assert [(item["from"], item["input_index"]) for item in contact_inputs] == [
        ("color_small", 0),
        ("color_large", 1),
        ("color_spots", 2),
    ]
    rops = [operation for operation in creates if operation["operator_type"] == "rop_image"]
    assert [node["parameters"]["copoutput"] for node in rops] == [
        "/project/selected.png",
        "/project/contact.png",
    ]
    assert all(node["parameters"]["docompile"] == 0 for node in rops)


def test_lsystem_botanical_recipe_preserves_registered_grammars_and_candidate_order():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "sop", "lsystem_botanical.yaml"))
    fragment = recipe.render_fragment(
        "/obj/BOTANICAL",
        run_code="UNIT_BOTANICAL",
        generations=5,
        seed_canopy=10,
        seed_fern=111,
        seed_coral=221,
        candidate_index=1,
        wire_radius=0.02,
    )
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    connects = [operation for operation in fragment["operations"] if operation["op"] == "connect"]
    assert fragment["recipe"] == {"id": "sop.lsystem_botanical", "version": "1.0.0"}
    assert len(creates) == 17
    assert len(connects) == 18
    assert sum(node["operator_type"] == "lsystem" for node in creates) == 3
    assert sum(node["operator_type"] == "polywire" for node in creates) == 3
    skeletons = [
        next(node for node in creates if node["ref"] == ref)
        for ref in ("skeleton_canopy", "skeleton_fern", "skeleton_coral")
    ]
    assert [node["parameters"]["premise"] for node in skeletons] == [
        'a("Cd",0.12,0.65,0.22)F(0.8)A',
        'a("Cd",0.10,0.35,0.08)X',
        'a("Cd",0.75,0.25,0.12)A',
    ]
    assert [node["parameters"]["randseed"] for node in skeletons] == [10, 111, 221]
    assert all(node["parameters"]["usefile"] == 0 for node in skeletons)
    assert all(node["parameters"]["thickinit"] == 1.0 for node in skeletons)
    selector_inputs = [item for item in connects if item["to"] == "selector"]
    assert [(item["from"], item["input_index"]) for item in selector_inputs] == [
        ("out_canopy", 0),
        ("out_fern", 1),
        ("out_coral", 2),
    ]
    merge_inputs = [item for item in connects if item["to"] == "compare_merge"]
    assert [(item["from"], item["input_index"]) for item in merge_inputs] == [
        ("compare_canopy", 0),
        ("compare_fern", 1),
        ("compare_coral", 2),
    ]
    transforms = [
        next(node for node in creates if node["ref"] == ref)
        for ref in ("compare_canopy", "compare_fern", "compare_coral")
    ]
    assert [node["parameters"]["tx"] for node in transforms] == [-2.0, 0.0, 2.0]
    frame = next(node for node in creates if node["ref"] == "compare_frame")
    assert frame["parameters"] == {"ty": -0.2, "scale": 0.72}


def test_recipe_fragment_is_transactional_composable_and_positioned():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "sop", "fractal_relic_candidate.yaml"))
    fragment = recipe.render_fragment(
        "/obj/RELIC",
        ref_prefix="cand_a_",
        position_offset=(-7.0, 0.0),
        candidate_code="A",
        lineage="candidate_A seed=42",
        base_radius=1.25,
        point_count=100,
    )
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    connects = [operation for operation in fragment["operations"] if operation["op"] == "connect"]
    assert fragment["recipe"] == {"id": "sop.fractal_relic_candidate", "version": "2.0.0"}
    assert len(creates) == 8
    assert len(connects) == 8
    assert creates[0]["ref"] == "cand_a_base"
    assert creates[0]["name"] == "CAND_A_BASE"
    assert creates[0]["position"] == [-8.0, 8.0]
    assert creates[0]["parameters"]["rad"] == [1.25, 1.25, 1.25]
    assert fragment["outputs"] == {"out": "cand_a_out", "compare": "cand_a_compare"}


def test_recipe_fragment_rejects_unsafe_prefix_and_position():
    recipe = load_recipe(os.path.join(ROOT, "recipes", "sop", "fractal_relic_candidate.yaml"))
    for kwargs, expected in (
        ({"ref_prefix": "../escape"}, "ref_prefix"),
        ({"position_offset": (0.0, float("inf"))}, "position_offset"),
    ):
        try:
            recipe.render_fragment("/obj/RELIC", **kwargs)
        except RecipeError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("expected RecipeError")
