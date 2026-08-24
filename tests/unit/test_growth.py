"""Pure native differential-growth contract tests."""

from __future__ import annotations

import pytest
from hermes_houdini.growth import validate_growth_solver_spec


def test_growth_solver_spec_is_exact_and_bounded():
    spec = validate_growth_solver_spec(
        solver_path="/obj/GROWTH/MAIN_SOLVER",
        run_id="unit_growth",
        point_radius=0.075,
        relax_iterations=5,
        blur_iterations=1,
        blur_step_size=0.25,
        segment_length=0.075,
    )
    assert spec["solver_path"] == "/obj/GROWTH/MAIN_SOLVER"
    assert spec["point_radius"] == pytest.approx(0.075)
    assert spec["relax_iterations"] == 5
    with pytest.raises(ValueError, match="point_radius must be <= 0.25"):
        validate_growth_solver_spec(**{**spec, "point_radius": 0.5})
    with pytest.raises(ValueError, match="between 1 and 12"):
        validate_growth_solver_spec(**{**spec, "relax_iterations": 13})
    with pytest.raises(ValueError, match="absolute Houdini node path"):
        validate_growth_solver_spec(**{**spec, "solver_path": "relative/solver"})
