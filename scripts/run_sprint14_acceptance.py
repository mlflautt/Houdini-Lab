"""Run the bounded Sprint 14 MPM acceptance and optional Karma proof.

This script is intended for the pinned Houdini 22 ``hython`` executable. It starts from
the process's new unsaved scene, refuses an existing artifact directory, and never clears
or overwrites artist data.
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
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--camera-y", type=float, default=5.2)
    arguments = parser.parse_args()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    if artifact_dir.exists():
        raise FileExistsError(f"refusing existing artifact directory: {artifact_dir}")
    if not 2 <= arguments.frames <= 24:
        raise ValueError("--frames must be between 2 and 24")

    obj = hou.node("/obj")
    if obj.node("HERMES_SPRINT14_ACCEPTANCE") is not None:
        raise FileExistsError("HERMES_SPRINT14_ACCEPTANCE already exists")
    geo = obj.createNode("geo", node_name="HERMES_SPRINT14_ACCEPTANCE", run_init_scripts=False)
    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    mpm_skill = load_skill("skills/simulate.mpm_matter_sculpture")
    mpm_calls = mpm_skill.plan(
        parent_node_id=geo.path(),
        artifact_dir=str(artifact_dir),
        run_id="sprint14_live",
        seed=1414,
        start_frame=1,
        end_frame=arguments.frames,
        particle_separation=0.12,
        source_radius=0.62,
        source_height=2.4,
        noise_height=0.08,
        substep_min=1,
        substep_max=32,
        output_mode="points",
        max_particles=150_000,
    )
    mpm_results = [_dispatch(dispatcher, call) for call in mpm_calls]
    _require_success(mpm_results)

    render_path = None
    visual_path = None
    critique_path = None
    if arguments.render:
        hou.setFrame(arguments.frames)
        lookdev_skill = load_skill("skills/lookdev.relic_stage")
        lookdev_calls = lookdev_skill.plan(
            source_sop_path=f"{geo.path()}/OUT_SPRINT14_LIVE_SELECTED",
            artifact_dir=str(artifact_dir),
            run_id="sprint14_lookdev",
            candidate_index=1,
            width=768,
            height=432,
            frame=float(arguments.frames),
            time_limit=60.0,
            max_threads=4,
            render_preview=True,
        )
        lookdev_results = [_dispatch(dispatcher, lookdev_calls[0])]
        camera_call = CommandEnvelope(
            tool="node.set_parameter",
            request_id="sprint14-camera-refine",
            arguments={
                "path": "/stage/SPRINT14_LOOKDEV_CAMERA",
                "name": "ty",
                "value": arguments.camera_y,
            },
            policy=Policy(risk=RiskClass.LOW, max_seconds=30),
        ).as_dict()
        lookdev_results.append(_dispatch(dispatcher, camera_call))
        lookdev_results.extend(_dispatch(dispatcher, call) for call in lookdev_calls[1:])
        _require_success(lookdev_results)
        render_path = artifact_dir / "observations" / "sprint14_lookdev_karma_cpu.png"
        visual_path = artifact_dir / "manifests" / "sprint14_visual_verification.json"
        visual_call = CommandEnvelope(
            tool="visual.analyze",
            request_id="sprint14-visual-analysis",
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
        ).as_dict()
        visual_result = _dispatch(dispatcher, visual_call)
        _require_success([visual_result])
        critique_path = artifact_dir / "manifests" / "sprint14_critique_packet.json"
        critique_call = CommandEnvelope(
            tool="verification.critique.package",
            request_id="sprint14-critique-packet",
            arguments={
                "image_paths": [str(render_path)],
                "graph_path": str(artifact_dir / "observations" / "sprint14_live_graph.svg"),
                "validation_paths": [
                    str(artifact_dir / "manifests" / "sprint14_live_mpm_validation.json"),
                    str(artifact_dir / "manifests" / "sprint14_live_cache_progress.json"),
                    str(artifact_dir / "manifests" / "sprint14_live_graph_manifest.json"),
                    str(artifact_dir / "manifests" / "sprint14_lookdev_lookdev_manifest.json"),
                    str(visual_path),
                ],
                "code_paths": [
                    str(Path(__file__).resolve()),
                    str(Path(__file__).resolve().parents[1] / "hermes_houdini" / "mpm.py"),
                    str(
                        Path(__file__).resolve().parents[1]
                        / "recipes"
                        / "sop"
                        / "mpm_matter_sculpture.yaml"
                    ),
                    str(
                        Path(__file__).resolve().parents[1]
                        / "skills"
                        / "simulate.mpm_matter_sculpture"
                        / "skill.py"
                    ),
                ],
                "output_path": str(critique_path),
            },
            policy=Policy(risk=RiskClass.LOW, max_seconds=30),
        ).as_dict()
        critique_result = _dispatch(dispatcher, critique_call)
        _require_success([critique_result])

    validation_path = artifact_dir / "manifests" / "sprint14_live_mpm_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": "success",
                "houdini": hou.applicationVersionString(),
                "license": str(hou.licenseCategory()),
                "frames": len(validation["frames"]),
                "final_particles": validation["frames"][-1]["metrics"]["points"],
                "centroid_motion": validation["centroid_motion"],
                "elapsed_seconds": validation["elapsed_seconds"],
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
