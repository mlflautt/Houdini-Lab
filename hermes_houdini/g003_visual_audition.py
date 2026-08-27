"""Pure planning for G003's three-way visual motion audition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from skills._lib import build_envelope

from hermes_houdini.schemas.command import Policy, RiskClass
from hermes_houdini.skill_loader import load_skill

SCHEMA = "hermes.houdini.g003.visual_audition_plan.v1"
SAMPLE_FRAMES = (2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24)
PRESENTATION_ORDER = (
    "motion.particle_calligraphy@1.0.0",
    "generate.differential_growth@1.0.0",
    "motion.kinetic_reliquary@1.1.0",
)
FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"


def _inside(root: Path, candidate: Path, label: str) -> Path:
    root = root.expanduser().resolve()
    candidate = candidate.expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must be inside project_root") from exc
    return candidate


def _render_calls(
    *,
    method_id: str,
    run_id: str,
    stage_node_path: str,
    render_settings_path: str,
    source_sop_path: str,
    source_start_frame: int,
    artifact_dir: Path,
    max_points: int,
    max_primitives: int,
    max_memory_bytes: int,
    panel_count: int,
) -> tuple[list[dict[str, object]], list[str]]:
    calls: list[dict[str, object]] = []
    render_paths: list[str] = []
    checkpoint_dir = artifact_dir / "checkpoints"
    log_dir = artifact_dir / "logs"
    observation_dir = artifact_dir / "observations"
    common = {
        "session_id": run_id,
        "project_id": method_id,
        "expected": {
            "gate": "G003-V",
            "method": method_id,
            "automatic_execution": False,
        },
    }
    for frame in SAMPLE_FRAMES:
        suffix = f"F{frame:03d}"
        render_path = observation_dir / f"{run_id}_f{frame:03d}_karma_cpu.png"
        render_paths.append(str(render_path))
        rop_name = f"{run_id.upper()}_KARMA_{suffix}"
        rop_path = f"/out/{rop_name}"
        graph_policy = Policy(
            risk=RiskClass.MEDIUM,
            max_seconds=30,
            max_points=max_points,
            max_primitives=max_primitives,
            max_memory_bytes=max_memory_bytes,
            max_frames=1,
            max_output_bytes=67_108_864,
            max_resolution=(640, 360),
        )
        render_policy = Policy(
            risk=RiskClass.EXTERNAL,
            allow_external_process=True,
            max_seconds=35,
            max_points=max_points,
            max_primitives=max_primitives,
            max_memory_bytes=max_memory_bytes,
            max_frames=frame - source_start_frame + 1,
            max_output_bytes=67_108_864,
            max_resolution=(640, 360),
        )
        calls.extend(
            [
                build_envelope(
                    "solaris.karma_rop.build",
                    {
                        "stage_node_path": stage_node_path,
                        "render_settings_path": render_settings_path,
                        "output_path": str(render_path),
                        "checkpoint_dir": str(checkpoint_dir),
                        "log_path": str(log_dir / f"{run_id}_{suffix}_rop.jsonl"),
                        "node_name": rop_name,
                        "width": 640,
                        "height": 360,
                        "frame": float(frame),
                        "time_limit": 30.0,
                        "max_threads": 4,
                    },
                    request_id=f"{run_id}-{suffix}-rop",
                    policy=graph_policy,
                    **common,
                ).as_dict(),
                build_envelope(
                    "render.karma.preview",
                    {
                        "rop_path": rop_path,
                        "output_path": str(render_path),
                        "log_path": str(log_dir / f"{run_id}_{suffix}_render.jsonl"),
                        "frame": float(frame),
                        "source_sop_path": source_sop_path,
                        "source_start_frame": float(source_start_frame),
                    },
                    request_id=f"{run_id}-{suffix}-render",
                    policy=render_policy,
                    **common,
                ).as_dict(),
            ]
        )
    calls.append(
        build_envelope(
            "visual.analyze",
            {
                "image_paths": render_paths,
                "output_path": str(
                    artifact_dir / "manifests" / f"{run_id}_visual_verification.json"
                ),
                "panel_count": panel_count,
                "panel_rows": 1,
                "expect_motion": True,
            },
            request_id=f"{run_id}-visual",
            policy=Policy(
                risk=RiskClass.LOW,
                max_seconds=60,
                max_memory_bytes=536_870_912,
                max_frames=len(SAMPLE_FRAMES),
                max_resolution=(640, 360),
            ),
            **common,
        ).as_dict()
    )
    return calls, render_paths


def _create_geo_call(*, run_id: str, name: str, artifact_dir: Path) -> dict[str, object]:
    return build_envelope(
        "graph.apply_batch",
        {
            "batch_id": f"G003-V:{run_id}:network",
            "operations": [
                {
                    "op": "create",
                    "ref": "network",
                    "parent_path": "/obj",
                    "operator_type": "geo",
                    "name": name,
                    "exact_name": True,
                    "category": "Object",
                    "role": "g003_visual_audition_network",
                    "position": [0.0, 0.0],
                    "parameters": {},
                    "comment": f"G003 Gate V neutral study: {run_id}",
                }
            ],
            "checkpoint_dir": str(artifact_dir / "checkpoints"),
            "log_path": str(artifact_dir / "logs" / f"{run_id}_network.jsonl"),
            "label": f"G003 Gate V create {run_id}",
            "checkpoint_stem": f"g003_v_{run_id}_network",
        },
        request_id=f"{run_id}-network",
        session_id="g003-v-20260827-a",
        project_id="project.living_biome",
        policy=Policy(
            risk=RiskClass.MEDIUM,
            max_seconds=30,
            max_points=100_000,
            max_primitives=100_000,
            max_memory_bytes=536_870_912,
            max_frames=24,
        ),
        expected={"gate": "G003-V", "automatic_execution": False},
    ).as_dict()


def _ffmpeg_preview(method_dir: Path, run_id: str) -> dict[str, object]:
    output = method_dir / "review" / f"{run_id}_6fps.mp4"
    pattern = method_dir / "observations" / f"{run_id}_f*_karma_cpu.png"
    return {
        "kind": "local_preview_encode",
        "executable": FFMPEG_PATH,
        "arguments": [
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            "6",
            "-pattern_type",
            "glob",
            "-i",
            str(pattern),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ],
        "input_frames": list(SAMPLE_FRAMES),
        "output_path": str(output),
        "max_seconds": 60,
        "max_output_bytes": 67_108_864,
        "network": False,
        "automatic_execution": False,
    }


def build_visual_audition_manifest(
    *,
    project_root: str | Path,
    artifact_root: str | Path,
    source_identity: dict[str, object],
    runtime_observation: dict[str, object],
) -> dict[str, object]:
    """Return the deterministic, non-executing Gate V manifest."""
    project = Path(project_root).expanduser().resolve()
    artifacts = _inside(project, Path(artifact_root), "artifact_root")
    if artifacts.exists():
        raise FileExistsError(f"refusing existing Gate V artifact root: {artifacts}")
    if not isinstance(source_identity, dict) or source_identity.get("dirty") is not False:
        raise ValueError("source_identity must explicitly record dirty=false")
    if source_identity.get("commit") != "df476c1af5db0cda4b80d8cc7ff5bd384cb51389":
        raise ValueError("source_identity.commit must equal the accepted G003 protected-main base")

    calligraphy_dir = artifacts / "01-particle-calligraphy"
    differential_dir = artifacts / "02-differential-growth"
    kinetic_dir = artifacts / "03-kinetic-instances"

    calligraphy = load_skill("skills/motion.particle_calligraphy")
    differential = load_skill("skills/generate.differential_growth")
    kinetic = load_skill("skills/motion.kinetic_reliquary")
    lookdev = load_skill("skills/lookdev.relic_stage")
    observed = (
        f"{calligraphy.id}@{calligraphy.version}",
        f"{differential.id}@{differential.version}",
        f"{kinetic.id}@{kinetic.version}",
    )
    if observed != PRESENTATION_ORDER:
        raise ValueError(f"registered motion identity drift: {observed!r}")

    calligraphy_run = "g003_v_calligraphy"
    calligraphy_parent = "/obj/G003_V_CALLIGRAPHY"
    calligraphy_calls = [_create_geo_call(run_id=calligraphy_run, name="G003_V_CALLIGRAPHY", artifact_dir=calligraphy_dir)]
    calligraphy_calls.extend(
        calligraphy.plan(
            parent_node_id=calligraphy_parent,
            artifact_dir=str(calligraphy_dir),
            run_id=calligraphy_run,
            seed=5201,
            start_frame=1,
            end_frame=24,
            candidate_index=0,
            wire_radius=0.06,
        )
    )
    calligraphy_lookdev = "g003_v_calligraphy_ld"
    calligraphy_calls.extend(
        lookdev.plan(
            source_sop_path=f"{calligraphy_parent}/OUT_G003_V_CALLIGRAPHY_COMPARE",
            artifact_dir=str(calligraphy_dir),
            run_id=calligraphy_lookdev,
            asset_prim_path="/World/G003V/ParticleCalligraphy",
            candidate_index=2,
            width=640,
            height=360,
            frame=24,
            source_start_frame=1,
            time_limit=30,
            max_threads=4,
            render_preview=False,
            dome_intensity=1.5,
            dome_exposure=1.0,
            camera_tx=0.0,
            camera_ty=-0.55,
            camera_tz=8.2,
            camera_rx=0.0,
            camera_ry=0.0,
            camera_rz=0.0,
            camera_focal_length=45.0,
        )
    )
    extra, calligraphy_renders = _render_calls(
        method_id=calligraphy.id,
        run_id=calligraphy_run,
        stage_node_path="/stage/OUT_G003_V_CALLIGRAPHY_LD_STAGE",
        render_settings_path="/Render/G003_V_CALLIGRAPHY_LD_Settings",
        source_sop_path=f"{calligraphy_parent}/OUT_G003_V_CALLIGRAPHY_COMPARE",
        source_start_frame=1,
        artifact_dir=calligraphy_dir,
        max_points=100_000,
        max_primitives=100_000,
        max_memory_bytes=536_870_912,
        panel_count=3,
    )
    calligraphy_calls.extend(extra)

    differential_run = "g003_v_differential"
    differential_parent = "/obj/G003_V_DIFFERENTIAL"
    differential_calls = [_create_geo_call(run_id=differential_run, name="G003_V_DIFFERENTIAL", artifact_dir=differential_dir)]
    differential_calls.extend(
        differential.plan(
            parent_node_id=differential_parent,
            artifact_dir=str(differential_dir),
            run_id=differential_run,
            seed=2401,
            candidate_index=1,
            start_frame=1,
            end_frame=24,
            frame_step=1,
            wire_radius=0.06,
        )
    )
    differential_lookdev = "g003_v_differential_ld"
    differential_calls.extend(
        lookdev.plan(
            source_sop_path=f"{differential_parent}/OUT_G003_V_DIFFERENTIAL_COMPARE",
            artifact_dir=str(differential_dir),
            run_id=differential_lookdev,
            asset_prim_path="/World/G003V/DifferentialGrowth",
            candidate_index=2,
            width=640,
            height=360,
            frame=24,
            source_start_frame=1,
            time_limit=30,
            max_threads=4,
            render_preview=False,
            dome_intensity=1.5,
            dome_exposure=1.0,
            camera_tx=-2.0,
            camera_ty=0.0,
            camera_tz=44.0,
            camera_rx=0.0,
            camera_ry=0.0,
            camera_rz=0.0,
            camera_focal_length=45.0,
            max_primitives=50_000,
        )
    )
    extra, differential_renders = _render_calls(
        method_id=differential.id,
        run_id=differential_run,
        stage_node_path="/stage/OUT_G003_V_DIFFERENTIAL_LD_STAGE",
        render_settings_path="/Render/G003_V_DIFFERENTIAL_LD_Settings",
        source_sop_path=f"{differential_parent}/OUT_G003_V_DIFFERENTIAL_COMPARE",
        source_start_frame=1,
        artifact_dir=differential_dir,
        max_points=50_000,
        max_primitives=50_000,
        max_memory_bytes=536_870_912,
        panel_count=2,
    )
    differential_calls.extend(extra)

    kinetic_run = "g003_v_kinetic"
    kinetic_calls = kinetic.plan(
        artifact_dir=str(kinetic_dir),
        run_id=kinetic_run,
        seed=22012,
        copy_count=24,
        start_frame=1,
        end_frame=24,
        mops_available=False,
        width=640,
        height=360,
        time_limit=30,
        max_threads=4,
        render_preview=False,
    )
    extra, kinetic_renders = _render_calls(
        method_id=kinetic.id,
        run_id=kinetic_run,
        stage_node_path="/stage/OUT_G003_V_KINETIC_STAGED_STAGE",
        render_settings_path="/Render/G003_V_KINETIC_StagedSettings",
        source_sop_path="/obj/G003_V_KINETIC/OUT_G003_V_KINETIC_KINETIC_STAGED",
        source_start_frame=1,
        artifact_dir=kinetic_dir,
        max_points=20_000,
        max_primitives=20_000,
        max_memory_bytes=1_073_741_824,
        panel_count=1,
    )
    kinetic_calls.extend(extra)

    methods = [
        {
            "presentation_index": 0,
            "capability": PRESENTATION_ORDER[0],
            "label": "Particle Calligraphy",
            "seed": 5201,
            "mode": "silent_fixture",
            "artifact_dir": str(calligraphy_dir),
            "source_sop_path": f"{calligraphy_parent}/OUT_G003_V_CALLIGRAPHY_COMPARE",
            "stage_node_path": "/stage/OUT_G003_V_CALLIGRAPHY_LD_STAGE",
            "render_settings_path": "/Render/G003_V_CALLIGRAPHY_LD_Settings",
            "render_paths": calligraphy_renders,
            "calls": calligraphy_calls,
            "postprocess": [_ffmpeg_preview(calligraphy_dir, calligraphy_run)],
        },
        {
            "presentation_index": 1,
            "capability": PRESENTATION_ORDER[1],
            "label": "Differential Growth",
            "seed": 2401,
            "mode": "native_solver_memory_cache_only",
            "artifact_dir": str(differential_dir),
            "source_sop_path": f"{differential_parent}/OUT_G003_V_DIFFERENTIAL_COMPARE",
            "stage_node_path": "/stage/OUT_G003_V_DIFFERENTIAL_LD_STAGE",
            "render_settings_path": "/Render/G003_V_DIFFERENTIAL_LD_Settings",
            "render_paths": differential_renders,
            "calls": differential_calls,
            "postprocess": [_ffmpeg_preview(differential_dir, differential_run)],
        },
        {
            "presentation_index": 2,
            "capability": PRESENTATION_ORDER[2],
            "label": "Kinetic Instances",
            "seed": 22012,
            "mode": "native_only_mops_false",
            "artifact_dir": str(kinetic_dir),
            "source_sop_path": "/obj/G003_V_KINETIC/OUT_G003_V_KINETIC_KINETIC_STAGED",
            "stage_node_path": "/stage/OUT_G003_V_KINETIC_STAGED_STAGE",
            "render_settings_path": "/Render/G003_V_KINETIC_StagedSettings",
            "render_paths": kinetic_renders,
            "calls": kinetic_calls,
            "postprocess": [_ffmpeg_preview(kinetic_dir, kinetic_run)],
        },
    ]
    contact_sheet = artifacts / "review" / "g003_v_contact_sheet_1280x240.png"
    contact_labels = artifacts / "review" / "g003_v_contact_sheet_labels.json"
    review_index = artifacts / "review" / "index.html"
    contact_sheet_action = {
        "kind": "stable_order_contact_sheet",
        "executable": FFMPEG_PATH,
        "arguments": [
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            calligraphy_renders[-1],
            "-i",
            differential_renders[-1],
            "-i",
            kinetic_renders[-1],
            "-filter_complex",
            (
                "[0:v]scale=426:240[a];[1:v]scale=426:240[b];"
                "[2:v]scale=426:240[c];[a][b][c]hstack=inputs=3,scale=1280:240[v]"
            ),
            "-map",
            "[v]",
            str(contact_sheet),
        ],
        "labels_path": str(contact_labels),
        "labels": [method["label"] for method in methods],
        "max_seconds": 60,
        "max_output_bytes": 67_108_864,
        "network": False,
        "automatic_execution": False,
    }
    review_index_action = {
        "kind": "write_static_review_index",
        "output_path": str(review_index),
        "ordered_methods": [
            {
                "label": method["label"],
                "capability": method["capability"],
                "preview_path": method["postprocess"][0]["output_path"],
                "final_frame_path": method["render_paths"][-1],
            }
            for method in methods
        ],
        "network": False,
        "automatic_execution": False,
    }
    return {
        "schema": SCHEMA,
        "schema_version": "1.0",
        "state": "blocked_pending_exact_live_approval_and_valid_apprentice_license",
        "automatic_execution": False,
        "source_identity": dict(source_identity),
        "runtime": {
            "required": {
                "houdini_build": "22.0.368",
                "license": "Apprentice",
                "python": "3.13",
                "package_skiplist": "SideFXLabs22.0.json",
                "renderer": "BRAY_HdKarma",
            },
            "observed": dict(runtime_observation),
        },
        "project_root": str(project),
        "artifact_root": str(artifacts),
        "scene": {
            "mode": "one_fresh_untitled_scene_three_explicit_branches",
            "final_snapshot_dir": str(artifacts / "scenes"),
            "extension": ".hipnc",
            "overwrite": False,
        },
        "presentation_order": list(PRESENTATION_ORDER),
        "timeline": {
            "start": 1,
            "end": 24,
            "sample_frames": list(SAMPLE_FRAMES),
            "fps": 24,
            "preview_fps": 6,
            "restore_original_frame": True,
        },
        "render": {
            "width": 640,
            "height": 360,
            "delegate": "BRAY_HdKarma",
            "path_traced_samples_ceiling": 16,
            "frames_per_method": 12,
            "total_frames": 36,
            "seconds_per_frame": 30,
            "aggregate_seconds": 1200,
            "threads": 4,
        },
        "budgets": {
            "aggregate_peak_memory_bytes": 4_294_967_296,
            "aggregate_output_bytes": 1_073_741_824,
            "retained_cache_bytes": 0,
            "particle_calligraphy": {"max_points": 100_000, "max_primitives": 100_000},
            "differential_growth": {"max_points": 50_000, "max_primitives": 50_000},
            "kinetic_instances": {"max_points": 20_000, "max_primitives": 20_000},
        },
        "methods": methods,
        "postprocess": [contact_sheet_action, review_index_action],
        "review": {
            "contact_sheet": {
                "output_path": str(contact_sheet),
                "resolution": [1280, 240],
                "source_frames": [
                    calligraphy_renders[-1],
                    differential_renders[-1],
                    kinetic_renders[-1],
                ],
                "labels": [method["label"] for method in methods],
                "labels_path": str(contact_labels),
            },
            "html_index": str(review_index),
            "mechanics_only": True,
            "technical_presentation": {
                "particle_calligraphy": "three-candidate comparison with neutral ivory MaterialX",
                "differential_growth": "rest-versus-grown comparison with neutral ivory MaterialX",
                "kinetic_instances": "native-only layered display-color presentation; MOPs false",
                "interpretation": "presentation choices aid legibility and do not imply rank",
            },
            "automatic_ranking": False,
            "winner": None,
            "human_rating": None,
            "selected_for_continuation": None,
        },
        "approval": {
            "manifest_sha256_subject": None,
            "graph_edit": False,
            "frame_range_cook": False,
            "scene_save": False,
            "karma_external_process": False,
            "preview_encode": False,
            "plugin_install": False,
            "external_model": False,
            "creative_selection": False,
        },
        "stop_conditions": [
            "source identity or dirty state differs",
            "Houdini build or Apprentice license differs or is unavailable",
            "registered capability, recipe, operator, or parameter identity drifts",
            "artifact root or any output already exists",
            "checkpoint fails",
            "observed count, memory, time, frame, resolution, or byte budget is exceeded",
            "render is blank, cropped, corrupt, or temporally duplicate",
            "cancellation is requested",
        ],
        "official_references": [
            "https://www.sidefx.com/docs/houdini/nodes/lop/sopimport.html",
            "https://www.sidefx.com/docs/houdini/nodes/lop/karmarendersettings.html",
            "https://www.sidefx.com/docs/houdini/nodes/out/usdrender.html",
            "https://www.sidefx.com/docs/houdini/nodes/lop/camera.html",
            "https://www.sidefx.com/docs/houdini/nodes/lop/domelight.html",
        ],
    }


def visual_audition_manifest_sha256(manifest: dict[str, object]) -> str:
    """Hash canonical JSON with the self-referential approval subject normalized to null."""
    normalized = json.loads(json.dumps(manifest, ensure_ascii=False, allow_nan=False))
    approval = normalized.get("approval")
    if isinstance(approval, dict):
        approval["manifest_sha256_subject"] = None
    payload = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "FFMPEG_PATH",
    "PRESENTATION_ORDER",
    "SAMPLE_FRAMES",
    "SCHEMA",
    "build_visual_audition_manifest",
    "visual_audition_manifest_sha256",
]
