"""Bare-Hython skill manifest loading without PyYAML."""

from __future__ import annotations

import json

import hermes_houdini.skill_loader as skill_loader


def test_json_compatible_manifest_loads_when_pyyaml_is_absent(tmp_path, monkeypatch):
    root = tmp_path / "model.example"
    root.mkdir()
    (root / "skill.py").write_text("def plan(**kwargs): return []\n", encoding="utf-8")
    manifest = {
        "id": "model.example",
        "version": "1.0.0",
        "summary": "bare Hython fixture",
        "contexts": ["SOP"],
        "houdini": {"tested_builds": ["22.0.368"]},
        "license": {"mode": "houdini-apprentice-noncommercial"},
        "inputs": {},
        "risk": "low",
        "checkpoint": "none",
        "cook_budget": {},
        "steps": [],
        "verification": {},
        "outputs": [],
        "rollback": "none",
    }
    (root / "skill.yaml").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(skill_loader, "yaml", None)
    definition = skill_loader.load_skill(root)
    assert definition.id == "model.example"
    assert definition.plan() == []
