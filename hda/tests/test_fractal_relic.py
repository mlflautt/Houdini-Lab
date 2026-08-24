"""Houdini regression and promotion tests for ``hermes::fractal_relic::2.0``."""

from __future__ import annotations

import json

import pytest

hou = pytest.importorskip("hou")

from hda.source.hermes_fractal_relic.build import build, upgrade_from_v1  # noqa: E402
from hermes_houdini.graph_batch import apply_batch  # noqa: E402
from skills._lib.fractal_relic import build_graph_spec  # noqa: E402


def _instance(result, name="RELIC_INSTANCE"):
    asset = hou.node(result["node_path"])
    assert asset is not None
    instance = asset.parent().createNode(result["type_name"], node_name=name)
    assert instance.matchesCurrentDefinition()
    instance.allowEditingOfContents()
    return asset, instance


def _metrics(node):
    geometry = node.geometry()
    bounds = geometry.boundingBox()
    return {
        "points": geometry.pointCount(),
        "primitives": geometry.primCount(),
        "bounds": [list(bounds.minvec()), list(bounds.maxvec())],
    }


def test_build_promotes_recipe_graph_controls_help_and_metadata():
    result = build()
    assert result["type_name"] == "hermes::fractal_relic::2.0"
    assert result["recipe"] == "sop.fractal_relic_candidate@2.0.0"
    assert result["noncommercial"] is True
    assert result["graph_nodes"] == 30
    required = {
        "seed",
        "iterations",
        "detail_level",
        "base_radius",
        "detail_radius",
        "noise_amplitude",
        "preview_candidate",
        "output_mode",
        "human_winner",
        "candidate_a_rating",
        "candidate_a_notes",
        "candidate_b_rating",
        "candidate_b_notes",
        "candidate_c_rating",
        "candidate_c_notes",
    }
    assert required <= set(result["parameter_names"])
    assert {"Help", "hermes_manifest.json"} <= set(result["definition_sections"])

    asset, instance = _instance(result)
    try:
        definition = instance.type().definition()
        manifest = json.loads(definition.sections()["hermes_manifest.json"].contents())
        assert manifest["selection"] == {"automatic_ranking": False, "method": "human"}
        assert manifest["license"]["engine_export_allowed"] is False
        assert "no candidate is ranked automatically" in definition.sections()["Help"].contents()
        assert instance.userData("hermes_recipe") == "sop.fractal_relic_candidate@2.0.0"

        recipe_nodes = [node for node in instance.children() if node.userData("hermes_recipe_ref")]
        assert len(recipe_nodes) == 28
        ids = [node.userData("hermes_id") for node in recipe_nodes]
        assert len(ids) == len(set(ids)) and all(ids)
        assert all(node.userData("hermes_created_by").startswith("hda:") for node in recipe_nodes)
        assert all(node.type().name() not in {"python", "attribwrangle"} for node in recipe_nodes)
    finally:
        asset.parent().destroy()


def test_promoted_controls_drive_candidates_without_auto_selecting():
    result = build(name="fractal_relic_controls")
    asset, instance = _instance(result)
    try:
        instance.parm("seed").set(100)
        instance.parm("iterations").set(2)
        instance.parm("detail_level").set(0)
        instance.parm("base_radius").set(1.25)
        instance.parm("detail_radius").set(0.06)
        instance.parm("noise_amplitude").set(0.2)
        instance.parm("preview_candidate").set(2)
        assert instance.node("CAND_A_SCATTER").parm("seed").eval() == pytest.approx(100)
        assert instance.node("CAND_B_SCATTER").parm("seed").eval() == pytest.approx(8019)
        assert instance.node("CAND_C_SCATTER").parm("seed").eval() == pytest.approx(15938)
        assert instance.node("CAND_A_BASE").parm("radx").eval() == pytest.approx(1.25)
        assert instance.node("SELECT_CANDIDATE").parm("input").eval() == 2

        instance.parm("output_mode").set(0)
        selected = _metrics(instance)
        instance.parm("output_mode").set(1)
        comparison = _metrics(instance)
        selected_width = selected["bounds"][1][0] - selected["bounds"][0][0]
        comparison_width = comparison["bounds"][1][0] - comparison["bounds"][0][0]
        assert comparison_width > selected_width * 2

        instance.parm("candidate_c_rating").set(4.5)
        instance.parm("candidate_c_notes").set("Strong silhouette; preserve the crown rhythm.")
        instance.parm("human_winner").set(3)
        assert instance.parm("preview_candidate").eval() == 2
        assert instance.parm("human_winner").eval() == 3
        assert instance.parm("candidate_c_rating").eval() == pytest.approx(4.5)
    finally:
        asset.parent().destroy()


