"""Tests for pure v1 project specification parsing and canonical hashing."""

from __future__ import annotations

import copy
import math
import shutil
from pathlib import Path

import pytest
import yaml
from hermes_houdini.project_spec import (
    PROJECT_SCHEMA,
    load_project_spec,
    normalize_project_spec,
    project_spec_sha256,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "projects"
VALID = FIXTURES / "g002-valid-three-variants.yaml"


def _raw_valid() -> dict:
    value = yaml.safe_load(VALID.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _reverse_mappings(value):
    if isinstance(value, dict):
        return {key: _reverse_mappings(item) for key, item in reversed(list(value.items()))}
    if isinstance(value, list):
        return [_reverse_mappings(item) for item in value]
    return value


@pytest.mark.parametrize(
    ("fixture", "message"),
    [
        ("g002-traversal.yaml", "beneath project_root"),
        ("g002-duplicate-ids.yaml", "duplicates id"),
        ("g002-unversioned-capability.yaml", "exact semantic version"),
        ("g002-budget-omission.yaml", "missing fields: render_samples"),
        ("g002-frame-inversion.yaml", "greater than or equal"),
        ("g002-non-finite.yaml", "finite non-negative number"),
        ("g002-automatic-ranking.yaml", "automatic_ranking must be false"),
        ("g002-prefilled-human.yaml", "human_rating must remain null"),
    ],
)
def test_deliberate_failure_fixtures(fixture: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_project_spec(FIXTURES / fixture, project_root=FIXTURES.parents[2])


def test_valid_fixture_preserves_order_paths_versions_and_blank_human_fields() -> None:
    normalized = load_project_spec(VALID, project_root=FIXTURES.parents[2])

    assert normalized["schema"] == PROJECT_SCHEMA
    assert [item["reference_id"] for item in normalized["references"]] == [
        "terrain-shapes",
        "palette-notes",
    ]
    assert [item["variant_id"] for item in normalized["variants"]] == [
        "amber-mesa",
        "verdant-rift",
        "lunar-basin",
    ]
    assert [item["instance_id"] for item in normalized["capability_instances"]] == [
        "world",
        "materials",
    ]
    assert normalized["capability_instances"][1]["capability_version"] == "1.2.0"
    assert normalized["roots"] == {
        "project": ".",
        "assets": "assets",
        "cache": "cache/g002",
        "renders": "renders/g002",
    }
    assert normalized["winner"] is None
    assert normalized["automatic_ranking"] is False
    assert all(item["human_rating"] is None for item in normalized["variants"])
    assert all(item["selected_for_continuation"] is None for item in normalized["variants"])


def test_hash_is_stable_across_mapping_key_order() -> None:
    raw = _raw_valid()
    root = FIXTURES.parents[2]
    first = normalize_project_spec(raw, project_root=root)
    second = normalize_project_spec(_reverse_mappings(raw), project_root=root)

    assert first == second
    assert project_spec_sha256(first) == project_spec_sha256(second)


def test_hash_is_stable_across_absolute_checkout_locations(tmp_path: Path) -> None:
    roots = [tmp_path / "checkout-a", tmp_path / "different" / "checkout-b"]
    hashes = []
    for root in roots:
        project_file = root / "specs" / "project.yaml"
        project_file.parent.mkdir(parents=True)
        shutil.copyfile(VALID, project_file)
        normalized = load_project_spec(project_file, project_root=root)
        hashes.append(project_spec_sha256(normalized))
        assert not any(str(root) in str(item) for item in normalized.values())
    assert hashes[0] == hashes[1]


def test_loading_is_explicit_and_confined(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.yaml"
    shutil.copyfile(VALID, outside)
    with pytest.raises(ValueError, match="specification path must resolve beneath"):
        load_project_spec(outside, project_root=project)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (project / "linked").symlink_to(outside, target_is_directory=True)
    raw = _raw_valid()
    raw["references"][0]["path"] = "linked/reference.png"
    with pytest.raises(ValueError, match="beneath project_root"):
        normalize_project_spec(raw, project_root=project)


def test_project_root_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="project_root must be absolute"):
        normalize_project_spec(_raw_valid(), project_root="relative")


def test_unknown_top_level_field_is_rejected() -> None:
    raw = _raw_valid()
    raw["surprise"] = True
    with pytest.raises(ValueError, match="unknown fields: surprise"):
        normalize_project_spec(raw, project_root=FIXTURES.parents[2])


@pytest.mark.parametrize("yaml_text", ["- not\n- an\n- object\n", "null\n", "plain scalar\n"])
def test_yaml_root_must_be_an_object(tmp_path: Path, yaml_text: str) -> None:
    path = tmp_path / "project.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    with pytest.raises(ValueError, match="YAML root must be an object"):
        load_project_spec(path, project_root=tmp_path)


def test_recursive_yaml_alias_is_rejected() -> None:
    raw = _raw_valid()
    raw["capability_instances"][0]["inputs"] = yaml.safe_load("&loop {self: *loop}\n")
    with pytest.raises(ValueError, match="recursive YAML alias"):
        normalize_project_spec(raw, project_root=FIXTURES.parents[2])


def test_non_json_alias_value_is_rejected_with_deterministic_path() -> None:
    raw = _raw_valid()
    raw["capability_instances"][0]["inputs"] = {"bad": {1, 2}}
    with pytest.raises(ValueError, match=r"capability_instances\[0\]\.inputs\.bad"):
        normalize_project_spec(raw, project_root=FIXTURES.parents[2])


def test_nan_cannot_enter_inputs_or_hash() -> None:
    raw = _raw_valid()
    raw["capability_instances"][0]["inputs"] = {"bad": math.nan}
    with pytest.raises(ValueError, match="NaN or Infinity"):
        normalize_project_spec(raw, project_root=FIXTURES.parents[2])
    with pytest.raises(ValueError, match="NaN or Infinity"):
        project_spec_sha256({"bad": math.inf})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("winner", "amber-mesa", "winner must remain null"),
        ("automatic_ranking", 0, "automatic_ranking must be false"),
    ],
)
def test_top_level_human_authority_fields_are_strict(
    field: str, value: object, message: str
) -> None:
    raw = _raw_valid()
    raw[field] = value
    with pytest.raises(ValueError, match=message):
        normalize_project_spec(raw, project_root=FIXTURES.parents[2])


def test_selected_continuation_and_decision_winner_must_remain_null() -> None:
    raw = _raw_valid()
    selected = copy.deepcopy(raw)
    selected["variants"][1]["selected_for_continuation"] = True
    with pytest.raises(ValueError, match="selected_for_continuation must remain null"):
        normalize_project_spec(selected, project_root=FIXTURES.parents[2])

    decision = copy.deepcopy(raw)
    decision["human_decisions"][0]["winner"] = "verdant-rift"
    with pytest.raises(ValueError, match="winner must remain null"):
        normalize_project_spec(decision, project_root=FIXTURES.parents[2])


def test_declared_ids_and_stage_budgets_must_resolve() -> None:
    raw = _raw_valid()
    raw["budgets"]["stages"].pop()
    with pytest.raises(ValueError, match="must match capability instances"):
        normalize_project_spec(raw, project_root=FIXTURES.parents[2])


def test_normalization_does_not_validate_capability_existence() -> None:
    raw = _raw_valid()
    raw["capability_instances"][0]["capability_id"] = "not_in_any_catalog"
    raw["capability_instances"][0]["capability_version"] = "99.0.0"
    normalized = normalize_project_spec(raw, project_root=FIXTURES.parents[2])
    assert normalized["capability_instances"][0]["capability_id"] == "not_in_any_catalog"
