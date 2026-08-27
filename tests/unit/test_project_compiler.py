from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys

import pytest
from hermes_houdini.project_compiler import PLAN_SCHEMA, compile_project


def _capability(capability_id: str, context: str, output: str) -> dict:
    return {
        "capability_id": capability_id,
        "version": "1.0.0",
        "kind": "skill",
        "contexts": [context],
        "outputs": [output],
        "approvals": ["artist_network_edit"] if capability_id == "consume" else [],
        "risk": "medium" if capability_id == "consume" else "low",
        "cook_budget": {"seconds": 2},
        "license": {"mode": "houdini-apprentice-noncommercial"},
        "tested_builds": ["22.0.368"],
        "optional_dependencies": [],
        "fallbacks": [],
        "evidence_status": "pending",
        "source": f"skills/{capability_id}/skill.yaml",
    }


def _instance(
    instance_id: str,
    capability_id: str,
    context: str,
    output_contract: str,
    *,
    variants: list[str] | None = None,
) -> dict:
    return {
        "instance_id": instance_id,
        "capability_id": capability_id,
        "capability_version": "1.0.0",
        "context": context,
        "parent_contract": f"{context.lower()}.parent.v1",
        "inputs": {},
        "output_contracts": {"main": output_contract},
        "variant_scope": variants or [],
        "dependencies": [],
        "requested_evidence": [{"gate_id": "graph", "status": "pending"}],
        "scope": {
            "graph_edit": "bounded_native_nodes",
            "cook": "single_node",
            "cache": "none",
            "render": "none",
        },
        "budget": {"seconds": 1, "memory_bytes": 100},
        "approvals": [],
        "permitted_native_fallbacks": [],
    }


def _inputs() -> tuple[dict, dict, list[dict]]:
    variants = [
        {
            "variant_id": "marsh",
            "label": "Marsh",
            "human_rating": None,
            "selected_for_continuation": None,
        },
        {
            "variant_id": "alpine",
            "label": "Alpine",
            "human_rating": None,
            "selected_for_continuation": None,
        },
        {
            "variant_id": "desert",
            "label": "Desert",
            "human_rating": None,
            "selected_for_continuation": None,
        },
    ]
    source = _instance("world", "produce", "SOP", "geo.world.v1", variants=[v["variant_id"] for v in variants])
    target = _instance("stage", "consume", "LOP", "usd.stage.v1", variants=[v["variant_id"] for v in variants])
    target["dependencies"] = ["world"]
    target["inputs"] = {
        "world": {
            "contract_id": "usd.import.v1",
            "from_instance_id": "world",
            "from_port": "main",
            "adapter_id": "sop-to-lop",
            "adapter_version": "1.0.0",
            "permitted_native_fallbacks": [],
        }
    }
    spec = {
        "schema": "hermes.houdini.project.v1",
        "schema_version": "1.0",
        "project_id": "living-biome",
        "title": "Living Biome",
        "brief": "Three equal-status biome directions.",
        "references": [],
        "compatibility": {
            "houdini_build": "22.0.368",
            "license_mode": "houdini-apprentice-noncommercial",
            "package_version": "0.35.0",
            "optional_dependencies": [],
            "permitted_native_fallbacks": [],
        },
        "roots": {"project": ".", "cache": "cache", "renders": "renders"},
        "seed_policy": {"mode": "fixed", "seed": 42},
        "timeline": {"start": 1, "end": 24, "fps": 24},
        "budgets": {
            "stage": {"seconds": 3, "memory_bytes": 1000},
            "aggregate": {"seconds": 10, "memory_bytes": 1000},
        },
        "capability_instances": [source, target],
        "variants": variants,
        "output_contracts": [
            {
                "contract_id": "shot.stage.v1",
                "from_instance_id": "stage",
                "from_port": "main",
            }
        ],
        "evidence_gates": [{"gate_id": "visual", "status": "pending"}],
        "human_decisions": [{"decision_id": "continue", "owner": None, "value": None}],
        "automatic_ranking": False,
        "winner": None,
    }
    catalog = {
        "schema": "hermes.houdini.capability_catalog",
        "schema_version": "1.0",
        "package_version": "0.35.0",
        "records": [
            _capability("produce", "SOP", "geo.world.v1"),
            _capability("consume", "LOP", "usd.stage.v1"),
        ],
    }
    adapter = {
        "schema": "hermes.houdini.project_adapter.v1",
        "adapter_id": "sop-to-lop",
        "version": "1.0.0",
        "from_contract": "geo.world.v1",
        "to_contract": "usd.import.v1",
        "source_context": "SOP",
        "target_context": "LOP",
        "native_fallback": "sop_import_native",
        "risk": "low",
        "approvals": [],
        "budget_effect": {"seconds": 0.25},
        "tested_builds": ["22.0.368"],
        "license_mode": "houdini-apprentice-noncommercial",
        "optional_dependencies": [],
        "evidence_status": "pending",
    }
    return spec, catalog, [adapter]


