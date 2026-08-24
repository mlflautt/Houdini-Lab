"""Source builder for the recipe-backed ``hermes::fractal_relic::2.0`` HDA.

The asset promotes the same pure graph specification used by ``model.fractal_relic``.
HOM creates, wires, tags, parameterizes, and packages native SOP nodes; Houdini remains
responsible for all geometry computation.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from hermes_houdini import get_hou
from hermes_houdini.ids import make_id
from skills._lib.fractal_relic import build_graph_spec

HDA_VERSION = "2.0"
RECIPE_ID = "sop.fractal_relic_candidate"
RECIPE_VERSION = "2.0.0"
_SAFE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,47}\Z")
_SAFE_VERSION = re.compile(r"\d+\.\d+\Z")

HELP_TEXT = """= Hermes Fractal Relic =

Recipe-backed three-candidate alien relic generator.

== Workflow ==
* Adjust seed, iterations, detail tier, radii, and deformation controls.
* Use Preview Candidate to choose the editable OUT_GEO branch.
* Use Output Mode to temporarily display all candidates side by side.
* Record human scores/notes; no candidate is ranked automatically.

The internal network is built from native SOPs and remains inspectable. Generated assets are
Houdini Apprentice/non-commercial, cannot be used with Houdini Engine, and retain .hdanc/.hipnc
license restrictions.
"""


def _parameter_templates(hou: Any) -> Any:
    form = hou.FolderParmTemplate(
        "form_folder",
        "Form",
        (
            hou.FloatParmTemplate(
                "base_radius",
                "Base Radius",
                1,
                default_value=(1.0,),
                min=0.25,
                max=5.0,
                min_is_strict=True,
                max_is_strict=True,
                help="Radius shared by the three candidate base forms.",
            ),
            hou.FloatParmTemplate(
                "detail_radius",
                "Detail Radius",
                1,
                default_value=(0.08,),
                min=0.01,
                max=0.5,
                min_is_strict=True,
                max_is_strict=True,
                help="Base radius of packed surface details before candidate mutation.",
            ),
            hou.FloatParmTemplate(
                "noise_amplitude",
                "Noise Amplitude",
                1,
                default_value=(0.16,),
                min=0.0,
                max=1.5,
                min_is_strict=True,
                max_is_strict=True,
                help="Native Attribute Noise displacement amplitude.",
            ),
        ),
    )
    variation = hou.FolderParmTemplate(
        "variation_folder",
        "Variation",
        (
            hou.IntParmTemplate(
                "seed",
                "Seed",
                1,
                default_value=(42,),
                min=0,
                max=1_000_000,
                min_is_strict=True,
                max_is_strict=True,
                help="Deterministically derives all three candidate seeds.",
            ),
            hou.IntParmTemplate(
                "iterations",
                "Iterations",
                1,
                default_value=(4,),
                min=1,
                max=8,
                min_is_strict=True,
                max_is_strict=True,
                help="Scales base frequency, scatter density, and relaxation.",
            ),
            hou.MenuParmTemplate(
                "detail_level",
                "Detail Level",
                ("draft", "preview", "final"),
                ("Draft", "Preview", "Final"),
                default_value=1,
                help="Bounded density tier: draft, preview, or final.",
            ),
        ),
    )
    selection = hou.FolderParmTemplate(
        "selection_folder",
        "Selection",
        (
            hou.MenuParmTemplate(
                "preview_candidate",
                "Preview Candidate",
                ("candidate_A", "candidate_B", "candidate_C"),
                ("A - Weathered Seed", "B - Balanced Relic", "C - Dense Crown"),
                default_value=0,
                help="Feeds OUT_GEO; this preview is not an automatic winner.",
            ),
            hou.MenuParmTemplate(
                "output_mode",
                "Output Mode",
                ("selected", "comparison"),
                ("Selected Candidate", "Three-Form Comparison"),
                default_value=0,
                help="Temporarily output the spatial comparison without deleting alternatives.",
            ),
            hou.MenuParmTemplate(
                "human_winner",
                "Human Winner",
                ("unrated", "candidate_A", "candidate_B", "candidate_C"),
                ("Unrated", "Candidate A", "Candidate B", "Candidate C"),
                default_value=0,
                help="Human decision record only; it does not drive geometry automatically.",
            ),
        ),
    )
    ratings: list[Any] = []
    for letter, label in zip(
        "ABC", ("Weathered Seed", "Balanced Relic", "Dense Crown"), strict=True
    ):
        ratings.extend(
            (
                hou.FloatParmTemplate(
                    f"candidate_{letter.lower()}_rating",
                    f"Candidate {letter} Rating",
                    1,
                    default_value=(0.0,),
                    min=0.0,
                    max=5.0,
                    min_is_strict=True,
                    max_is_strict=True,
                    help=f"Human score for {label}; 0 means unrated.",
                ),
                hou.StringParmTemplate(
                    f"candidate_{letter.lower()}_notes",
                    f"Candidate {letter} Notes",
                    1,
                    default_value=("",),
                    help=f"Human creative notes for {label}.",
                ),
            )
        )
    rating_folder = hou.FolderParmTemplate("ratings_folder", "Human Ratings", tuple(ratings))
    provenance = hou.FolderParmTemplate(
        "provenance_folder",
        "Provenance",
        (
            hou.StringParmTemplate(
                "source_recipe",
                "Source Recipe",
                1,
                default_value=(f"{RECIPE_ID}@{RECIPE_VERSION}",),
            ),
            hou.StringParmTemplate(
                "license_mode",
                "License Mode",
                1,
                default_value=("houdini-apprentice-noncommercial",),
            ),
        ),
    )
    return hou.ParmTemplateGroup((form, variation, selection, rating_folder, provenance))


def _set_parameter(node: Any, name: str, value: Any) -> None:
    parm = node.parm(name)
    parm_tuple = node.parmTuple(name)
    if parm is not None:
        parm.set(value)
    elif parm_tuple is not None:
        parm_tuple.set(value)
    else:
        raise ValueError(f"operator {node.type().name()} has no parameter {name}")


def _instantiate_operations(
    parent: Any, operations: list[dict[str, Any]], type_name: str
) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for operation in operations:
        op = operation["op"]
        if op == "create":
            if operation["parent_path"] != parent.path():
                raise ValueError(f"recipe escaped HDA parent: {operation['parent_path']}")
            node = parent.createNode(
                operation["operator_type"],
                node_name=operation["name"],
                exact_type_name=True,
            )
            if operation.get("exact_name") and node.name() != operation["name"]:
                raise ValueError(
                    f"requested exact node name {operation['name']!r} but got {node.name()!r}"
                )
            node.setPosition(operation["position"])
            for name, value in operation.get("parameters", {}).items():
                _set_parameter(node, name, value)
            ref = operation["ref"]
            node.setUserData("hermes_id", make_id("Sop", f"hda:{type_name}:{ref}"))
            node.setUserData("hermes_role", operation.get("role", ""))
            node.setUserData("hermes_created_by", f"hda:{type_name}")
            node.setUserData("hermes_manifest_version", "2")
            node.setUserData("hermes_recipe_ref", ref)
            node.setUserData("hermes_recipe", f"{RECIPE_ID}@{RECIPE_VERSION}")
            node.setComment(operation.get("comment", ""))
            refs[ref] = node
        elif op == "connect":
            source = refs[operation["from"]]
            target = refs[operation["to"]]
            target.setInput(
                operation.get("input_index", 0),
                source,
                operation.get("output_index", 0),
            )
        elif op == "set_flags":
            node = refs[operation["target"]]
            if "display" in operation:
                node.setDisplayFlag(operation["display"])
            if "render" in operation:
                node.setRenderFlag(operation["render"])
            if "bypass" in operation:
                node.bypass(operation["bypass"])
        else:
            raise ValueError(f"unsupported recipe operation in HDA build: {op}")
    return refs


def _expression(node: Any, parm_name: str, expression: str, hou: Any) -> None:
    parm = node.parm(parm_name)
    if parm is None:
        raise ValueError(f"missing promoted target parameter: {node.path()}/{parm_name}")
    parm.setExpression(expression, language=hou.exprLanguage.Hscript)


def _wire_promoted_controls(refs: dict[str, Any], hou: Any) -> None:
    density = 'if(ch("../detail_level")==0,40,if(ch("../detail_level")==1,80,160))'
    mutations = (
        ("a", 0, 0.80, 0.80, 1.15, -3.0),
        ("b", 7_919, 1.00, 1.00, 1.00, 0.0),
        ("c", 15_838, 1.25, 1.25, 0.75, 3.0),
    )
    for (
        letter,
        seed_offset,
        density_factor,
        noise_factor,
        detail_factor,
        compare_factor,
    ) in mutations:
        base = refs[f"cand_{letter}_base"]
        for parm_name in ("radx", "rady", "radz"):
            _expression(base, parm_name, 'ch("../base_radius")', hou)
        _expression(base, "freq", 'min(10,3+ch("../iterations"))', hou)

        noise = refs[f"cand_{letter}_noise"]
        _expression(
            noise,
            "amplitude",
            f'ch("../noise_amplitude")*{noise_factor}',
            hou,
        )
        _expression(noise, "elementsize", 'max(0.15,ch("../base_radius")*0.65)', hou)
        _expression(noise, "offset", f'(ch("../seed")+{seed_offset})*0.001', hou)

        scatter = refs[f"cand_{letter}_scatter"]
        _expression(
            scatter,
            "npts",
            f'round(ch("../iterations")*{density}*{density_factor})',
            hou,
        )
        _expression(scatter, "seed", f'ch("../seed")+{seed_offset}', hou)
        _expression(scatter, "relaxiterations", 'min(10,ch("../iterations")+2)', hou)

        detail = refs[f"cand_{letter}_detail"]
        for parm_name in ("radx", "rady", "radz"):
            _expression(detail, parm_name, f'ch("../detail_radius")*{detail_factor}', hou)
        _expression(
            refs[f"cand_{letter}_compare"],
            "tx",
            f'ch("../base_radius")*{compare_factor}',
            hou,
        )
    _expression(refs["candidate_switch"], "input", 'ch("../preview_candidate")', hou)


def _manifest_document(type_name: str) -> dict[str, Any]:
    return {
        "schema": "hermes.houdini.hda_manifest",
        "schema_version": "1.0",
        "type_name": type_name,
        "skill": "model.fractal_relic@1.1.0",
        "recipe": f"{RECIPE_ID}@{RECIPE_VERSION}",
        "license": {
            "mode": "houdini-apprentice-noncommercial",
            "commercial_use": False,
            "engine_export_allowed": False,
            "file_extension": ".hdanc",
        },
        "cook_budget": {
            "max_points": 3_000_000,
            "max_primitives": 3_000_000,
            "max_memory_bytes": 536_870_912,
            "max_seconds": 90,
            "max_frames": 1,
        },
        "selection": {"method": "human", "automatic_ranking": False},
    }


def _validate_identity(namespace: str, name: str, version: str) -> None:
    if not _SAFE_NAME.fullmatch(namespace):
        raise ValueError("namespace must be a safe identifier")
    if not _SAFE_NAME.fullmatch(name):
        raise ValueError("name must be a safe identifier")
    if not _SAFE_VERSION.fullmatch(version):
        raise ValueError("version must be '<major>.<minor>'")


def build(
    namespace: str = "hermes",
    name: str = "fractal_relic",
    version: str = HDA_VERSION,
    dest_dir: str = "",
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build and install the HDA definition, optionally writing one `.hdanc` artifact."""
    _validate_identity(namespace, name, version)
    hou = get_hou()
    type_name = f"{namespace}::{name}::{version}"
    hda_file = ""
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
        hda_file = os.path.join(dest_dir, f"{namespace}_{name}_{version.replace('.', '_')}.hdanc")
        if os.path.exists(hda_file) and not overwrite:
            raise FileExistsError(f"HDA output exists and overwrite is disabled: {hda_file}")

    obj = hou.node("/obj")
    container = obj.createNode(
        "geo",
        node_name="HERMES_RELIC_BUILD_CONTAINER",
        run_init_scripts=False,
        exact_type_name=True,
    )
    subnet = container.createNode("subnet", node_name="HERMES_RELIC_BUILD", exact_type_name=True)
    try:
        graph = build_graph_spec(parent_path=subnet.path())
        refs = _instantiate_operations(subnet, graph["operations"], type_name)
        subnet.setParmTemplateGroup(_parameter_templates(hou))
        _wire_promoted_controls(refs, hou)

        output_mode = subnet.createNode("switch", node_name="HDA_OUTPUT_MODE", exact_type_name=True)
        output_mode.setPosition((1.0, -10.0))
        output_mode.setInput(0, refs["out_geo"])
        output_mode.setInput(1, refs["out_comparison"])
        _expression(output_mode, "input", 'ch("../output_mode")', hou)
        output_mode.setUserData("hermes_id", make_id("Sop", f"hda:{type_name}:output_mode"))
        output_mode.setUserData("hermes_role", "asset_output_mode")
        output_mode.setUserData("hermes_created_by", f"hda:{type_name}")

        output = subnet.createNode("null", node_name="HDA_OUTPUT", exact_type_name=True)
        output.setPosition((1.0, -12.0))
        output.setInput(0, output_mode)
        output.setDisplayFlag(True)
        output.setRenderFlag(True)
        output.setUserData("hermes_id", make_id("Sop", f"hda:{type_name}:output"))
        output.setUserData("hermes_role", "asset_output")
        output.setUserData("hermes_created_by", f"hda:{type_name}")
        refs["out_comparison"].setDisplayFlag(False)
        refs["out_geo"].setRenderFlag(False)

        asset = subnet.createDigitalAsset(
            name=type_name,
            hda_file_name=hda_file or None,
            description="Hermes Fractal Relic",
            min_num_inputs=0,
            max_num_inputs=0,
            save_as_embedded=not bool(hda_file),
            create_backup=False,
        )
        definition = asset.type().definition()
        if definition is None:
            raise RuntimeError("digital asset definition was not created")
        definition.setParmTemplateGroup(_parameter_templates(hou), create_backup=False)
        definition.addSection("Help", HELP_TEXT)
        definition.addSection(
            "hermes_manifest.json",
            json.dumps(_manifest_document(type_name), indent=2, sort_keys=True),
        )
        asset.setUserData("hermes_id", make_id("Sop", f"hda:{type_name}:asset"))
        asset.setUserData("hermes_role", "fractal_relic_asset")
        asset.setUserData("hermes_created_by", f"hda:{type_name}")
        asset.setUserData("hermes_license", "noncommercial")
        asset.setUserData("hermes_recipe", f"{RECIPE_ID}@{RECIPE_VERSION}")
        asset.setUserData("hermes_skill", "model.fractal_relic@1.1.0")
        definition.updateFromNode(asset)
        asset.matchCurrentDefinition()
        parameter_names = sorted(
            template.name() for template in definition.parmTemplateGroup().entriesWithoutFolders()
        )
        return {
            "type_name": type_name,
            "hda_file": hda_file or None,
            "node_path": asset.path(),
            "noncommercial": True,
            "recipe": f"{RECIPE_ID}@{RECIPE_VERSION}",
            "parameter_names": parameter_names,
            "graph_nodes": len(asset.children()),
            "definition_sections": sorted(definition.sections()),
        }
    except Exception:
        if container.parent() is not None:
            container.destroy()
        raise


def upgrade_from_v1(source: Any, target: Any) -> dict[str, Any]:
    """Copy the three compatible v1 controls without deleting or replacing the source node."""
    if target.type().name() != "hermes::fractal_relic::2.0":
        raise ValueError("target must be hermes::fractal_relic::2.0")
    transferred: dict[str, Any] = {}
    for name in ("seed", "iterations", "detail_level"):
        source_parm = source.parm(name)
        target_parm = target.parm(name)
        if source_parm is None or target_parm is None:
            continue
        value = source_parm.eval()
        target_parm.set(value)
        transferred[name] = value
    target.setUserData("hermes_upgraded_from", source.type().name())
    return {"source": source.path(), "target": target.path(), "transferred": transferred}


__all__ = [
    "HDA_VERSION",
    "HELP_TEXT",
    "RECIPE_ID",
    "RECIPE_VERSION",
    "build",
    "upgrade_from_v1",
]
