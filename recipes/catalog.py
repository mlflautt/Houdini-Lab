"""Registration of bundled declarative recipes with the central Hermes registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_houdini.registry import REGISTRY

from .parser import Recipe, load_recipe

_ROOT = Path(__file__).resolve().parent
_REGISTERED = False


def _handler(recipe: Recipe):
    def render(
        *,
        parent_path: str,
        inputs: dict[str, Any] | None = None,
        ref_prefix: str = "",
        position_offset: list[float] | tuple[float, float] = (0.0, 0.0),
    ) -> dict[str, Any]:
        if not isinstance(inputs or {}, dict):
            raise ValueError("recipe inputs must be an object")
        if not isinstance(position_offset, (list, tuple)) or len(position_offset) != 2:
            raise ValueError("position_offset must have two components")
        return recipe.render_fragment(
            parent_path,
            ref_prefix=ref_prefix,
            position_offset=(position_offset[0], position_offset[1]),
            **(inputs or {}),
        )

    return render


def register_bundled_recipes() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    for path in sorted(_ROOT.glob("*/*.yaml")):
        recipe = load_recipe(path)
        REGISTRY.register(
            recipe.id,
            recipe.version,
            _handler(recipe),
            kind="recipe",
            risk="medium",
            doc=recipe.summary,
            meta={
                "contexts": recipe.contexts,
                "inputs": recipe.inputs,
                "outputs": recipe.outputs,
                "cook_budget": recipe.meta.get("cook_budget", {}),
                "source": str(path),
            },
        )
    _REGISTERED = True


__all__ = ["register_bundled_recipes"]
