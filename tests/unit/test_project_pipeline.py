from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from hermes_houdini.project_pipeline import (
    adapt_project_for_compiler,
    build_project_plan,
    load_and_plan_project,
    load_project_adapter_registry,
    observe_project,
    select_project_catalog,
)
from hermes_houdini.project_spec import normalize_project_spec
from yaml import safe_load

ROOT = Path(__file__).resolve().parents[2]
PROJECT_PATH = ROOT / "projects" / "living_biome" / "project.yaml"
EXPECTED_CAPABILITIES = {
    "grow.botanical_grammar@1.0.0",
    "lookdev.procedural_material_foundry@1.0.0",
    "motion.particle_calligraphy@1.0.0",
    "world.world_seed_atlas_labs@1.0.0",
}


def _bundle() -> dict:
    return load_and_plan_project(PROJECT_PATH, project_root=ROOT)


def _codes(plan: dict) -> set[str]:
    return {item["code"] for item in plan["blockers"]}


def test_living_biome_compiles_as_dry_equal_status_plan() -> None:
    bundle = _bundle()
    project = bundle["project"]
    plan = bundle["plan"]

    assert plan["status"] == "planned"
    assert plan["blockers"] == []
    assert len(plan["stages"]) == 15
    assert [item["variant_id"] for item in plan["variants"]] == [
        "amber-mesa",
        "verdant-rift",
        "lunar-basin",
    ]
    assert plan["automatic_execution"] is False
    assert plan["automatic_ranking"] is False
    assert plan["winner"] is None
    assert all(item["human_rating"] is None for item in project["variants"])
    assert all(item["selected_for_continuation"] is None for item in project["variants"])
    assert all(item["winner"] is None for item in project["human_decisions"])


def test_registry_catalog_and_compiler_adapter_are_portable_and_exact() -> None:
    project = _bundle()["project"]
    registry = load_project_adapter_registry()
    catalog = select_project_catalog(project)
    compiler_project, adapters = adapt_project_for_compiler(
        project, adapter_records=registry["records"]
    )

    assert registry["record_count"] == 4
    assert all(item["source"].startswith("project_contracts/adapters/") for item in registry["records"])
    assert catalog["record_count"] == 4
    assert set(catalog["filters"]["exact_project_identities"]) == EXPECTED_CAPABILITIES
    assert all(item["license_mode"] == "houdini-apprentice-noncommercial" for item in adapters)
    assert all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for item in adapters
        for value in item["budget_effect"].values()
    )
    assert all(isinstance(item["output_contracts"], dict) for item in compiler_project["capability_instances"])


def test_observer_preserves_pending_human_and_mechanical_evidence() -> None:
    bundle = _bundle()
    index = observe_project(
        bundle["project"], bundle["plan"], project_root=ROOT
    )

    assert index["blockers"] == []
    assert index["automatic_execution"] is False
    assert index["winner"] is None
    assert index["mechanical_status"] == "pending"
    assert index["human_status"] == "pending"
    assert len(index["stages"]) == 15


def test_pipeline_hashes_are_stable_across_fresh_processes() -> None:
    code = (
        "from pathlib import Path; "
        "from hermes_houdini.project_pipeline import load_and_plan_project; "
        f"b=load_and_plan_project(Path({str(PROJECT_PATH)!r}), project_root=Path({str(ROOT)!r})); "
        "print(b['project_sha256'], b['plan']['plan_sha256'])"
    )
    results = [
        subprocess.check_output([sys.executable, "-c", code], cwd=ROOT, text=True).strip()
        for _ in range(2)
    ]
    assert results[0] == results[1]


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda project, catalog, registry: project["capability_instances"][0].update(
                capability_version="99.0.0"
            ),
            "missing_capability",
        ),
        (
            lambda project, catalog, registry: catalog["records"].append(
                copy.deepcopy(catalog["records"][0])
            ),
            "ambiguous_capability",
        ),
        (
            lambda project, catalog, registry: registry["records"].append(
                copy.deepcopy(registry["records"][0])
            ),
            "ambiguous_adapter",
        ),
        (
            lambda project, catalog, registry: project["capability_instances"][0].update(
                dependencies=["stage"]
            ),
            "dependency_cycle",
        ),
        (
            lambda project, catalog, registry: project["budgets"]["aggregate"].update(points=1),
            "aggregate_budget_overflow",
        ),
        (
            lambda project, catalog, registry: project["compatibility"].update(
                houdini_build="22.0.999"
            ),
            "houdini_build_mismatch",
        ),
        (
            lambda project, catalog, registry: catalog["records"][0].update(
                optional_dependencies=["unavailable-plugin"]
            ),
            "unavailable_dependency",
        ),
    ],
)
def test_integration_failures_are_explicit_blockers(mutate, code: str) -> None:
    project = copy.deepcopy(_bundle()["project"])
    catalog = select_project_catalog(project)
    registry = load_project_adapter_registry()
    mutate(project, catalog, registry)

    plan = build_project_plan(project, catalog=catalog, adapter_registry=registry)

    assert code in _codes(plan)


def test_human_fields_cannot_be_prefilled() -> None:
    source = PROJECT_PATH.read_text(encoding="utf-8").replace(
        "human_rating: null", "human_rating: 5", 1
    )
    with pytest.raises(ValueError, match="must remain null"):
        normalize_project_spec(safe_load(source), project_root=ROOT)


def test_observer_detects_live_artifact_hash_mismatch(tmp_path: Path) -> None:
    bundle = _bundle()
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"live bytes")
    index = observe_project(
        bundle["project"],
        bundle["plan"],
        project_root=tmp_path,
        artifacts=[
            {
                "path": str(artifact),
                "sha256": hashlib.sha256(b"different bytes").hexdigest(),
                "durable": True,
                "verify": True,
            }
        ],
    )

    assert "artifact_hash_mismatch" in {item["code"] for item in index["blockers"]}


def test_cli_is_helpful_by_default_and_writes_only_explicit_new_output(tmp_path: Path) -> None:
    script = ROOT / "scripts" / "plan_project.py"
    help_result = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert help_result.returncode == 0
    assert "validate" in help_result.stdout

    copied = tmp_path / "project.yaml"
    copied.write_bytes(PROJECT_PATH.read_bytes())
    output = tmp_path / "plan.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "plan",
            "--project",
            str(copied),
            "--project-root",
            str(tmp_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "planned"
    second = subprocess.run(
        [
            sys.executable,
            str(script),
            "plan",
            "--project",
            str(copied),
            "--project-root",
            str(tmp_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert second.returncode == 2
    assert "output must be a new path" in second.stderr
