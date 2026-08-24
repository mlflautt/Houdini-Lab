"""Pure Solaris lookdev and preview contract tests."""

from __future__ import annotations

import pytest
from hermes_houdini.solaris import (
    KARMA_CPU_DELEGATE,
    validate_material_specs,
    validate_preview_spec,
)


def _materials():
    return [
        {
            "id": f"candidate_{index}",
            "builder_name": f"CANDIDATE_{index}_MTLX",
            "material_path": f"/materials/candidate_{index}",
            "base_color": [0.1 * index, 0.2, 0.3],
            "metalness": 0.2,
            "roughness": 0.4,
        }
        for index in range(3)
    ]


def test_material_specs_are_exact_finite_and_unique():
    normalized = validate_material_specs(_materials())
    assert len(normalized) == 3
    assert [item["id"] for item in normalized] == ["candidate_0", "candidate_1", "candidate_2"]
    duplicate = _materials()
    duplicate[2]["material_path"] = duplicate[0]["material_path"]
    with pytest.raises(ValueError, match="unique"):
        validate_material_specs(duplicate)
    with pytest.raises(ValueError, match="exactly three"):
        validate_material_specs(_materials()[:2])


def test_preview_spec_is_one_frame_apprentice_safe_and_cpu_pinned(tmp_path):
    spec = validate_preview_spec(
        output_path=str(tmp_path / "preview.png"),
        width=640,
        height=360,
        frame=1,
        time_limit=30,
        max_threads=4,
    )
    assert spec["delegate"] == KARMA_CPU_DELEGATE
    assert spec["width"] == 640 and spec["height"] == 360
    with pytest.raises(ValueError, match="exceeds Apprentice ceiling"):
        validate_preview_spec(
            output_path=str(tmp_path / "too_large.png"),
            width=1281,
            height=720,
            frame=1,
            time_limit=30,
            max_threads=4,
        )
    with pytest.raises(ValueError, match="absolute .exr or .png"):
        validate_preview_spec(
            output_path="relative.jpg",
            width=640,
            height=360,
            frame=1,
            time_limit=30,
            max_threads=4,
        )
