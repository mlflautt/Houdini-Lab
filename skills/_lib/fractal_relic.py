"""Shared pure graph specification for the fractal-relic skill and HDA builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from recipes.parser import load_recipe

_DENSITY = {"draft": 40, "preview": 80, "final": 160}
_RECIPES = Path(__file__).resolve().parents[2] / "recipes"
_CANDIDATE_RECIPE = load_recipe(_RECIPES / "sop" / "fractal_relic_candidate.yaml")
_CANDIDATES = (
    {
        "id": "candidate_A",
        "label": "weathered_seed",
        "seed_offset": 0,
        "density_factor": 0.80,
        "noise_factor": 0.80,
        "detail_factor": 1.15,
        "compare_x": -3.0,
    },
    {
        "id": "candidate_B",
        "label": "balanced_relic",
        "seed_offset": 7_919,
        "density_factor": 1.00,
        "noise_factor": 1.00,
        "detail_factor": 1.00,
        "compare_x": 0.0,
    },
    {
        "id": "candidate_C",
        "label": "dense_crown",
        "seed_offset": 15_838,
        "density_factor": 1.25,
        "noise_factor": 1.25,
        "detail_factor": 0.75,
        "compare_x": 3.0,
    },
)


def _path(parent: str, name: str) -> str:
    return f"{parent.rstrip('/')}/{name}"


def _create(
    *,
    ref: str,
    parent: str,
    operator_type: str,
    name: str,
    role: str,
    position: tuple[float, float],
    parameters: dict[str, Any] | None = None,
    comment: str = "",
) -> dict[str, Any]:
    return {
        "op": "create",
        "ref": ref,
        "parent_path": parent,
        "operator_type": operator_type,
        "name": name,
        "exact_name": True,
        "category": "Sop",
        "role": role,
        "position": list(position),
        "parameters": parameters or {},
        "comment": comment,
    }


def _candidate_fragment(
    *,
    parent: str,
    candidate: dict[str, Any],
    index: int,
    seed: int,
    iterations: int,
    density: int,
    base_radius: float,
    detail_radius: float,
    noise_amplitude: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    letter = chr(ord("A") + index)
    prefix = f"cand_{letter.lower()}"
    column = (index - 1) * 7.0
    candidate_seed = seed + int(candidate["seed_offset"])
    point_count = max(1, round(density * float(candidate["density_factor"])))
    candidate_noise = noise_amplitude * float(candidate["noise_factor"])
    candidate_detail = detail_radius * float(candidate["detail_factor"])
    compare_x = base_radius * float(candidate["compare_x"])
    lineage = f"{candidate['id']} seed={candidate_seed}; human rating pending"
    fragment = _CANDIDATE_RECIPE.render_fragment(
        parent,
        ref_prefix=f"{prefix}_",
        position_offset=(column, 0.0),
        candidate_code=letter,
        lineage=lineage,
        base_radius=base_radius,
        sphere_frequency=min(10, 3 + iterations),
        noise_amplitude=candidate_noise,
        element_size=max(0.15, base_radius * 0.65),
        noise_offset=candidate_seed * 0.001,
        point_count=point_count,
        seed=candidate_seed,
        relax_iterations=min(10, iterations + 2),
        detail_radius=candidate_detail,
        compare_x=compare_x,
    )
    provenance = {
        "candidate_id": candidate["id"],
        "label": candidate["label"],
        "switch_input": index,
        "seed": candidate_seed,
        "mutations": {
            "point_count": point_count,
            "noise_amplitude": candidate_noise,
            "detail_radius": candidate_detail,
        },
        "output_node_path": _path(parent, f"OUT_CAND_{letter}"),
        "presentation_offset_x": compare_x,
        "human_rating": {"score": None, "notes": "", "selected": False},
        "automatic_rank": None,
        "recipe": fragment["recipe"],
        "refs": fragment["refs"],
    }
    return fragment["operations"], provenance


def build_graph_spec(
    *,
    parent_path: str,
    seed: int = 42,
    iterations: int = 4,
    detail_level: str = "preview",
    base_radius: float = 1.0,
    detail_radius: float = 0.08,
    noise_amplitude: float = 0.16,
    preview_candidate: int = 0,
) -> dict[str, Any]:
    """Return the exact recipe-backed graph shared by the raw skill and HDA source."""
    if detail_level not in _DENSITY:
        raise ValueError(f"unsupported detail_level: {detail_level}")
    if preview_candidate not in {0, 1, 2}:
        raise ValueError("preview_candidate must be 0, 1, or 2")
    operations: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    density = _DENSITY[detail_level] * iterations
    for index, candidate in enumerate(_CANDIDATES):
        candidate_operations, provenance = _candidate_fragment(
            parent=parent_path,
            candidate=candidate,
            index=index,
            seed=seed,
            iterations=iterations,
            density=density,
            base_radius=base_radius,
            detail_radius=detail_radius,
            noise_amplitude=noise_amplitude,
        )
        operations.extend(candidate_operations)
        candidates.append(provenance)

    operations.extend(
        [
            _create(
                ref="comparison_merge",
                parent=parent_path,
                operator_type="merge",
                name="MERGE_COMPARISON",
                role="comparison_assembly",
                position=(-2.0, -6.0),
                comment="All candidates shown side by side for human evaluation",
            ),
            *[
                {
                    "op": "connect",
                    "from": candidate["refs"]["compare"],
                    "to": "comparison_merge",
                    "input_index": index,
                }
                for index, candidate in enumerate(candidates)
            ],
            _create(
                ref="out_comparison",
                parent=parent_path,
                operator_type="null",
                name="OUT_COMPARISON",
                role="comparison_output",
                position=(-2.0, -8.0),
                comment="Display/validation output containing all unrated candidates",
            ),
            {"op": "connect", "from": "comparison_merge", "to": "out_comparison"},
            _create(
                ref="candidate_switch",
                parent=parent_path,
                operator_type="switch",
                name="SELECT_CANDIDATE",
                role="human_selection",
                position=(4.0, -6.0),
                parameters={"input": preview_candidate},
                comment="Human-controlled preview input; this is not an automatic winner",
            ),
            *[
                {
                    "op": "connect",
                    "from": candidate["refs"]["out"],
                    "to": "candidate_switch",
                    "input_index": index,
                }
                for index, candidate in enumerate(candidates)
            ],
            _create(
                ref="out_geo",
                parent=parent_path,
                operator_type="null",
                name="OUT_GEO",
                role="selected_output",
                position=(4.0, -8.0),
                comment="Editable selected-candidate contract; human choice only",
            ),
            {"op": "connect", "from": "candidate_switch", "to": "out_geo"},
            {"op": "set_flags", "target": "out_comparison", "display": True},
            {"op": "set_flags", "target": "out_geo", "render": True},
        ]
    )
    public_parameters: dict[str, list[str]] = {_path(parent_path, "SELECT_CANDIDATE"): ["input"]}
    for index in range(len(candidates)):
        letter = chr(ord("A") + index)
        public_parameters.update(
            {
                _path(parent_path, f"CAND_{letter}_BASE"): ["radx", "rady", "radz", "freq"],
                _path(parent_path, f"CAND_{letter}_DEFORM"): [
                    "amplitude",
                    "elementsize",
                    "offset",
                ],
                _path(parent_path, f"CAND_{letter}_SCATTER"): [
                    "npts",
                    "seed",
                    "relaxiterations",
                ],
                _path(parent_path, f"CAND_{letter}_DETAIL"): ["radx", "rady", "radz"],
            }
        )
    return {
        "operations": operations,
        "candidates": candidates,
        "comparison_path": _path(parent_path, "OUT_COMPARISON"),
        "selected_path": _path(parent_path, "OUT_GEO"),
        "public_parameters": public_parameters,
        "recipe": {"id": _CANDIDATE_RECIPE.id, "version": _CANDIDATE_RECIPE.version},
    }


__all__ = ["build_graph_spec"]
