from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from hermes_houdini.project_adapters import (
    build_adapter_registry,
    load_adapter_record,
    normalize_adapter_record,
    resolve_adapter,
)

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATHS = sorted((ROOT / "project_contracts" / "adapters").glob("*.yaml"))


def _record(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": "hermes.houdini.project_adapter.v1",
        "adapter_id": "test.contract_adapter",
        "version": "1.2.3",
        "from_contract": "source.contract",
        "to_contract": "target.contract",
        "source_context": "SOP",
        "target_context": "LOP",
        "recipe": {"id": "lop.test_adapter", "version": "2.0.0"},
        "risk": "medium",
        "approvals": ["explicit_medium_risk_approval"],
        "budget_effect": {"max_seconds": 10, "render_frames": 0},
        "tested_builds": ["22.0.368"],
        "license_modes": ["houdini-apprentice-noncommercial"],
        "optional_dependencies": [],
        "evidence_status": "pending",
        "source_audit": ["recipes/lop/test_adapter.yaml"],
    }
    value.update(updates)
    return value


def _registry(*records: dict[str, object]) -> dict[str, object]:
    return {"records": list(records)}


def test_bundled_descriptors_are_exact_and_audited() -> None:
    records = [load_adapter_record(path.relative_to(ROOT)) for path in ADAPTER_PATHS]

    assert [(item["adapter_id"], item["version"]) for item in records] == [
        ("project.botanical_geometry_to_world_layer", "1.0.0"),
        ("project.motion_geometry_to_world_layer", "1.0.0"),
        ("project.pbr_channels_to_material_bindings", "1.0.0"),
        ("project.world_geometry_to_solaris", "1.0.0"),
    ]
    assert all(item["tested_builds"] == ["22.0.368"] for item in records)
    assert all(item["evidence_status"] == "pending" for item in records)
    assert all(item["source_audit"] for item in records)
    assert sum("recipe" in item for item in records) == 2
    assert sum("native_fallback" in item for item in records) == 2


def test_normalization_is_key_order_stable_and_hashes_content() -> None:
    value = _record()
    reversed_value = dict(reversed(list(value.items())))

    first = normalize_adapter_record(value, source="a.yaml")
    second = normalize_adapter_record(reversed_value, source="a.yaml")

    assert first == second
    assert len(first["content_sha256"]) == 64
    assert first["source_context"] == "SOP"
    assert first["target_context"] == "LOP"


