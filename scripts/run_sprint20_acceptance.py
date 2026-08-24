"""Run bounded SideFX Labs 22.0.368 fixture, rollback, render, and evidence acceptance."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import hou
from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.plugin_registry import audit_package_json, inventory_plugin_tree
from hermes_houdini.policy import default_policy
from hermes_houdini.schemas.command import CommandEnvelope, Policy, RiskClass

RUN_CODE = "SPRINT20_LABS"
NETWORK_PATH = f"/obj/{RUN_CODE}_ACCEPTANCE"
GALLERY_PATH = f"{NETWORK_PATH}/OUT_{RUN_CODE}_GALLERY"
STAGE_PATH = f"/stage/OUT_{RUN_CODE}_STAGE"
ROP_PATH = f"/out/{RUN_CODE}_KARMA_PREVIEW"
CERTIFIED = {
    "artifact_mesh_utility": {
        "node": f"{NETWORK_PATH}/{RUN_CODE}_LABS_CURVATURE",
        "output": f"{NETWORK_PATH}/OUT_{RUN_CODE}_ARTIFACT",
        "type": "labs::measure_curvature::3.1",
        "attributes": {"Cd", "concavity", "convexity"},
    },
    "terrain_cartography_utility": {
        "node": f"{NETWORK_PATH}/{RUN_CODE}_LABS_TERRAIN_ANALYSIS",
        "output": f"{NETWORK_PATH}/OUT_{RUN_CODE}_TERRAIN",
        "type": "labs::terrain_analysis::1.0",
        "attributes": {"Cd", "slope"},
    },
    "motion_instancing_utility": {
        "node": f"{NETWORK_PATH}/{RUN_CODE}_LABS_INSTANCE_ATTRIBUTES",
        "output": f"{NETWORK_PATH}/OUT_{RUN_CODE}_INSTANCES",
        "type": "labs::instance_attributes::1.0",
        "attributes": {"orient", "pscale", "scale"},
    },
}


def _dispatch(dispatcher: Dispatcher, envelope: CommandEnvelope):
    outcome = dispatcher.process_one(envelope)
    if outcome.result.status.value != "blocked":
        return outcome.result
    approval = outcome.result.data["approval"]["approval_id"]
    return dispatcher.process_one(
        CommandEnvelope(
            tool="approval.grant",
            request_id=f"{envelope.request_id}-grant",
            arguments={"approval_id": approval},
        )
    ).result


def _require_success(*results) -> None:
    failures = [result.errors for result in results if result.status.value != "success"]
    if failures:
        raise RuntimeError(f"Sprint 20 command failed: {failures}")


def _envelope(
    tool: str, request_id: str, arguments: dict[str, Any], policy: Policy
) -> CommandEnvelope:
    return CommandEnvelope(
        tool=tool,
        request_id=request_id,
        arguments=arguments,
        policy=policy,
        session_id="sprint20_live",
        project_id="system.sidefx_labs_acceptance",
        expected={"sprint": 20, "run_id": "sprint20_live"},
    )


def _metrics(node: hou.SopNode) -> dict[str, Any]:
    geometry = node.geometry()
    bounds = geometry.boundingBox()
    return {
        "points": int(geometry.intrinsicValue("pointcount")),
        "primitives": int(geometry.intrinsicValue("primitivecount")),
        "memory_bytes": int(geometry.intrinsicValue("memoryusage")),
        "point_attributes": sorted(attribute.name() for attribute in geometry.pointAttribs()),
        "primitive_attributes": sorted(attribute.name() for attribute in geometry.primAttribs()),
        "bounds_min": list(bounds.minvec()),
        "bounds_max": list(bounds.maxvec()),
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def _validate_fixtures(output_path: Path) -> dict[str, Any]:
    results = []
    total_points = 0
    total_primitives = 0
    for fixture_id, contract in CERTIFIED.items():
        node = hou.node(contract["node"])
        output = hou.node(contract["output"])
        if node is None or output is None:
            raise RuntimeError(f"fixture {fixture_id} has a missing contract node")
        if node.type().name() != contract["type"]:
            raise RuntimeError(f"fixture {fixture_id} resolved the wrong Labs node type")
        if node.userData("hermes_role") is None or node.input(0) is None:
            raise RuntimeError(f"fixture {fixture_id} is untagged or disconnected")
        started = time.monotonic()
        node.cook(force=True)
        output.cook(force=True)
        seconds = time.monotonic() - started
        errors = list(node.errors()) + list(output.errors())
        warnings = list(node.warnings()) + list(output.warnings())
        if errors or warnings:
            raise RuntimeError(f"fixture {fixture_id} produced Houdini messages: {errors + warnings}")
        node_metrics = _metrics(node)
        output_metrics = _metrics(output)
        missing = contract["attributes"] - set(node_metrics["point_attributes"])
        if missing:
            raise RuntimeError(f"fixture {fixture_id} is missing attributes: {sorted(missing)}")
        if node_metrics["points"] <= 0 or node_metrics["points"] > 100_000:
            raise RuntimeError(f"fixture {fixture_id} violates its 100000-point budget")
        if output_metrics["primitives"] <= 0 or output_metrics["points"] > 100_000:
            raise RuntimeError(f"fixture {fixture_id} produced an invalid visual contract")
        if seconds > 30.0:
            raise RuntimeError(f"fixture {fixture_id} violates its 30-second budget")
        total_points += int(output_metrics["points"])
        total_primitives += int(output_metrics["primitives"])
        results.append(
            {
                "id": fixture_id,
                "labs_node_path": node.path(),
                "labs_node_type": node.type().name(),
                "labs_role": node.userData("hermes_role"),
                "input_path": node.input(0).path(),
                "output_path": output.path(),
                "seconds": round(seconds, 6),
                "labs_metrics": node_metrics,
                "visual_contract_metrics": output_metrics,
                "errors": errors,
                "warnings": warnings,
                "human_rating": None,
                "automatic_rank": None,
            }
        )
    gallery = hou.node(GALLERY_PATH)
    if gallery is None:
        raise RuntimeError("Labs gallery output is missing")
    gallery.cook(force=True)
    gallery_metrics = _metrics(gallery)
    report = {
        "schema": "hermes.houdini.sidefx_labs_fixture_acceptance",
        "schema_version": "1.0",
        "houdini_version": hou.applicationVersionString(),
        "license_mode": str(hou.licenseCategory()),
        "plugin": "SideFXLabs22.0@22.0.368",
        "certification_scope": "three_exact_node_types_only",
        "fixtures": results,
        "gallery_metrics": gallery_metrics,
        "fixture_output_totals": {"points": total_points, "primitives": total_primitives},
        "selection": {"winner": None, "human_selection_required": True},
    }
    _write_json(output_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    artifacts = Path(args.artifact_dir).expanduser()
    if not artifacts.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    if artifacts.exists():
        raise FileExistsError(f"refusing existing artifact directory: {artifacts}")
    for name in ("checkpoints", "logs", "manifests", "observations", "scenes"):
        (artifacts / name).mkdir(parents=True, exist_ok=False)

    preference_root = Path(hou.getenv("HOUDINI_USER_PREF_DIR"))
    package_dir = preference_root / "packages"
    package_json = package_dir / "SideFXLabs22.0.json"
    plugin_root = package_dir / "SideFXLabs22.0"
    package_audit = audit_package_json(
        package_json, plugin_root=plugin_root, expected_name="SideFXLabs22.0"
    )
    tree_inventory = inventory_plugin_tree(plugin_root)
    _write_json(artifacts / "manifests" / "installed_package_audit.json", package_audit)
    _write_json(artifacts / "manifests" / "installed_tree_inventory.json", tree_inventory)

    hou.hipFile.clear(suppress_save_prompt=True)
    dispatcher = Dispatcher(policy=default_policy([str(artifacts)]))
    graph_policy = Policy(
        risk=RiskClass.MEDIUM,
        max_seconds=90,
        max_points=100_000,
        max_primitives=100_000,
        max_memory_bytes=2_147_483_648,
        max_resolution=(768, 432),
    )
    low_policy = Policy(
        risk=RiskClass.LOW,
        max_seconds=90,
        max_points=100_000,
        max_primitives=100_000,
        max_memory_bytes=2_147_483_648,
        max_resolution=(768, 432),
    )
    create = _dispatch(
        dispatcher,
        _envelope(
            "graph.apply_batch",
            "sprint20-create-network",
            {
                "batch_id": "system.sidefx_labs_acceptance:sprint20_live:network",
                "operations": [
                    {
                        "op": "create",
                        "ref": "labs_acceptance",
                        "parent_path": "/obj",
                        "operator_type": "geo",
                        "name": f"{RUN_CODE}_ACCEPTANCE",
                        "exact_name": True,
                        "category": "Object",
                        "role": "sidefx_labs_acceptance_network",
                        "position": [0.0, 0.0],
                        "parameters": {},
                        "comment": "SideFXLabs22.0@22.0.368; three certified fixtures only",
                    }
                ],
                "checkpoint_dir": str(artifacts / "checkpoints"),
                "log_path": str(artifacts / "logs" / "network.jsonl"),
                "label": "Create Sprint 20 Labs acceptance network",
                "checkpoint_stem": "sprint20_labs_network",
            },
            graph_policy,
        ),
    )
    _require_success(create)
    recipe = _dispatch(
        dispatcher,
        _envelope(
            "recipe.instantiate",
            "sprint20-build-fixtures",
            {
                "recipe_id": "sop.sidefx_labs_acceptance_gallery",
                "version": "1.0.0",
                "parent_path": NETWORK_PATH,
                "batch_id": "system.sidefx_labs_acceptance:sprint20_live:fixtures",
                "checkpoint_dir": str(artifacts / "checkpoints"),
                "log_path": str(artifacts / "logs" / "fixtures.jsonl"),
                "inputs": {"run_code": RUN_CODE},
                "label": "Build three certified Labs fixture branches",
                "checkpoint_stem": "sprint20_labs_fixtures",
            },
            graph_policy,
        ),
    )
    _require_success(recipe)
    validation = _validate_fixtures(artifacts / "manifests" / "fixture_validation.json")

    render_path = artifacts / "observations" / "sprint20_labs_karma_cpu.png"
    stage = _dispatch(
        dispatcher,
        _envelope(
            "recipe.instantiate",
            "sprint20-build-stage",
            {
                "recipe_id": "lop.sidefx_labs_acceptance_stage",
                "version": "1.0.0",
                "parent_path": "/stage",
                "batch_id": "system.sidefx_labs_acceptance:sprint20_live:stage",
                "checkpoint_dir": str(artifacts / "checkpoints"),
                "log_path": str(artifacts / "logs" / "stage.jsonl"),
                "inputs": {
                    "run_code": RUN_CODE,
                    "gallery_sop_path": GALLERY_PATH,
                    "render_picture": str(render_path),
                    "width": 768,
                    "height": 432,
                },
                "label": "Build Sprint 20 Karma proof stage",
                "checkpoint_stem": "sprint20_labs_stage",
            },
            graph_policy,
        ),
    )
    _require_success(stage)

    metadata = {
        "sprint": 20,
        "plugin": {
            "name": "SideFXLabs22.0",
            "version": "22.0.368",
            "archive_sha256": "9a4a0893af760d46b1222b3ffba514846113ca8481e47a65da53b5b3c74e87d5",
            "package_json_sha256": package_audit["package_sha256"],
            "installation_scope": "houdini_user_preferences",
        },
        "certified_node_types": [contract["type"] for contract in CERTIFIED.values()],
        "certification_scope": "three_exact_node_types_only",
        "human_rating": None,
        "automatic_rank": None,
    }
    obj_svg = artifacts / "observations" / "sprint20_labs_obj_graph.svg"
    lop_svg = artifacts / "observations" / "sprint20_labs_lop_graph.svg"
    graph_manifest = artifacts / "manifests" / "sprint20_labs_graph_manifest.json"
    evidence_results = [
        _dispatch(
            dispatcher,
            _envelope(
                "graph.capture_svg",
                "sprint20-obj-svg",
                {"node_path": NETWORK_PATH, "output_path": str(obj_svg), "max_nodes": 64},
                low_policy,
            ),
        ),
        _dispatch(
            dispatcher,
            _envelope(
                "graph.capture_svg",
                "sprint20-lop-svg",
                {"node_path": "/stage", "output_path": str(lop_svg), "max_nodes": 32},
                low_policy,
            ),
        ),
        _dispatch(
            dispatcher,
            _envelope(
                "graph.capture_manifest",
                "sprint20-graph-manifest",
                {
                    "node_path": NETWORK_PATH,
                    "output_path": str(graph_manifest),
                    "public_parameters": {
                        CERTIFIED["artifact_mesh_utility"]["node"]: ["method", "viscolor"],
                        CERTIFIED["terrain_cartography_utility"]["node"]: [
                            "slope",
                            "horizontalcurvature",
                            "visualizeattribute",
                        ],
                        CERTIFIED["motion_instancing_utility"]["node"]: [
                            "pscalemin",
                            "pscalemax",
                            "spinrandseed",
                            "rotrandseed",
                        ],
                    },
                    "metric_node_paths": [GALLERY_PATH],
                    "metadata": metadata,
                },
                low_policy,
            ),
        ),
        _dispatch(
            dispatcher,
            _envelope(
                "hip.save_snapshot",
                "sprint20-save",
                {"output_dir": str(artifacts / "scenes"), "stem": "sidefx_labs_sprint20_final"},
                low_policy,
            ),
        ),
    ]
    _require_success(*evidence_results)

    visual_path = None
    critique_path = None
    if args.render:
        rop = _dispatch(
            dispatcher,
            _envelope(
                "solaris.karma_rop.build",
                "sprint20-build-rop",
                {
                    "stage_node_path": STAGE_PATH,
                    "render_settings_path": f"/Render/{RUN_CODE}_Settings",
                    "output_path": str(render_path),
                    "checkpoint_dir": str(artifacts / "checkpoints"),
                    "log_path": str(artifacts / "logs" / "karma_rop.jsonl"),
                    "node_name": f"{RUN_CODE}_KARMA_PREVIEW",
                    "width": 768,
                    "height": 432,
                    "frame": 1.0,
                    "time_limit": 90.0,
                    "max_threads": 4,
                },
                graph_policy,
            ),
        )
        _require_success(rop)
        render = _dispatch(
            dispatcher,
            _envelope(
                "render.karma.preview",
                "sprint20-render",
                {
                    "rop_path": ROP_PATH,
                    "output_path": str(render_path),
                    "log_path": str(artifacts / "logs" / "karma_render.jsonl"),
                    "frame": 1.0,
                },
                Policy(
                    risk=RiskClass.EXTERNAL,
                    allow_external_process=True,
                    max_seconds=90,
                    max_points=100_000,
                    max_primitives=100_000,
                    max_memory_bytes=2_147_483_648,
                    max_frames=1,
                    max_output_bytes=536_870_912,
                    max_resolution=(768, 432),
                ),
            ),
        )
        _require_success(render)
        visual_path = artifacts / "manifests" / "visual_verification.json"
        visual = _dispatch(
            dispatcher,
            _envelope(
                "visual.analyze",
                "sprint20-visual",
                {
                    "image_paths": [str(render_path)],
                    "output_path": str(visual_path),
                    "panel_count": 3,
                },
                low_policy,
            ),
        )
        _require_success(visual)
        critique_path = artifacts / "manifests" / "critique_packet.json"
        critique = _dispatch(
            dispatcher,
            _envelope(
                "verification.critique.package",
                "sprint20-critique",
                {
                    "image_paths": [str(render_path)],
                    "graph_path": str(obj_svg),
                    "validation_paths": [
                        str(artifacts / "manifests" / "fixture_validation.json"),
                        str(graph_manifest),
                        str(visual_path),
                    ],
                    "code_paths": [
                        str(Path(__file__).resolve()),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "recipes"
                            / "sop"
                            / "sidefx_labs_acceptance_gallery.yaml"
                        ),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "hermes_houdini"
                            / "plugin_registry.py"
                        ),
                    ],
                    "output_path": str(critique_path),
                },
                low_policy,
            ),
        )
        _require_success(critique)

    print(
        json.dumps(
            {
                "status": "success",
                "artifact_dir": str(artifacts),
                "package_audit": package_audit,
                "tree_counts": tree_inventory["counts"],
                "fixtures": validation["fixtures"],
                "gallery_metrics": validation["gallery_metrics"],
                "render": str(render_path) if args.render else None,
                "visual_verification": str(visual_path) if visual_path else None,
                "critique_packet": str(critique_path) if critique_path else None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    hou.exit(exit_code=0, suppress_save_prompt=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
