from __future__ import annotations

import pytest
from hermes_houdini.botanical import (
    BOTANICAL_GRAMMARS,
    BOTANICAL_ORDER,
    validate_botanical_spec,
)


def test_botanical_spec_is_registered_seeded_and_bounded():
    spec = validate_botanical_spec(
        generations=6,
        seed=4103,
        candidate_index=1,
        wire_radius=0.018,
    )
    assert tuple(spec["candidate_order"]) == BOTANICAL_ORDER
    assert spec["candidate_seeds"] == {"canopy": 4103, "fern": 4204, "coral": 4314}
    assert spec["estimated_skeleton_segments"] == {
        "canopy": 365,
        "fern": 1330,
        "coral": 3906,
    }
    assert spec["estimated_wire_points"] == 67_212
    assert spec["estimated_wire_primitives"] == 134_424
    assert set(BOTANICAL_GRAMMARS) == set(BOTANICAL_ORDER)
    assert all(grammar["rules"] for grammar in BOTANICAL_GRAMMARS.values())


def test_botanical_spec_rejects_unsafe_generation_seed_and_radius():
    with pytest.raises(ValueError, match="generations must be between 1 and 6"):
        validate_botanical_spec(generations=7, seed=1, candidate_index=0, wire_radius=0.018)
    with pytest.raises(ValueError, match="seed must be between"):
        validate_botanical_spec(
            generations=4,
            seed=2_147_483_437,
            candidate_index=0,
            wire_radius=0.018,
        )
    with pytest.raises(ValueError, match="wire_radius"):
        validate_botanical_spec(generations=4, seed=1, candidate_index=0, wire_radius=0.5)