def _compile() -> dict:
    spec, catalog, adapters = _inputs()
    return compile_project(spec, capability_catalog=catalog, adapter_records=adapters)


def _codes(plan: dict) -> set[str]:
    return {item["code"] for item in plan["blockers"]}


def _reverse_keys(value):
    if isinstance(value, dict):
        return {key: _reverse_keys(value[key]) for key in reversed(value)}
    if isinstance(value, list):
        return [_reverse_keys(item) for item in value]
    return value


def test_valid_plan_is_deterministic_reviewable_and_non_executable():
    plan = _compile()

    assert plan["schema"] == PLAN_SCHEMA
    assert plan["status"] == "planned"
    assert not plan["blockers"]
    assert len(plan["stages"]) == 6
    assert len(plan["topological_order"]) == 6
    assert plan["automatic_execution"] is False
    assert plan["automatic_ranking"] is False
    assert plan["winner"] is None
    assert [item["variant_id"] for item in plan["variants"]] == ["marsh", "alpine", "desert"]
    assert all(item["human_rating"] is None for item in plan["variants"])
    assert plan["human_decisions"][0]["owner"] is None
    assert plan["aggregate_budget"] == {"memory_bytes": 600, "seconds": 6.75}
    consumer = next(item for item in plan["stages"] if item["instance_id"] == "stage")
    assert consumer["checkpoint"] == {"required": True, "boundary": "before_stage"}
    assert consumer["approvals"] == [
        {"approval_id": "artist_network_edit", "status": "pending"}
    ]
    assert consumer["contract_bindings"][0]["adapter"]["record"]["adapter_id"] == "sop-to-lop"


def test_plan_hash_excludes_only_itself():
    plan = _compile()
    recorded = plan.pop("plan_sha256")
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert recorded == hashlib.sha256(encoded.encode()).hexdigest()


def test_key_order_and_adapter_input_order_do_not_change_plan():
    spec, catalog, adapters = _inputs()
    unused = copy.deepcopy(adapters[0])
    unused.update(adapter_id="unused", version="9.9.9")
    first = compile_project(
        spec,
        capability_catalog=catalog,
        adapter_records=[adapters[0], unused],
    )
    second = compile_project(
        _reverse_keys(spec),
        capability_catalog=_reverse_keys(catalog),
        adapter_records=[_reverse_keys(unused), _reverse_keys(adapters[0])],
    )
    assert first == second


def test_hash_is_stable_in_a_fresh_process():
    spec, catalog, adapters = _inputs()
    payload = json.dumps({"spec": spec, "catalog": catalog, "adapters": adapters})
    code = (
        "import json,sys; from hermes_houdini.project_compiler import compile_project; "
        "x=json.load(sys.stdin); print(compile_project(x['spec'], "
        "capability_catalog=x['catalog'], adapter_records=x['adapters'])['plan_sha256'])"
    )
    hashes = [
        subprocess.check_output([sys.executable, "-c", code], input=payload, text=True).strip()
        for _ in range(2)
    ]
    assert hashes[0] == hashes[1] == _compile()["plan_sha256"]


def test_disconnected_graph_preserves_source_order():
    spec, catalog, adapters = _inputs()
    spec["capability_instances"][1]["dependencies"] = []
    spec["capability_instances"][1]["inputs"] = {}
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert [item["instance_id"] for item in plan["stages"]] == [
        "world",
        "world",
        "world",
        "stage",
        "stage",
        "stage",
    ]


def test_dependency_cycle_blocks():
    spec, catalog, adapters = _inputs()
    spec["capability_instances"][0]["dependencies"] = ["stage"]
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert "dependency_cycle" in _codes(plan)


def test_duplicate_provider_requires_explicit_source():
    spec, catalog, adapters = _inputs()
    duplicate = copy.deepcopy(spec["capability_instances"][0])
    duplicate["instance_id"] = "world-two"
    spec["capability_instances"].insert(1, duplicate)
    spec["capability_instances"][2]["inputs"]["world"].pop("from_instance_id")
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert "multiple_unresolved_providers" in _codes(plan)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda spec, catalog: catalog.update(records=catalog["records"][:1]), "missing_capability"),
        (
            lambda spec, catalog: catalog["records"].append(copy.deepcopy(catalog["records"][1])),
            "ambiguous_capability",
        ),
        (
            lambda spec, catalog: spec["capability_instances"][1].update(context="SOP"),
            "context_mismatch",
        ),
        (
            lambda spec, catalog: catalog["records"][1].update(tested_builds=["22.0.999"]),
            "houdini_build_mismatch",
        ),
        (
            lambda spec, catalog: catalog["records"][1].update(license={"mode": "commercial"}),
            "license_mismatch",
        ),
        (lambda spec, catalog: catalog.update(package_version="0.34.0"), "package_version_mismatch"),
    ],
)
def test_capability_and_compatibility_drift_blocks(mutation, expected):
    spec, catalog, adapters = _inputs()
    mutation(spec, catalog)
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert expected in _codes(plan)


