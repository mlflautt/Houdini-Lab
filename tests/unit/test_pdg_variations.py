from __future__ import annotations

import pytest
from hermes_houdini.pdg_variations import build_variation_plan, validate_variation_estimate
from hermes_houdini.schemas.command import Policy


def _plan(**overrides):
    arguments = {
        "source_node_path": "/obj/RELIC/ASSET",
        "output_dir": "/tmp/hermes_variations",
        "base_seed": 100,
        "count": 5,
        "seed_step": 11,
        "base_radius_range": [0.8, 1.2],
        "noise_amplitude_range": [0.1, 0.3],
        "iterations": 3,
        "detail_level": "preview",
        "candidate_index": 1,
    }
    arguments.update(overrides)
    return build_variation_plan(**arguments)


def test_variation_plan_is_reproducible_linearly_spaced_and_human_selected():
    first = _plan()
    second = _plan()
    assert first == second
    assert [item["seed"] for item in first["variations"]] == [100, 111, 122, 133, 144]
    assert [item["base_radius"] for item in first["variations"]] == [0.8, 0.9, 1.0, 1.1, 1.2]
    assert [item["noise_amplitude"] for item in first["variations"]] == [
        0.1,
        0.15,
        0.2,
        0.25,
        0.3,
    ]
    assert first["selection"] == {
        "method": "human",
        "winner": None,
        "automatic_ranking": False,
    }
    assert all(item["human_rating"]["score"] is None for item in first["variations"])
    assert all("wedge_" in item["geometry_path"] for item in first["variations"])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"count": 1}, "count"),
        ({"count": 101}, "count"),
        ({"seed_step": 0}, "seed_step"),
        ({"base_radius_range": [1.0, 0.5]}, "end"),
        ({"noise_amplitude_range": [0.1, float("nan")]}, "finite"),
        ({"iterations": 9}, "iterations"),
        ({"detail_level": "ultra"}, "detail_level"),
        ({"candidate_index": 3}, "candidate_index"),
    ],
)
def test_variation_plan_rejects_unbounded_or_invalid_controls(overrides, message):
    with pytest.raises(ValueError, match=message):
        _plan(**overrides)


def test_pdg_estimate_enforces_work_item_total_time_memory_and_output_budgets():
    estimate = {
        "work_items": 4,
        "seconds_per_item": 2.0,
        "points_per_item": 10_000,
        "primitives_per_item": 10_000,
        "memory_bytes_per_item": 8_000_000,
        "output_bytes_total": 32_000_000,
    }
    policy = Policy(
        max_work_items=4,
        max_seconds=8.0,
        max_points=10_000,
        max_primitives=10_000,
        max_memory_bytes=8_000_000,
        max_output_bytes=32_000_000,
    )
    assert validate_variation_estimate(estimate, policy) == estimate

    for key, value in (
        ("work_items", 5),
        ("seconds_per_item", 2.1),
        ("points_per_item", 10_001),
        ("primitives_per_item", 10_001),
        ("memory_bytes_per_item", 8_000_001),
        ("output_bytes_total", 32_000_001),
    ):
        over = {**estimate, key: value}
        with pytest.raises(ValueError, match="exceeds policy"):
            validate_variation_estimate(over, policy)


def test_pdg_estimate_schema_is_strict():
    valid = {
        "work_items": 2,
        "seconds_per_item": 1.0,
        "points_per_item": 1,
        "primitives_per_item": 1,
        "memory_bytes_per_item": 1,
        "output_bytes_total": 1,
    }
    with pytest.raises(ValueError, match="missing keys"):
        validate_variation_estimate({"work_items": 2}, Policy())
    with pytest.raises(ValueError, match="unknown keys"):
        validate_variation_estimate({**valid, "surprise": 1}, Policy())
    with pytest.raises(ValueError, match="non-negative integer"):
        validate_variation_estimate({**valid, "work_items": True}, Policy())
