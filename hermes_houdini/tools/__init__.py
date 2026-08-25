"""Tool implementations (inside Houdini when HOM is available).

Each function is a bounded operation registered with @tool. HOM is accessed lazily via
get_hou(); functions raise clearly when called without Houdini. Tools cover: system/license,
HIP, read-only graph, geometry, cook, foundational SOP edit, VEX template, HDA.
"""

from __future__ import annotations

from typing import Any

from hda.catalog import register_bundled_hdas
from recipes.catalog import register_bundled_recipes

from .. import get_hou
from ..botanical import cook_validate_botanical
from ..calligraphy import apply_baked_audio_envelope, cook_validate_calligraphy
from ..cook import (
    COOK_JOBS,
    append_cook_record,
    execute_job,
    metrics_for_clean_node,
)
from ..copernicus import cook_validate_reaction, export_managed_image
from ..district import (
    build_district_assembly,
    build_district_graph,
    cook_district_graph,
    generate_district_manifest,
    validate_district,
)
from ..execution import current_envelope
from ..expressions import validate_hscript_expression
from ..graph_batch import apply_batch
from ..growth import populate_growth_solver
from ..ids import make_id
from ..inspect import describe_hip, describe_network, describe_node
from ..kinetic import (
    cook_validate_kinetic_presentation,
    cook_validate_kinetic_reliquary,
    validate_kinetic_stage,
)
from ..labs_atlas import cook_validate_labs_atlas
from ..local_critic import (
    materialize_calibration_corpus,
    probe_ollama,
    run_local_critique,
    score_calibration,
)
from ..material_foundry import cook_validate_material_foundry, validate_material_foundry_stage
from ..membrane import cook_validate_membranes
from ..mpm import cook_validate_mpm
from ..observation import graph_manifest, graph_svg, list_viewers, viewport_capture
from ..pdg_variations import (
    build_variation_gallery,
    build_variation_graph,
    cook_variation_graph,
    generate_variation_manifest,
)
from ..rbd import cook_validate_rbd
from ..registry import REGISTRY, tool
from ..schemas.command import Policy, Status, ToolResult
from ..solaris import (
    build_karma_render_rop,
    populate_materialx_library,
    render_karma_preview,
    validate_stage,
)
from ..transactions import save_checkpoint
from ..validation import node_type_exists, validate_cooked_node
from ..verification_routing import route_verification
from ..visual_verification import analyze_visual_evidence, build_critique_packet
from ..world_seed import cook_validate_world_seed_atlas, validate_world_seed_stage

register_bundled_recipes()
register_bundled_hdas()


# ---------------- system / license ----------------
@tool(
    "system.capabilities", risk="read_only", doc="Report Houdini build, Python, license, renderer."
)
def system_capabilities() -> dict[str, Any]:
    hou = get_hou()
    import sys

    return {
        "houdini_version": hou.applicationVersionString(),
        "python_version": sys.version.split()[0],
        "license": hou.licenseCategory().name() if hasattr(hou, "licenseCategory") else "unknown",
    }


@tool("registry.describe", risk="read_only", doc="List registered tools, recipes, and HDAs.")
def registry_describe(kind: str = "") -> dict[str, Any]:
    if kind and kind not in {"tool", "recipe", "hda"}:
        raise ValueError("kind must be tool, recipe, hda, or empty")
    entries = REGISTRY.describe()
    return {"entries": [entry for entry in entries if not kind or entry["kind"] == kind]}


@tool("recipe.describe", risk="read_only", doc="Describe one registered versioned recipe.")
def recipe_describe(recipe_id: str, version: str = "") -> dict[str, Any]:
    entry = REGISTRY.resolve(recipe_id, version or None)
    if entry is None or entry.kind != "recipe":
        raise ValueError(f"registered recipe not found: {recipe_id}@{version or 'latest'}")
    return {
        "id": entry.name,
        "version": entry.version,
        "risk": entry.risk,
        "summary": entry.doc,
        "meta": entry.meta,
    }


