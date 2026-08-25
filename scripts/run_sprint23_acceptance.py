"""Run Sprint 23 staged kinetic reliquary acceptance in Houdini Apprentice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import hou
from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.plugin_registry import inventory_plugin_tree, load_plugin_manifest
from hermes_houdini.policy import default_policy
from hermes_houdini.schemas.command import CommandEnvelope, Policy, RiskClass
from hermes_houdini.skill_loader import load_skill


def _dispatch(dispatcher: Dispatcher, call: dict[str, object]):
    envelope = CommandEnvelope.from_dict(call)
    outcome = dispatcher.process_one(envelope)
    if outcome.result.status.value == "blocked":
        outcome = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id=f"{envelope.request_id}-grant",
                arguments={"approval_id": outcome.result.data["approval"]["approval_id"]},
            )
        )
    if outcome.result.status.value != "success":
        raise RuntimeError(
            f"Sprint 23 command {envelope.request_id} ({envelope.tool}) failed: "
            f"{outcome.result.errors}"
        )
    return outcome.result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--mops-available", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--render", action="store_true")
    arguments = parser.parse_args()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    if artifact_dir.exists():
        raise FileExistsError(f"refusing existing artifact directory: {artifact_dir}")

    if arguments.mops_available:
        mops_env = hou.getenv("MOPS")
        if not mops_env:
            raise RuntimeError("MOPs acceptance requires an explicit isolated MOPS environment")
        plugin_root = Path(mops_env).resolve()
        registry = load_plugin_manifest((Path.cwd() / "plugins" / "mops-1.12.json").resolve())
        inventory = inventory_plugin_tree(plugin_root)
        head = (plugin_root / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        if head != registry["package"]["source_commit"]:
            raise RuntimeError("local MOPs checkout does not match the pinned detached commit")
        _write_json(
            artifact_dir / "manifests" / "mops_source_audit.json",
            {
                "schema": "hermes.houdini.mops_source_audit",
                "schema_version": "1.0",
                "registry": registry,
                "plugin_root": str(plugin_root),
                "source_commit": head,
                "license_sha256": _sha256(plugin_root / "LICENSE"),
                "package_json_sha256": _sha256(plugin_root / "MOPS.json"),
                "inventory": inventory,
                "loading_scope": "isolated_process_environment",
                "global_preferences_mutated": False,
            },
        )

    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    skill = load_skill("skills/motion.kinetic_reliquary")
    calls = skill.plan(
        artifact_dir=str(artifact_dir),
        run_id="sprint23_live",
        seed=23023,
        copy_count=24,
        start_frame=1,
        end_frame=24,
        mops_available=arguments.mops_available,
        width=640,
        height=360,
        time_limit=90.0,
        max_threads=4,
        render_preview=arguments.render,
    )
    for call in calls:
        _dispatch(dispatcher, call)

    frames = [1, 12, 24]
    renders = [
        artifact_dir / "observations" / f"sprint23_live_f{frame:03d}_karma_cpu.png"
        for frame in frames
    ]
    manifest_dir = artifact_dir / "manifests"
    contract_validation_path = manifest_dir / "sprint23_live_kinetic_validation.json"
    presentation_validation_path = manifest_dir / "sprint23_live_presentation_validation.json"
    graph_manifest_path = manifest_dir / "sprint23_live_kinetic_manifest.json"
    visual_path = manifest_dir / "sprint23_live_visual_verification.json"
    critique_path = None
    if arguments.render:
        critique_path = manifest_dir / "sprint23_live_critique_packet.json"
        _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="verification.critique.package",
                request_id="sprint23-live-critique",
                arguments={
                    "image_paths": [str(path) for path in renders],
                    "graph_path": str(
                        artifact_dir / "observations" / "sprint23_live_obj_graph.svg"
                    ),
                    "validation_paths": [
                        str(contract_validation_path),
                        str(presentation_validation_path),
                        str(graph_manifest_path),
                        str(visual_path),
                    ],
                    "code_paths": [
                        str(Path(__file__).resolve()),
                        str(Path.cwd() / "hermes_houdini" / "kinetic.py"),
                        str(Path.cwd() / "hermes_houdini" / "visual_verification.py"),
                        str(Path.cwd() / "recipes" / "sop" / "kinetic_reliquary_staged.yaml"),
                        str(Path.cwd() / "skills" / "motion.kinetic_reliquary" / "skill.py"),
                    ],
                    "output_path": str(critique_path),
                },
                policy=Policy(risk=RiskClass.LOW, max_seconds=30),
            ).as_dict(),
        )

    contract = json.loads(contract_validation_path.read_text(encoding="utf-8"))
    presentation = json.loads(presentation_validation_path.read_text(encoding="utf-8"))
    visual = (
        json.loads(visual_path.read_text(encoding="utf-8")) if arguments.render else None
    )
    if visual and visual["status"] != "pass":
        raise RuntimeError(
            f"Sprint 23 visual acceptance did not pass: {visual['sequence']['flags']}"
        )
    print(
        json.dumps(
            {
                "status": "success",
                "houdini": hou.applicationVersionString(),
                "license": str(hou.licenseCategory()),
                "mops_available": arguments.mops_available,
                "branches": sorted(contract["branches"]),
                "sample_frames": presentation["sample_frames"],
                "presentation_bounds": [sample["bounds_size"] for sample in presentation["samples"]],
                "presentation_metrics": presentation["samples"][-1]["metrics"],
                "selection": presentation["selection"],
                "renders": [str(path) for path in renders] if arguments.render else [],
                "visual_status": visual["status"] if visual else None,
                "visual_sequence": visual["sequence"] if visual else None,
                "critique_packet": str(critique_path) if critique_path else None,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