def test_hda_comparison_geometry_matches_shared_raw_graph(tmp_path):
    result = build(name="fractal_relic_equivalence")
    asset, instance = _instance(result)
    raw = hou.node("/obj").createNode(
        "geo", node_name="HERMES_RELIC_EQUIVALENCE", run_init_scripts=False
    )
    try:
        controls = {
            "seed": 222,
            "iterations": 3,
            "detail_level": "draft",
            "base_radius": 0.9,
            "detail_radius": 0.07,
            "noise_amplitude": 0.12,
            "preview_candidate": 1,
        }
        graph = build_graph_spec(parent_path=raw.path(), **controls)
        result_raw = apply_batch(
            batch_id="hda-equivalence",
            operations=graph["operations"],
            checkpoint_dir=str(tmp_path / "checkpoints"),
            log_path=str(tmp_path / "graph.jsonl"),
            checkpoint_stem="hda_equivalence",
        )
        assert result_raw.status.value == "success", result_raw.errors
        raw_output = raw.node("OUT_COMPARISON")
        raw_output.cook(force=True)
        raw_metrics = _metrics(raw_output)

        for name, value in controls.items():
            if name == "detail_level":
                value = 0
            instance.parm(name).set(value)
        hda_comparison = instance.node("OUT_COMPARISON")
        hda_comparison.cook(force=True)
        hda_metrics = _metrics(hda_comparison)
        assert hda_metrics["points"] == raw_metrics["points"]
        assert hda_metrics["primitives"] == raw_metrics["primitives"]
        assert [value for vector in hda_metrics["bounds"] for value in vector] == pytest.approx(
            [value for vector in raw_metrics["bounds"] for value in vector]
        )
    finally:
        raw.destroy()
        asset.parent().destroy()


def test_hdanc_publish_is_non_destructive_by_default(tmp_path):
    result = build(name="fractal_relic_disk", dest_dir=str(tmp_path))
    asset = hou.node(result["node_path"])
    try:
        assert result["hda_file"].endswith(".hdanc")
        assert (tmp_path / "hermes_fractal_relic_disk_2_0.hdanc").is_file()
        with pytest.raises(FileExistsError, match="overwrite is disabled"):
            build(name="fractal_relic_disk", dest_dir=str(tmp_path))
    finally:
        asset.parent().destroy()


def test_v1_controls_upgrade_into_new_v2_instance_non_destructively():
    result = build()
    asset, target = _instance(result, name="RELIC_V2_TARGET")
    source = asset.parent().createNode("subnet", node_name="RELIC_V1_SOURCE")
    group = hou.ParmTemplateGroup(
        (
            hou.IntParmTemplate("seed", "Seed", 1, default_value=(42,)),
            hou.IntParmTemplate("iterations", "Iterations", 1, default_value=(4,)),
            hou.IntParmTemplate("detail_level", "Detail Level", 1, default_value=(1,)),
        )
    )
    source.setParmTemplateGroup(group)
    source.parm("seed").set(909)
    source.parm("iterations").set(7)
    source.parm("detail_level").set(2)
    try:
        upgraded = upgrade_from_v1(source, target)
        assert upgraded["transferred"] == {"seed": 909, "iterations": 7, "detail_level": 2}
        assert target.parm("seed").eval() == 909
        assert target.parm("iterations").eval() == 7
        assert target.parm("detail_level").eval() == 2
        assert target.userData("hermes_upgraded_from") == "subnet"
        assert source.parent() is not None
    finally:
        asset.parent().destroy()