@tool(
    "recipe.instantiate",
    risk="medium",
    doc="Render and atomically instantiate one registered recipe with checkpoint/replay.",
)
def recipe_instantiate(
    recipe_id: str,
    parent_path: str,
    batch_id: str,
    checkpoint_dir: str,
    log_path: str,
    inputs: dict[str, Any] | None = None,
    version: str = "",
    ref_prefix: str = "",
    position_offset: list[float] | None = None,
    label: str = "Hermes recipe instantiate",
    checkpoint_stem: str = "hermes_recipe",
) -> ToolResult:
    entry = REGISTRY.resolve(recipe_id, version or None)
    if entry is None or entry.kind != "recipe":
        raise ValueError(f"registered recipe not found: {recipe_id}@{version or 'latest'}")
    fragment = entry.handler(
        parent_path=parent_path,
        inputs=inputs or {},
        ref_prefix=ref_prefix,
        position_offset=position_offset or [0.0, 0.0],
    )
    result = apply_batch(
        batch_id=batch_id,
        operations=fragment["operations"],
        checkpoint_dir=checkpoint_dir,
        log_path=log_path,
        label=label,
        checkpoint_stem=checkpoint_stem,
    )
    result.data["recipe"] = fragment["recipe"]
    result.data["recipe_outputs"] = fragment["outputs"]
    return result


@tool(
    "hda.build_registered",
    risk="medium",
    doc="Build a registered non-commercial HDA source into a new .hdanc artifact.",
)
def hda_build_registered(hda_id: str, dest_dir: str, version: str = "") -> dict[str, Any]:
    entry = REGISTRY.resolve(hda_id, version or None)
    if entry is None or entry.kind != "hda":
        raise ValueError(f"registered HDA not found: {hda_id}@{version or 'latest'}")
    result = entry.handler(dest_dir=dest_dir)
    result["registry"] = {"id": entry.name, "version": entry.version}
    return result


@tool("hip.describe", risk="read_only", doc="Summarize current HIP file.")
def hip_describe() -> dict[str, Any]:
    return describe_hip()


@tool(
    "hip.create_checkpoint",
    risk="low",
    doc="Save an incremented .hipnc checkpoint before risky work.",
)
def hip_create_checkpoint(output_dir: str, stem: str = "hermes") -> dict[str, Any]:
    path = save_checkpoint(output_dir, stem)
    return {"checkpoint": path}


@tool(
    "hip.save_snapshot",
    risk="low",
    doc="Save an incremented non-commercial HIP snapshot while preserving the in-memory name.",
)
def hip_save_snapshot(output_dir: str, stem: str = "hermes_final") -> dict[str, Any]:
    path = save_checkpoint(output_dir, stem)
    return {"artifact": path, "noncommercial": True}


# ---------------- read-only graph ----------------
@tool("network.describe", risk="read_only", doc="List children of a network context.")
def network_describe(path: str = "/obj") -> dict[str, Any]:
    return describe_network(path)


@tool("node.describe", risk="read_only", doc="Describe a node's type/flags/errors/userdata.")
def node_describe(path: str) -> dict[str, Any]:
    return describe_node(path)


@tool("node.find_by_hermes_id", risk="read_only", doc="Resolve a stable Hermes id to a path.")
def node_find_by_hermes_id(hermes_id: str) -> dict[str, Any]:
    from ..inspect import find_by_hermes_id

    path = find_by_hermes_id(hermes_id)
    return {"path": path}


# ---------------- geometry ----------------
@tool("geometry.metrics", risk="read_only", doc="Point/primitive counts + bounds for a node.")
def geometry_metrics(node_path: str) -> dict[str, Any]:
    return metrics_for_clean_node(node_path)


@tool(
    "geometry.validate",
    risk="read_only",
    doc="Validate already-cooked SOP metrics without triggering an implicit cook.",
)
def geometry_validate(node_path: str, expectations: dict[str, Any]) -> dict[str, Any]:
    return validate_cooked_node(node_path, expectations)


