"""Run bounded Sprint 19 native World Seed Atlas acceptance and visual QA."""

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
    return dispatcher.process_one(
        CommandEnvelope(
            tool="approval.grant",
            request_id=f"{envelope.request_id}-grant",
            arguments={"approval_id": outcome.result.data["approval"]["approval_id"]},
        )
    ).result


def _require_success(results) -> None:
    failures = [result.errors for result in results if result.status.value != "success"]
    if failures:
        raise RuntimeError(f"Sprint 19 acceptance command failed: {failures}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--terrain-samples", type=int, default=128)
    parser.add_argument("--render", action="store_true")
    arguments = parser.parse_args()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    if artifact_dir.exists():
        raise FileExistsError(f"refusing existing artifact directory: {artifact_dir}")

    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    skill = load_skill("skills/world.world_seed_atlas")
    calls = skill.plan(
        artifact_dir=str(artifact_dir),
        run_id="sprint19_live",
        base_seed=19019,
        terrain_samples=arguments.terrain_samples,
        world_size=9.0,
        width=768,
        height=432,
        frame=1.0,
        time_limit=120.0,
        max_threads=4,
        render_preview=arguments.render,
    )
    results = [_dispatch(dispatcher, call) for call in calls]
    _require_success(results)

    render = artifact_dir / "observations" / "sprint19_live_karma_cpu.png"
    visual = None
    critique = None
    if arguments.render:
        visual = artifact_dir / "manifests" / "sprint19_live_visual_verification.json"
        visual_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="visual.analyze",
                request_id="sprint19-live-visual",
                arguments={
                    "image_paths": [str(render)],
                    "output_path": str(visual),
                    "panel_count": 3,
                },
                policy=Policy(
                    risk=RiskClass.LOW,
                    max_seconds=30,
                    max_resolution=(768, 432),
                ),
            ).as_dict(),
        )
        _require_success([visual_result])
        critique = artifact_dir / "manifests" / "sprint19_live_critique_packet.json"
        critique_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="verification.critique.package",
                request_id="sprint19-live-critique",
                arguments={
                    "image_paths": [str(render)],
                    "graph_path": str(
                        artifact_dir / "observations" / "sprint19_live_lop_graph.svg"
                    ),
                    "validation_paths": [
                        str(artifact_dir / "manifests" / "sprint19_live_world_validation.json"),
                        str(artifact_dir / "manifests" / "sprint19_live_world_seed_manifest.json"),
                        str(visual),
                    ],
                    "code_paths": [
                        str(Path(__file__).resolve()),
                        str(
                            Path(__file__).resolve().parents[1] / "hermes_houdini" / "world_seed.py"
                        ),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "recipes"
                            / "sop"
                            / "world_seed_biome.yaml"
                        ),
                        str(
                            Path(__file__).resolve().parents[1]
                            / "skills"
                            / "world.world_seed_atlas"
                            / "skill.py"
                        ),
                    ],
                    "output_path": str(critique),
                },
                policy=Policy(risk=RiskClass.LOW, max_seconds=30),
            ).as_dict(),
        )
        _require_success([critique_result])

    validation_path = artifact_dir / "manifests" / "sprint19_live_world_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": "success",
                "houdini": hou.applicationVersionString(),
                "license": str(hou.licenseCategory()),
                "terrain_samples": validation["spec"]["terrain_samples"],
                "candidates": [item["id"] for item in validation["candidates"]],
                "total_points": validation["total_points"],
                "total_primitives": validation["total_primitives"],
                "selection": validation["selection"],
                "validation": str(validation_path),
                "render": str(render) if arguments.render else None,
                "visual": str(visual) if visual else None,
                "critique_packet": str(critique) if critique else None,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
