"""Run one exactly approved G003 Gate V manifest through registered Houdini tools."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess
import time
from pathlib import Path
from typing import Any

from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.g003_execution import (
    APPROVAL_SCHEMA,
    EXECUTION_SCHEMA,
    append_jsonl,
    contact_labels,
    review_index_html,
    sha256_file,
    tree_bytes,
    validate_approved_manifest,
    write_json_exclusive,
)
from hermes_houdini.policy import default_policy
from hermes_houdini.schemas.command import CommandEnvelope


def _emit(kind: str, **values: object) -> None:
    print(json.dumps({"event": kind, **values}, sort_keys=True, default=str), flush=True)


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def _source_preflight(manifest: dict[str, Any]) -> dict[str, object]:
    source = manifest["source_identity"]
    branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    if branch != source["branch"]:
        raise RuntimeError(f"branch drift: {branch!r} != {source['branch']!r}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source["commit"], "HEAD"], check=False
    )
    if ancestor.returncode != 0:
        raise RuntimeError("approved protected-main base is not an ancestor of HEAD")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], text=True
    ).strip()
    if dirty:
        raise RuntimeError(f"tracked worktree is dirty: {dirty}")
    return {
        "branch": branch,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "accepted_base": source["commit"],
        "accepted_base_is_ancestor": True,
        "tracked_worktree_clean": True,
    }


def _runtime_preflight(manifest: dict[str, Any]) -> tuple[Any, dict[str, object]]:
    import hou

    required = manifest["runtime"]["required"]
    build = hou.applicationVersionString()
    license_name = hou.licenseCategory().name()
    if build != required["houdini_build"]:
        raise RuntimeError(f"Houdini build drift: {build} != {required['houdini_build']}")
    if license_name.lower() != str(required["license"]).lower():
        raise RuntimeError(f"license drift: {license_name} != {required['license']}")
    if os.environ.get("HOUDINI_PACKAGE_SKIPLIST") != required["package_skiplist"]:
        raise RuntimeError("HOUDINI_PACKAGE_SKIPLIST drift")
    hip_path = hou.hipFile.path()
    root_descendants = sum(len(node.children()) for node in hou.node("/").children())
    if not hip_path.endswith("untitled.hip") or root_descendants:
        raise RuntimeError(
            f"fresh scene required; hip={hip_path!r}, root descendant count={root_descendants}"
        )
    return hou, {
        "build": build,
        "license": license_name,
        "hip_path": hip_path,
        "fresh_scene": True,
        "initial_frame": hou.frame(),
    }


def _dispatch_approved(
    dispatcher: Dispatcher, envelope: CommandEnvelope
) -> tuple[Any, str | None]:
    """Use the dispatcher's single-use approval store for the exact manifest envelope."""
    outcome = dispatcher.process_one(envelope)
    approval_id = None
    if outcome.result.status.value == "blocked":
        approval = outcome.result.data.get("approval")
        if not isinstance(approval, dict) or not approval.get("approval_id"):
            return outcome.result, None
        approval_id = str(approval["approval_id"])
        outcome = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id=f"{envelope.request_id}-manifest-grant",
                arguments={"approval_id": approval_id},
            )
        )
    return outcome.result, approval_id


