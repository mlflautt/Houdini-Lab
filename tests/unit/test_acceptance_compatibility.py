from __future__ import annotations

import pytest
from hermes_houdini.acceptance.compatibility import (
    compare_compatibility,
    normalize_expectation,
    validate_compatibility_output_path,
)


def _expectation() -> dict[str, object]:
    return {
        "expectation_id": "builtin-box-h22",
        "context": "SOP",
        "category": "Sop",
        "operator_type": "box",
        "required_parameters": {
            "type": {"type": "Menu", "default": 0},
            "size": {"type": "Float", "default": [1.0, 1.0, 1.0]},
        },
        "optional_parameters": {"vertexnormals": {"type": "Toggle", "default": False}},
        "tested_build_range": {"minimum": "22.0.368", "maximum": "22.0.368"},
    }


def _observation() -> dict[str, object]:
    return {
        "live_build": "22.0.368",
        "license": "Apprentice",
        "context": "SOP",
        "category": "Sop",
        "operator_type": "box",
        "available": True,
        "parameters": {
            "type": {"type": "Menu", "default": 0},
            "size": {"type": "Float", "default": [1.0, 1.0, 1.0]},
            "vertexnormals": {"type": "Toggle", "default": False},
        },
    }


def test_normalize_expectation_requires_context_operator_parameters_and_range() -> None:
    normalized = normalize_expectation(_expectation())

    assert normalized["context"] == "SOP"
    assert normalized["category"] == "Sop"
    assert normalized["operator_type"] == "box"
    assert normalized["tested_build_range"] == {
        "minimum": "22.0.368",
        "maximum": "22.0.368",
    }


def test_matching_observation_reports_exact_live_provenance() -> None:
    result = compare_compatibility(_expectation(), _observation())

    assert result["compatible"] is True
    assert result["status"] == "pass"
    assert result["live_build"] == "22.0.368"
    assert result["license"] == "Apprentice"
    assert result["diffs"] == []


def test_missing_operator_is_actionable() -> None:
    observation = _observation()
    observation.update(available=False, parameters={})

    result = compare_compatibility(_expectation(), observation)

    assert result["status"] == "blocked"
    assert result["diffs"] == [
        {
            "code": "missing_operator",
            "path": "SOP/Sop/box",
            "expected": "available",
            "observed": "missing",
            "message": "missing operator SOP/Sop/box on Houdini 22.0.368 (Apprentice)",
        }
    ]


def test_intentional_mismatch_diff_is_deterministic_and_actionable() -> None:
    expectation = _expectation()
    expectation["required_parameters"] = {
        "legacy_size": {"type": "Int", "default": 2},
        "size": {"type": "Int", "default": [2, 2, 2]},
    }
    observation = _observation()
    observation["parameters"]["surprise"] = {"type": "String", "default": "new"}

    result = compare_compatibility(expectation, observation)

    assert result["compatible"] is False
    assert [diff["code"] for diff in result["diffs"]] == [
        "missing_parameter",
        "parameter_type_drift",
        "parameter_default_drift",
        "unexpected_parameter",
        "unexpected_parameter",
    ]
    assert result["diffs"][0]["message"] == (
        "box is missing required parameter legacy_size (expected Int default 2)"
    )
    assert result["diffs"][1]["message"] == (
        "box.size type drift: expected Int, observed Float"
    )
    assert result["diffs"][2]["message"] == (
        "box.size default drift: expected [2, 2, 2], observed [1.0, 1.0, 1.0]"
    )
    assert [diff["path"] for diff in result["diffs"]] == sorted(
        diff["path"] for diff in result["diffs"]
    )


def test_build_outside_tested_range_is_named() -> None:
    observation = _observation()
    observation["live_build"] = "22.0.400"

    result = compare_compatibility(_expectation(), observation)

    assert result["diffs"][0]["code"] == "build_outside_tested_range"
    assert "22.0.368..22.0.368" in result["diffs"][0]["message"]


@pytest.mark.parametrize("field", ["context", "category", "operator_type"])
def test_observed_identity_drift_is_not_hidden(field: str) -> None:
    observation = _observation()
    observation[field] = "wrong"

    result = compare_compatibility(_expectation(), observation)

    assert any(diff["code"] == f"{field}_drift" for diff in result["diffs"])


def test_invalid_expectation_rejects_overlap_and_reversed_build_range() -> None:
    overlap = _expectation()
    overlap["optional_parameters"]["size"] = {}
    with pytest.raises(ValueError, match="both required and optional"):
        normalize_expectation(overlap)

    reversed_range = _expectation()
    reversed_range["tested_build_range"] = {"minimum": "22.0.400", "maximum": "22.0.368"}
    with pytest.raises(ValueError, match="minimum must not exceed maximum"):
        normalize_expectation(reversed_range)


def test_probe_output_path_policy_rejects_relative_and_system_roots() -> None:
    with pytest.raises(ValueError, match="must be absolute"):
        validate_compatibility_output_path("relative/probe.json")
    with pytest.raises(ValueError, match="narrow writable"):
        validate_compatibility_output_path("/etc/probe.json")
