"""Run bounded Sprint 17 native RBD acceptance and optional Karma CPU proof."""

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
    parser.add_argument("--profile", type=int, default=0)
    arguments = parser.parse_args()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    if artifact_dir.exists():
        raise FileExistsError(f"refusing existing artifact directory: {artifact_dir}")
    if arguments.profile not in {0, 1, 2}:
        raise ValueError("--profile must be 0, 1, or 2")

    hou.hipFile.clear(suppress_save_prompt=True)
    network = hou.node("/obj").createNode("geo", "HERMES_RBD_SPRINT17_LIVE")
    for child in network.children():
        child.destroy()
    network.setUserData("hermes_id", "sop:sprint17:rbd-live")
    network.setUserData("hermes_role", "rbd_acceptance_network")
    network.setUserData("hermes_created_by", "scripts/run_sprint17_acceptance.py")

    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    skill = load_skill("skills/simulate.rbd_art_directed_fracture")
    calls = skill.plan(
        parent_node_id=network.path(),
        artifact_dir=str(artifact_dir),
        run_id="sprint17_live",
        seed=1717,
        start_frame=1,
        end_frame=48,
        profile_index=arguments.profile,
    )
    results = [_dispatch(dispatcher, call) for call in calls]
    _require_success(results)

    render_path = None
    visual_path = None
    critique_path = None
    if arguments.render:
        hou.setFrame(48)
        source_path = f"{network.path()}/OUT_SPRINT17_LIVE_COMPARE"
        lookdev = load_skill("skills/lookdev.relic_stage")
        lookdev_calls = lookdev.plan(
            source_sop_path=source_path,
            artifact_dir=str(artifact_dir),
            run_id="sprint17_lookdev",
            candidate_index=0,
            width=768,
            height=432,
            frame=48.0,
            time_limit=90.0,
            max_threads=4,
            render_preview=True,
        )
        lookdev_results = [_dispatch(dispatcher, lookdev_calls[0])]
        camera_values = {
            "tx": 20.0,
            "ty": 12.5,
            "tz": 24.0,
            "rx": -15.0,
            "ry": 39.0,
            "focalLength": 52.0,
        }
        for name, value in camera_values.items():
            lookdev_results.append(
                _dispatch(
                    dispatcher,
                    CommandEnvelope(
                        tool="node.set_parameter",
                        request_id=f"sprint17-camera-{name}",
                        arguments={
                            "path": "/stage/SPRINT17_LOOKDEV_CAMERA",
                            "name": name,
                            "value": value,
                        },
                        policy=Policy(risk=RiskClass.LOW, max_seconds=30),
                    ).as_dict(),
                )
            )
        lookdev_results.extend(_dispatch(dispatcher, call) for call in lookdev_calls[1:])
        _require_success(lookdev_results)
        render_path = artifact_dir / "observations" / "sprint17_lookdev_karma_cpu.png"
        visual_path = artifact_dir / "manifests" / "sprint17_visual_verification.json"
        visual_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="visual.analyze",
                request_id="sprint17-visual-analysis",
                arguments={
                    "image_paths": [str(render_path)],
                    "output_path": str(visual_path),
                    "panel_count": 2,
                },
                policy=Policy(
                    risk=RiskClass.LOW,
                    max_seconds=30,
                    max_resolution=(768, 432),
                ),
            ).as_dict(),
        )
        _require_success([visual_result])
        critique_path = artifact_dir / "manifests" / "sprint17_critique_packet.json"
        critique_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="verification.critique.package",
                request_id="sprint17-critique-packet",
                arguments={
                    "image_paths": [str(render_path)],
                    "graph_path": str(artifact_dir / "observations" / "sprint17_live_graph.svg"),
                    "validation_paths": [
                        str(artifact_dir / "manifests" / "sprint17_live_rbd_validation.json"),
                        str(artifact_dir / "manifests" / "sprint17_live_graph_manifest.json"),
                        str(visual_path),
                    ],
                    "code_paths": [
                        str(Path(__file__).resolve()),
                        str(Path(__file__).resolve().parents[1] / "hermes_houdini" / "rbd.py"),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "recipes"
                            / "sop"
                            / "rbd_art_directed_fracture.yaml"
                        ),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "skills"
                            / "simulate.rbd_art_directed_fracture"
                            / "skill.py"
                        ),
                    ],
                    "output_path": str(critique_path),
                },
                policy=Policy(risk=RiskClass.LOW, max_seconds=30),
            ).as_dict(),
        )
        _require_success([critique_result])

    validation_path = artifact_dir / "manifests" / "sprint17_live_rbd_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": "success",
                "houdini": hou.applicationVersionString(),
                "license": str(hou.licenseCategory()),
                "profile": validation["spec"]["profile"],
                "piece_count": validation["piece_count"],
                "initial_constraints": validation["initial_constraints"],
                "broken_constraints": validation["broken_constraints"],
                "vertical_drop": validation["vertical_drop"],
                "frames": len(validation["frames"]),
                "transform_cache": validation["transform_cache"],
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
