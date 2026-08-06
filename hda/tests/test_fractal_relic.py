"""Regression test for hermes::fractal_relic HDA.

Requires Houdini/hython. Skipped by pytest when `hou` is unavailable.
"""
from __future__ import annotations

import pytest

hou = pytest.importorskip("hou")

from .build import build  # noqa: E402


def test_build_creates_definition():
    result = build(namespace="hermes", name="fractal_relic", version="1.0")
    assert result["type_name"] == "hermes::fractal_relic::1.0"
    assert result["noncommercial"] is True
    # instantiation smoke test
    obj = hou.node("/obj")
    instance = obj.createNode(result["type_name"])
    assert instance is not None
    instance.destroy()
