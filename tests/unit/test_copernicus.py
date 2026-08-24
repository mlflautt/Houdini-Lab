"""Pure Copernicus Reaction-Diffusion contract tests."""

from __future__ import annotations

import pytest
from hermes_houdini.copernicus import REACTION_PRESETS, validate_reaction_spec


def test_reaction_spec_is_deterministic_bounded_and_contact_safe():
    spec = validate_reaction_spec(
        resolution=256,
        iterations=8,
        iterations_per_step=6,
        candidate_index=1,
    )
    assert spec["total_steps"] == 48
    assert spec["presets"] == list(REACTION_PRESETS)
    assert spec["contact_scale"] == 1.0
    assert spec["contact_resolution"] == [768, 256]

    large = validate_reaction_spec(
        resolution=512,
        iterations=4,
        iterations_per_step=8,
        candidate_index=0,
    )
    assert large["contact_scale"] == 0.5
    assert large["contact_resolution"] == [768, 256]


def test_reaction_spec_rejects_unbounded_or_reordered_candidates():
    with pytest.raises(ValueError, match="must be <= 48"):
        validate_reaction_spec(
            resolution=256,
            iterations=8,
            iterations_per_step=7,
            candidate_index=0,
        )
    with pytest.raises(ValueError, match="resolution must be one of"):
        validate_reaction_spec(
            resolution=192,
            iterations=4,
            iterations_per_step=4,
            candidate_index=0,
        )
    with pytest.raises(ValueError, match="preserve exact order"):
        validate_reaction_spec(
            resolution=128,
            iterations=4,
            iterations_per_step=4,
            candidate_index=0,
            presets=["spots", "bigwaves", "smallwaves"],
        )