def test_missing_and_ambiguous_adapters_block():
    spec, catalog, adapters = _inputs()
    missing = compile_project(spec, capability_catalog=catalog, adapter_records=[])
    ambiguous = compile_project(
        spec,
        capability_catalog=catalog,
        adapter_records=[adapters[0], copy.deepcopy(adapters[0])],
    )
    assert "missing_adapter" in _codes(missing)
    assert "ambiguous_adapter" in _codes(ambiguous)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("source_context", "DOP", "adapter_context_mismatch"),
        ("tested_builds", ["22.0.999"], "adapter_build_mismatch"),
        ("license_mode", "commercial", "adapter_license_mismatch"),
    ],
)
def test_adapter_compatibility_drift_blocks(field, value, expected):
    spec, catalog, adapters = _inputs()
    adapters[0][field] = value
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert expected in _codes(plan)


def test_dependency_requires_explicitly_permitted_native_fallback():
    spec, catalog, adapters = _inputs()
    catalog["records"][0]["optional_dependencies"] = ["SideFXLabs"]
    catalog["records"][0]["fallbacks"] = ["native_world"]
    blocked = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    spec["capability_instances"][0]["permitted_native_fallbacks"] = ["native_world"]
    permitted = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert "unavailable_dependency" in _codes(blocked)
    assert "unavailable_dependency" not in _codes(permitted)
    assert permitted["stages"][0]["native_fallback"] == "native_world"


def test_stage_and_aggregate_budget_overflow_block():
    spec, catalog, adapters = _inputs()
    spec["budgets"]["stage"]["seconds"] = 0.5
    spec["budgets"]["aggregate"]["memory_bytes"] = 500
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert {"stage_budget_overflow", "aggregate_budget_overflow"} <= _codes(plan)


def test_undeclared_output_and_missing_dependency_block():
    spec, catalog, adapters = _inputs()
    target = spec["capability_instances"][1]
    target["dependencies"] = ["absent"]
    target["inputs"]["world"]["from_port"] = "missing"
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert {"undeclared_output", "missing_dependency_stage"} <= _codes(plan)


def test_capability_must_declare_instance_output_contract():
    spec, catalog, adapters = _inputs()
    catalog["records"][0]["outputs"] = ["different.contract.v1"]
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert "undeclared_output_contract" in _codes(plan)


def test_prefilled_creative_selection_is_blocked_but_preserved_for_review():
    spec, catalog, adapters = _inputs()
    spec["automatic_ranking"] = True
    spec["winner"] = "marsh"
    spec["variants"][0]["human_rating"] = 5
    plan = compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
    assert {
        "automatic_ranking_forbidden",
        "winner_forbidden",
        "human_field_not_blank",
    } <= _codes(plan)
    assert plan["variants"][0]["human_rating"] == 5
    assert plan["automatic_ranking"] is False
    assert plan["winner"] is None


def test_pending_evidence_approval_and_human_slots_are_not_promoted():
    plan = _compile()
    consumer = next(item for item in plan["stages"] if item["instance_id"] == "stage")
    assert consumer["evidence"] == [{"gate_id": "graph", "status": "pending"}]
    assert consumer["approvals"][0]["status"] == "pending"
    assert plan["evidence_gates"] == [{"gate_id": "visual", "status": "pending"}]
    assert plan["human_decisions"] == [
        {"decision_id": "continue", "owner": None, "value": None}
    ]


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (([], {}, []), "spec must be a mapping"),
        (({}, [], []), "capability_catalog must be a mapping"),
        (({}, {}, ["bad"]), "adapter_records items must be mappings"),
    ],
)
def test_programmer_type_errors_have_deterministic_paths(args, message):
    spec, catalog, adapters = args
    with pytest.raises(ValueError, match=message):
        compile_project(spec, capability_catalog=catalog, adapter_records=adapters)


def test_non_finite_json_value_reports_path():
    spec, catalog, adapters = _inputs()
    spec["budgets"]["stage"]["seconds"] = float("inf")
    with pytest.raises(ValueError, match=r"spec\.budgets\.stage\.seconds"):
        compile_project(spec, capability_catalog=catalog, adapter_records=adapters)
