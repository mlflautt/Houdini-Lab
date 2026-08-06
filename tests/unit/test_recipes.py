"""Recipe parser unit tests (no Houdini; uses a tiny inline YAML fallback if pyyaml missing)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from recipes.parser import Recipe, load_recipe  # noqa: E402

RECIPE_YAML = """
id: sop.scatter_cluster_points
version: 1.0.0
summary: test
contexts: [SOP]
inputs:
  parent_path: {type: string}
  count: {type: integer, default: 100}
nodes:
  - id: src
    type: scatter
    name: SCATTER_PTS
    params: {force_total: "{{count}}"}
connections:
  - [src, 0, src, 0]
outputs: [src]
"""


def _recipe_from_text(tmp_path) -> Recipe:
    p = tmp_path / "r.yaml"
    p.write_text(RECIPE_YAML)
    return load_recipe(p)


def test_load_and_render(tmp_path):
    r = _recipe_from_text(tmp_path)
    assert r.id == "sop.scatter_cluster_points"
    calls = r.render("/obj/ASSET", count=500)
    # 1 create + 1 connect
    assert len(calls) == 2
    create = [c for c in calls if c["tool"] == "node.create"][0]
    assert create["arguments"]["parameters"]["force_total"] == "500"


def test_template_substitution(tmp_path):
    r = _recipe_from_text(tmp_path)
    calls = r.render("/obj/ASSET", count=10)
    create = [c for c in calls if c["tool"] == "node.create"][0]
    assert create["arguments"]["parameters"]["force_total"] == "10"
