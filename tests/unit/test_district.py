from __future__ import annotations

import pytest
from hermes_houdini.district import build_district_plan


def _plan(**overrides):
    arguments = {
        "source_node_path": "/obj/DISTRICT_SOURCE/OUT_BUILDING",
        "output_dir": "/tmp/hermes_district",
        "base_seed": 1601,
        "count": 12,
        "seed_step": 53,
        "columns": 4,
        "lot_spacing": 6.0,
    }
    arguments.update(overrides)
    return build_district_plan(**arguments)


def test_district_plan_is_reproducible_gridded_and_never_ranks_candidates():
    first = _plan()
    assert first == _plan()
    assert [item["seed"] for item in first["candidates"]] == [
        1601,
        1654,
        1707,
        1760,
        1813,
        1866,
        1919,
        1972,
        2025,
        2078,
        2131,
        2184,
    ]
    assert [item["style"] for item in first["candidates"]] == [
        "block",
        "block",
        "block",
        "terrace",
        "terrace",
        "terrace",
        "terrace",
        "terrace",
        "terrace",
        "needle",
        "needle",
        "needle",
    ]
    assert first["candidates"][0]["placement"] == {
        "x": -9.0,
        "y": 0.0,
        "z": 6.0,
        "rotation_y": 90.0,
    }
    assert first["candidates"][-1]["placement"]["x"] == 9.0
    assert first["candidates"][-1]["placement"]["z"] == -6.0
    assert first["selection"] == {
        "method": "human",
        "winner": None,
        "automatic_ranking": False,
    }
    assert all(item["human_rating"]["score"] is None for item in first["candidates"])
    assert all(item["geometry_path"].endswith(".bgeo.sc") for item in first["candidates"])


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"count": 3}, "count"),
        ({"count": 17}, "count"),
        ({"base_seed": -1}, "base_seed"),
        ({"seed_step": 0}, "seed_step"),
        ({"columns": 1}, "columns"),
        ({"lot_spacing": 5.0}, "lot_spacing"),
        ({"lot_spacing": 21.0}, "lot_spacing"),
        ({"output_dir": "relative"}, "absolute"),
    ],
)
def test_district_plan_rejects_invalid_or_unbounded_controls(overrides, message):
    with pytest.raises(ValueError, match=message):
        _plan(**overrides)
