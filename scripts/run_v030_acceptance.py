"""Run or resume the disposable Hermes v0.30 fractal-relic acceptance loop."""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Any

import hou
from bridge.auth import make_secret, sign
from bridge.interactive import forward_signed_payload
from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.policy import default_policy
from hermes_houdini.runtime import InteractiveRuntime
from hermes_houdini.schemas.command import CommandEnvelope, Policy, RiskClass
from hermes_houdini.skill_loader import load_skill


def _dispatch(dispatcher: Dispatcher, envelope: CommandEnvelope | dict[str, Any]):
    if isinstance(envelope, dict):
        envelope = CommandEnvelope.from_dict(envelope)
    outcome = dispatcher.process_one(envelope)
    approval = None
    if outcome.result.status.value == "blocked" and "approval" in outcome.result.data:
        approval = dict(outcome.result.data["approval"])
        outcome = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id=f"{envelope.request_id}-grant",
                arguments={"approval_id": approval["approval_id"]},
            )
        )
    if outcome.result.status.value != "success":
        raise RuntimeError(f"{envelope.tool} failed: {outcome.result.errors}")
    return outcome.result, approval


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def _bridge_roundtrip(
    runtime: InteractiveRuntime, secret: str, envelope: CommandEnvelope
) -> dict[str, Any]:
    payload = json.dumps(envelope.as_dict(), separators=(",", ":")).encode("utf-8")
    result: dict[str, Any] = {}
    errors: list[Exception] = []

    def send() -> None:
        try:
            result.update(
                forward_signed_payload(
                    payload,
                    sign(secret, payload),
                    port=runtime.port,
                    timeout=5.0,
                )
            )
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=send)
    thread.start()
    deadline = time.monotonic() + 5.0
    while thread.is_alive() and time.monotonic() < deadline:
        runtime.pump()
        thread.join(timeout=0.01)
    thread.join(timeout=0.1)
    if thread.is_alive() or errors:
        raise RuntimeError(f"authenticated bridge roundtrip failed: {errors}")
    if result.get("status") != "success":
        raise RuntimeError(f"authenticated bridge command failed: {result.get('errors')}")
    return result


def _bridge_bootstrap(
    dispatcher: Dispatcher,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    secret = make_secret()
    runtime = InteractiveRuntime(secret=secret, port=0, dispatcher=dispatcher, request_timeout=5.0)
    runtime.start()
    try:
        session = _bridge_roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="session.describe",
                request_id="v030-bridge-session",
                session_id="v030-live-session",
                project_id="v030-fractal-relic",
            ),
        )["data"]
        catalog = _bridge_roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="system.catalog",
                request_id="v030-bridge-catalog",
                arguments={"context": "SOP", "kind": "skill", "houdini_build": "22.0.368"},
            ),
        )["data"]
        evidence = {
            "host": "127.0.0.1",
            "authenticated": True,
            "bridge_mode": session["bridge_mode"],
            "commands": ["session.describe", "system.catalog"],
        }
        return session, catalog, evidence
    finally:
        runtime.stop()


def _session(dispatcher: Dispatcher, request_id: str) -> dict[str, Any]:
    result, _ = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="session.describe",
            request_id=request_id,
            session_id="v030-live-session",
            project_id="v030-fractal-relic",
        ),
    )
    return result.data


