"""Pure control-plane acceptance for catalog, intent, and handoff contracts."""

from __future__ import annotations

import json

import pytest
from hermes_houdini.capabilities import build_catalog
from hermes_houdini.dispatcher import Dispatcher
from hermes_houdini.handoff import create_handoff, inspect_handoff, plan_resume
from hermes_houdini.policy import default_policy
from hermes_houdini.schemas.command import CommandEnvelope, Status
from hermes_houdini.schemas.control_plane import (
    CapabilityRecord,
    CompatibilityIdentity,
    IntentPlan,
)


def _compatibility() -> dict[str, object]:
    return CompatibilityIdentity(
        houdini_build="22.0.368",
        python_version="3.11.0",
        license_mode="houdini-apprentice-noncommercial",
        package_version="0.25.0",
    ).as_dict()


def _intent() -> dict[str, object]:
    return IntentPlan(
        objective="Build three comparable relic forms and preserve human selection.",
        selected_capabilities=(
            {"id": "model.fractal_relic", "version": "1.1.0", "reason": "native SOP graph"},
        ),
        alternatives=(
            {"id": "sop.fractal_relic_candidate", "status": "retained"},
            {"id": "hermes::fractal_relic", "status": "deferred"},
        ),
        constraints={"license": "apprentice", "automatic_ranking": False},
        resource_estimate={
            "seconds": 60,
            "memory_bytes": 536_870_912,
            "frames": 1,
            "output_bytes": 50_000_000,
        },
        approvals=({"risk": "medium", "status": "required"},),
        verification={"graph": "required", "data": "required", "visual": "pending"},
        human_decisions=({"decision": "candidate winner", "status": "pending"},),
    ).as_dict()


def test_capability_record_rejects_unknown_evidence_state():
    with pytest.raises(ValueError, match="evidence status"):
        CapabilityRecord(
            capability_id="x",
            version="1.0.0",
            kind="tool",
            summary="x",
            contexts=("SYSTEM",),
            risk="low",
            evidence_status="maybe",
        )


def test_catalog_is_deterministic_and_spans_all_registry_kinds():
    Dispatcher()
    first = build_catalog()
    second = build_catalog()
    assert first["catalog_sha256"] == second["catalog_sha256"]
    assert first["record_count"] == len(first["records"])
    assert {record["kind"] for record in first["records"]} == {"tool", "recipe", "hda", "skill"}
    assert all(not record["source"].startswith("/") for record in first["records"])
    assert any(record["capability_id"] == "model.fractal_relic" for record in first["records"])
    assert any(record["capability_id"] == "session.describe" for record in first["records"])


def test_catalog_filters_context_kind_risk_build_and_license():
    Dispatcher()
    skills = build_catalog(context="sop", kind="skill", houdini_build="22.0.368")
    assert skills["records"]
    assert all(record["kind"] == "skill" for record in skills["records"])
    assert all("SOP" in record["contexts"] for record in skills["records"])
    assert all("22.0.368" in record["tested_builds"] for record in skills["records"])
    apprentice = build_catalog(
        kind="skill", license_mode="houdini-apprentice-noncommercial", risk="medium"
    )
    assert apprentice["records"]
    assert all(record["risk"] == "medium" for record in apprentice["records"])


def test_intent_plan_forbids_automatic_winner_and_requires_visual_gate():
    plan = _intent()
    assert plan["winner"] is None
    assert plan["automatic_ranking"] is False
    plan["winner"] = "candidate-a"
    with pytest.raises(ValueError, match="winner"):
        IntentPlan.from_dict(plan)
    plan["winner"] = None
    del plan["verification"]["visual"]
    with pytest.raises(ValueError, match="verification"):
        IntentPlan.from_dict(plan)


def test_handoff_round_trip_hashes_artifacts_and_dry_plans_resume(tmp_path):
    artifact = tmp_path / "graph.svg"
    artifact.write_text("<svg/>", encoding="utf-8")
    output = tmp_path / "handoff.json"
    created = create_handoff(
        output_path=str(output),
        project_root=str(tmp_path),
        project_id="relic-project",
        session_id="session-one",
        compatibility=_compatibility(),
        intent_plan=_intent(),
        artifacts=[{"path": str(artifact), "kind": "graph"}],
        evidence=[{"kind": "graph", "status": "pass"}, {"kind": "visual", "status": "pending"}],
        rejected_alternatives=[{"id": "candidate-b", "reason": "not rejected; retained"}],
        pending_gates=["human_visual_review"],
    )
    assert output.is_file()
    assert created["content_sha256"]
    inspected = inspect_handoff(str(output))
    assert inspected["valid"] is True
    assert inspected["artifact_integrity"][0]["valid"] is True
    resume = plan_resume(file_path=str(output), current_compatibility=_compatibility())
    assert resume["status"] == "ready"
    assert resume["automatic_execution"] is False
    assert resume["steps"][-1]["requires_human_decision"] is True


def test_handoff_detects_tampering(tmp_path):
    output = tmp_path / "handoff.json"
    create_handoff(
        output_path=str(output),
        project_root=str(tmp_path),
        project_id="p",
        session_id="s",
        compatibility=_compatibility(),
        intent_plan=_intent(),
    )
    raw = json.loads(output.read_text(encoding="utf-8"))
    raw["project_id"] = "tampered"
    output.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        inspect_handoff(str(output))


def test_handoff_rejects_nested_path_escape(tmp_path):
    outside = tmp_path.parent / "outside-replay.jsonl"
    with pytest.raises(ValueError, match="outside project_root"):
        create_handoff(
            output_path=str(tmp_path / "handoff.json"),
            project_root=str(tmp_path),
            project_id="p",
            session_id="s",
            compatibility=_compatibility(),
            intent_plan=_intent(),
            replay_logs=[str(outside)],
        )


def test_handoff_inspection_rejects_embedded_root_outside_dispatcher_roots(tmp_path):
    broad_root = tmp_path.parent
    output = tmp_path / "handoff.json"
    create_handoff(
        output_path=str(output),
        project_root=str(broad_root),
        project_id="p",
        session_id="s",
        compatibility=_compatibility(),
        intent_plan=_intent(),
    )
    with pytest.raises(ValueError, match="dispatcher-approved roots"):
        inspect_handoff(str(output), allowed_roots=[str(tmp_path)])


def test_dispatcher_enforces_project_root_allowlist(tmp_path):
    dispatcher = Dispatcher(policy=default_policy([str(tmp_path)]))
    outcome = dispatcher.process_one(
        CommandEnvelope(
            tool="handoff.create",
            arguments={
                "output_path": str(tmp_path / "handoff.json"),
                "project_root": "/etc",
                "project_id": "p",
                "session_id": "s",
                "compatibility": _compatibility(),
                "intent_plan": _intent(),
            },
        )
    )
    assert outcome.result.status == Status.BLOCKED
    assert "outside approved roots" in outcome.result.errors[0]


def test_resume_blocks_incompatible_protocol(tmp_path):
    output = tmp_path / "handoff.json"
    create_handoff(
        output_path=str(output),
        project_root=str(tmp_path),
        project_id="p",
        session_id="s",
        compatibility=_compatibility(),
        intent_plan=_intent(),
    )
    current = _compatibility()
    current["protocol_version"] = "2.0"
    resume = plan_resume(file_path=str(output), current_compatibility=current)
    assert resume["status"] == "blocked"
    assert "protocol_version_mismatch" in resume["blockers"]
