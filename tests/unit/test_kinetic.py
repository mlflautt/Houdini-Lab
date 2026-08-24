"""Pure Sprint 22 MOPs capability, recipe, and skill tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from hermes_houdini.kinetic import (
    KINETIC_VARIANTS,
    MOPS_KINETIC_NODE_TYPES,
    detect_mops_capability,
    validate_kinetic_spec,
)
from hermes_houdini.plugin_registry import load_plugin_manifest
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe

ROOT = Path(__file__).resolve().parents[2]


def test_mops_capability_and_kinetic_spec_are_bounded_and_unranked():
    assert detect_mops_capability(MOPS_KINETIC_NODE_TYPES)["available"] is True
    assert detect_mops_capability([])["missing_node_types"] == list(MOPS_KINETIC_NODE_TYPES)
    spec = validate_kinetic_spec(
        seed=22012, copy_count=24, start_frame=1, end_frame=24, mops_available=True
    )
    assert spec["sample_frames"] == [1, 12, 24]
    assert [item["id"] for item in spec["candidates"]] == list(KINETIC_VARIANTS)
    assert spec["selection"]["winner"] is None
    assert all(item["human_rating"]["score"] is None for item in spec["candidates"])
    with pytest.raises(ValueError, match="copy_count"):
        validate_kinetic_spec(
            seed=22012, copy_count=100, start_frame=1, end_frame=24, mops_available=True
        )


def test_mops_recipe_uses_only_pinned_types_and_native_default():
    recipe = load_recipe(ROOT / "recipes" / "sop" / "kinetic_reliquary_mops.yaml")
    fragment = recipe.render_fragment("/obj/KINETIC")
    creates = [operation for operation in fragment["operations"] if operation["op"] == "create"]
    plugin_types = {
        operation["operator_type"]
        for operation in creates
        if operation["operator_type"].startswith("MOPS::")
    }
    assert plugin_types == set(MOPS_KINETIC_NODE_TYPES)
    selector = next(operation for operation in creates if operation["role"] == "kinetic_human_selector")
    assert selector["parameters"]["input"] == 0
    native = load_recipe(ROOT / "recipes" / "sop" / "kinetic_reliquary_native.yaml")
    native_types = [
        operation["operator_type"]
        for operation in native.render_fragment("/obj/KINETIC")["operations"]
        if operation["op"] == "create"
    ]
    assert not any(node_type.startswith("MOPS::") for node_type in native_types)
    assert "attribwrangle" not in native_types

    staged = load_recipe(ROOT / "recipes" / "sop" / "kinetic_reliquary_staged.yaml")
    staged_types = [
        operation["operator_type"]
        for operation in staged.render_fragment("/obj/KINETIC")["operations"]
        if operation["op"] == "create"
    ]
    assert not any(node_type.startswith("MOPS::") for node_type in staged_types)
    assert staged_types.count("sphere") == 4
    assert staged_types.count("unpack") == 4


def test_kinetic_skill_selects_mops_or_native_fallback(tmp_path):
    skill = load_skill(ROOT / "skills" / "motion.kinetic_reliquary")
    enabled = skill.plan(
        artifact_dir=str(tmp_path), run_id="unit_mops", mops_available=True, render_preview=False
    )
    recipes = [
        call["arguments"]["recipe_id"]
        for call in enabled
        if call["tool"] == "recipe.instantiate"
    ]
    assert recipes == [
        "sop.kinetic_reliquary_native",
        "sop.kinetic_reliquary_mops",
        "sop.kinetic_reliquary_staged",
        "lop.kinetic_reliquary_staged_stage",
    ]
    validation = next(
        call for call in enabled if call["tool"] == "motion.kinetic_reliquary.validate"
    )
    assert validation["arguments"]["mops_available"] is True
    presentation = next(
        call
        for call in enabled
        if call["tool"] == "motion.kinetic_reliquary.presentation.validate"
    )
    assert presentation["arguments"]["presentation_path"].endswith("_KINETIC_STAGED")
    fallback = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="unit_native",
        mops_available=False,
        render_preview=False,
    )
    fallback_recipes = [
        call["arguments"]["recipe_id"]
        for call in fallback
        if call["tool"] == "recipe.instantiate"
    ]
    assert "sop.kinetic_reliquary_mops_unavailable" in fallback_recipes
    assert "sop.kinetic_reliquary_mops" not in fallback_recipes
    assert "sop.kinetic_reliquary_staged_native" in fallback_recipes

    rendered = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="unit_rendered",
        mops_available=True,
        render_preview=True,
    )
    visual = next(call for call in rendered if call["tool"] == "visual.analyze")
    assert visual["arguments"]["expect_motion"] is True
    assert visual["arguments"]["panel_count"] == 4
    assert visual["arguments"]["panel_rows"] == 1


def test_mops_registry_record_is_pinned_and_apprentice_allowed():
    record = load_plugin_manifest((ROOT / "plugins" / "mops-1.12.json").resolve())
    assert record["package"]["source_commit"] == "65c4cff83003a51b31edbefa1dd1a11bd3ac3c25"
    assert record["certified_node_types"] == list(MOPS_KINETIC_NODE_TYPES)
    assert record["apprentice"]["status"] == "allowed"
