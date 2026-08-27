from __future__ import annotations

import copy
from pathlib import Path

import pytest
from hermes_houdini.g003_execution import (
    contact_labels,
    review_index_html,
    validate_approved_manifest,
)
from hermes_houdini.g003_visual_audition import (
    build_visual_audition_manifest,
    visual_audition_manifest_sha256,
)

ACCEPTED = "df476c1af5db0cda4b80d8cc7ff5bd384cb51389"


def _manifest(tmp_path: Path) -> dict[str, object]:
    manifest = build_visual_audition_manifest(
        project_root=tmp_path,
        artifact_root=tmp_path / ".hermes" / "g003" / "gate-v" / "test-execution",
        source_identity={"commit": ACCEPTED, "branch": "test", "dirty": False},
        runtime_observation={
            "status": "pass",
            "detail": "read-only runtime probe passed",
            "mutation_performed": False,
        },
    )
    manifest["approval"]["manifest_sha256_subject"] = visual_audition_manifest_sha256(manifest)
    return manifest


def _rehash(manifest: dict[str, object]) -> str:
    digest = visual_audition_manifest_sha256(manifest)
    manifest["approval"]["manifest_sha256_subject"] = digest
    return digest


def test_approved_manifest_validation_is_pure_and_preserves_human_authority(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    digest = manifest["approval"]["manifest_sha256_subject"]
    result = validate_approved_manifest(manifest, approved_sha256=digest)
    assert result["call_count"] == 115
    assert result["render_count"] == 36
    assert not Path(result["artifact_root"]).exists()
    assert manifest["review"]["winner"] is None
    assert manifest["review"]["human_rating"] is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["methods"][0]["calls"][0]["policy"].update(allow_network=True), "network"),
        (lambda value: value["methods"][0]["calls"][0]["policy"].update(allow_arbitrary_code=True), "arbitrary"),
        (lambda value: value["review"].update(winner="calligraphy"), "winner"),
        (
            lambda value: value["methods"][0]["calls"][1]["arguments"].update(
                log_path="/private/tmp/outside.jsonl"
            ),
            "must be inside",
        ),
    ],
)
def test_approved_manifest_refuses_policy_human_and_path_drift(
    tmp_path: Path, mutation, message: str
) -> None:
    manifest = copy.deepcopy(_manifest(tmp_path))
    mutation(manifest)
    digest = _rehash(manifest)
    with pytest.raises((ValueError, FileExistsError), match=message):
        validate_approved_manifest(manifest, approved_sha256=digest)


def test_approved_manifest_refuses_hash_reuse_and_existing_root(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    digest = manifest["approval"]["manifest_sha256_subject"]
    with pytest.raises(ValueError, match="approval subject mismatch"):
        validate_approved_manifest(manifest, approved_sha256="0" * 64)
    Path(manifest["artifact_root"]).mkdir(parents=True)
    with pytest.raises(FileExistsError, match="existing artifact root"):
        validate_approved_manifest(manifest, approved_sha256=digest)


def test_review_helpers_emit_portable_stable_order_without_a_winner(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    labels = contact_labels(manifest)
    assert labels["presentation_order"] == [
        "Particle Calligraphy",
        "Differential Growth",
        "Kinetic Instances",
    ]
    assert labels["winner"] is None
    page = review_index_html(manifest)
    assert page.index("Particle Calligraphy") < page.index("Differential Growth")
    assert page.index("Differential Growth") < page.index("Kinetic Instances")
    assert "https://" not in page
    assert "Human rating: <em>unselected</em>" in page