def _execute(artifact_dir: Path, *, render: bool, human_feedback: str) -> dict[str, Any]:
    if artifact_dir.exists():
        raise FileExistsError(f"refusing existing artifact directory: {artifact_dir}")
    artifact_dir.mkdir(parents=True)
    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    before, catalog, bridge_evidence = _bridge_bootstrap(dispatcher)
    if not any(item["capability_id"] == "model.fractal_relic" for item in catalog["records"]):
        raise RuntimeError("model.fractal_relic missing from filtered capability catalog")
    plan_result, _ = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="intent.plan.create",
            request_id="v030-intent-plan",
            arguments={
                "objective": "Build three comparable alien relic forms for human review.",
                "selected_capabilities": [
                    {
                        "id": "model.fractal_relic",
                        "version": "1.1.0",
                        "reason": "small deterministic native-SOP system test",
                    }
                ],
                "alternatives": [
                    {"id": "sop.fractal_relic_candidate", "status": "retained"},
                    {"id": "hermes::fractal_relic", "status": "deferred"},
                ],
                "constraints": {
                    "license": "houdini-apprentice-noncommercial",
                    "single_frame": True,
                    "automatic_ranking": False,
                },
                "resource_estimate": {
                    "seconds": 120,
                    "memory_bytes": 1_073_741_824,
                    "frames": 1,
                    "output_bytes": 536_870_912,
                },
                "approvals": [{"risk": "medium", "scope": "graph batch", "status": "required"}],
                "verification": {
                    "graph": "named contracts and replay log",
                    "data": "bounded cooked geometry metrics",
                    "visual": "Karma CPU proof" if render else "pending live render",
                },
                "human_decisions": [{"decision": "candidate winner", "status": "pending"}],
            },
        ),
    )
    plan = plan_result.data
    parent_result, _ = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="node.create",
            request_id="v030-parent",
            arguments={
                "parent_path": "/obj",
                "operator_type": "geo",
                "name": "HERMES_V030_RELIC",
                "category": "Object",
                "role": "v030_acceptance_root",
                "created_by": "acceptance:v0.30",
            },
            policy=Policy(risk=RiskClass.LOW),
        ),
    )
    parent_path = parent_result.data["path"]
    model = load_skill("skills/model.fractal_relic")
    model_calls = model.plan(
        parent_node_id=parent_path,
        artifact_dir=str(artifact_dir),
        run_id="v030_relic",
        seed=30030,
        detail_level="draft",
        iterations=2,
    )
    approvals = []
    results = []
    visual_status = "pending"
    for call in model_calls:
        result, approval = _dispatch(dispatcher, call)
        results.append(result.as_dict())
        if approval:
            approvals.append(approval)
    if render:
        lookdev = load_skill("skills/lookdev.relic_stage")
        lookdev_calls = lookdev.plan(
            source_sop_path=f"{parent_path}/OUT_GEO",
            artifact_dir=str(artifact_dir),
            run_id="v030_proof",
            width=640,
            height=360,
            time_limit=90.0,
            max_threads=4,
            render_preview=True,
        )
        for index, call in enumerate(lookdev_calls):
            result, approval = _dispatch(dispatcher, call)
            results.append(result.as_dict())
            if approval:
                approvals.append(approval)
            if index == 0:
                # Preserve the recipe's viewing direction while adding mechanical crop margin
                # for the explicit v0.30 proof camera. Keep it checkpointed and replayable.
                framing, framing_approval = _dispatch(
                    dispatcher,
                    CommandEnvelope(
                        tool="graph.apply_batch",
                        request_id="v030-camera-framing",
                        arguments={
                            "batch_id": "v030:proof_camera_framing",
                            "operations": [
                                {
                                    "op": "set_parameter",
                                    "target": "/stage/V030_PROOF_CAMERA",
                                    "name": parameter,
                                    "value": value,
                                }
                                for parameter, value in (
                                    ("tx", 8.1),
                                    ("ty", 5.4),
                                    ("tz", 10.8),
                                )
                            ],
                            "checkpoint_dir": str(artifact_dir / "checkpoints"),
                            "log_path": str(
                                artifact_dir / "logs" / "v030_proof_camera_framing.jsonl"
                            ),
                            "label": "Hermes v0.30 proof camera framing",
                            "checkpoint_stem": "v030_proof_camera",
                        },
                    ),
                )
                results.append(framing.as_dict())
                if framing_approval:
                    approvals.append(framing_approval)
        visual_result, _ = _dispatch(
            dispatcher,
            CommandEnvelope(
                tool="visual.analyze",
                request_id="v030-visual-analyze",
                arguments={
                    "image_paths": [
                        str(artifact_dir / "observations" / "v030_proof_karma_cpu.png")
                    ],
                    "output_path": str(
                        artifact_dir / "manifests" / "v030_visual_verification.json"
                    ),
                    "panel_count": 1,
                    "panel_rows": 1,
                    "expect_motion": False,
                },
            ),
        )
        visual_status = str(visual_result.data["status"])
        results.append(visual_result.as_dict())
        if visual_status == "fail":
            raise RuntimeError("Karma proof failed deterministic visual verification")
    after = _session(dispatcher, "v030-session-after")
    scene_paths = sorted((artifact_dir / "scenes").glob("*.hipnc"), key=lambda path: path.stat().st_mtime)
    if not scene_paths:
        raise RuntimeError("acceptance did not create a final .hipnc snapshot")
    checkpoint = scene_paths[-1]
    artifact_paths = [
        path
        for directory in ("observations", "manifests", "scenes")
        for path in sorted((artifact_dir / directory).glob("**/*"))
        if path.is_file()
    ]
    visual_paths = [path for path in artifact_paths if path.suffix.lower() == ".png"]
    replay_logs = [str(path) for path in sorted((artifact_dir / "logs").glob("*.jsonl"))]
    feedback = {
        "text": human_feedback,
        "status": "recorded" if human_feedback else "pending",
        "verbatim": True,
    }
    handoff_path = artifact_dir / "handoff" / "v030_relic_handoff.json"
    handoff_result, _ = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="handoff.create",
            request_id="v030-handoff-create",
            arguments={
                "output_path": str(handoff_path),
                "project_root": str(artifact_dir),
                "project_id": "v030-fractal-relic",
                "session_id": "v030-live-session",
                "compatibility": after["compatibility"],
                "intent_plan": plan,
                "checkpoint": str(checkpoint),
                "replay_logs": replay_logs,
                "artifacts": [{"path": str(path), "kind": path.suffix.lstrip(".")} for path in artifact_paths],
                "stable_nodes": after["managed_nodes"]["nodes"],
                "evidence": [
                    {"kind": "graph", "status": "pass"},
                    {"kind": "data", "status": "pass"},
                    {"kind": "visual", "status": visual_status if visual_paths else "pending"},
                    {"kind": "human_review", "status": "pending"},
                ],
                "human_feedback": [feedback],
                "pending_gates": ["human_candidate_review"],
            },
        ),
    )
    transcript = {
        "schema": "hermes.houdini.v030_acceptance",
        "schema_version": "1.0",
        "mode": "execute",
        "status": "success",
        "session_before": before,
        "bridge": bridge_evidence,
        "catalog": {"record_count": catalog["record_count"], "sha256": catalog["catalog_sha256"]},
        "intent_plan": plan,
        "approvals_granted": approvals,
        "command_results": results,
        "session_after": after,
        "visual_proof": [str(path) for path in visual_paths],
        "human_feedback": feedback,
        "handoff_path": str(handoff_path),
        "handoff_sha256": handoff_result.data["content_sha256"],
    }
    _write_json(artifact_dir / "v030_execute_transcript.json", transcript)
    return transcript