def _run_ffmpeg(action: dict[str, Any], output: Path) -> dict[str, object]:
    executable = str(action["executable"])
    if executable != "/opt/homebrew/bin/ffmpeg":
        raise RuntimeError(f"unapproved executable: {executable}")
    if output.exists():
        raise FileExistsError(f"refusing existing postprocess output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    completed = subprocess.run(
        [executable, *action["arguments"]],
        check=False,
        capture_output=True,
        text=True,
        timeout=float(action["max_seconds"]),
    )
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({completed.returncode}): {completed.stderr[-2000:]}")
    if not output.is_file():
        raise RuntimeError(f"ffmpeg did not create expected output: {output}")
    size = output.stat().st_size
    if size > int(action["max_output_bytes"]):
        raise RuntimeError(f"postprocess output exceeds action budget: {output}")
    return {
        "kind": action["kind"],
        "output": str(output),
        "seconds": round(elapsed, 6),
        "bytes": size,
        "sha256": sha256_file(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--approved-manifest-sha256", required=True)
    parser.add_argument(
        "--approval-note",
        default="",
        help="Exact human or operator authorization wording retained in the live receipt.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate source, runtime, dispatcher, and tools without creating the artifact root.",
    )
    arguments = parser.parse_args()
    manifest_path = Path(arguments.manifest).expanduser().resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = validate_approved_manifest(
        manifest,
        approved_sha256=arguments.approved_manifest_sha256,
        require_artifact_root_absent=True,
    )
    artifact_root = Path(contract["artifact_root"])
    source = _source_preflight(manifest)
    hou, runtime = _runtime_preflight(manifest)
    dispatcher = Dispatcher(policy=default_policy([str(artifact_root)]))
    for call in contract["calls"]:
        envelope = CommandEnvelope.from_dict(call)
        valid, detail = dispatcher.validate(envelope, approval_granted=True)
        if not valid:
            raise RuntimeError(f"preflight rejected {envelope.request_id}: {detail}")
    ffmpeg_version = subprocess.check_output(
        ["/opt/homebrew/bin/ffmpeg", "-version"], text=True
    ).splitlines()[0]
    if "ffmpeg version 9.0.1" not in ffmpeg_version:
        raise RuntimeError(f"ffmpeg version drift: {ffmpeg_version}")
    if arguments.preflight_only:
        _emit(
            "preflight",
            status="pass",
            manifest_sha256=contract["manifest_sha256"],
            artifact_root=str(artifact_root),
            artifact_root_absent=not artifact_root.exists(),
            source=source,
            runtime=runtime,
            call_count=contract["call_count"],
            render_count=contract["render_count"],
            ffmpeg=ffmpeg_version,
            mutation_performed=False,
        )
        return
    if not arguments.approval_note.strip():
        raise ValueError("--approval-note is required for live execution")

    artifact_root.mkdir(parents=True, exist_ok=False)
    receipt_dir = artifact_root / "manifests"
    event_log = receipt_dir / "g003_v_execution.jsonl"
    approval_receipt = {
        "schema": APPROVAL_SCHEMA,
        "approved_manifest_sha256": contract["manifest_sha256"],
        "manifest_path": str(manifest_path),
        "approval_note": arguments.approval_note,
        "source": source,
        "runtime": runtime,
        "approved_call_count": contract["call_count"],
        "creative_selection": False,
        "downstream_lanes_authorized": False,
        "started_unix": time.time(),
    }
    write_json_exclusive(receipt_dir / "g003_v_live_approval.json", approval_receipt)
    append_jsonl(event_log, {"event": "start", **approval_receipt})
    _emit("start", artifact_root=str(artifact_root), calls=contract["call_count"])

    render_seconds = 0.0
    warnings: list[dict[str, object]] = []
    completed_calls = 0
    original_frame = float(runtime["initial_frame"])
    try:
        for index, call in enumerate(contract["calls"], start=1):
            if (artifact_root / "CANCEL").exists():
                raise RuntimeError("cancellation sentinel detected")
            envelope = CommandEnvelope.from_dict(call)
            frame_before = hou.frame()
            started = time.monotonic()
            try:
                result, approval_id = _dispatch_approved(dispatcher, envelope)
            finally:
                frame_after_call = hou.frame()
                if frame_after_call != frame_before:
                    hou.setFrame(frame_before)
            elapsed = time.monotonic() - started
            record = {
                "event": "call",
                "index": index,
                "total": contract["call_count"],
                "request_id": envelope.request_id,
                "tool": envelope.tool,
                "single_use_approval_id": approval_id,
                "seconds": round(elapsed, 6),
                "frame_before": frame_before,
                "frame_after_call": frame_after_call,
                "frame_restored": hou.frame(),
                "result": result.as_dict(),
            }
            append_jsonl(event_log, record)
            _emit(
                "call",
                index=index,
                total=contract["call_count"],
                request_id=envelope.request_id,
                tool=envelope.tool,
                status=result.status.value,
                seconds=round(elapsed, 3),
            )
            if result.status.value != "success":
                raise RuntimeError(
                    f"registered call failed: {envelope.request_id} {envelope.tool}: "
                    f"{result.errors}"
                )
            if envelope.tool == "render.karma.preview":
                render_seconds += elapsed
                if render_seconds > float(manifest["render"]["aggregate_seconds"]):
                    raise RuntimeError("aggregate render-time budget exceeded")
            if envelope.tool == "visual.analyze":
                visual_status = result.data.get("status")
                if visual_status == "fail":
                    raise RuntimeError(
                        "mechanical visual verification failed: "
                        f"{result.data.get('sequence', {}).get('flags', [])}"
                    )
                if visual_status == "warn":
                    warnings.append(
                        {
                            "request_id": envelope.request_id,
                            "image_flags": [
                                item["flags"]
                                for item in result.data.get("images", [])
                                if item.get("flags")
                            ],
                            "sequence_flags": result.data.get("sequence", {}).get("flags", []),
                        }
                    )
            completed_calls = index
            if tree_bytes(artifact_root) > int(manifest["budgets"]["aggregate_output_bytes"]):
                raise RuntimeError("aggregate output-byte budget exceeded")
            if _peak_rss_bytes() > int(manifest["budgets"]["aggregate_peak_memory_bytes"]):
                raise RuntimeError("peak-memory budget exceeded")

        postprocess_records = []
        for method in manifest["methods"]:
            action = method["postprocess"][0]
            record = _run_ffmpeg(action, Path(action["output_path"]))
            postprocess_records.append(record)
            append_jsonl(event_log, {"event": "postprocess", **record})
            _emit("postprocess", **record)
        contact = manifest["postprocess"][0]
        contact_output = Path(manifest["review"]["contact_sheet"]["output_path"])
        record = _run_ffmpeg(contact, contact_output)
        postprocess_records.append(record)
        append_jsonl(event_log, {"event": "postprocess", **record})
        write_json_exclusive(contact["labels_path"], contact_labels(manifest))
        index_path = Path(manifest["postprocess"][1]["output_path"])
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("x", encoding="utf-8") as stream:
            stream.write(review_index_html(manifest))
            stream.flush()
            os.fsync(stream.fileno())
        index_record = {
            "kind": "write_static_review_index",
            "output": str(index_path),
            "bytes": index_path.stat().st_size,
            "sha256": sha256_file(index_path),
        }
        postprocess_records.append(index_record)
        append_jsonl(event_log, {"event": "postprocess", **index_record})
        output_bytes = tree_bytes(artifact_root)
        if output_bytes > int(manifest["budgets"]["aggregate_output_bytes"]):
            raise RuntimeError("aggregate output-byte budget exceeded after postprocessing")
        final = {
            "schema": EXECUTION_SCHEMA,
            "status": "success_with_mechanical_warnings" if warnings else "success",
            "approved_manifest_sha256": contract["manifest_sha256"],
            "source": source,
            "runtime": {**runtime, "final_hip_path": hou.hipFile.path()},
            "completed_calls": completed_calls,
            "render_calls": contract["render_count"],
            "render_seconds": round(render_seconds, 6),
            "peak_rss_bytes": _peak_rss_bytes(),
            "output_bytes": output_bytes,
            "postprocess": postprocess_records,
            "mechanical_warnings": warnings,
            "automatic_ranking": False,
            "winner": None,
            "human_rating": None,
            "selected_for_continuation": None,
            "completed_unix": time.time(),
        }
        write_json_exclusive(receipt_dir / "g003_v_execution_receipt.json", final)
        append_jsonl(event_log, {"event": "complete", **final})
        _emit("complete", **final)
    except Exception as exc:
        failure = {
            "event": "failure",
            "status": "stopped",
            "completed_calls": completed_calls,
            "render_seconds": round(render_seconds, 6),
            "peak_rss_bytes": _peak_rss_bytes(),
            "output_bytes": tree_bytes(artifact_root),
            "error": f"{type(exc).__name__}: {exc}",
            "stopped_unix": time.time(),
        }
        append_jsonl(event_log, failure)
        _emit("failure", **failure)
        raise
    finally:
        if hou.frame() != original_frame:
            hou.setFrame(original_frame)


if __name__ == "__main__":
    main()
