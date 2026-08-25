"""hython integration tests. Require Houdini (`hou`). Skipped otherwise."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

hou = pytest.importorskip("hou")

from bridge.auth import sign  # noqa: E402
from bridge.interactive import forward_signed_payload  # noqa: E402
from hermes_houdini.botanical import cook_validate_botanical  # noqa: E402
from hermes_houdini.copernicus import cook_validate_reaction  # noqa: E402
from hermes_houdini.dispatcher import Dispatcher  # noqa: E402
from hermes_houdini.policy import ApprenticePolicy, default_policy  # noqa: E402
from hermes_houdini.runtime import InteractiveRuntime  # noqa: E402
from hermes_houdini.schemas.command import CommandEnvelope, Policy  # noqa: E402
from hermes_houdini.skill_loader import load_skill  # noqa: E402
from hermes_houdini.tools import REGISTRY  # noqa: E402  (registers tools)
from hermes_houdini.transactions import next_checkpoint_path  # noqa: E402
from recipes.parser import load_recipe  # noqa: E402


def _runtime_roundtrip(runtime, secret, envelope):
    payload = json.dumps(envelope.as_dict(), separators=(",", ":")).encode()
    result = {}
    errors = []

    def send():
        try:
            result.update(
                forward_signed_payload(
                    payload, sign(secret, payload), port=runtime.port, timeout=3.0
                )
            )
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=send)
    thread.start()
    deadline = time.monotonic() + 3.0
    while thread.is_alive() and time.monotonic() < deadline:
        runtime.pump()
        thread.join(timeout=0.01)
    thread.join(timeout=0.1)
    assert not thread.is_alive()
    assert not errors, errors
    return result


def test_registry_has_tools():
    tools = REGISTRY.list(kind="tool")
    names = {t.name for t in tools}
    assert "node.create" in names
    assert "hip.describe" in names
    assert "graph.capture_manifest" in names
    assert "hip.save_snapshot" in names
    assert "growth.solver.populate" in names
    assert "cop.reaction.validate" in names
    assert "cop.material_foundry.validate" in names
    assert "cop.image.export" in names
    assert "botanical.validate" in names
    assert "motion.calligraphy.validate" in names
    assert "motion.calligraphy.apply_audio_envelope" in names
    assert "visual.analyze" in names
    assert "verification.critique.package" in names
    assert "verification.local_critic.probe" in names
    assert "verification.local_critic.run" in names
    assert "verification.local_critic.calibrate" in names
    assert "verification.local_critic.corpus.build" in names
    assert "verification.route" in names
    assert "simulate.membrane.validate" in names
    assert "simulate.mpm.validate" in names
    assert "simulate.rbd.validate" in names
    assert "solaris.material_foundry.validate" in names
    assert "world_seed.validate" in names
    assert "solaris.world_seed.validate" in names
    assert "district.build" in names
    assert "district.generate" in names
    assert "district.cook" in names
    assert "district.assemble" in names
    assert "district.validate" in names


def test_create_node_and_describe():
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_TEST_GEO")
    d = Dispatcher(policy=ApprenticePolicy())
    env = CommandEnvelope(
        tool="node.create",
        request_id="t1",
        arguments={
            "parent_path": geo.path(),
            "operator_type": "box",
            "name": "SRC_BOX",
            "category": "Sop",
            "role": "test",
        },
    )
    out = d.process_one(env)
    assert out.result.status.value == "success"
    assert out.result.data["type"] == "box"
    geo.destroy()


def test_checkpoint_path_increment(tmp_path):
    base = str(tmp_path / "shot_v001.hipnc")
    p1 = next_checkpoint_path(base)
    # Should increment to shot002.hipnc (preserving the _v prefix in the version)
    assert p1.endswith("002.hipnc"), f"got {p1}"


def test_bundled_recipe_nodes_match_pinned_houdini_build():
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_RECIPE_TEST", run_init_scripts=False)
    dispatcher = Dispatcher(policy=ApprenticePolicy())
    lop_nodes = []
    copnet = hou.node("/img").createNode(
        "copnet", node_name="HERMES_COP_RECIPE_TEST", run_init_scripts=False
    )
    topnet = hou.node("/tasks").createNode(
        "topnet", node_name="HERMES_TOP_RECIPE_TEST", run_init_scripts=False
    )
    try:
        for recipe_path, parent_path, overrides in (
            (
                "recipes/lop/relic_lookdev_stage.yaml",
                "/stage",
                {
                    "source_sop_path": "/obj/HERMES_RECIPE_TEST",
                    "render_picture": "/tmp/hermes_recipe_test.png",
                    "run_code": "TYPE_TEST",
                },
            ),
            ("recipes/sop/fractal_relic_candidate.yaml", geo.path(), {}),
            ("recipes/sop/differential_growth_loop.yaml", geo.path(), {}),
            ("recipes/sop/lsystem_botanical.yaml", geo.path(), {}),
            ("recipes/sop/scatter_cluster_points.yaml", geo.path(), {}),
            ("recipes/sop/sweep_petals.yaml", geo.path(), {}),
            ("recipes/sop/vellum_relic_drop.yaml", geo.path(), {}),
            (
                "recipes/sop/vellum_membrane_lab.yaml",
                geo.path(),
                {"run_code": "TYPE_MEMBRANE"},
            ),
            (
                "recipes/sop/mpm_matter_sculpture.yaml",
                geo.path(),
                {"run_code": "TYPE_MPM", "particle_separation": 0.2},
            ),
            (
                "recipes/sop/particle_calligraphy.yaml",
                geo.path(),
                {"run_code": "TYPE_CALLIGRAPHY"},
            ),
            (
                "recipes/sop/procedural_building_lot.yaml",
                geo.path(),
                {"run_code": "TYPE_DISTRICT"},
            ),
            (
                "recipes/sop/rbd_art_directed_fracture.yaml",
                geo.path(),
                {
                    "run_code": "TYPE_RBD",
                    "transform_cache": "/tmp/type_rbd_transforms.$F4.bgeo.sc",
                },
            ),
            (
                "recipes/cop/reaction_diffusion_pattern.yaml",
                copnet.path(),
                {
                    "run_code": "TYPE_REACTION",
                    "end_small_path": f"{copnet.path()}/TYPE_REACTION_SMALL_WAVES",
                    "end_large_path": f"{copnet.path()}/TYPE_REACTION_LARGE_WAVES",
                    "end_spots_path": f"{copnet.path()}/TYPE_REACTION_SPOTS",
                    "contact_output": "/tmp/type_reaction_contact.png",
                    "selected_output": "/tmp/type_reaction_selected.png",
                },
            ),
            (
                "recipes/top/procedural_district.yaml",
                topnet.path(),
                {
                    "source_sop_path": f"{geo.path()}/OUT_BUILDING",
                    "output_pattern": "/tmp/type_district_`@wedgeindex`.bgeo.sc",
                    "temp_dir": "/tmp/type_district_pdg",
                    "lot_count": 4,
                },
            ),
        ):
            recipe = load_recipe(recipe_path)
            for call in recipe.render(parent_path, **overrides):
                if call["tool"] != "node.create":
                    continue
                env = CommandEnvelope(tool=call["tool"], arguments=call["arguments"])
                outcome = dispatcher.process_one(env)
                assert outcome.result.status.value == "success", outcome.result.errors
                if parent_path == "/stage":
                    lop_nodes.append(hou.node(outcome.result.data["path"]))
    finally:
        for node in reversed(lop_nodes):
            if node is not None and node.parent() is not None:
                node.destroy()
        if copnet.parent() is not None:
            copnet.destroy()
        if topnet.parent() is not None:
            topnet.destroy()
        geo.destroy()


def test_relic_lookdev_skill_builds_materialx_and_validates_usd_stage_without_render(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_LOOKDEV_SOURCE", run_init_scripts=False)
    sphere = geo.createNode("sphere", node_name="SOURCE_RELIC")
    sphere.parmTuple("rad").set((1.0, 1.0, 1.0))
    source = geo.createNode("null", node_name="OUT_GEO")
    source.setInput(0, sphere)
    skill = load_skill("skills/lookdev.relic_stage")
    calls = skill.plan(
        source_sop_path=source.path(),
        artifact_dir=str(tmp_path),
        run_id="hython_lookdev",
        candidate_index=1,
        width=320,
        height=180,
        render_preview=False,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    created_lops = []
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        created_lops = [
            node
            for node in hou.node("/stage").children()
            if node.name().startswith("HYTHON_LOOKDEV")
        ] + [hou.node("/stage/OUT_HYTHON_LOOKDEV_STAGE")]
        library = hou.node("/stage/HYTHON_LOOKDEV_MATERIALS")
        selector = hou.node("/stage/HYTHON_LOOKDEV_SELECT_MATERIAL")
        assert library is not None and selector is not None
        assert selector.parm("input").eval() == 1
        builders = [child for child in library.children() if child.type().name() == "subnet"]
        assert len(builders) == 3
        assert all(
            any(child.type().name() == "mtlxstandard_surface" for child in builder.children())
            for builder in builders
        )
        stage_result = results[2].data
        assert stage_result["prim_count"] > 0
        assert stage_result["binding"]["material_path"] == "/materials/HYTHON_LOOKDEV_amber"
        assert stage_result["errors"] == []
        assert (tmp_path / "observations" / "hython_lookdev_lop_graph.svg").is_file()
        manifest = json.loads(
            (tmp_path / "manifests" / "hython_lookdev_lookdev_manifest.json").read_text()
        )
        assert manifest["metadata"]["selection"]["winner"] is None
        assert manifest["metadata"]["selection"]["automatic_ranking"] is False
        assert list((tmp_path / "scenes").glob("lookdev_hython_lookdev_final_v*.hipnc"))
    finally:
        for node in reversed(created_lops):
            if node is not None and node.parent() is not None:
                node.destroy()
        if geo.parent() is not None:
            geo.destroy()


def test_node_create_rejects_unknown_parameters_without_leaving_partial_node():
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_INVALID_PARM_TEST", run_init_scripts=False)
    dispatcher = Dispatcher(policy=ApprenticePolicy())
    try:
        env = CommandEnvelope(
            tool="node.create",
            arguments={
                "parent_path": geo.path(),
                "operator_type": "box",
                "name": "INVALID_BOX",
                "parameters": {"does_not_exist": 1},
            },
        )
        outcome = dispatcher.process_one(env)
        assert outcome.result.status.value == "error"
        assert geo.node("INVALID_BOX") is None
    finally:
        geo.destroy()


def test_node_set_parameter_accepts_literals_and_preserves_expressions():
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_SET_PARM_TEST", run_init_scripts=False)
    box = geo.createNode("box", node_name="BOX")
    dispatcher = Dispatcher(policy=ApprenticePolicy())
    try:
        literal = dispatcher.process_one(
            CommandEnvelope(
                tool="node.set_parameter",
                request_id="set-literal",
                arguments={"path": box.path(), "name": "sizex", "value": 2.5},
            )
        ).result
        assert literal.status.value == "success", literal.errors
        assert box.parm("sizex").eval() == pytest.approx(2.5)

        box.parm("sizex").setExpression("1+1")
        protected = dispatcher.process_one(
            CommandEnvelope(
                tool="node.set_parameter",
                request_id="preserve-expression",
                arguments={"path": box.path(), "name": "sizex", "value": 1.0},
            )
        ).result
        assert protected.status.value == "error"
        assert "has an expression" in protected.errors[0]
        assert box.parm("sizex").expression() == "1+1"
    finally:
        geo.destroy()


def test_interactive_runtime_edits_one_persistent_houdini_scene_with_approval():
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_RUNTIME_TEST", run_init_scripts=False)
    secret = "hython-runtime-test-secret"
    runtime = InteractiveRuntime(
        secret=secret,
        port=0,
        dispatcher=Dispatcher(policy=ApprenticePolicy()),
        request_timeout=2.0,
    )
    runtime.start()
    try:
        source = _runtime_roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="node.create",
                request_id="hython-create-source",
                arguments={
                    "parent_path": geo.path(),
                    "operator_type": "sphere",
                    "name": "SRC_RUNTIME",
                    "role": "test_source",
                },
            ),
        )
        output = _runtime_roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="node.create",
                request_id="hython-create-output",
                arguments={
                    "parent_path": geo.path(),
                    "operator_type": "null",
                    "name": "OUT_RUNTIME",
                    "role": "test_output",
                },
            ),
        )
        blocked = _runtime_roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="node.connect",
                request_id="hython-connect",
                arguments={
                    "from_path": source["data"]["path"],
                    "to_path": output["data"]["path"],
                },
            ),
        )
        assert blocked["status"] == "blocked"
        assert geo.node("OUT_RUNTIME").input(0) is None

        approval_id = blocked["data"]["approval"]["approval_id"]
        granted = _runtime_roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="approval.grant",
                request_id="hython-connect-grant",
                arguments={"approval_id": approval_id},
            ),
        )
        described = _runtime_roundtrip(
            runtime,
            secret,
            CommandEnvelope(
                tool="node.describe",
                request_id="hython-describe-output",
                arguments={"path": output["data"]["path"]},
            ),
        )
        assert granted["status"] == "success"
        assert granted["data"]["approval"]["decision"] == "granted"
        assert geo.node("OUT_RUNTIME").input(0) == geo.node("SRC_RUNTIME")
        assert described["data"]["user_data"]["hermes_role"] == "test_output"
    finally:
        runtime.stop()
        geo.destroy()


def _grant_batch(dispatcher, request_id, arguments):
    blocked = dispatcher.process_one(
        CommandEnvelope(tool="graph.apply_batch", request_id=request_id, arguments=arguments)
    )
    assert blocked.result.status.value == "blocked"
    approval_id = blocked.result.data["approval"]["approval_id"]
    return dispatcher.process_one(
        CommandEnvelope(
            tool="approval.grant",
            request_id=f"{request_id}-grant",
            arguments={"approval_id": approval_id},
        )
    ).result


def _dispatch_planned_call(dispatcher, call):
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


def test_particle_calligraphy_skill_validates_native_temporal_fixture(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_CALLIGRAPHY_TEST", run_init_scripts=False)
    original_frame = hou.frame()
    skill = load_skill("skills/motion.particle_calligraphy")
    calls = skill.plan(
        parent_node_id=geo.path(),
        artifact_dir=str(tmp_path),
        run_id="hython_calligraphy",
        start_frame=1,
        end_frame=12,
        seed=5201,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        hou.setFrame(7)
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        assert hou.frame() == pytest.approx(7)
        validation = json.loads(
            (tmp_path / "manifests" / "hython_calligraphy_calligraphy_validation.json").read_text()
        )
        assert len(validation["frames"]) == 12
        assert validation["peak_trail_points"] > 0
        assert validation["known_compatibility"]["status"] == "verified_workaround"
        assert validation["selection"]["winner"] is None
        assert validation["selection"]["automatic_ranking"] is False
        assert geo.node("OUT_HYTHON_CALLIGRAPHY_COMPARE").isDisplayFlagSet()
        comparison = geo.node("OUT_HYTHON_CALLIGRAPHY_COMPARE")
        labels = geo.node("OUT_HYTHON_CALLIGRAPHY_LABELS")
        assert labels is not None
        assert labels.userData("hermes_role") == "calligraphy_labels_contract"
        assert labels not in comparison.inputAncestors()
        assert [
            node.parm("text").evalAsString()
            for node in (
                geo.node("HYTHON_CALLIGRAPHY_ARC_LABEL"),
                geo.node("HYTHON_CALLIGRAPHY_FAN_LABEL"),
                geo.node("HYTHON_CALLIGRAPHY_ORBIT_LABEL"),
            )
        ] == ["ARC  seed 5201", "FAN  seed 5302", "ORBIT  seed 5412"]
        assert list(geo.node("HYTHON_CALLIGRAPHY_SELECT_CALLIGRAPHY").inputs())[:3] == [
            geo.node("OUT_HYTHON_CALLIGRAPHY_ARC"),
            geo.node("OUT_HYTHON_CALLIGRAPHY_FAN"),
            geo.node("OUT_HYTHON_CALLIGRAPHY_ORBIT"),
        ]
        assert list((tmp_path / "scenes").glob("calligraphy_hython_calligraphy_final_v*.hipnc"))
    finally:
        hou.setFrame(original_frame)
        if geo.parent() is not None:
            geo.destroy()


def test_particle_calligraphy_applies_project_relative_baked_envelope(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_CALLIGRAPHY_AUDIO", run_init_scripts=False)
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "envelope.json").write_text(
        json.dumps(
            {
                "schema": "hermes.audio_envelope.v1",
                "fps": hou.fps(),
                "samples": [0.0, 0.25, 0.5, 0.75, 1.0],
            }
        ),
        encoding="utf-8",
    )
    skill = load_skill("skills/motion.particle_calligraphy")
    calls = skill.plan(
        parent_node_id=geo.path(),
        artifact_dir=str(tmp_path),
        project_root=str(tmp_path),
        audio_envelope_relative_path="audio/envelope.json",
        run_id="hython_calligraphy_audio",
        start_frame=1,
        end_frame=12,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        for candidate_id in ("ARC", "FAN", "ORBIT"):
            particle = geo.node(f"HYTHON_CALLIGRAPHY_AUDIO_{candidate_id}_PARTICLES")
            assert all(
                len(particle.parm(name).keyframes()) == 5 for name in ("windx", "windy", "windz")
            )
        validation = json.loads(
            (
                tmp_path / "manifests" / "hython_calligraphy_audio_calligraphy_validation.json"
            ).read_text()
        )
        assert validation["audio_envelope"] == {
            "applied": True,
            "mode": "baked_data",
            "relative_path": "audio/envelope.json",
        }
    finally:
        if geo.parent() is not None:
            geo.destroy()


def test_fractal_relic_skill_executes_and_replays_equivalent_graph(tmp_path):
    obj = hou.node("/obj")
    original_name = hou.hipFile.name()
    parent_path = "/obj/HERMES_RELIC_SKILL_TEST"
    geo = obj.createNode("geo", node_name="HERMES_RELIC_SKILL_TEST", run_init_scripts=False)
    skill = load_skill("skills/model.fractal_relic")
    calls = skill.plan(
        parent_node_id=parent_path,
        artifact_dir=str(tmp_path),
        run_id="hython_relic",
        seed=123,
        detail_level="draft",
        iterations=2,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        assert geo.node("OUT_COMPARISON").isDisplayFlagSet()
        assert geo.node("OUT_GEO").isRenderFlagSet()
        assert geo.node("SELECT_CANDIDATE").parm("input").eval() == 0
        assert all(geo.node(f"OUT_CAND_{letter}") for letter in "ABC")
        assert all(node.type().name() not in {"python", "attribwrangle"} for node in geo.children())

        graph_log = tmp_path / "logs" / "hython_relic_graph.jsonl"
        cook_log = tmp_path / "logs" / "hython_relic_cook.jsonl"
        graph_svg = tmp_path / "observations" / "hython_relic_graph.svg"
        manifest_path = tmp_path / "manifests" / "hython_relic_graph_manifest.json"
        assert graph_log.is_file() and cook_log.is_file() and graph_svg.is_file()
        assert list((tmp_path / "scenes").glob("relic_hython_relic_final_v*.hipnc"))
        assert hou.hipFile.name() == original_name

        manifest = json.loads(manifest_path.read_text())
        metadata = manifest["metadata"]
        assert metadata["selection"]["winner"] is None
        assert metadata["selection"]["automatic_ranking"] is False
        assert [item["seed"] for item in metadata["candidates"]] == [123, 8042, 15961]
        assert all(item["human_rating"]["score"] is None for item in metadata["candidates"])
        original_metrics = manifest["metrics"][f"{parent_path}/OUT_COMPARISON"]
        original_ids = sorted(
            node.userData("hermes_id") for node in geo.children() if node.userData("hermes_id")
        )

        replay_record = json.loads(graph_log.read_text().splitlines()[0])
        geo.destroy()
        geo = obj.createNode("geo", node_name="HERMES_RELIC_SKILL_TEST", run_init_scripts=False)
        replay_result = _grant_batch(
            dispatcher,
            "hython-relic-replay",
            {
                "batch_id": replay_record["batch_id"],
                "operations": replay_record["operations"],
                "checkpoint_dir": str(tmp_path / "replay_checkpoints"),
                "log_path": str(tmp_path / "replay_graph.jsonl"),
                "label": "Replay fractal relic",
                "checkpoint_stem": "replay_relic",
            },
        )
        assert replay_result.status.value == "success", replay_result.errors
        replay_cook = json.loads(json.dumps(calls[1]))
        replay_cook["request_id"] = "hython-relic-replay-cook"
        replay_cook["arguments"]["log_path"] = str(tmp_path / "replay_cook.jsonl")
        replay_cook_result = _dispatch_planned_call(dispatcher, replay_cook)
        assert replay_cook_result.status.value == "success", replay_cook_result.errors
        replay_metrics = replay_cook_result.data["metrics"]
        replay_ids = sorted(
            node.userData("hermes_id") for node in geo.children() if node.userData("hermes_id")
        )
        assert replay_ids == original_ids
        assert replay_metrics["points"] == original_metrics["points"]
        assert replay_metrics["primitives"] == original_metrics["primitives"]
        assert [value for vector in replay_metrics["bounds"] for value in vector] == pytest.approx(
            [value for vector in original_metrics["bounds"] for value in vector]
        )
    finally:
        if geo.parent() is not None:
            geo.destroy()


def test_vellum_relic_drop_skill_cooks_bounded_sequence_and_preserves_contracts(tmp_path):
    obj = hou.node("/obj")
    original_name = hou.hipFile.name()
    original_frame = float(hou.frame())
    parent_path = "/obj/HERMES_VELLUM_SKILL_TEST"
    geo = obj.createNode("geo", node_name="HERMES_VELLUM_SKILL_TEST", run_init_scripts=False)
    skill = load_skill("skills/simulate.vellum_relic_drop")
    calls = skill.plan(
        parent_node_id=parent_path,
        artifact_dir=str(tmp_path),
        run_id="hython_drop",
        start_frame=1,
        end_frame=12,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        expected = {
            "OUT_HYTHON_DROP_REST",
            "OUT_HYTHON_DROP_CONSTRAINTS",
            "OUT_HYTHON_DROP_COLLIDER",
            "OUT_HYTHON_DROP_SIM_RAW",
            "OUT_HYTHON_DROP_CACHE",
            "OUT_HYTHON_DROP_COMPARE",
        }
        assert expected <= {node.name() for node in geo.children()}
        assert geo.node("OUT_HYTHON_DROP_COMPARE").isDisplayFlagSet()
        assert geo.node("OUT_HYTHON_DROP_COMPARE").isRenderFlagSet()
        assert all(node.type().name() not in {"python", "attribwrangle"} for node in geo.children())
        solver = geo.node("HYTHON_DROP_SOLVER")
        assert [node.path() for node in solver.inputs()] == [
            f"{parent_path}/HYTHON_DROP_PRESSURE_CONSTRAINTS",
            f"{parent_path}/HYTHON_DROP_PRESSURE_CONSTRAINTS",
            f"{parent_path}/OUT_HYTHON_DROP_COLLIDER",
        ]

        temporal = results[1]
        assert temporal.cook.frames == [float(frame) for frame in range(1, 13)]
        assert len(temporal.data["frame_metrics"]) == 12
        assert all(
            item["points"] > 0 and item["primitives"] > 0 for item in temporal.data["frame_metrics"]
        )
        assert (
            temporal.data["frame_metrics"][0]["bounds"]
            != temporal.data["frame_metrics"][-1]["bounds"]
        )
        assert float(hou.frame()) == original_frame

        cache = geo.node("HYTHON_DROP_FILE_CACHE")
        assert cache.parm("file").unexpandedString() == str(
            tmp_path / "cache" / "hython_drop" / "v001" / "hython_drop.$F4.bgeo.sc"
        )
        assert cache.parm("loadfromdisk").eval() == 0
        assert not (tmp_path / "cache" / "hython_drop" / "v001").exists()

        cook_log = tmp_path / "logs" / "hython_drop_temporal_cook.jsonl"
        graph_svg = tmp_path / "observations" / "hython_drop_graph.svg"
        manifest_path = tmp_path / "manifests" / "hython_drop_graph_manifest.json"
        assert cook_log.is_file() and graph_svg.is_file() and manifest_path.is_file()
        assert list((tmp_path / "scenes").glob("vellum_hython_drop_final_v*.hipnc"))
        assert hou.hipFile.name() == original_name
        manifest = json.loads(manifest_path.read_text())
        assert manifest["metadata"]["cache_contract"]["write_implicit"] is False
        assert manifest["metadata"]["temporal_contract"]["frame_count"] == 12
    finally:
        if geo.parent() is not None:
            geo.destroy()


def test_vellum_membrane_lab_validates_three_material_profiles_and_restores_frame(tmp_path):
    obj = hou.node("/obj")
    original_frame = float(hou.frame())
    geo = obj.createNode("geo", node_name="HERMES_MEMBRANE_TEST", run_init_scripts=False)
    skill = load_skill("skills/simulate.vellum_membrane_lab")
    calls = skill.plan(
        parent_node_id=geo.path(),
        artifact_dir=str(tmp_path),
        run_id="hython_membrane",
        start_frame=1,
        end_frame=12,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        hou.setFrame(5)
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        assert float(hou.frame()) == pytest.approx(5)
        assert geo.node("OUT_HYTHON_MEMBRANE_COMPARE").isDisplayFlagSet()
        assert (
            geo.node("OUT_HYTHON_MEMBRANE_LABELS")
            not in geo.node("OUT_HYTHON_MEMBRANE_COMPARE").inputAncestors()
        )
        assert [node.path() for node in geo.node("HYTHON_MEMBRANE_REINFORCED_SOLVER").inputs()] == [
            f"{geo.path()}/HYTHON_MEMBRANE_REINFORCED_SURFACE_STRUTS",
            f"{geo.path()}/OUT_HYTHON_MEMBRANE_REINFORCED_CONSTRAINTS",
            f"{geo.path()}/OUT_HYTHON_MEMBRANE_COLLIDER",
        ]
        validation = json.loads(
            (tmp_path / "manifests" / "hython_membrane_membrane_validation.json").read_text()
        )
        assert len(validation["frames"]) == 12
        assert validation["final_checks"]["silk"]["anchored_max_drift"] == pytest.approx(0)
        assert validation["final_checks"]["silk"]["mean_dynamic_displacement"] > 0.25
        assert (
            validation["final_checks"]["reinforced"]["constraint_primitives"]
            > validation["final_checks"]["silk"]["constraint_primitives"] * 1.2
        )
        assert validation["selection"]["winner"] is None
        assert validation["selection"]["automatic_ranking"] is False
        assert validation["cache"]["write_implicit"] is False
        assert not (tmp_path / "cache" / "hython_membrane" / "v001").exists()
        assert list((tmp_path / "scenes").glob("membrane_hython_membrane_final_v*.hipnc"))
    finally:
        hou.setFrame(original_frame)
        if geo.parent() is not None:
            geo.destroy()


def test_rbd_art_directed_fracture_validates_transforms_and_restores_frame(tmp_path):
    obj = hou.node("/obj")
    original_frame = float(hou.frame())
    geo = obj.createNode("geo", node_name="HERMES_RBD_TEST", run_init_scripts=False)
    skill = load_skill("skills/simulate.rbd_art_directed_fracture")
    calls = skill.plan(
        parent_node_id=geo.path(),
        artifact_dir=str(tmp_path),
        run_id="hython_rbd",
        start_frame=1,
        end_frame=48,
        profile_index=0,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        hou.setFrame(7)
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        assert float(hou.frame()) == pytest.approx(7)
        assert geo.node("OUT_HYTHON_RBD_COMPARE").isDisplayFlagSet()
        assert (
            geo.node("OUT_HYTHON_RBD_LABELS")
            not in geo.node("OUT_HYTHON_RBD_COMPARE").inputAncestors()
        )
        fracture = geo.node("HYTHON_RBD_MATERIAL_FRACTURE")
        assert fracture.type().name() == "rbdmaterialfracture::4.0"
        assert list(fracture.outputLabels()) == [
            "Geometry",
            "Constraint Geometry",
            "Proxy Geometry",
        ]
        solver = geo.node("HYTHON_RBD_BULLET_SOLVER")
        assert solver.type().name() == "rbdbulletsolver"
        assert list(solver.outputLabels())[3] == "Simulation Points"
        cache = geo.node("HYTHON_RBD_TRANSFORM_FILE_CACHE")
        assert cache.parm("loadfromdisk").eval() == 0
        assert cache.parm("f2").eval() == pytest.approx(48)
        validation = json.loads(
            (tmp_path / "manifests" / "hython_rbd_rbd_validation.json").read_text()
        )
        assert len(validation["frames"]) == 48
        assert validation["piece_count"] <= 5_000
        assert validation["broken_constraints"] > 0
        assert validation["vertical_drop"] > 1.0
        assert all(len(frame["transform_sha256"]) == 64 for frame in validation["frames"])
        assert validation["frames"][0]["piece_count"] == validation["frames"][-1]["piece_count"]
        assert validation["transform_cache"]["status"] == "configured_not_written"
        assert not (tmp_path / "cache" / "hython_rbd" / "v001").exists()
        assert list((tmp_path / "scenes").glob("rbd_hython_rbd_final_v*.hipnc"))
    finally:
        hou.setFrame(original_frame)
        if geo.parent() is not None:
            geo.destroy()


def test_mpm_matter_sculpture_validates_proxy_and_durable_progress(tmp_path):
    obj = hou.node("/obj")
    original_frame = float(hou.frame())
    geo = obj.createNode("geo", node_name="HERMES_MPM_TEST", run_init_scripts=False)
    skill = load_skill("skills/simulate.mpm_matter_sculpture")
    calls = skill.plan(
        parent_node_id=geo.path(),
        artifact_dir=str(tmp_path),
        run_id="hython_mpm",
        start_frame=1,
        end_frame=4,
        particle_separation=0.2,
        source_radius=0.42,
        source_height=1.8,
        noise_height=0.03,
        substep_max=16,
        max_particles=20_000,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        hou.setFrame(7)
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        assert float(hou.frame()) == pytest.approx(7)
        assert geo.node("OUT_HYTHON_MPM_SELECTED").isDisplayFlagSet()
        solver = geo.node("HYTHON_MPM_MPM_SOLVER")
        assert [node.type().name() for node in solver.inputs()] == [
            "merge",
            "mpmcollider",
            "mpmcontainer",
        ]
        cache = geo.node("HYTHON_MPM_FILE_CACHE")
        assert cache.parm("filemode").evalAsString() == "none"
        assert cache.parm("loadfromdisk").eval() == 0
        validation = json.loads(
            (tmp_path / "manifests" / "hython_mpm_mpm_validation.json").read_text()
        )
        progress = json.loads(
            (tmp_path / "manifests" / "hython_mpm_cache_progress.json").read_text()
        )
        assert len(validation["frames"]) == 4
        assert validation["centroid_motion"] > 0.05
        assert all(len(frame["source_counts"]) == 3 for frame in validation["frames"])
        assert validation["cache"]["write_implicit"] is False
        assert progress["status"] == "complete"
        assert progress["completed_frames"] == [1, 2, 3, 4]
        assert not (tmp_path / "cache" / "hython_mpm" / "v001").exists()
        assert list((tmp_path / "scenes").glob("mpm_hython_mpm_final_v*.hipnc"))
    finally:
        hou.setFrame(original_frame)
        if geo.parent() is not None:
            geo.destroy()


def test_differential_growth_skill_populates_native_feedback_and_cooks_bounded_sequence(tmp_path):
    obj = hou.node("/obj")
    original_name = hou.hipFile.name()
    original_frame = float(hou.frame())
    parent_path = "/obj/HERMES_GROWTH_SKILL_TEST"
    geo = obj.createNode("geo", node_name="HERMES_GROWTH_SKILL_TEST", run_init_scripts=False)
    skill = load_skill("skills/generate.differential_growth")
    calls = skill.plan(
        parent_node_id=parent_path,
        artifact_dir=str(tmp_path),
        run_id="hython_growth",
        seed=2401,
        candidate_index=1,
        start_frame=1,
        end_frame=18,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        expected = {
            "OUT_HYTHON_GROWTH_REST_CURVE",
            "OUT_HYTHON_GROWTH_GROWTH_CURVE",
            "OUT_HYTHON_GROWTH_GROWTH_WIRE",
            "OUT_HYTHON_GROWTH_COMPARE",
        }
        assert expected <= {node.name() for node in geo.children()}
        assert geo.node("OUT_HYTHON_GROWTH_COMPARE").isDisplayFlagSet()
        assert geo.node("OUT_HYTHON_GROWTH_COMPARE").isRenderFlagSet()
        assert geo.node("HYTHON_GROWTH_SELECT_SOURCE").parm("input").eval() == 1
        assert all(node.type().name() not in {"python", "attribwrangle"} for node in geo.children())

        solver = geo.node("HYTHON_GROWTH_SOLVER")
        feedback = solver.node("d/s")
        separation = feedback.node("HERMES_POINT_SEPARATION")
        smoothing = feedback.node("HERMES_CURVE_RELAX")
        spacing = feedback.node("HERMES_EDGE_SPACING")
        output = feedback.node("OUT")
        assert [separation.type().name(), smoothing.type().name(), spacing.type().name()] == [
            "relax",
            "attribblur",
            "resample",
        ]
        assert separation.input(0) == feedback.node("Prev_Frame")
        assert smoothing.input(0) == separation
        assert spacing.input(0) == smoothing
        assert output.input(0) == spacing
        assert all(node.userData("hermes_id") for node in (separation, smoothing, spacing))
        assert solver.parm("cachetodisk").eval() == 0

        populated = results[1]
        assert populated.data["algorithm"] == "native_relax_attribblur_resample"
        temporal = results[2]
        assert temporal.cook.frames == [float(frame) for frame in range(1, 19)]
        frame_metrics = temporal.data["frame_metrics"]
        assert len(frame_metrics) == 18
        assert all(0 < item["points"] <= 50_000 for item in frame_metrics)
        assert all(0 < item["primitives"] <= 50_000 for item in frame_metrics)
        assert frame_metrics[-1]["points"] > frame_metrics[0]["points"]
        assert float(hou.frame()) == original_frame

        assert (tmp_path / "logs" / "hython_growth_solver.jsonl").is_file()
        assert (tmp_path / "logs" / "hython_growth_temporal_cook.jsonl").is_file()
        assert (tmp_path / "observations" / "hython_growth_graph.svg").is_file()
        assert (tmp_path / "observations" / "hython_growth_solver_graph.svg").is_file()
        manifest_path = tmp_path / "manifests" / "hython_growth_graph_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["metadata"]["algorithm"]["python_geometry_compute"] is False
        assert manifest["metadata"]["selection"]["winner"] is None
        assert manifest["metadata"]["temporal_contract"]["frame_count"] == 18
        assert list((tmp_path / "scenes").glob("growth_hython_growth_final_v*.hipnc"))
        assert hou.hipFile.name() == original_name
    finally:
        if geo.parent() is not None:
            geo.destroy()


def test_differential_growth_population_refuses_nonpristine_artist_feedback(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_GROWTH_REFUSAL", run_init_scripts=False)
    solver = geo.createNode("solver", node_name="ARTIST_SOLVER")
    feedback = solver.node("d/s")
    output = feedback.node("OUT")
    artist_input = feedback.node("Input_1")
    output.setInput(0, artist_input)
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        result = _dispatch_planned_call(
            dispatcher,
            CommandEnvelope(
                tool="growth.solver.populate",
                request_id="growth-refuse-artist-network",
                arguments={
                    "solver_path": solver.path(),
                    "run_id": "refusal_test",
                    "checkpoint_dir": str(tmp_path / "checkpoints"),
                    "log_path": str(tmp_path / "logs" / "growth.jsonl"),
                },
                policy=Policy(max_points=50_000, max_primitives=50_000, max_frames=24),
            ).as_dict(),
        )
        assert result.status.value == "error"
        assert "not pristine" in result.errors[0]
        assert output.input(0) == artist_input
        assert feedback.node("HERMES_POINT_SEPARATION") is None
        assert not (tmp_path / "checkpoints").exists()
    finally:
        geo.destroy()


def test_botanical_grammar_skill_cooks_registered_native_candidates_and_refuses_rule_drift(
    tmp_path,
):
    obj = hou.node("/obj")
    original_name = hou.hipFile.name()
    geo = obj.createNode("geo", node_name="HERMES_BOTANICAL_SKILL_TEST", run_init_scripts=False)
    skill = load_skill("skills/grow.botanical_grammar")
    calls = skill.plan(
        parent_node_id=geo.path(),
        artifact_dir=str(tmp_path),
        run_id="hython_botanical",
        seed=4103,
        generations=4,
        candidate_index=1,
        wire_radius=0.018,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        skeletons = [
            geo.node("HYTHON_BOTANICAL_CANOPY_SKELETON"),
            geo.node("HYTHON_BOTANICAL_FERN_SKELETON"),
            geo.node("HYTHON_BOTANICAL_CORAL_SKELETON"),
        ]
        wires = [
            geo.node("OUT_HYTHON_BOTANICAL_CANOPY"),
            geo.node("OUT_HYTHON_BOTANICAL_FERN"),
            geo.node("OUT_HYTHON_BOTANICAL_CORAL"),
        ]
        assert [node.type().name() for node in skeletons] == ["lsystem", "lsystem", "lsystem"]
        assert [node.parm("randseed").eval() for node in skeletons] == [4103, 4204, 4314]
        assert all(node.parm("usefile").eval() == 0 for node in skeletons)
        assert all(node.parm("generations").eval() == 4 for node in skeletons)
        assert all(node.input(0).type().name() == "polywire" for node in wires)
        assert all(
            node.input(0).input(0) == skeleton
            for node, skeleton in zip(wires, skeletons, strict=True)
        )
        assert all(node.type().name() not in {"python", "attribwrangle"} for node in geo.children())

        selector = geo.node("HYTHON_BOTANICAL_SELECT_BOTANICAL")
        selected = geo.node("OUT_HYTHON_BOTANICAL_SELECTED")
        compare = geo.node("OUT_HYTHON_BOTANICAL_COMPARE")
        assert selector.parm("input").eval() == 1
        assert selected.input(0) == selector
        assert compare.isDisplayFlagSet() and compare.isRenderFlagSet()
        assert compare.input(0).userData("hermes_role") == "botanical_compare_frame"
        assert [node.userData("hermes_role") for node in compare.input(0).input(0).inputs()] == [
            "botanical_compare_transform_canopy",
            "botanical_compare_transform_fern",
            "botanical_compare_transform_coral",
        ]

        validation = results[1].data
        assert [item["candidate_id"] for item in validation["skeletons"]] == [
            "canopy",
            "fern",
            "coral",
        ]
        assert [(item["points"], item["primitives"]) for item in validation["skeletons"]] == [
            (42, 40),
            (131, 27),
            (157, 156),
        ]
        assert len({(item["points"], item["primitives"]) for item in validation["skeletons"]}) == 3
        assert all(
            {"P", "Cd", "width", "arc", "gen", "up"} <= set(item["point_attributes"])
            for item in validation["skeletons"]
        )
        assert validation["observed_wire_points"] <= 250_000
        assert validation["observed_wire_primitives"] <= 250_000
        assert validation["selection"]["winner"] is None
        assert (tmp_path / "observations" / "hython_botanical_graph.svg").is_file()
        manifest_path = tmp_path / "manifests" / "hython_botanical_graph_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["metadata"]["algorithm"]["safe_registered_grammars_only"] is True
        assert manifest["metadata"]["selection"]["comparison_order"] == [
            "canopy",
            "fern",
            "coral",
        ]
        assert list((tmp_path / "scenes").glob("botanical_hython_botanical_final_v*.hipnc"))
        assert hou.hipFile.name() == original_name

        skeletons[0].parm("rule1").set("A=FF")
        with pytest.raises(ValueError, match="unregistered rule 1"):
            cook_validate_botanical(
                network_path=geo.path(),
                skeleton_node_paths=[node.path() for node in skeletons],
                wire_node_paths=[node.path() for node in wires],
                selected_path=selected.path(),
                compare_path=compare.path(),
                generations=4,
                seed=4103,
                candidate_index=1,
                wire_radius=0.018,
                output_path=str(tmp_path / "must_not_exist_botanical.json"),
            )
        assert not (tmp_path / "must_not_exist_botanical.json").exists()
    finally:
        if geo.parent() is not None:
            geo.destroy()


def test_reaction_diffusion_skill_cooks_validates_and_exports_native_contact_sheet(tmp_path):
    original_name = hou.hipFile.name()
    skill = load_skill("skills/generate.reaction_diffusion_pattern")
    calls = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="hython_reaction",
        seed=3109,
        resolution=64,
        candidate_index=1,
        iterations=4,
        iterations_per_step=6,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    network = None
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        network = hou.node("/img/HYTHON_REACTION_COPNET")
        assert network is not None
        assert network.type().category().name() == "CopNet"
        assert tuple(int(value) for value in network.parmTuple("res").eval()) == (64, 64)
        assert network.parm("precision").eval() == 1

        end_nodes = [
            network.node("HYTHON_REACTION_SMALL_WAVES"),
            network.node("HYTHON_REACTION_LARGE_WAVES"),
            network.node("HYTHON_REACTION_SPOTS"),
        ]
        assert [node.type().name() for node in end_nodes] == [
            "reactiondiffusion_block_end",
            "reactiondiffusion_block_end",
            "reactiondiffusion_block_end",
        ]
        assert [node.parm("presetsgs").evalAsString() for node in end_nodes] == [
            "smallwaves",
            "bigwaves",
            "spots",
        ]
        assert [(node.parm("kill").eval(), node.parm("feed").eval()) for node in end_nodes] == [
            (0.3865, 0.0899),
            (0.0, 0.0444),
            (0.8045, 0.2222),
        ]
        assert all(node.parm("simulate").eval() == 0 for node in end_nodes)
        assert all(node.parm("continuouscook").eval() == 0 for node in end_nodes)
        assert all(node.parm("cacheenabled").eval() == 0 for node in end_nodes)
        assert all(
            node.parm("iterations").eval() * node.parm("iterationsperstep").eval() == 24
            for node in end_nodes
        )
        begins = [
            network.node("HYTHON_REACTION_SMALL_WAVES_BEGIN"),
            network.node("HYTHON_REACTION_LARGE_WAVES_BEGIN"),
            network.node("HYTHON_REACTION_SPOTS_BEGIN"),
        ]
        assert [node.parm("blockpath").evalAsString() for node in begins] == [
            node.path() for node in end_nodes
        ]
        assert all(end.input(0) == begin for begin, end in zip(begins, end_nodes, strict=True))
        selector = network.node("HYTHON_REACTION_SELECT_PATTERN")
        assert selector.parm("input").eval() == 1
        contact = network.node("OUT_HYTHON_REACTION_CONTACT_SHEET")
        assert contact.isDisplayFlagSet()
        assert [node.path() for node in contact.input(0).inputs()] == [
            f"{network.path()}/HYTHON_REACTION_COLOR_SMALL_WAVES",
            f"{network.path()}/HYTHON_REACTION_COLOR_LARGE_WAVES",
            f"{network.path()}/HYTHON_REACTION_COLOR_SPOTS",
        ]
        assert all(
            node.type().name() not in {"python", "pythonfilter"} for node in network.children()
        )

        validation = results[2].data
        assert validation["spec"]["total_steps"] == 24
        assert [item["candidate_id"] for item in validation["patterns"]] == [
            "smallwaves",
            "bigwaves",
            "spots",
        ]
        assert all(item["resolution"] == [64, 64] for item in validation["patterns"])
        assert all(item["components"] == 1 for item in validation["patterns"])
        assert all(item["nonfinite_values"] == 0 for item in validation["patterns"])
        assert all(item["dynamic_range"] >= 0.02 for item in validation["patterns"])
        assert len({item["buffer_sha256"] for item in validation["patterns"]}) == 3
        assert validation["contact_sheet"]["resolution"] == [192, 64]
        assert validation["selection"]["winner"] is None

        contact_path = tmp_path / "observations" / "hython_reaction_contact_sheet.png"
        selected_path = tmp_path / "observations" / "hython_reaction_selected.png"
        assert contact_path.is_file() and contact_path.stat().st_size > 100
        assert selected_path.is_file() and selected_path.stat().st_size > 100
        assert results[3].data["resolution"] == [192, 64]
        assert results[4].data["resolution"] == [64, 64]
        manifest_path = tmp_path / "manifests" / "hython_reaction_graph_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["metadata"]["algorithm"]["compiled_cook"] is False
        assert manifest["metadata"]["algorithm"]["live_simulation"] is False
        assert manifest["metadata"]["selection"]["contact_order"] == [
            "smallwaves",
            "bigwaves",
            "spots",
        ]
        assert (tmp_path / "observations" / "hython_reaction_graph.svg").is_file()
        assert list((tmp_path / "scenes").glob("reaction_hython_reaction_final_v*.hipnc"))
        assert hou.hipFile.name() == original_name

        end_nodes[1].parm("kill").set(0.3707)
        with pytest.raises(ValueError, match="stale callback-driven coefficient kill"):
            cook_validate_reaction(
                network_path=network.path(),
                pattern_node_paths=[node.path() for node in end_nodes],
                contact_sheet_path=contact.path(),
                resolution=64,
                iterations=4,
                iterations_per_step=6,
                candidate_index=1,
                output_path=str(tmp_path / "must_not_exist.json"),
            )
        assert not (tmp_path / "must_not_exist.json").exists()
    finally:
        if network is not None and network.parent() is not None:
            network.destroy()


def test_cop_image_export_refuses_unmanaged_rop(tmp_path):
    network = hou.node("/img").createNode(
        "copnet", node_name="HERMES_UNMANAGED_COP_EXPORT", run_init_scripts=False
    )
    source = network.createNode("constant", node_name="ARTIST_IMAGE")
    rop = network.createNode("rop_image", node_name="ARTIST_ROP")
    rop.setInput(0, source)
    output_path = tmp_path / "artist.png"
    rop.parm("copoutput").set(str(output_path))
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        result = _dispatch_planned_call(
            dispatcher,
            CommandEnvelope(
                tool="cop.image.export",
                request_id="refuse-unmanaged-cop-rop",
                arguments={
                    "rop_path": rop.path(),
                    "output_path": str(output_path),
                    "log_path": str(tmp_path / "export.jsonl"),
                    "expected_resolution": [1024, 1024],
                    "frame": 1,
                },
                policy=Policy(max_seconds=10, max_resolution=(1280, 720)),
            ).as_dict(),
        )
        assert result.status.value == "error"
        assert "managed reaction-diffusion ROP" in result.errors[0]
        assert not output_path.exists()
    finally:
        network.destroy()


def test_registered_recipe_and_hda_tools_execute_only_after_exact_approval(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_CATALOG_TEST", run_init_scripts=False)
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        recipe_call = CommandEnvelope(
            tool="recipe.instantiate",
            request_id="catalog-recipe",
            arguments={
                "recipe_id": "sop.fractal_relic_candidate",
                "version": "2.0.0",
                "parent_path": geo.path(),
                "batch_id": "catalog-recipe-01",
                "checkpoint_dir": str(tmp_path / "recipe_checkpoints"),
                "log_path": str(tmp_path / "recipe.jsonl"),
                "ref_prefix": "catalog_",
                "inputs": {
                    "candidate_code": "A",
                    "lineage": "catalog integration candidate",
                    "point_count": 24,
                },
            },
        )
        blocked = dispatcher.process_one(recipe_call)
        assert blocked.result.status.value == "blocked"
        assert geo.node("CAND_A_BASE") is None
        recipe_result = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id="catalog-recipe-grant",
                arguments={"approval_id": blocked.result.data["approval"]["approval_id"]},
            )
        ).result
        assert recipe_result.status.value == "success", recipe_result.errors
        assert recipe_result.data["recipe"] == {
            "id": "sop.fractal_relic_candidate",
            "version": "2.0.0",
        }
        assert geo.node("OUT_CAND_A") is not None

        hda_call = CommandEnvelope(
            tool="hda.build_registered",
            request_id="catalog-hda",
            arguments={
                "hda_id": "hermes::fractal_relic",
                "version": "2.0.0",
                "dest_dir": str(tmp_path / "hda"),
            },
        )
        blocked_hda = dispatcher.process_one(hda_call)
        assert blocked_hda.result.status.value == "blocked"
        hda_result = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id="catalog-hda-grant",
                arguments={"approval_id": blocked_hda.result.data["approval"]["approval_id"]},
            )
        ).result
        assert hda_result.status.value == "success", hda_result.errors
        assert hda_result.data["registry"] == {
            "id": "hermes::fractal_relic",
            "version": "2.0.0",
        }
        assert hda_result.data["hda_file"].endswith(".hdanc")
        built_asset = hou.node(hda_result.data["node_path"])
        assert built_asset is not None
        built_asset.parent().destroy()
    finally:
        if geo.parent() is not None:
            geo.destroy()


def test_local_pdg_variations_cook_hda_outputs_and_build_editable_gallery(tmp_path):
    from hda.source.hermes_fractal_relic.build import build as build_relic_hda

    hda_result = build_relic_hda(dest_dir=str(tmp_path / "hda"))
    source = hou.node(hda_result["node_path"])
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    topnet = None
    gallery = None
    camera = None
    try:
        original_parms = {
            name: source.parm(name).eval()
            for name in (
                "seed",
                "base_radius",
                "noise_amplitude",
                "iterations",
                "detail_level",
                "preview_candidate",
                "output_mode",
            )
        }
        build_call = CommandEnvelope(
            tool="pdg.variation.build",
            request_id="pdg-variation-build",
            arguments={
                "source_node_path": source.path(),
                "output_dir": str(tmp_path / "geometry"),
                "checkpoint_dir": str(tmp_path / "checkpoints"),
                "log_path": str(tmp_path / "logs" / "pdg_build.jsonl"),
                "network_name": "HERMES_PDG_INTEGRATION",
                "base_seed": 500,
                "count": 3,
                "seed_step": 13,
                "base_radius_range": [0.85, 1.15],
                "noise_amplitude_range": [0.1, 0.24],
                "iterations": 2,
                "detail_level": "draft",
                "candidate_index": 1,
                "scheduler_seconds_per_item": 30,
                "scheduler_memory_mb": 2048,
            },
        )
        blocked = dispatcher.process_one(build_call)
        assert blocked.result.status.value == "blocked"
        built = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id="pdg-variation-build-grant",
                arguments={"approval_id": blocked.result.data["approval"]["approval_id"]},
            )
        ).result
        assert built.status.value == "success", built.errors
        topnet = hou.node(built.data["network_path"])
        assert topnet is not None
        assert topnet.parm("topscheduler").evalAsString() == "LOCAL_BOUNDED"
        assert topnet.node("TOP_WEDGE_VARIANTS").type().name() == "wedge"
        assert topnet.node("CACHE_VARIANT_GEOMETRY").type().name() == "ropgeometry"
        assert topnet.node("WAIT_ALL_VARIANTS").type().name() == "waitforall"
        assert all(
            node.type().name() not in {"pythonprocessor", "pythonscript"}
            for node in topnet.children()
        )

        manifest_path = tmp_path / "manifests" / "variations.json"
        generated = dispatcher.process_one(
            CommandEnvelope(
                tool="pdg.variation.generate",
                request_id="pdg-variation-generate",
                arguments={"topnet_path": topnet.path(), "output_path": str(manifest_path)},
            )
        ).result
        assert generated.status.value == "success", generated.errors
        assert [item["seed"] for item in generated.data["items"]] == [500, 513, 526]
        assert generated.data["selection"]["winner"] is None

        cook_policy = Policy(
            allow_external_process=True,
            max_work_items=3,
            max_seconds=90,
            max_points=50_000,
            max_primitives=50_000,
            max_memory_bytes=2_147_483_648,
            max_output_bytes=100_000_000,
        )
        cook_call = CommandEnvelope(
            tool="pdg.variation.cook",
            request_id="pdg-variation-cook",
            policy=cook_policy,
            arguments={
                "topnet_path": topnet.path(),
                "manifest_path": str(manifest_path),
                "result_path": str(tmp_path / "manifests" / "variation_results.json"),
                "scene_path": str(tmp_path / "scenes" / "pdg_variations.hipnc"),
                "log_path": str(tmp_path / "logs" / "pdg_cook.jsonl"),
                "estimate": {
                    "work_items": 3,
                    "seconds_per_item": 30,
                    "points_per_item": 50_000,
                    "primitives_per_item": 50_000,
                    "memory_bytes_per_item": 2_147_483_648,
                    "output_bytes_total": 100_000_000,
                },
            },
        )
        consent_missing = CommandEnvelope.from_dict(cook_call.as_dict())
        consent_missing.request_id = "pdg-variation-cook-no-consent"
        consent_missing.policy.allow_external_process = False
        refused = dispatcher.process_one(consent_missing)
        assert refused.result.status.value == "blocked"
        refused_result = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id="pdg-variation-cook-no-consent-grant",
                arguments={"approval_id": refused.result.data["approval"]["approval_id"]},
            )
        ).result
        assert refused_result.status.value == "error"
        assert "allow_external_process=true" in refused_result.errors[0]

        blocked_cook = dispatcher.process_one(cook_call)
        assert blocked_cook.result.status.value == "blocked"
        cooked = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id="pdg-variation-cook-grant",
                arguments={"approval_id": blocked_cook.result.data["approval"]["approval_id"]},
            )
        ).result
        assert cooked.status.value == "success", cooked.errors
        assert len(cooked.data["variations"]) == 3
        assert all(item["metrics"]["points"] > 0 for item in cooked.data["variations"])
        assert all(Path(item["geometry_path"]).is_file() for item in cooked.data["variations"])
        assert cooked.data["selection"]["automatic_ranking"] is False
        assert {name: source.parm(name).eval() for name in original_parms} == original_parms

        gallery_call = CommandEnvelope(
            tool="pdg.variation.build_gallery",
            request_id="pdg-gallery-build",
            arguments={
                "result_path": str(tmp_path / "manifests" / "variation_results.json"),
                "checkpoint_dir": str(tmp_path / "gallery_checkpoints"),
                "log_path": str(tmp_path / "logs" / "gallery.jsonl"),
                "gallery_name": "HERMES_PDG_GALLERY_TEST",
                "camera_name": "HERMES_PDG_CAMERA_TEST",
            },
        )
        blocked_gallery = dispatcher.process_one(gallery_call)
        assert blocked_gallery.result.status.value == "blocked"
        gallery_result = dispatcher.process_one(
            CommandEnvelope(
                tool="approval.grant",
                request_id="pdg-gallery-build-grant",
                arguments={"approval_id": blocked_gallery.result.data["approval"]["approval_id"]},
            )
        ).result
        assert gallery_result.status.value == "success", gallery_result.errors
        gallery = hou.node(gallery_result.data["gallery_path"])
        camera = hou.node(gallery_result.data["camera_path"])
        output = hou.node(gallery_result.data["output_path"])
        assert gallery is not None and camera is not None and output is not None
        assert len([node for node in gallery.children() if node.type().name() == "file"]) == 3
        assert len([node for node in output.input(0).inputs() if node is not None]) == 6
        assert all(
            json.loads(node.userData("hermes_human_rating"))
            == {"score": None, "notes": "", "selected": False}
            for node in gallery.children()
            if node.type().name() == "file"
        )
        gallery_cook = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.node",
                request_id="pdg-gallery-cook",
                policy=Policy(max_points=100_000, max_primitives=100_000, max_seconds=20),
                arguments={
                    "node_path": output.path(),
                    "scope": "display_chain",
                    "force": True,
                    "estimate": {
                        "points": 100_000,
                        "primitives": 100_000,
                        "memory_bytes": 200_000_000,
                        "seconds": 20,
                    },
                    "log_path": str(tmp_path / "logs" / "gallery_cook.jsonl"),
                },
            )
        ).result
        assert gallery_cook.status.value == "success", gallery_cook.errors
        assert gallery_cook.cook.points > sum(
            item["metrics"]["points"] for item in cooked.data["variations"]
        )
    finally:
        if camera is not None and camera.parent() is not None:
            camera.destroy()
        if gallery is not None and gallery.parent() is not None:
            gallery.destroy()
        if topnet is not None and topnet.parent() is not None:
            topnet.destroy()
        if source is not None and source.parent() is not None:
            source.parent().destroy()


def test_procedural_district_cooks_native_lots_and_builds_validated_assembly(tmp_path):
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    skill = load_skill("skills/world.procedural_district")
    calls = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="hython_district",
        base_seed=901,
        lot_count=4,
        seed_step=19,
        columns=2,
        lot_spacing=6.0,
    )
    source = None
    topnet = None
    assembly = None
    camera = None
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        source = hou.node("/obj/HERMES_DISTRICT_SRC_HYTHON_DISTRICT")
        topnet = hou.node("/tasks/HERMES_PDG_DISTRICT_HYTHON_DISTRICT")
        assembly = hou.node("/obj/HERMES_DISTRICT_HYTHON_DISTRICT")
        camera = hou.node("/obj/CAM_DISTRICT_HYTHON_DISTRICT")
        assert source is not None and topnet is not None and assembly is not None
        assert camera is not None
        assert source.node("OUT_BUILDING") is not None
        assert source.node("DISTRICT_PROFILE_SWITCH").type().name() == "switch"
        assert topnet.parm("topscheduler").evalAsString() == "LOCAL_BOUNDED"
        assert topnet.node("TOP_WEDGE_LOTS").type().name() == "wedge"
        assert topnet.node("CACHE_LOT_GEOMETRY").type().name() == "ropgeometry"
        assert topnet.node("WAIT_ALL_LOTS").type().name() == "waitforall"
        assert all(
            node.type().name() not in {"pythonprocessor", "pythonscript"}
            for node in topnet.children()
        )

        result_path = tmp_path / "manifests" / "hython_district_district_results.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert len(result["candidates"]) == 4
        assert [candidate["style"] for candidate in result["candidates"]] == [
            "block",
            "terrace",
            "terrace",
            "needle",
        ]
        assert all(Path(candidate["geometry_path"]).is_file() for candidate in result["candidates"])
        assert all(len(candidate["metrics"]["sha256"]) == 64 for candidate in result["candidates"])
        assert result["selection"] == {
            "method": "human",
            "winner": None,
            "automatic_ranking": False,
        }

        district_merge = assembly.node("MERGE_DISTRICT_LOTS")
        gallery_merge = assembly.node("MERGE_GALLERY_CANDIDATES")
        assert len(district_merge.inputs()) == 5
        assert len(gallery_merge.inputs()) == 8
        validation = json.loads(
            (tmp_path / "manifests" / "hython_district_district_validation.json").read_text(
                encoding="utf-8"
            )
        )
        assert validation["passed"] is True
        assert validation["scheduler_slots"] == 1
        assert validation["profiles"] == ["block", "needle", "terrace"]
        assert validation["district_metrics"]["points"] > 0
        assert validation["gallery_metrics"]["points"] > 0
        assert (tmp_path / "observations" / "hython_district_top_graph.svg").is_file()
        assert (tmp_path / "observations" / "hython_district_assembly_graph.svg").is_file()
        assert list((tmp_path / "scenes").glob("hython_district_final_v*.hipnc"))
    finally:
        for node in (camera, assembly, topnet, source):
            if node is not None and node.parent() is not None:
                node.destroy()


def test_graph_batch_commits_checkpoints_logs_and_replays_with_stable_ids(tmp_path):
    obj = hou.node("/obj")
    original_name = hou.hipFile.name()
    checkpoint_dir = tmp_path / "checkpoints"
    log_path = tmp_path / "replay.jsonl"
    operations = [
        {
            "op": "create",
            "ref": "src",
            "parent_path": "/obj/HERMES_BATCH_TEST",
            "operator_type": "sphere",
            "name": "SRC_BATCH",
            "category": "Sop",
            "role": "source",
            "parameters": {"radx": 1.25},
        },
        {
            "op": "create",
            "ref": "out",
            "parent_path": "/obj/HERMES_BATCH_TEST",
            "operator_type": "null",
            "name": "OUT_BATCH",
            "category": "Sop",
            "role": "output",
        },
        {"op": "connect", "from": "src", "to": "out"},
        {"op": "set_comment", "target": "out", "comment": "Editable output contract"},
        {"op": "set_flags", "target": "out", "display": True, "render": True},
    ]
    arguments = {
        "batch_id": "integration.replay-01",
        "operations": operations,
        "checkpoint_dir": str(checkpoint_dir),
        "log_path": str(log_path),
    }
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    stable_ids = None
    for replay_index in range(2):
        geo = obj.createNode("geo", node_name="HERMES_BATCH_TEST", run_init_scripts=False)
        try:
            result = _grant_batch(dispatcher, f"batch-success-{replay_index}", arguments)
            assert result.status.value == "success", result.errors
            assert result.checkpoint and result.checkpoint.endswith(".hipnc")
            assert result.artifacts == [str(log_path)]
            assert hou.hipFile.name() == original_name
            source = geo.node("SRC_BATCH")
            output = geo.node("OUT_BATCH")
            assert output.input(0) == source
            assert source.parm("radx").eval() == pytest.approx(1.25)
            assert output.comment() == "Editable output contract"
            assert output.isDisplayFlagSet() and output.isRenderFlagSet()
            ids = [source.userData("hermes_id"), output.userData("hermes_id")]
            assert all(ids)
            assert all(
                node.userData("hermes_batch_id") == "integration.replay-01"
                for node in (source, output)
            )
            assert {item.change for item in result.changed_nodes} == {"created"}
            if stable_ids is None:
                stable_ids = ids
                duplicate = _grant_batch(dispatcher, "batch-success-duplicate", arguments)
                assert duplicate.status.value == "error"
                assert "batch_id already applied" in duplicate.errors[0]
                assert geo.node("SRC_BATCH") == source and geo.node("OUT_BATCH") == output
            else:
                assert ids == stable_ids
        finally:
            geo.destroy()
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [record["status"] for record in records] == ["success", "success"]
    assert all(record["request"]["tool"] == "graph.apply_batch" for record in records)
    assert records[0]["graph_diff"]["created"]


def test_graph_batch_rolls_back_partial_mutation_and_records_failure(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_BATCH_ROLLBACK", run_init_scripts=False)
    original = geo.createNode("box", node_name="ORIGINAL")
    original.setDisplayFlag(True)
    original.parm("sizex").setExpression("1+1")
    log_path = tmp_path / "rollback.jsonl"
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    operations = [
        {
            "op": "create",
            "ref": "temp",
            "parent_path": geo.path(),
            "operator_type": "null",
            "name": "TEMP_NODE",
            "category": "Sop",
        },
        {"op": "set_flags", "target": "temp", "display": True},
        {
            "op": "set_parameter",
            "target": original.path(),
            "name": "sizex",
            "value": 1,
        },
    ]
    try:
        result = _grant_batch(
            dispatcher,
            "batch-rollback",
            {
                "batch_id": "integration.rollback-01",
                "operations": operations,
                "checkpoint_dir": str(tmp_path / "checkpoints"),
                "log_path": str(log_path),
            },
        )
        assert result.status.value == "error"
        assert result.data["rolled_back"] is True
        assert result.data["durable_restore_used"] is False
        assert geo.node("TEMP_NODE") is None
        assert original.isDisplayFlagSet() is True
        assert original.parm("sizex").expression() == "1+1"
        record = json.loads(log_path.read_text().splitlines()[0])
        assert record["status"] == "rolled_back"
        assert record["changes_before_rollback"]
    finally:
        geo.destroy()


def test_budgeted_cook_job_restores_frame_validates_and_logs(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_COOK_TEST", run_init_scripts=False)
    source = geo.createNode("box", node_name="SRC_COOK")
    output = geo.createNode("null", node_name="OUT_COOK")
    output.setInput(0, source)
    source.parm("sizex").setExpression("$F")
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    policy = {
        "max_points": 100,
        "max_primitives": 100,
        "max_memory_bytes": 10_000_000,
        "max_seconds": 5.0,
        "max_frames": 1,
    }
    estimate = {
        "points": 8,
        "primitives": 6,
        "memory_bytes": 1_000_000,
        "seconds": 1.0,
    }
    log_path = tmp_path / "cook.jsonl"
    original_frame = float(hou.frame())
    try:
        dirty_metrics = dispatcher.process_one(
            CommandEnvelope(
                tool="geometry.metrics",
                request_id="dirty-metrics",
                arguments={"node_path": output.path()},
            )
        ).result
        assert dirty_metrics.status.value == "error"
        assert "explicit cook job" in dirty_metrics.errors[0]

        submitted = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.submit",
                request_id="cook-submit",
                policy=Policy.from_dict(policy),
                arguments={
                    "node_path": output.path(),
                    "force": True,
                    "estimate": estimate,
                    "log_path": str(log_path),
                },
            )
        ).result
        assert submitted.status.value == "success", submitted.errors
        assert submitted.data["state"] == "pending"
        job_id = submitted.data["job_id"]

        cooked = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.run",
                request_id="cook-run",
                arguments={"job_id": job_id},
            )
        ).result
        assert cooked.status.value == "success", cooked.errors
        assert cooked.cook.points == 8
        assert cooked.cook.primitives == 6
        assert cooked.cook.frames == [original_frame]
        assert cooked.cook.node_path == output.path()
        assert float(hou.frame()) == original_frame

        metrics = dispatcher.process_one(
            CommandEnvelope(
                tool="geometry.metrics",
                request_id="clean-metrics",
                arguments={"node_path": output.path()},
            )
        ).result
        assert metrics.status.value == "success"
        assert metrics.data["point_attributes"] == ["P"]

        validation = dispatcher.process_one(
            CommandEnvelope(
                tool="geometry.validate",
                request_id="geometry-validation",
                arguments={
                    "node_path": output.path(),
                    "expectations": {
                        "min_points": 8,
                        "max_points": 8,
                        "required_point_attributes": ["P"],
                        "require_finite_bounds": True,
                    },
                },
            )
        ).result
        assert validation.status.value == "success"
        assert validation.data["valid"] is True

        frame_submit = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.submit",
                request_id="cook-frame-submit",
                policy=Policy.from_dict(policy),
                arguments={
                    "node_path": output.path(),
                    "scope": "one_frame",
                    "frame": 3,
                    "force": True,
                    "estimate": estimate,
                    "log_path": str(log_path),
                },
            )
        ).result
        frame_cooked = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.run",
                request_id="cook-frame-run",
                arguments={"job_id": frame_submit.data["job_id"]},
            )
        ).result
        assert frame_cooked.status.value == "success", frame_cooked.errors
        assert frame_cooked.cook.frames == [3.0]
        assert float(hou.frame()) == original_frame

        range_submit = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.submit",
                request_id="cook-range-submit",
                policy=Policy.from_dict({**policy, "max_frames": 3}),
                arguments={
                    "node_path": output.path(),
                    "scope": "frame_range",
                    "frame_range": [1, 3, 1],
                    "force": True,
                    "estimate": estimate,
                    "log_path": str(log_path),
                },
            )
        ).result
        range_cooked = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.run",
                request_id="cook-range-run",
                arguments={"job_id": range_submit.data["job_id"]},
            )
        ).result
        assert range_cooked.status.value == "success", range_cooked.errors
        assert range_cooked.cook.frames == [1.0, 2.0, 3.0]
        assert [item["frame"] for item in range_cooked.data["frame_metrics"]] == [
            1.0,
            2.0,
            3.0,
        ]
        assert range_cooked.data["frame_metrics"][-1]["bounds"][1][0] == pytest.approx(1.5)
        assert float(hou.frame()) == original_frame

        cancelled_submit = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.submit",
                request_id="cook-cancel-submit",
                policy=Policy.from_dict(policy),
                arguments={
                    "node_path": output.path(),
                    "estimate": estimate,
                    "log_path": str(log_path),
                },
            )
        ).result
        cancelled = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.cancel",
                request_id="cook-cancel",
                arguments={"job_id": cancelled_submit.data["job_id"]},
            )
        ).result
        assert cancelled.data["state"] == "cancelled"
        refused = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.run",
                request_id="cook-run-cancelled",
                arguments={"job_id": cancelled.data["job_id"]},
            )
        ).result
        assert refused.status.value == "error"

        records = [json.loads(line) for line in log_path.read_text().splitlines()]
        assert [record["event"] for record in records] == [
            "submitted",
            "finished",
            "submitted",
            "finished",
            "submitted",
            "finished",
            "submitted",
            "cancelled",
        ]
    finally:
        geo.destroy()


def test_graph_svg_is_headless_visual_artifact_without_selection_side_effects(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_GRAPH_CAPTURE", run_init_scripts=False)
    source = geo.createNode("sphere", node_name="SRC_FORM")
    output = geo.createNode("null", node_name="OUT_FORM")
    source.setPosition(hou.Vector2(0, 1))
    output.setPosition(hou.Vector2(0, -1))
    output.setInput(0, source)
    source.setSelected(True, clear_all_selected=True)
    artifact = tmp_path / "network.svg"
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    try:
        captured = dispatcher.process_one(
            CommandEnvelope(
                tool="graph.capture_svg",
                request_id="graph-svg",
                arguments={"node_path": geo.path(), "output_path": str(artifact)},
            )
        ).result
        assert captured.status.value == "success", captured.errors
        assert captured.data["nodes"] == 2
        assert captured.data["wires"] == 1
        assert artifact.is_file()
        svg = artifact.read_text()
        assert "SRC_FORM" in svg and "OUT_FORM" in svg and "<path" in svg
        assert hou.selectedNodes() == (source,)

        viewers = dispatcher.process_one(
            CommandEnvelope(tool="observation.viewers", request_id="headless-viewers")
        ).result
        assert viewers.data == {"available": False, "viewers": []}
    finally:
        source.setSelected(False)
        geo.destroy()


def test_cook_budget_blocks_known_cache_and_reports_dirty_output_overrun(tmp_path):
    obj = hou.node("/obj")
    geo = obj.createNode("geo", node_name="HERMES_COOK_BUDGET", run_init_scripts=False)
    box = geo.createNode("box", node_name="BUDGET_BOX")
    box.cook(force=True)
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    policy = Policy(
        max_points=4,
        max_primitives=10,
        max_memory_bytes=10_000_000,
        max_seconds=5,
    )
    estimate = {
        "points": 4,
        "primitives": 6,
        "memory_bytes": 1_000_000,
        "seconds": 1.0,
    }
    log_path = str(tmp_path / "budget.jsonl")

    def submit(request_id):
        return dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.submit",
                request_id=request_id,
                policy=policy,
                arguments={
                    "node_path": box.path(),
                    "force": True,
                    "estimate": estimate,
                    "log_path": log_path,
                },
            )
        ).result

    try:
        initial_count = box.cookCount()
        clean_job = submit("known-cache-submit")
        blocked = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.run",
                request_id="known-cache-run",
                arguments={"job_id": clean_job.data["job_id"]},
            )
        ).result
        assert blocked.status.value == "blocked"
        assert "points 8 > budget 4" in blocked.errors
        assert box.cookCount() == initial_count

        box.parm("sizey").set(2.0)
        assert box.needsToCook() is True
        dirty_job = submit("dirty-overrun-submit")
        overrun = dispatcher.process_one(
            CommandEnvelope(
                tool="cook.job.run",
                request_id="dirty-overrun-run",
                arguments={"job_id": dirty_job.data["job_id"]},
            )
        ).result
        assert overrun.status.value == "error"
        assert "points 8 > budget 4" in overrun.errors
        assert overrun.data["job"]["state"] == "failed"
    finally:
        geo.destroy()


def test_material_foundry_skill_validates_native_channels_and_materialx_stage(tmp_path):
    skill = load_skill("skills/lookdev.procedural_material_foundry")
    calls = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="hython_foundry",
        resolution=64,
        candidate_index=1,
        render_preview=False,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    network = swatches = None
    try:
        results = [_dispatch_planned_call(dispatcher, call) for call in calls]
        assert all(result.status.value == "success" for result in results), [
            result.errors for result in results
        ]
        network = hou.node("/img/HYTHON_FOUNDRY_COPNET")
        swatches = hou.node("/obj/HYTHON_FOUNDRY_SWATCHES")
        assert network is not None and swatches is not None
        assert not any(
            node.type().name() in {"python", "pythonfilter"} for node in network.children()
        )
        materials = [
            network.node("OUT_HYTHON_FOUNDRY_VERDIGRIS_USD_MATERIAL"),
            network.node("OUT_HYTHON_FOUNDRY_EMBERGLAZE_USD_MATERIAL"),
            network.node("OUT_HYTHON_FOUNDRY_MOONLICHEN_USD_MATERIAL"),
        ]
        assert [node.type().name() for node in materials] == ["usdmaterial"] * 3
        channel_validation = results[3].data
        assert channel_validation["spec"]["channels"] == [
            "base_color",
            "roughness",
            "height",
            "normal",
        ]
        assert all(
            candidate["channels"]["base_color"]["components"] == 3
            for candidate in channel_validation["candidates"]
        )
        assert all(
            candidate["channels"]["roughness"]["components"] == 1
            for candidate in channel_validation["candidates"]
        )
        stage_validation = results[6].data
        assert stage_validation["material_system"] == "MaterialX"
        assert len(stage_validation["bindings"]) == 3
        assert all(item["materialx_outputs"] for item in stage_validation["bindings"])
        assert stage_validation["selection"]["winner"] is None
        assert (tmp_path / "manifests" / "hython_foundry_pbr_channels.json").is_file()
        assert (tmp_path / "observations" / "hython_foundry_cop_graph.svg").is_file()
        assert list((tmp_path / "scenes").glob("material_foundry_hython_foundry_final_v*.hipnc"))
    finally:
        # H22.0.368 can bus-error when an in-memory USD material library is torn down
        # immediately before its live COP source network. The isolated hython process owns
        # this disposable scene, so process teardown is the safer cleanup boundary.
        pass


def test_world_seed_atlas_cooks_three_native_worlds_and_validates_usd_stage(tmp_path):
    skill = load_skill("skills/world.world_seed_atlas")
    calls = skill.plan(
        artifact_dir=str(tmp_path),
        run_id="hython_world_seed",
        base_seed=19019,
        terrain_samples=64,
        world_size=9.0,
        render_preview=False,
    )
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    results = [_dispatch_planned_call(dispatcher, call) for call in calls]
    assert all(result.status.value == "success" for result in results), [
        result.errors for result in results
    ]

    validation = results[4].data
    assert [item["id"] for item in validation["candidates"]] == [
        "amber_mesa",
        "verdant_rift",
        "lunar_basin",
    ]
    assert 0 < validation["total_points"] <= 150_000
    assert 0 < validation["total_primitives"] <= 150_000
    assert validation["selection"] == {
        "method": "human",
        "winner": None,
        "automatic_ranking": False,
    }
    assert all(item["metrics"]["point_attributes"] for item in validation["candidates"])
    assert all("Cd" in item["metrics"]["point_attributes"] for item in validation["candidates"])

    for candidate_id in ("AMBER_MESA", "VERDANT_RIFT", "LUNAR_BASIN"):
        network = hou.node(f"/obj/HYTHON_WORLD_SEED_{candidate_id}")
        assert network is not None
        output = network.node(f"OUT_HYTHON_WORLD_SEED_{candidate_id}_WORLD")
        assert output is not None
        assert output.userData("hermes_role") == "world_seed_world_contract"
        assert output.geometry().pointCount() > 0
        assert not any(node.type().name() == "python" for node in network.children())

    stage_validation = results[6].data
    assert [item["id"] for item in stage_validation["worlds"]] == [
        "amber_mesa",
        "verdant_rift",
        "lunar_basin",
    ]
    assert all(item["descendants"] > 0 for item in stage_validation["worlds"])
    assert stage_validation["selection"]["winner"] is None
    assert (tmp_path / "manifests" / "hython_world_seed_world_validation.json").is_file()
    assert (tmp_path / "observations" / "hython_world_seed_obj_graph.svg").is_file()
    assert (tmp_path / "observations" / "hython_world_seed_lop_graph.svg").is_file()
    assert list((tmp_path / "scenes").glob("world_seed_atlas_hython_world_seed_final_v*.hipnc"))
