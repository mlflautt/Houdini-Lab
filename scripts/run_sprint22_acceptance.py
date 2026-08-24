"""Run Sprint 22 native/optional-MOPs kinetic reliquary acceptance."""

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
        raise RuntimeError(f"Sprint 22 acceptance command failed: {failures}")


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
        plugin_audit = {
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
        }
        _write_json(artifact_dir / "manifests" / "mops_source_audit.json", plugin_audit)

    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    skill = load_skill("skills/motion.kinetic_reliquary")
    calls = skill.plan(
        artifact_dir=str(artifact_dir),
        run_id="sprint22_live",
        seed=22012,
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
    results = [_dispatch(dispatcher, call) for call in calls]
    _require_success(results)

    frames = [1, 12, 24]
    renders = [
        artifact_dir / "observations" / f"sprint22_live_f{frame:03d}_karma_cpu.png"
        for frame in frames
    ]
    visual = None
    critique = None
    if arguments.render:
        visual = artifact_dir / "manifests" / "sprint22_live_visual_verification.json"
        visual_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="visual.analyze",
                request_id="sprint22-live-visual",
                arguments={
                    "image_paths": [str(path) for path in renders],
                    "output_path": str(visual),
                    "panel_count": 4 if arguments.mops_available else 1,
                },
                policy=Policy(risk=RiskClass.LOW, max_seconds=30, max_resolution=(640, 360)),
            ).as_dict(),
        )
        _require_success([visual_result])
        critique = artifact_dir / "manifests" / "sprint22_live_critique_packet.json"
        critique_result = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="verification.critique.package",
                request_id="sprint22-live-critique",
                arguments={
                    "image_paths": [str(path) for path in renders],
                    "graph_path": str(artifact_dir / "observations" / "sprint22_live_obj_graph.svg"),
                    "validation_paths": [
                        str(artifact_dir / "manifests" / "sprint22_live_kinetic_validation.json"),
                        str(artifact_dir / "manifests" / "sprint22_live_kinetic_manifest.json"),
                        str(visual),
                    ],
                    "code_paths": [
                        str(Path(__file__).resolve()),
                        str(Path(__file__).resolve().parents[1] / "hermes_houdini" / "kinetic.py"),
                        str(Path(__file__).resolve().parents[1] / "recipes" / "sop" / "kinetic_reliquary_mops.yaml"),
                        str(Path(__file__).resolve().parents[1] / "skills" / "motion.kinetic_reliquary" / "skill.py"),
                    ],
                    "output_path": str(critique),
                },
                policy=Policy(risk=RiskClass.LOW, max_seconds=30),
            ).as_dict(),
        )
        _require_success([critique_result])

    validation_path = artifact_dir / "manifests" / "sprint22_live_kinetic_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": "success",
                "houdini": hou.applicationVersionString(),
                "license": str(hou.licenseCategory()),
                "mops_available": arguments.mops_available,
                "capability": validation["capability"],
                "branches": sorted(validation["branches"]),
                "sample_frames": validation["spec"]["sample_frames"],
                "comparison_metrics": validation["comparison_metrics"],
                "selection": validation["selection"],
                "validation": str(validation_path),
                "renders": [str(path) for path in renders] if arguments.render else [],
                "visual": str(visual) if visual else None,
                "critique_packet": str(critique) if critique else None,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
