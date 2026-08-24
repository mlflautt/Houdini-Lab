"""Registered HScript expression-subset safety tests."""

from __future__ import annotations

import pytest
from hermes_houdini.expressions import validate_hscript_expression
from hermes_houdini.graph_batch import validate_batch


def test_registered_hscript_subset_allows_only_point_and_frame_contracts():
    assert validate_hscript_expression('point(0, $PT, "life", 1)')
    assert validate_hscript_expression("$FF - 0.5")
    with pytest.raises(ValueError, match="unsupported functions"):
        validate_hscript_expression('system("touch")')
    with pytest.raises(ValueError, match="unsupported variables"):
        validate_hscript_expression("$HOME")
    with pytest.raises(ValueError, match="unsafe HScript syntax"):
        validate_hscript_expression("`run(1)`")


def test_batch_rejects_literal_expression_overlap_and_unsafe_expression():
    operation = {
        "op": "create",
        "ref": "shift",
        "parent_path": "/obj/TEST",
        "operator_type": "timeshift",
        "parameters": {"integerframe": 0},
        "expressions": {"frame": "$FF - 0.5"},
    }
    assert validate_batch("safe-expression", [operation])[0]["expressions"]["frame"]
    with pytest.raises(ValueError, match="literal and expression"):
        validate_batch(
            "overlap-expression",
            [{**operation, "parameters": {"frame": 1}, "expressions": {"frame": "$FF"}}],
        )
    with pytest.raises(ValueError, match="unsupported functions"):
        validate_batch(
            "unsafe-expression",
            [{**operation, "expressions": {"frame": 'system("touch")'}}],
        )