def _resume(artifact_dir: Path, *, load_checkpoint: bool) -> dict[str, Any]:
    handoff_path = artifact_dir / "handoff" / "v030_relic_handoff.json"
    dispatcher = Dispatcher(policy=default_policy([str(artifact_dir)]))
    fresh = _session(dispatcher, "v030-resume-before")
    inspected, _ = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="handoff.inspect",
            request_id="v030-handoff-inspect",
            arguments={"file_path": str(handoff_path)},
        ),
    )
    resume, _ = _dispatch(
        dispatcher,
        CommandEnvelope(
            tool="handoff.resume_plan",
            request_id="v030-handoff-resume-plan",
            arguments={
                "file_path": str(handoff_path),
                "current_compatibility": fresh["compatibility"],
            },
        ),
    )
    if resume.data["status"] == "blocked":
        raise RuntimeError(f"handoff resume blocked: {resume.data['blockers']}")
    resolved = []
    if load_checkpoint:
        checkpoint = inspected.data["bundle"]["checkpoint"]
        hou.hipFile.load(checkpoint, suppress_save_prompt=True, ignore_load_warnings=False)
        for node in inspected.data["bundle"]["stable_nodes"]:
            result, _ = _dispatch(
                dispatcher,
                CommandEnvelope(
                    tool="node.find_by_hermes_id",
                    request_id=f"v030-resolve-{len(resolved)}",
                    arguments={"hermes_id": node["hermes_id"]},
                ),
            )
            resolved.append({"hermes_id": node["hermes_id"], "path": result.data["path"]})
        if not resolved or not all(item["path"] for item in resolved):
            raise RuntimeError("fresh session did not resolve every stable Hermes id")
    transcript = {
        "schema": "hermes.houdini.v030_acceptance",
        "schema_version": "1.0",
        "mode": "resume",
        "status": "success",
        "fresh_session": fresh,
        "handoff_valid": inspected.data["valid"],
        "resume_plan": resume.data,
        "checkpoint_loaded_by_operator": load_checkpoint,
        "resolved_stable_nodes": resolved,
        "automatic_refinement_executed": False,
    }
    _write_json(artifact_dir / "v030_resume_transcript.json", transcript)
    return transcript


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--mode", choices=("execute", "resume"), default="execute")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--human-feedback", default="")
    parser.add_argument("--load-checkpoint", action="store_true")
    parser.add_argument("--summary", action="store_true")
    arguments = parser.parse_args()
    artifact_dir = Path(arguments.artifact_dir).expanduser()
    if not artifact_dir.is_absolute():
        raise ValueError("--artifact-dir must be absolute")
    if arguments.mode == "execute":
        result = _execute(
            artifact_dir,
            render=arguments.render,
            human_feedback=arguments.human_feedback,
        )
    else:
        result = _resume(artifact_dir, load_checkpoint=arguments.load_checkpoint)
    if arguments.summary:
        compact = {
            "mode": result["mode"],
            "status": result["status"],
            "package_version": result.get("session_after", result.get("fresh_session", {}))
            .get("compatibility", {})
            .get("package_version", ""),
            "handoff_path": result.get("handoff_path", ""),
            "handoff_valid": result.get("handoff_valid"),
            "resume_status": result.get("resume_plan", {}).get("status"),
            "resolved_stable_nodes": len(result.get("resolved_stable_nodes", [])),
            "visual_proof": result.get("visual_proof", []),
        }
        print(json.dumps(compact, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
