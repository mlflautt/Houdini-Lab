"""Bare-Hython integration boundaries introduced in Sprints 20.1–22."""

from __future__ import annotations

from pathlib import Path

import hou
from hermes_houdini.skill_loader import load_skill
from recipes.parser import load_recipe

ROOT = Path(__file__).resolve().parents[2]


def test_bare_hython_loads_json_compatible_optional_plugin_skills():
    labs = load_skill(ROOT / "skills" / "world.world_seed_atlas_labs")
    kinetic = load_skill(ROOT / "skills" / "motion.kinetic_reliquary")
    assert labs.id == "world.world_seed_atlas_labs"
    assert kinetic.id == "motion.kinetic_reliquary"
    assert hou.applicationVersionString() == "22.0.368"


def test_plugin_disabled_recipes_contain_no_optional_operator_types():
    labs = load_recipe(ROOT / "recipes" / "sop" / "world_seed_labs_unavailable.yaml")
    kinetic = load_recipe(
        ROOT / "recipes" / "sop" / "kinetic_reliquary_mops_unavailable.yaml"
    )
    operations = [
        *labs.render_fragment("/obj/LABS_FALLBACK")["operations"],
        *kinetic.render_fragment("/obj/MOPS_FALLBACK")["operations"],
    ]
    types = [operation.get("operator_type", "") for operation in operations]
    assert not any(node_type.startswith("labs::") for node_type in types)
    assert not any(node_type.startswith("MOPS::") for node_type in types)
