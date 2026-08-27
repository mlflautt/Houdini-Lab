"""Pure contract tests for the G002 project observer and drift index."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from hermes_houdini.project_observer import (
    EVIDENCE_RUNGS,
    PROJECT_INDEX_SCHEMA,
    build_project_index,
)

SOURCE_HASH = "1" * 64
PLAN_HASH = "2" * 64


def _project() -> dict:
    return {
        "schema": "hermes.houdini.project.v1",
        "project_id": "living-biome",
        "project_sha256": SOURCE_HASH,
        "compatibility": {
            "houdini_build": "22.0.368",
            "license": "apprentice-non-commercial",
            "package": "0.35.0",
            "optional_dependencies": ["sidefx-labs@22.0.368"],
        },
        "variants": [
            {
                "variant_id": "bog",
                "human_rating": None,
                "selected_for_continuation": None,
            },
            {
                "variant_id": "alpine",
                "human_rating": None,
                "selected_for_continuation": None,
            },
            {
                "variant_id": "desert",
                "human_rating": None,
                "selected_for_continuation": None,
            },
        ],
        "human_decisions": [
            {
                "decision_id": "biome-lineage",
                "winner": None,
                "feedback": None,
                "selected_for_continuation": None,
            }
        ],
    }


def _plan() -> dict:
    return {
        "schema": "hermes.houdini.project_plan.v1",
        "project_id": "living-biome",
        "plan_sha256": PLAN_HASH,
        "compatibility": _project()["compatibility"],
        "variants": _project()["variants"],
        "human_decisions": _project()["human_decisions"],
        "stages": [
            {
                "stage_id": "terrain",
                "capability_id": "world.seed",
                "capability_version": "1.0.0",
                "output_contracts": ["terrain.geo"],
                "checkpoint": {"boundary": "before", "required": True},
                "approvals": [{"approval_id": "graph-edit", "required": True, "status": "pass"}],
                "evidence_gates": [
                    {"rung": "graph", "required": True},
                    {"rung": "data", "required": True},
                ],
            },
            {
                "stage_id": "lookdev",
                "capability_id": "material.foundry",
                "capability_version": "1.0.0",
                "inputs": [{"contract_id": "terrain.geo", "producer_stage_id": "terrain"}],
                "output_contracts": ["lookdev.usd"],
                "evidence_gates": [{"rung": "pixel", "required": True}],
            },
        ],
        "automatic_execution": False,
    }


def _runtime(**overrides) -> dict:
    value = {
        **_project()["compatibility"],
        "source_sha256": SOURCE_HASH,
        "capability_adapter_identity": [
            {"kind": "capability", "id": "world.seed", "version": "1.0.0"},
            {"kind": "capability", "id": "material.foundry", "version": "1.0.0"},
        ],
    }
    value.update(overrides)
    return value


def _record(stage_id: str, status: str = "pass", **overrides) -> dict:
    rungs = ["graph", "data"] if stage_id == "terrain" else ["pixel"]
    value = {
        "stage_id": stage_id,
        "source_sha256": SOURCE_HASH,
        "plan_sha256": PLAN_HASH,
        "status": status,
        "evidence": [{"rung": rung, "status": status} for rung in rungs],
    }
    value.update(overrides)
    return value


def _full_records() -> list[dict]:
    return [_record("terrain"), _record("lookdev")]


def test_dry_plan_is_pending_and_preserves_independent_rungs_and_human_slots():
    index = build_project_index(_project(), _plan())

    assert index["schema"] == PROJECT_INDEX_SCHEMA
    assert index["mechanical_status"] == "pending"
    assert index["human_status"] == "pending"
    assert [item["execution_status"] for item in index["stages"]] == ["pending", "pending"]
    assert set(EVIDENCE_RUNGS).issubset(index["evidence_by_rung"])
    assert index["evidence_by_rung"]["graph"][0]["status"] == "pending"
    assert index["evidence_by_rung"]["pixel"][0]["status"] == "not_applicable"
    assert index["winner"] is None
    assert index["variants"] == _project()["variants"]
    assert index["human_records"] == []


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("pass", "pass"),
        ("warn", "warn"),
        ("pending", "pending"),
        ("blocked", "blocked"),
        ("not_applicable", "pending"),
    ],
)
def test_all_five_g001_evidence_states_remain_distinct(state, expected):
    records = [_record("terrain", state), _record("lookdev", state)]
    index = build_project_index(
        _project(), _plan(), runtime_identity=_runtime(), execution_records=records
    )

    assert index["mechanical_status"] == expected
    assert index["evidence_by_rung"]["graph"][0]["status"] == state
    assert index["evidence_by_rung"]["pixel"][1]["status"] == state


def test_explicit_non_applicable_stage_retains_concrete_reason():
    plan = _plan()
    plan["stages"][1]["status"] = "not_applicable"
    plan["stages"][1]["non_applicable_reason"] = "dry compiler lane produces no pixels"
    index = build_project_index(
        _project(), plan, runtime_identity=_runtime(), execution_records=[_record("terrain")]
    )

    stage = index["stages"][1]
    assert stage["execution_status"] == "not_applicable"
    assert all(row["reason"] == "dry compiler lane produces no pixels" for row in stage["evidence"])
    assert index["mechanical_status"] == "pass"


def test_full_mechanical_evidence_does_not_infer_human_acceptance():
    index = build_project_index(
        _project(), _plan(), runtime_identity=_runtime(), execution_records=_full_records()
    )

    assert index["mechanical_status"] == "pass"
    assert index["human_status"] == "pending"
    assert index["winner"] is None
    assert index["blockers"] == []
    assert all(
        row["status"] in {"match", "not_applicable", "not_checked"} for row in index["drift"]
    )


def test_human_fields_are_copied_only_from_explicit_stage_bound_record():
    records = _full_records()
    records[1]["human"] = {
        "status": "pass",
        "reviewer": "artist",
        "rating": 4,
        "winner": "bog",
        "feedback": "Continue the humid silhouette language.",
        "continuation": "bog-v2",
    }
    index = build_project_index(_project(), _plan(), execution_records=records)

    assert index["human_status"] == "pass"
    assert index["winner"] == "bog"
    assert index["human_records"][0]["feedback"].startswith("Continue")
    assert all(variant["human_rating"] is None for variant in index["variants"])

    project = _project()
    project["variants"][0]["human_rating"] = 5
    plan = _plan()
    plan["variants"] = project["variants"]
    with pytest.raises(ValueError, match="explicit human record"):
        build_project_index(project, plan)


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"houdini_build": "22.5.1"}, "houdini_build_drift"),
        ({"license": "commercial"}, "license_drift"),
        ({"package": "0.99.0"}, "package_drift"),
        ({"optional_dependencies": []}, "optional_dependency_drift"),
        ({"source_sha256": "f" * 64}, "source_hash_drift"),
        ({"capability_adapter_identity": []}, "capability_adapter_identity_drift"),
    ],
)
def test_runtime_drift_categories_are_structured_blockers(override, code):
    index = build_project_index(
        _project(),
        _plan(),
        runtime_identity=_runtime(**override),
        execution_records=_full_records(),
    )

    assert index["mechanical_status"] == "blocked"
    assert code in {item["code"] for item in index["blockers"]}
    assert next(row for row in index["drift"] if row["category"] == code.removesuffix("_drift"))[
        "status"
    ] == "drift"


def test_unknown_duplicate_and_hash_mismatched_records_are_blockers():
    records = [
        _record("terrain"),
        _record("terrain"),
        _record("lookdev", plan_sha256="f" * 64),
        _record("not-planned"),
    ]
    index = build_project_index(_project(), _plan(), execution_records=records)

    codes = [item["code"] for item in index["blockers"]]
    assert "unknown_execution_stage" in codes
    assert "duplicate_execution_record" in codes
    assert "execution_record_hash_mismatch" in codes
    assert index["mechanical_status"] == "blocked"
    assert index["stages"][0]["execution_record"] is None
    assert index["stages"][1]["execution_record"] is None


def test_contracts_checkpoints_approvals_and_stage_order_are_indexed():
    index = build_project_index(_project(), _plan())

    assert [stage["stage_id"] for stage in index["stages"]] == ["terrain", "lookdev"]
    assert index["contracts"]["producers"][0] == {
        "contract_id": "lookdev.usd",
        "stage_id": "lookdev",
    }
    assert index["contracts"]["consumers"] == [
        {"contract_id": "terrain.geo", "stage_id": "lookdev", "producer_stage_id": "terrain"}
    ]
    assert index["checkpoints"] == [
        {"stage_id": "terrain", "checkpoint": {"boundary": "before", "required": True}}
    ]
    assert index["approvals"][0]["approval_id"] == "graph-edit"


def test_explicit_topological_order_controls_stage_order_and_is_validated():
    plan = _plan()
    plan["stages"] = list(reversed(plan["stages"]))
    plan["topological_order"] = ["terrain", "lookdev"]
    index = build_project_index(_project(), plan)
    assert [stage["stage_id"] for stage in index["stages"]] == ["terrain", "lookdev"]

    plan["topological_order"] = ["terrain"]
    with pytest.raises(ValueError, match="every stage_id exactly once"):
        build_project_index(_project(), plan)


def test_plan_diagnostics_and_rejected_lineage_are_preserved():
    plan = _plan()
    plan["blockers"] = [{"code": "compiler_blocker", "stage_id": "terrain"}]
    plan["warnings"] = ["compiler_warning"]
    plan["rejected_alternatives"] = [{"variant_id": "old-bog", "reason": "superseded"}]
    index = build_project_index(_project(), plan)

    assert index["mechanical_status"] == "blocked"
    assert index["blockers"][0]["code"] == "compiler_blocker"
    assert index["warnings"][0]["code"] == "compiler_warning"
    assert index["rejected_lineage"][0]["variant_id"] == "old-bog"


def test_artifact_metadata_is_preserved_without_root_and_filesystem_is_not_touched(monkeypatch):
    artifact = {"path": "relative/metadata-only.bgeo.sc", "sha256": "a" * 64, "durable": True}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("hidden filesystem discovery attempted")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(Path, "is_file", forbidden)
    monkeypatch.setattr(Path, "stat", forbidden)
    index = build_project_index(_project(), _plan(), artifacts=[artifact])

    assert index["artifacts"][0]["path"] == artifact["path"]
    assert index["artifacts"][0]["integrity"]["status"] == "not_checked"
    assert index["blockers"] == []


def test_root_requires_absolute_confined_artifact_paths(tmp_path):
    outside = str(tmp_path.parent / "outside.bgeo.sc")
    relative = "cache/relative.bgeo.sc"
    index = build_project_index(
        _project(),
        _plan(),
        project_root=tmp_path,
        artifacts=[{"path": outside}, {"path": relative}],
    )

    assert {item["code"] for item in index["blockers"]} == {
        "artifact_outside_project_root",
        "artifact_path_not_absolute",
    }
    with pytest.raises(ValueError, match="project_root must be absolute"):
        build_project_index(_project(), _plan(), project_root="relative")


def test_durable_hash_and_opt_in_byte_verification(tmp_path):
    artifact_path = tmp_path / "cache" / "terrain.bgeo.sc"
    artifact_path.parent.mkdir()
    artifact_path.write_bytes(b"terrain-v1")
    actual = hashlib.sha256(b"terrain-v1").hexdigest()

    default = build_project_index(
        _project(),
        _plan(),
        project_root=tmp_path,
        artifacts=[{"path": str(artifact_path), "sha256": actual, "durable": True}],
    )
    assert default["artifacts"][0]["integrity"]["status"] == "not_checked"

    verified = build_project_index(
        _project(),
        _plan(),
        project_root=tmp_path,
        artifacts=[
            {"path": str(artifact_path), "sha256": actual, "durable": True, "verify": True}
        ],
    )
    assert verified["artifacts"][0]["integrity"]["status"] == "pass"
    assert next(row for row in verified["drift"] if row["category"] == "artifact_integrity")[
        "status"
    ] == "match"

    mismatch = build_project_index(
        _project(),
        _plan(),
        project_root=tmp_path,
        artifacts=[
            {"path": str(artifact_path), "sha256": "f" * 64, "durable": True, "verify": True}
        ],
    )
    assert "artifact_hash_mismatch" in {item["code"] for item in mismatch["blockers"]}
    assert mismatch["mechanical_status"] == "blocked"


def test_input_order_and_mapping_key_order_do_not_change_index_hash(tmp_path):
    first_path = str(tmp_path / "a.dat")
    second_path = str(tmp_path / "b.dat")
    artifacts = [
        {"path": second_path, "sha256": "b" * 64},
        {"path": first_path, "sha256": "a" * 64},
    ]
    first = build_project_index(
        _project(),
        _plan(),
        project_root=tmp_path,
        execution_records=_full_records(),
        artifacts=artifacts,
    )
    shuffled_project = json.loads(json.dumps(_project(), sort_keys=True))
    shuffled_plan = json.loads(json.dumps(_plan(), sort_keys=True))
    second = build_project_index(
        shuffled_project,
        shuffled_plan,
        project_root=tmp_path,
        execution_records=list(reversed(_full_records())),
        artifacts=list(reversed(artifacts)),
    )

    assert first["index_sha256"] == second["index_sha256"]
    assert [item["path"] for item in first["artifacts"]] == [first_path, second_path]


def test_index_hash_excludes_only_itself():
    index = build_project_index(_project(), _plan())
    original = index["index_sha256"]
    changed_self = dict(index, index_sha256="not-the-hash")
    changed_payload = dict(index, project_id="changed")

    def hash_without_self(value):
        payload = {key: item for key, item in value.items() if key != "index_sha256"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()

    assert hash_without_self(changed_self) == original
    assert hash_without_self(changed_payload) != original
