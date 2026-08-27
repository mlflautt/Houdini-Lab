"""Harness-neutral validation and artifact helpers for approved G003 execution."""

from __future__ import annotations

import hashlib
import html
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .g003_visual_audition import (
    FFMPEG_PATH,
    PRESENTATION_ORDER,
    SAMPLE_FRAMES,
    SCHEMA,
    visual_audition_manifest_sha256,
)

EXECUTION_SCHEMA = "hermes.houdini.g003.execution_receipt.v1"
APPROVAL_SCHEMA = "hermes.houdini.g003.live_approval.v1"
EXPECTED_CALL_COUNT = 115
EXPECTED_RENDER_COUNT = 36
_FILE_ARGUMENTS = {
    "checkpoint_dir",
    "log_path",
    "output_dir",
    "output_path",
    "scene_path",
    "manifest_path",
    "result_path",
}


def _inside(root: Path, candidate: Path, label: str) -> Path:
    root = root.expanduser().resolve()
    candidate = candidate.expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must be inside {root}") from exc
    return candidate


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def flatten_manifest_calls(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return stable-order calls without mutating the approved manifest."""
    methods = manifest.get("methods")
    if not isinstance(methods, list) or len(methods) != 3:
        raise ValueError("methods must contain exactly three entries")
    calls: list[dict[str, Any]] = []
    for method_index, method in enumerate(methods):
        item = _mapping(method, f"methods[{method_index}]")
        method_calls = item.get("calls")
        if not isinstance(method_calls, list) or not method_calls:
            raise ValueError(f"methods[{method_index}].calls must be a non-empty list")
        for call_index, call in enumerate(method_calls):
            calls.append(dict(_mapping(call, f"methods[{method_index}].calls[{call_index}]")))
    return calls


def validate_approved_manifest(
    manifest: Mapping[str, Any],
    *,
    approved_sha256: str,
    require_artifact_root_absent: bool = True,
) -> dict[str, Any]:
    """Fail closed unless one exact dry manifest is safe to hand to a live operator."""
    if manifest.get("schema") != SCHEMA:
        raise ValueError(f"unsupported manifest schema: {manifest.get('schema')!r}")
    actual_hash = visual_audition_manifest_sha256(dict(manifest))
    if approved_sha256 != actual_hash:
        raise ValueError(f"approval subject mismatch: {actual_hash}")
    approval = _mapping(manifest.get("approval"), "approval")
    if approval.get("manifest_sha256_subject") != actual_hash:
        raise ValueError("embedded approval subject does not match canonical manifest")
    if manifest.get("automatic_execution") is not False:
        raise ValueError("automatic_execution must remain false")
    runtime = _mapping(manifest.get("runtime"), "runtime")
    observed = _mapping(runtime.get("observed"), "runtime.observed")
    if observed.get("status") != "pass" or observed.get("mutation_performed") is not False:
        raise ValueError("runtime observation must be a passing mutation-free probe")

    project_root = Path(str(manifest.get("project_root", ""))).expanduser()
    artifact_root = Path(str(manifest.get("artifact_root", ""))).expanduser()
    if not project_root.is_absolute() or not artifact_root.is_absolute():
        raise ValueError("project_root and artifact_root must be absolute")
    project_root = project_root.resolve()
    artifact_root = _inside(project_root, artifact_root, "artifact_root")
    if require_artifact_root_absent and artifact_root.exists():
        raise FileExistsError(f"refusing existing artifact root: {artifact_root}")

    methods = manifest["methods"]
    capabilities = [str(_mapping(item, "method").get("capability")) for item in methods]
    if capabilities != list(PRESENTATION_ORDER):
        raise ValueError("presentation capability order drift")
    if [item.get("presentation_index") for item in methods] != [0, 1, 2]:
        raise ValueError("presentation indices must remain 0, 1, 2")
    calls = flatten_manifest_calls(manifest)
    if len(calls) != EXPECTED_CALL_COUNT:
        raise ValueError(f"expected {EXPECTED_CALL_COUNT} registered calls, found {len(calls)}")
    request_ids = [str(call.get("request_id", "")) for call in calls]
    if any(not value for value in request_ids) or len(set(request_ids)) != len(request_ids):
        raise ValueError("registered calls require unique non-empty request_id values")
    render_calls = []
    for index, call in enumerate(calls):
        tool = call.get("tool")
        if not isinstance(tool, str) or not tool:
            raise ValueError(f"calls[{index}].tool must be a non-empty string")
        policy = _mapping(call.get("policy"), f"calls[{index}].policy")
        if policy.get("allow_network") is not False:
            raise ValueError(f"calls[{index}] may not allow network access")
        if policy.get("allow_arbitrary_code") is not False:
            raise ValueError(f"calls[{index}] may not allow arbitrary code")
        if policy.get("allow_overwrite") is not False:
            raise ValueError(f"calls[{index}] may not allow overwrite")
        if policy.get("allow_external_process") is True and tool != "render.karma.preview":
            raise ValueError(f"calls[{index}] external process is not an approved Karma preview")
        arguments = _mapping(call.get("arguments"), f"calls[{index}].arguments")
        for name in _FILE_ARGUMENTS.intersection(arguments):
            value = arguments[name]
            if isinstance(value, str) and value:
                _inside(artifact_root, Path(value), f"calls[{index}].arguments.{name}")
        if tool == "render.karma.preview":
            render_calls.append(call)
    if len(render_calls) != EXPECTED_RENDER_COUNT:
        raise ValueError(f"expected {EXPECTED_RENDER_COUNT} render calls")
    frames = [int(_mapping(call["arguments"], "render arguments")["frame"]) for call in render_calls]
    if frames != list(SAMPLE_FRAMES) * 3:
        raise ValueError("render frame order drift")

    review = _mapping(manifest.get("review"), "review")
    if review.get("automatic_ranking") is not False:
        raise ValueError("automatic ranking must remain disabled")
    for name in ("winner", "human_rating", "selected_for_continuation"):
        if review.get(name) is not None:
            raise ValueError(f"review.{name} must remain null before human review")
    postprocess = manifest.get("postprocess")
    if not isinstance(postprocess, list) or len(postprocess) != 2:
        raise ValueError("postprocess must contain contact-sheet and review-index actions")
    actions = [method["postprocess"][0] for method in methods] + [postprocess[0]]
    for index, raw in enumerate(actions):
        action = _mapping(raw, f"postprocess actions[{index}]")
        if action.get("executable") != FFMPEG_PATH:
            raise ValueError("postprocess executable drift")
        if action.get("network") is not False or action.get("automatic_execution") is not False:
            raise ValueError("postprocess must remain local and non-automatic")
        output = action.get("output_path")
        if output is None and action.get("kind") == "stable_order_contact_sheet":
            output = _mapping(review.get("contact_sheet"), "review.contact_sheet").get(
                "output_path"
            )
        _inside(artifact_root, Path(str(output)), f"postprocess actions[{index}].output")
    index_action = _mapping(postprocess[1], "postprocess[1]")
    if index_action.get("kind") != "write_static_review_index":
        raise ValueError("postprocess[1] must write the static review index")
    if index_action.get("network") is not False or index_action.get("automatic_execution") is not False:
        raise ValueError("review index must remain local and non-automatic")
    _inside(artifact_root, Path(str(index_action.get("output_path"))), "review index output")

    return {
        "manifest_sha256": actual_hash,
        "project_root": str(project_root),
        "artifact_root": str(artifact_root),
        "calls": calls,
        "call_count": len(calls),
        "render_count": len(render_calls),
        "presentation_order": capabilities,
    }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_bytes(root: str | Path) -> int:
    return sum(path.stat().st_size for path in Path(root).rglob("*") if path.is_file())


def write_json_exclusive(path: str | Path, value: object) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_jsonl(path: str | Path, value: object) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(value, sort_keys=True, separators=(",", ":"), default=str) + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def contact_labels(manifest: Mapping[str, Any]) -> dict[str, Any]:
    action = _mapping(manifest["postprocess"][0], "postprocess[0]")
    return {
        "schema": "hermes.houdini.g003.contact_sheet_labels.v1",
        "presentation_order": list(action["labels"]),
        "automatic_ranking": False,
        "winner": None,
        "human_rating": None,
    }


def review_index_html(manifest: Mapping[str, Any]) -> str:
    """Return one portable, stable-order review page without scripts or remote resources."""
    action = _mapping(manifest["postprocess"][1], "postprocess[1]")
    output = Path(str(action["output_path"]))
    cards = []
    for index, raw in enumerate(action["ordered_methods"], start=1):
        method = _mapping(raw, f"ordered_methods[{index - 1}]")
        preview = os.path.relpath(str(method["preview_path"]), output.parent)
        still = os.path.relpath(str(method["final_frame_path"]), output.parent)
        label = html.escape(str(method["label"]))
        cards.append(
            "<section><h2>{index}. {label}</h2><p><code>{capability}</code></p>"
            "<video controls loop muted preload='metadata' src='{preview}'></video>"
            "<a href='{still}'><img src='{still}' alt='{label} final sampled frame'></a>"
            "<p>Human rating: <em>unselected</em></p></section>".format(
                index=index,
                label=label,
                capability=html.escape(str(method["capability"])),
                preview=html.escape(preview, quote=True),
                still=html.escape(still, quote=True),
            )
        )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>G003 Gate V motion audition</title><style>
body{{margin:0;background:#11151a;color:#ece7dc;font:16px system-ui;padding:24px}}main{{max-width:1100px;margin:auto}}
section{{border-top:1px solid #45505d;padding:22px 0}}video,img{{display:block;width:100%;max-width:960px;background:#050607;margin:12px 0}}
code{{color:#b8d7d0}}em{{color:#d6b97a}}</style></head><body><main>
<h1>G003 Gate V — stable-order motion audition</h1>
<p>Authentic Houdini Apprentice/Karma CPU evidence. Presentation order is fixed and carries no ranking.</p>
{cards}</main></body></html>
""".format(cards="\n".join(cards))


__all__ = [
    "APPROVAL_SCHEMA",
    "EXECUTION_SCHEMA",
    "EXPECTED_CALL_COUNT",
    "EXPECTED_RENDER_COUNT",
    "append_jsonl",
    "contact_labels",
    "flatten_manifest_calls",
    "review_index_html",
    "sha256_file",
    "tree_bytes",
    "validate_approved_manifest",
    "write_json_exclusive",
]