def test_loader_rejects_non_object_yaml(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- not\n- an\n- object\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain an object"):
        load_adapter_record(path)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"schema": "wrong"}, "adapter.schema"),
        ({"version": "latest"}, "exact semantic version"),
        ({"version": "1.0"}, "exact semantic version"),
        ({"version": "01.0.0"}, "exact semantic version"),
        ({"adapter_id": "Bad Adapter"}, "lowercase dotted identifier"),
        ({"source_context": "VIEWPORT"}, "supported Houdini context"),
        ({"risk": "privileged"}, "risk is unsupported"),
        ({"evidence_status": "certified"}, "evidence_status is unsupported"),
        ({"tested_builds": []}, "must not be empty"),
        ({"license_modes": []}, "must not be empty"),
        ({"budget_effect": []}, "budget_effect must be an object"),
        ({"budget_effect": {"max_seconds": float("nan")}}, "finite values"),
        ({"optional_dependencies": ["plugin", "plugin"]}, "must not contain duplicates"),
    ],
)
def test_malformed_descriptor_is_rejected(updates: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_adapter_record(_record(**updates))


def test_descriptor_requires_exactly_one_implementation_reference() -> None:
    neither = _record()
    neither.pop("recipe")
    with pytest.raises(ValueError, match="exactly one"):
        normalize_adapter_record(neither)

    both = _record(native_fallback="g003.native_test_adapter")
    with pytest.raises(ValueError, match="exactly one"):
        normalize_adapter_record(both)


def test_recipe_reference_requires_exact_id_and_semver() -> None:
    with pytest.raises(ValueError, match="exactly id and version"):
        normalize_adapter_record(
            _record(recipe={"id": "lop.test_adapter", "version": "2.0.0", "latest": True})
        )
    with pytest.raises(ValueError, match="recipe.version"):
        normalize_adapter_record(_record(recipe={"id": "lop.test_adapter", "version": "2"}))


def test_native_fallback_is_named_metadata_not_an_execution_claim() -> None:
    value = _record()
    value.pop("recipe")
    value["native_fallback"] = "g003.native_test_adapter"

    normalized = normalize_adapter_record(value)

    assert normalized["native_fallback"] == "g003.native_test_adapter"
    assert "recipe" not in normalized
    assert normalized["evidence_status"] == "pending"


def test_registry_is_deterministic_across_input_order() -> None:
    forward = build_adapter_registry(ADAPTER_PATHS)
    reverse = build_adapter_registry(reversed(ADAPTER_PATHS))

    assert forward == reverse
    assert forward["record_count"] == 4
    assert [item["adapter_id"] for item in forward["records"]] == sorted(
        item["adapter_id"] for item in forward["records"]
    )
    assert len(forward["registry_sha256"]) == 64


def test_registry_rejects_duplicate_identity() -> None:
    with pytest.raises(ValueError, match="duplicate adapter registry identity"):
        build_adapter_registry([ADAPTER_PATHS[0], ADAPTER_PATHS[0]])


def test_resolve_exact_adapter_preserves_contract_metadata() -> None:
    record = normalize_adapter_record(_record(), source="test.yaml")

    result = resolve_adapter(
        _registry(record),
        from_contract="source.contract",
        to_contract="target.contract",
        version="1.2.3",
        build="22.0.368",
        license_mode="houdini-apprentice-noncommercial",
        allowed_dependencies=[],
    )

    assert result["status"] == "resolved"
    assert result["adapter"] == record
    assert result["adapter"]["risk"] == "medium"
    assert result["adapter"]["approvals"] == ["explicit_medium_risk_approval"]
    assert result["adapter"]["budget_effect"] == {"max_seconds": 10, "render_frames": 0}
    assert result["candidates"] == [
        {
            "adapter_id": "test.contract_adapter",
            "version": "1.2.3",
            "source": "test.yaml",
            "content_sha256": record["content_sha256"],
        }
    ]


def test_resolve_missing_reports_other_exact_contract_versions() -> None:
    record = normalize_adapter_record(_record(), source="test.yaml")

    result = resolve_adapter(
        _registry(record),
        from_contract="source.contract",
        to_contract="target.contract",
        version="9.0.0",
        build="22.0.368",
        license_mode="houdini-apprentice-noncommercial",
        allowed_dependencies=[],
    )

    assert result["status"] == "missing"
    assert [candidate["version"] for candidate in result["candidates"]] == ["1.2.3"]


def test_resolve_ambiguous_reports_every_identity_without_first_match() -> None:
    first = normalize_adapter_record(_record(), source="first.yaml")
    second_value = _record(adapter_id="test.alternate_adapter")
    second = normalize_adapter_record(second_value, source="second.yaml")

    result = resolve_adapter(
        _registry(first, second),
        from_contract="source.contract",
        to_contract="target.contract",
        version="1.2.3",
        build="22.0.368",
        license_mode="houdini-apprentice-noncommercial",
        allowed_dependencies=[],
    )

    assert result["status"] == "ambiguous"
    assert [item["adapter_id"] for item in result["candidates"]] == [
        "test.alternate_adapter",
        "test.contract_adapter",
    ]
    assert "adapter" not in result


def test_resolve_reports_build_license_and_dependency_incompatibility() -> None:
    record = normalize_adapter_record(
        _record(optional_dependencies=["SideFXLabs22.0"]), source="plugin.yaml"
    )

    result = resolve_adapter(
        _registry(record),
        from_contract="source.contract",
        to_contract="target.contract",
        version="1.2.3",
        build="22.5.1",
        license_mode="houdini-fx-commercial",
        allowed_dependencies=[],
    )

    assert result["status"] == "incompatible"
    assert [reason["code"] for reason in result["reasons"]] == [
        "unsupported_build",
        "unsupported_license",
        "missing_dependencies",
    ]


def test_dependency_adapter_resolves_only_when_explicitly_allowed() -> None:
    record = normalize_adapter_record(
        _record(optional_dependencies=["SideFXLabs22.0"]), source="plugin.yaml"
    )

    result = resolve_adapter(
        _registry(record),
        from_contract="source.contract",
        to_contract="target.contract",
        version="1.2.3",
        build="22.0.368",
        license_mode="houdini-apprentice-noncommercial",
        allowed_dependencies=["SideFXLabs22.0"],
    )

    assert result["status"] == "resolved"


def test_native_fallback_does_not_inherit_a_plugin_dependency() -> None:
    value = _record(adapter_id="test.native_fallback", optional_dependencies=[])
    value.pop("recipe")
    value["native_fallback"] = "g003.native_test_adapter"
    record = normalize_adapter_record(value, source="native.yaml")

    result = resolve_adapter(
        _registry(record),
        from_contract="source.contract",
        to_contract="target.contract",
        version="1.2.3",
        build="22.0.368",
        license_mode="houdini-apprentice-noncommercial",
        allowed_dependencies=[],
    )

    assert result["status"] == "resolved"
    assert result["adapter"]["native_fallback"] == "g003.native_test_adapter"
    assert result["adapter"]["evidence_status"] == "pending"


def test_record_is_plain_json_data() -> None:
    record = normalize_adapter_record(copy.deepcopy(_record()), source="test.yaml")
    assert json.loads(json.dumps(record)) == record
