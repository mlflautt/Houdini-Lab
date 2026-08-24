"""Deterministic native-Houdini World Seed Atlas planning and validation.

Pure specification logic imports without Houdini. HOM validation only inspects and cooks the
registered native SOP/LOP contracts; HeightField, Scatter, Copy to Points, and Karma do the work.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from . import get_hou
from .cook import geometry_metrics
from .execution import current_envelope

WORLD_SEED_IDS = ("amber_mesa", "verdant_rift", "lunar_basin")
TERRAIN_SAMPLES = (64, 96, 128)
_SEED_OFFSETS = (0, 137, 271)
_PROFILES = (
    {
        "id": "amber_mesa",
        "translation_x": -9.5,
        "noise_amplitude": 2.4,
        "noise_element_size": 2.6,
        "terrace_step_size": 0.55,
        "scatter_count": 54,
        "scatter_radius": 0.14,
        "hero_radius": 1.05,
        "platonic_type": 3,
        "terrain_color": (0.33, 0.075, 0.025),
        "accent_color": (1.0, 0.31, 0.025),
    },
    {
        "id": "verdant_rift",
        "translation_x": 0.0,
        "noise_amplitude": 1.8,
        "noise_element_size": 3.4,
        "terrace_step_size": 0.9,
        "scatter_count": 72,
        "scatter_radius": 0.11,
        "hero_radius": 1.2,
        "platonic_type": 4,
        "terrain_color": (0.025, 0.22, 0.11),
        "accent_color": (0.16, 0.95, 0.47),
    },
    {
        "id": "lunar_basin",
        "translation_x": 9.5,
        "noise_amplitude": 1.1,
        "noise_element_size": 1.6,
        "terrace_step_size": 0.35,
        "scatter_count": 42,
        "scatter_radius": 0.17,
        "hero_radius": 0.92,
        "platonic_type": 0,
        "terrain_color": (0.075, 0.09, 0.18),
        "accent_color": (0.36, 0.64, 1.0),
    },
)


def validate_world_seed_spec(
    *, base_seed: int, terrain_samples: int, world_size: float
) -> dict[str, Any]:
    """Return a bounded, fixed-order three-world specification."""
    if (
        not isinstance(base_seed, int)
        or isinstance(base_seed, bool)
        or not 0 <= base_seed <= 2_147_483_376
    ):
        raise ValueError("base_seed must be an integer between 0 and 2147483376")
    if terrain_samples not in TERRAIN_SAMPLES:
        raise ValueError(f"terrain_samples must be one of {list(TERRAIN_SAMPLES)}")
    if (
        not isinstance(world_size, (int, float))
        or isinstance(world_size, bool)
        or not math.isfinite(world_size)
        or not 8.0 <= float(world_size) <= 10.0
    ):
        raise ValueError("world_size must be a finite number between 8 and 10")

    estimated_terrain_points = 3 * terrain_samples * terrain_samples
    if estimated_terrain_points > 150_000:
        raise ValueError("terrain estimate exceeds the 150000-point display budget")
    candidates = []
    for index, profile in enumerate(_PROFILES):
        seed = base_seed + _SEED_OFFSETS[index]
        candidates.append(
            {
                **profile,
                "index": index,
                "seed": seed,
                "noise_offset": [
                    round((seed % 997) / 41.0, 8),
                    round(((seed * 17 + 31) % 991) / 43.0, 8),
                    0.0,
                ],
                "human_rating": {"score": None, "notes": "", "selected": False},
                "automatic_rank": None,
            }
        )
    return {
        "base_seed": base_seed,
        "terrain_samples": terrain_samples,
        "world_size": float(world_size),
        "estimated_terrain_points": estimated_terrain_points,
        "candidate_order": list(WORLD_SEED_IDS),
        "candidates": candidates,
        "selection": {
            "method": "human",
            "winner": None,
            "automatic_ranking": False,
        },
    }


def _node_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or value == "/":
        raise ValueError(f"{label} must be an absolute Houdini node path")
    return value


def _new_json(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute() or path.suffix.lower() != ".json":
        raise ValueError("output_path must be an absolute .json path")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _messages(node: Any) -> tuple[list[str], list[str]]:
    return ([str(item) for item in node.errors()], [str(item) for item in node.warnings()])


def _close(actual: Any, expected: float) -> bool:
    return math.isclose(float(actual), float(expected), abs_tol=1e-6)


def cook_validate_world_seed_atlas(
    *,
    candidate_contracts: list[dict[str, Any]],
    base_seed: int,
    terrain_samples: int,
    world_size: float,
    output_path: str,
) -> dict[str, Any]:
    """Cook and verify three exact native HeightField world contracts."""
    hou = get_hou()
    spec = validate_world_seed_spec(
        base_seed=base_seed, terrain_samples=terrain_samples, world_size=world_size
    )
    if not isinstance(candidate_contracts, list) or len(candidate_contracts) != 3:
        raise ValueError("candidate_contracts must contain exactly three worlds")
    output = _new_json(output_path)
    envelope = current_envelope()
    policy = envelope.policy if envelope and envelope.policy else None
    max_points = int(policy.max_points) if policy else 150_000
    max_primitives = int(policy.max_primitives) if policy else 150_000
    max_seconds = float(policy.max_seconds) if policy else 120.0
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    total_points = 0
    total_primitives = 0

    required_keys = {
        "id",
        "network_path",
        "base_path",
        "noise_path",
        "terrace_path",
        "terrain_path",
        "points_path",
        "forms_path",
        "hero_path",
        "world_path",
    }
    for index, (contract, candidate) in enumerate(
        zip(candidate_contracts, spec["candidates"], strict=True)
    ):
        if not isinstance(contract, dict) or set(contract) != required_keys:
            raise ValueError("each candidate contract must declare the exact registered paths")
        if contract["id"] != candidate["id"]:
            raise ValueError("candidate_contracts must preserve the registered world order")
        network = hou.node(_node_path(contract["network_path"], "network_path"))
        if network is None or network.type().category().name() != "Object":
            raise ValueError(f"world network not found: {contract['network_path']}")
        nodes = {
            key.removesuffix("_path"): hou.node(_node_path(value, key))
            for key, value in contract.items()
            if key.endswith("_path") and key != "network_path"
        }
        if any(node is None or node.parent() != network for node in nodes.values()):
            raise ValueError(f"world {candidate['id']} has a missing or foreign contract node")

        exact_types = {
            "base": "heightfield",
            "noise": "heightfield_noise",
            "terrace": "heightfield_terrace",
            "terrain": "null",
            "points": "null",
            "forms": "null",
            "hero": "null",
            "world": "null",
        }
        exact_roles = {
            "base": "world_seed_heightfield_base",
            "noise": "world_seed_heightfield_noise",
            "terrace": "world_seed_heightfield_terrace",
            "terrain": "world_seed_terrain_contract",
            "points": "world_seed_biome_points_contract",
            "forms": "world_seed_biome_forms_contract",
            "hero": "world_seed_hero_contract",
            "world": "world_seed_world_contract",
        }
        for key, node in nodes.items():
            if node.type().name().split("::")[0] != exact_types[key]:
                raise ValueError(f"world {candidate['id']} has wrong {key} node type")
            if node.userData("hermes_role") != exact_roles[key]:
                raise ValueError(f"world {candidate['id']} has stale {key} role")

        if nodes["noise"].input(0) != nodes["base"] or nodes["terrace"].input(0) != nodes["noise"]:
            raise ValueError(f"world {candidate['id']} HeightField chain is disconnected")
        if nodes["base"].parmTuple("gridsamples").eval() != (terrain_samples,):
            raise ValueError(f"world {candidate['id']} has unregistered terrain samples")
        if not _close(nodes["noise"].parm("amp").eval(), candidate["noise_amplitude"]):
            raise ValueError(f"world {candidate['id']} has unregistered noise amplitude")
        if not _close(nodes["noise"].parm("elementsize").eval(), candidate["noise_element_size"]):
            raise ValueError(f"world {candidate['id']} has unregistered noise scale")
        if tuple(
            round(float(value), 8) for value in nodes["noise"].parmTuple("offset").eval()
        ) != tuple(candidate["noise_offset"]):
            raise ValueError(f"world {candidate['id']} has unregistered noise offset")
        if not _close(
            nodes["terrace"].parm("terrace_max_step_size").eval(),
            candidate["terrace_step_size"],
        ):
            raise ValueError(f"world {candidate['id']} has unregistered terrace scale")

        nodes["world"].cook(force=True)
        errors, warnings = _messages(nodes["world"])
        if errors or warnings:
            raise ValueError(f"world {candidate['id']} has Houdini messages")
        metrics = geometry_metrics(nodes["world"])
        if metrics["points"] <= candidate["scatter_count"] or metrics["primitives"] < 100:
            raise ValueError(f"world {candidate['id']} produced incomplete geometry")
        if "Cd" not in metrics["point_attributes"]:
            raise ValueError(f"world {candidate['id']} is missing display-color provenance")
        total_points += int(metrics["points"])
        total_primitives += int(metrics["primitives"])
        if total_points > max_points or total_primitives > max_primitives:
            raise ValueError("World Seed Atlas exceeds geometry policy budget")
        results.append(
            {
                "id": candidate["id"],
                "index": index,
                "seed": candidate["seed"],
                "network_path": network.path(),
                "contracts": {key: node.path() for key, node in nodes.items()},
                "metrics": metrics,
                "human_rating": candidate["human_rating"],
                "automatic_rank": None,
            }
        )
        if time.monotonic() - started > max_seconds:
            raise TimeoutError("World Seed Atlas validation exceeded policy.max_seconds")

    document = {
        "schema": "hermes.houdini.world_seed_atlas_validation",
        "schema_version": "1.0",
        "status": "success",
        "houdini": {
            "build": hou.applicationVersionString(),
            "license": hou.licenseCategory().name(),
        },
        "request": envelope.as_dict() if envelope else None,
        "spec": spec,
        "candidates": results,
        "total_points": total_points,
        "total_primitives": total_primitives,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "selection": spec["selection"],
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "artifact": str(output),
        "candidates": results,
        "total_points": total_points,
        "total_primitives": total_primitives,
        "selection": spec["selection"],
    }


def validate_world_seed_stage(
    *, stage_node_path: str, prim_paths: list[str], max_prims: int = 25_000
) -> dict[str, Any]:
    """Verify the simultaneous three-world USD/Karma stage contract."""
    hou = get_hou()
    from pxr import Usd

    if not isinstance(prim_paths, list) or len(prim_paths) != 3:
        raise ValueError("prim_paths must contain exactly three world roots")
    if not isinstance(max_prims, int) or isinstance(max_prims, bool) or max_prims < 1:
        raise ValueError("max_prims must be a positive integer")
    node = hou.node(_node_path(stage_node_path, "stage_node_path"))
    if node is None or node.type().category().name() != "Lop":
        raise ValueError(f"LOP stage contract not found: {stage_node_path}")
    stage = node.stage()
    if stage is None:
        raise ValueError("World Seed USD stage did not compose")
    count = sum(1 for _ in stage.Traverse())
    if count > max_prims:
        raise ValueError("World Seed USD stage exceeds max_prims")
    verified = []
    for candidate_id, prim_path in zip(WORLD_SEED_IDS, prim_paths, strict=True):
        path = _node_path(prim_path, f"{candidate_id}.prim_path")
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            raise ValueError(f"missing USD world prim: {path}")
        descendant_count = sum(1 for _ in Usd.PrimRange(prim)) - 1
        if descendant_count < 1:
            raise ValueError(f"USD world has no geometry descendants: {path}")
        verified.append({"id": candidate_id, "prim_path": path, "descendants": descendant_count})
    errors, warnings = _messages(node)
    if errors or warnings:
        raise ValueError("World Seed USD stage has Houdini messages")
    return {
        "stage_node_path": node.path(),
        "prim_count": count,
        "worlds": verified,
        "selection": {"winner": None, "automatic_ranking": False},
    }