# ---------------- foundational graph edit ----------------
@tool(
    "node.create",
    risk="low",
    doc="Create a node with stable id + comment; supports exact operator type.",
)
def node_create(
    parent_path: str,
    operator_type: str,
    name: str = "",
    category: str = "Sop",
    role: str = "",
    parameters: dict[str, Any] | None = None,
    expressions: dict[str, str] | None = None,
    comment: str = "",
    created_by: str = "tool:node.create@1.0.0",
    stable_id: str = "",
    batch_id: str = "",
) -> dict[str, Any]:
    hou = get_hou()
    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f"parent not found: {parent_path}")
    if not node_type_exists(category, operator_type):
        raise ValueError(f"operator type {operator_type} not in category {category}")
    if stable_id:
        from ..inspect import find_by_hermes_id

        existing = find_by_hermes_id(stable_id)
        if existing is not None:
            raise ValueError(f"stable id already exists at {existing}: {stable_id}")
    node = parent.createNode(operator_type, node_name=name or None, exact_type_name=True)
    try:
        expressions = expressions or {}
        if set(parameters or {}).intersection(expressions):
            raise ValueError("a parameter cannot be both literal and expression")
        for parm_name, expression in expressions.items():
            validate_hscript_expression(expression, f"expressions.{parm_name}")
        missing = [
            parm_name
            for parm_name in [*(parameters or {}), *expressions]
            if node.parm(parm_name) is None and node.parmTuple(parm_name) is None
        ]
        if missing:
            raise ValueError(
                f"operator {operator_type} has no parameters: {', '.join(sorted(missing))}"
            )
        hermes_id = stable_id or make_id(category, node.path())
        node.setUserData("hermes_id", hermes_id)
        node.setUserData("hermes_role", role)
        node.setUserData("hermes_created_by", created_by)
        node.setUserData("hermes_manifest_version", "1")
        if batch_id:
            node.setUserData("hermes_batch_id", batch_id)
        if comment:
            node.setComment(comment)
        for k, v in (parameters or {}).items():
            parm = node.parm(k)
            if parm is not None:
                parm.set(v)
            else:
                node.parmTuple(k).set(v)
        for parm_name, expression in expressions.items():
            parm = node.parm(parm_name)
            if parm is None:
                raise ValueError(f"expression parameter must be scalar: {parm_name}")
            parm.setExpression(expression, language=hou.exprLanguage.Hscript)
    except Exception:
        # Roll back only the node created by this call; never leave a partial node.
        node.destroy()
        raise
    return {
        "hermes_id": hermes_id,
        "path": node.path(),
        "type": node.type().name(),
        "category": category,
    }


@tool("node.connect", risk="medium", doc="Connect output of one node to an input of another.")
def node_connect(
    from_path: str, to_path: str, input_index: int = 0, output_index: int = 0
) -> dict[str, Any]:
    hou = get_hou()
    src = hou.node(from_path)
    dst = hou.node(to_path)
    if src is None or dst is None:
        raise ValueError("node not found")
    dst.setInput(input_index, src, output_index)
    return {"connected": [from_path, output_index, to_path, input_index]}


@tool(
    "node.set_parameter",
    risk="low",
    doc="Set a single parameter (preserves expressions if present).",
)
def node_set_parameter(path: str, name: str, value: Any) -> dict[str, Any]:
    hou = get_hou()
    node = hou.node(path)
    if node is None:
        raise ValueError(f"node not found: {path}")
    parm = node.parm(name)
    if parm is None:
        raise ValueError(f"missing parameter {name}")
    if parm.keyframes():
        # Expressions are represented as keyframes; literal assignment must never clobber them.
        raise ValueError(f"parameter {name} has an expression; use set_expression")
    parm.set(value)
    return {"path": path, "parm": name, "value": value}


@tool(
    "graph.apply_batch",
    risk="medium",
    doc="Apply one checkpointed, allowlisted graph-edit batch with rollback and replay log.",
)
def graph_apply_batch(
    batch_id: str,
    operations: list[dict[str, Any]],
    checkpoint_dir: str,
    log_path: str,
    label: str = "Hermes graph batch",
    checkpoint_stem: str = "hermes_graph",
) -> ToolResult:
    return apply_batch(
        batch_id=batch_id,
        operations=operations,
        checkpoint_dir=checkpoint_dir,
        log_path=log_path,
        label=label,
        checkpoint_stem=checkpoint_stem,
    )


