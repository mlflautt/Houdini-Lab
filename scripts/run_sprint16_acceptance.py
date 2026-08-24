"""Run bounded Sprint 16 district acceptance and optional Karma CPU proof.

The script starts from a new Houdini scene, refuses an existing artifact directory, and
executes only the skill's explicit approval-aware commands. It is intended for pinned hython.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import hou
from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.policy import default_policy
from hermes_houdini.schemas.command import CommandEnvelope, Policy, RiskClass
from hermes_houdini.skill_loader import load_skill


def _dispatch(dispatcher: Dispatcher, call: dict[str, object]):
    envelope = CommandEnvelope.from_dict(call)
    outcome = dispatcher.process_one(envelope)
    if outcome.result.status.value != "blocked":
        return outcome.result
    approval_id = outcome.result.data["approval"]["approval_id"]
    return dispatcher.process_one(
        CommandEnvelope(
            tool="approval.grant",
            request_id=f"{envelope.request_id}-grant",
            arguments={"approval_id": approval_id},
        )
    ).result


def _require_success(results) -> None:
    failures = [result.errors for result in results if result.status.value != "success"]
    if failures:
        raise RuntimeError(f"acceptance command failed: {failures}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--lots", type=int, default=12)
    arguments = parser.parse_args()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    if artifact_dir.exists():
        raise FileExistsError(f"refusing existing artifact directory: {artifact_dir}")
    if not 4 <= arguments.lots <= 16:
        raise ValueError("--lots must be between 4 and 16")

    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    district_skill = load_skill("skills/world.procedural_district")
    district_calls = district_skill.plan(
        artifact_dir=str(artifact_dir),
        run_id="sprint16_live",
        base_seed=1616,
        lot_count=arguments.lots,
        seed_step=53,
        columns=4,
        lot_spacing=6.0,
    )
    district_results = [_dispatch(dispatcher, call) for call in district_calls]
    _require_success(district_results)

    render_path = None
    visual_path = None
    critique_path = None
    if arguments.render:
        source_path = "/obj/HERMES_DISTRICT_SPRINT16_LIVE/OUT_DISTRICT"
        lookdev_skill = load_skill("skills/lookdev.relic_stage")
        lookdev_calls = lookdev_skill.plan(
            source_sop_path=source_path,
            artifact_dir=str(artifact_dir),
            run_id="sprint16_lookdev",
            candidate_index=2,
            width=768,
            height=432,
            frame=1.0,
            time_limit=90.0,
            max_threads=4,
            render_preview=True,
        )
        lookdev_results = [_dispatch(dispatcher, lookdev_calls[0])]
        camera_values = {
            "tx": 66.0,
            "ty": 46.0,
            "tz": 86.0,
            "rx": -20.0,
            "ry": 36.9,
            "focalLength": 44.0,
        }
        for name, value in camera_values.items():
            lookdev_results.append(
                _dispatch(
                    dispatcher,
                    CommandEnvelope(
                        tool="node.set_parameter",
                        request_id=f"sprint16-camera-{name}",
                        arguments={
                            "path": "/stage/SPRINT16_LOOKDEV_CAMERA",
                            "name": name,
                            "value": value,
                        },
                        policy=Policy(risk=RiskClass.LOW, max_seconds=30),
                    ).as_dict(),
                )
            )
        lookdev_results.extend(_dispatch(dispatcher, call) for call in lookdev_calls[1:])
        _require_success(lookdev_results)
        render_path = artifact_dir / "observations" / "sprint16_lookdev_karma_cpu.png"
        visual_path = artifact_dir / "manifests" / "sprint16_visual_verification.json"
        visual_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="visual.analyze",
                request_id="sprint16-visual-analysis",
                arguments={
                    "image_paths": [str(render_path)],
                    "output_path": str(visual_path),
                    "panel_count": 1,
                },
                policy=Policy(
                    risk=RiskClass.LOW,
                    max_seconds=30,
                    max_resolution=(768, 432),
                ),
            ).as_dict(),
        )
        _require_success([visual_result])
        critique_path = artifact_dir / "manifests" / "sprint16_critique_packet.json"
        critique_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="verification.critique.package",
                request_id="sprint16-critique-packet",
                arguments={
                    "image_paths": [str(render_path)],
                    "graph_path": str(
                        artifact_dir / "observations" / "sprint16_live_assembly_graph.svg"
                    ),
                    "validation_paths": [
                        str(artifact_dir / "manifests" / "sprint16_live_district_validation.json"),
                        str(artifact_dir / "manifests" / "sprint16_live_graph_manifest.json"),
                        str(visual_path),
                    ],
                    "code_paths": [
                        str(Path(__file__).resolve()),
                        str(Path(__file__).resolve().parents[1] / "hermes_houdini" / "district.py"),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "recipes"
                            / "top"
                            / "procedural_district.yaml"
                        ),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "skills"
                            / "world.procedural_district"
                            / "skill.py"
                        ),
                    ],
                    "output_path": str(critique_path),
                },
                policy=Policy(risk=RiskClass.LOW, max_seconds=30),
            ).as_dict(),
        )
        _require_success([critique_result])

    validation_path = artifact_dir / "manifests" / "sprint16_live_district_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    result_path = artifact_dir / "manifests" / "sprint16_live_district_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": "success",
                "houdini": hou.applicationVersionString(),
                "license": str(hou.licenseCategory()),
                "lots": len(result["candidates"]),
                "profiles": validation["profiles"],
                "cache_total_bytes": validation["cache_total_bytes"],
                "district_metrics": validation["district_metrics"],
                "gallery_metrics": validation["gallery_metrics"],
                "pdg_elapsed_seconds": result["elapsed_seconds"],
                "validation": str(validation_path),
                "render": str(render_path) if render_path else None,
                "visual": str(visual_path) if visual_path else None,
                "critique_packet": str(critique_path) if critique_path else None,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