# ---------------- cook ----------------
def _submitted_cook_job(
    node_path: str,
    estimate: dict[str, Any],
    log_path: str,
    scope: str,
    frame: float | None,
    frame_range: list[float] | None,
    force: bool,
):
    hou = get_hou()
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"node not found: {node_path}")
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else Policy()
    job = COOK_JOBS.submit(
        node_path=node.path(),
        node_session_id=node.sessionId(),
        scope=scope,
        frame=frame,
        frame_range=frame_range,
        force=force,
        estimate=estimate,
        policy=policy,
        log_path=log_path,
    )
    try:
        append_cook_record(log_path, "submitted", job)
    except Exception:
        COOK_JOBS.cancel(job.job_id)
        raise
    return job


@tool(
    "cook.job.submit",
    risk="low",
    doc="Submit a bounded cook job with an explicit scope, estimate, policy, and log.",
)
def cook_job_submit(
    node_path: str,
    estimate: dict[str, Any],
    log_path: str,
    scope: str = "single_node",
    frame: float | None = None,
    frame_range: list[float] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    return _submitted_cook_job(
        node_path, estimate, log_path, scope, frame, frame_range, force
    ).as_dict()


@tool("cook.job.status", risk="read_only", doc="Read one cook job's current state and result.")
def cook_job_status(job_id: str) -> dict[str, Any]:
    return COOK_JOBS.get(job_id).as_dict()


@tool("cook.job.cancel", risk="low", doc="Cancel a cook job before it starts.")
def cook_job_cancel(job_id: str) -> dict[str, Any]:
    job = COOK_JOBS.cancel(job_id)
    append_cook_record(job.log_path, "cancelled", job)
    return job.as_dict()


@tool("cook.job.run", risk="low", doc="Run one previously submitted cook job on the main thread.")
def cook_job_run(job_id: str) -> ToolResult:
    job = COOK_JOBS.begin(job_id)
    try:
        result = execute_job(job)
    except Exception as exc:
        result = ToolResult(status=Status.ERROR)
        result.errors.append(f"unexpected cook failure: {type(exc).__name__}: {exc}")
    COOK_JOBS.finish(job_id, result)
    try:
        append_cook_record(job.log_path, "finished", job)
    except Exception as exc:
        result.status = Status.PARTIAL
        result.errors.append(f"cook provenance failure: {exc}")
        COOK_JOBS.finish(job_id, result)
    result.data["job"] = COOK_JOBS.get(job_id).as_dict()
    result.artifacts.append(job.log_path)
    return result


@tool(
    "cook.node",
    risk="low",
    doc="Submit and immediately run one bounded cook job; use cook.job.* for cancellation.",
)
def cook_node_tool(
    node_path: str,
    estimate: dict[str, Any],
    log_path: str,
    scope: str = "single_node",
    frame: float | None = None,
    frame_range: list[float] | None = None,
    force: bool = False,
) -> ToolResult:
    job = _submitted_cook_job(node_path, estimate, log_path, scope, frame, frame_range, force)
    return cook_job_run(job.job_id)


# ---------------- PDG / local variations ----------------
@tool(
    "pdg.variation.build",
    risk="medium",
    doc="Build a checkpointed native Wedge/ROP Geometry local variation graph.",
)
def pdg_variation_build(**arguments: Any) -> ToolResult:
    return build_variation_graph(**arguments)


@tool(
    "pdg.variation.generate",
    risk="low",
    doc="Generate static Wedge work items and an immutable human-rating manifest.",
)
def pdg_variation_generate(topnet_path: str, output_path: str) -> dict[str, Any]:
    return generate_variation_manifest(topnet_path=topnet_path, output_path=output_path)


@tool(
    "pdg.variation.cook",
    risk="medium",
    doc="Run bounded one-slot local PDG geometry jobs after explicit external-process consent.",
)
def pdg_variation_cook(
    topnet_path: str,
    manifest_path: str,
    result_path: str,
    scene_path: str,
    log_path: str,
    estimate: dict[str, Any],
) -> ToolResult:
    return cook_variation_graph(
        topnet_path=topnet_path,
        manifest_path=manifest_path,
        result_path=result_path,
        scene_path=scene_path,
        log_path=log_path,
        estimate=estimate,
    )


@tool(
    "pdg.variation.build_gallery",
    risk="medium",
    doc="Build a checkpointed native-SOP comparison gallery from successful variation outputs.",
)
def pdg_variation_build_gallery(**arguments: Any) -> ToolResult:
    return build_variation_gallery(**arguments)


# ---------------- procedural districts ----------------
@tool(
    "district.build",
    risk="medium",
    doc="Build checkpointed native-SOP lot profiles and a one-slot Wedge/ROP district graph.",
)
def district_build(**arguments: Any) -> ToolResult:
    return build_district_graph(**arguments)


@tool(
    "district.generate",
    risk="low",
    doc="Generate static district Wedge items and freeze their exact immutable plan manifest.",
)
def district_generate(topnet_path: str, output_path: str) -> dict[str, Any]:
    return generate_district_manifest(topnet_path=topnet_path, output_path=output_path)


@tool(
    "district.cook",
    risk="medium",
    doc="Run approved one-slot local district cache jobs with immutable outputs and budgets.",
)
def district_cook(**arguments: Any) -> ToolResult:
    return cook_district_graph(**arguments)


@tool(
    "district.assemble",
    risk="medium",
    doc="Build editable district and equal-scale no-winner gallery branches from validated caches.",
)
def district_assemble(**arguments: Any) -> ToolResult:
    return build_district_assembly(**arguments)


@tool(
    "district.validate",
    risk="low",
    doc="Validate district TOP contracts, immutable caches, assembly, gallery, and selection.",
)
def district_validate(**arguments: Any) -> dict[str, Any]:
    return validate_district(**arguments)


# ---------------- native generative feedback ----------------
@tool(
    "growth.solver.populate",
    risk="medium",
    doc="Populate one pristine Solver SOP with a bounded native differential-growth subgraph.",
)
def growth_solver_populate(**arguments: Any) -> ToolResult:
    return populate_growth_solver(**arguments)


# ---------------- native botanical grammars ----------------
@tool(
    "botanical.validate",
    risk="low",
    doc="Cook and validate three bounded registered native L-System botanical grammars.",
)
def botanical_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_botanical(**arguments)


# ---------------- native particle calligraphy ----------------
@tool(
    "motion.calligraphy.validate",
    risk="low",
    doc="Cook and validate a bounded three-candidate native Particle Trail calligraphy graph.",
)
def motion_calligraphy_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_calligraphy(**arguments)


@tool(
    "motion.calligraphy.apply_audio_envelope",
    risk="medium",
    doc="Checkpoint and keyframe native Particle wind controls from project-relative baked JSON.",
)
def motion_calligraphy_apply_audio_envelope(**arguments: Any) -> ToolResult:
    return apply_baked_audio_envelope(**arguments)


# ---------------- native Vellum membrane studies ----------------
@tool(
    "simulate.membrane.validate",
    risk="low",
    doc="Cook and validate three pinned native Vellum membrane material candidates.",
)
def simulate_membrane_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_membranes(**arguments)


@tool(
    "simulate.rbd.validate",
    risk="low",
    doc="Cook and validate bounded native RBD fracture, Bullet, and transform-cache contracts.",
)
def simulate_rbd_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_rbd(**arguments)


@tool(
    "simulate.mpm.validate",
    risk="medium",
    doc="Cook and validate one bounded native multi-material MPM proxy with durable progress.",
)
def simulate_mpm_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_mpm(**arguments)


# ---------------- Copernicus / image generation ----------------
@tool(
    "cop.reaction.validate",
    risk="low",
    doc="Cook and numerically validate three bounded native Reaction-Diffusion patterns.",
)
def cop_reaction_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_reaction(**arguments)


@tool(
    "cop.material_foundry.validate",
    risk="low",
    doc="Cook and validate three native named PBR channel sets and USD Material COP bindings.",
)
def cop_material_foundry_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_material_foundry(**arguments)


@tool(
    "cop.image.export",
    risk="medium",
    doc="Render one managed Copernicus ROP Image to a new bounded PNG artifact.",
)
def cop_image_export(**arguments: Any) -> ToolResult:
    return export_managed_image(**arguments)


# ---------------- Solaris / look development ----------------
@tool(
    "solaris.materialx.populate",
    risk="medium",
    doc="Populate one managed Material Library LOP with three editable MaterialX candidates.",
)
def solaris_materialx_populate(**arguments: Any) -> ToolResult:
    return populate_materialx_library(**arguments)


@tool(
    "solaris.stage.validate",
    risk="low",
    doc="Explicitly compose one bounded LOP stage and verify USD prim/material contracts.",
)
def solaris_stage_validate(**arguments: Any) -> dict[str, Any]:
    return validate_stage(**arguments)


@tool(
    "solaris.material_foundry.validate",
    risk="low",
    doc="Compose the three-swatch stage and verify every USD binding and connected MaterialX output.",
)
def solaris_material_foundry_validate(**arguments: Any) -> dict[str, Any]:
    return validate_material_foundry_stage(**arguments)


# ---------------- native World Seed Atlas ----------------
@tool(
    "world_seed.validate",
    risk="low",
    doc="Cook and validate three fixed-order native HeightField biome contracts.",
)
def world_seed_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_world_seed_atlas(**arguments)


@tool(
    "world_seed.labs.validate",
    risk="low",
    doc="Validate capability-gated native/Labs World Seed comparison contracts.",
)
def world_seed_labs_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_labs_atlas(**arguments)


@tool(
    "motion.kinetic_reliquary.validate",
    risk="low",
    doc="Validate native and optional-MOPs kinetic reliquary branches across bounded frames.",
)
def motion_kinetic_reliquary_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_kinetic_reliquary(**arguments)


@tool(
    "motion.kinetic_reliquary.presentation.validate",
    risk="low",
    doc="Validate camera-facing layered presentation bounds, color, budgets, and temporal change.",
)
def motion_kinetic_reliquary_presentation_validate(**arguments: Any) -> dict[str, Any]:
    return cook_validate_kinetic_presentation(**arguments)


@tool(
    "solaris.kinetic_reliquary.validate",
    risk="low",
    doc="Validate the kinetic reliquary USD/Karma stage without material assumptions.",
)
def solaris_kinetic_reliquary_validate(**arguments: Any) -> dict[str, Any]:
    return validate_kinetic_stage(**arguments)


@tool(
    "solaris.world_seed.validate",
    risk="low",
    doc="Validate the simultaneous three-world USD/Karma atlas stage.",
)
def solaris_world_seed_validate(**arguments: Any) -> dict[str, Any]:
    return validate_world_seed_stage(**arguments)


@tool(
    "solaris.karma_rop.build",
    risk="medium",
    doc="Build a checkpointed USD Render ROP configured for one bounded Karma CPU preview.",
)
def solaris_karma_rop_build(**arguments: Any) -> ToolResult:
    return build_karma_render_rop(**arguments)


@tool(
    "render.karma.preview",
    risk="external",
    doc="Launch one approved, bounded Karma CPU frame through a managed USD Render ROP.",
)
def render_karma_preview_tool(**arguments: Any) -> ToolResult:
    return render_karma_preview(**arguments)


# ---------------- observation ----------------
@tool("observation.viewers", risk="read_only", doc="List explicit GUI viewer/viewport handles.")
def observation_viewers() -> dict[str, Any]:
    return list_viewers()


@tool("graph.capture_svg", risk="low", doc="Render a selection-independent network SVG.")
def graph_capture_svg(node_path: str, output_path: str, max_nodes: int = 500) -> dict[str, Any]:
    return graph_svg(node_path, output_path, max_nodes=max_nodes)


@tool(
    "graph.capture_manifest",
    risk="low",
    doc="Write a graph/provenance JSON manifest with optional clean geometry metrics.",
)
def graph_capture_manifest(
    node_path: str,
    output_path: str,
    public_parameters: dict[str, list[str]] | None = None,
    metric_node_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return graph_manifest(
        node_path=node_path,
        output_path=output_path,
        public_parameters=public_parameters,
        metric_node_paths=metric_node_paths,
        metadata=metadata,
    )


@tool(
    "viewport.capture",
    risk="low",
    doc="Capture one named GUI viewport through an explicit camera at Apprentice resolution.",
)
def viewport_capture_tool(
    viewer_name: str,
    viewport_name: str,
    camera_path: str,
    output_path: str,
    frame: float,
    width: int = 1280,
    height: int = 720,
) -> dict[str, Any]:
    return viewport_capture(
        viewer_name=viewer_name,
        viewport_name=viewport_name,
        camera_path=camera_path,
        output_path=output_path,
        frame=frame,
        width=width,
        height=height,
    )


@tool(
    "visual.analyze",
    risk="low",
    doc="Run deterministic exposure, grid composition, sequence motion, and duplicate checks.",
)
def visual_analyze(**arguments: Any) -> dict[str, Any]:
    return analyze_visual_evidence(**arguments)


@tool(
    "verification.critique.package",
    risk="low",
    doc="Hash images, graph, validation, and code into an advisory multimodal critique packet.",
)
def verification_critique_package(**arguments: Any) -> dict[str, Any]:
    return build_critique_packet(**arguments)


@tool(
    "verification.local_critic.probe",
    risk="external",
    doc="Probe an already-running IPv4-loopback Ollama service without starting or mutating it.",
)
def verification_local_critic_probe(**arguments: Any) -> dict[str, Any]:
    return probe_ollama(**arguments)


@tool(
    "verification.local_critic.run",
    risk="external",
    doc="Run one explicitly enabled, bounded, advisory critique with an installed local model.",
)
def verification_local_critic_run(**arguments: Any) -> dict[str, Any]:
    return run_local_critique(**arguments)


@tool(
    "verification.local_critic.calibrate",
    risk="low",
    doc="Score saved local-critic responses against the deterministic mechanical corpus.",
)
def verification_local_critic_calibrate(**arguments: Any) -> dict[str, Any]:
    return score_calibration(**arguments)


@tool(
    "verification.local_critic.corpus.build",
    risk="low",
    doc="Materialize deterministic bad-image fixtures and hashed packets for model calibration.",
)
def verification_local_critic_corpus_build(**arguments: Any) -> dict[str, Any]:
    return materialize_calibration_corpus(**arguments)


@tool(
    "verification.route",
    risk="low",
    doc="Route verified reports to repair, calibration, optional critique, or human review.",
)
def verification_route(**arguments: Any) -> dict[str, Any]:
    return route_verification(**arguments)


# ---------------- VEX template ----------------
@tool("vex.validate_snippet", risk="read_only", doc="Sanity-check a VEX snippet text.")
def vex_validate_snippet(code: str) -> dict[str, Any]:
    # Lightweight structural check; real compile needs Houdini VEX context.
    issues = []
    if "@" in code and "float" not in code and "int" not in code and "vector" not in code:
        issues.append("uses @ attributes but no type declaration found")
    if code.count("{") != code.count("}"):
        issues.append("unbalanced braces")
    return {"valid": not issues, "issues": issues}


# ---------------- HDA ----------------
@tool(
    "hda.create_from_subnet",
    risk="medium",
    doc="Wrap a subnet into a namespaced, versioned HDA definition.",
)
def hda_create_from_subnet(
    subnet_path: str, namespace: str = "hermes", name: str = "tool", version: str = "1.0"
) -> dict[str, Any]:
    hou = get_hou()
    subnet = hou.node(subnet_path)
    if subnet is None:
        raise ValueError(f"subnet not found: {subnet_path}")
    type_name = f"{namespace}::{name}::{version}"
    subnet.createDigitalAsset(name=type_name, hda_file_name=None, save_as_embedded=True)
    return {
        "type_name": type_name,
        "namespace": namespace,
        "version": version,
        "noncommercial": True,
    }


__all__ = ["REGISTRY"]
