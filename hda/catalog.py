"""Registration of version-controlled HDA source builders."""

from __future__ import annotations

from typing import Any

from hermes_houdini.registry import REGISTRY

_REGISTERED = False


def _build_fractal_relic(*, dest_dir: str) -> dict[str, Any]:
    from hda.source.hermes_fractal_relic.build import build

    return build(dest_dir=dest_dir, overwrite=False)


def register_bundled_hdas() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    REGISTRY.register(
        "hermes::fractal_relic",
        "2.0.0",
        _build_fractal_relic,
        kind="hda",
        risk="medium",
        doc="Build the recipe-backed three-candidate fractal relic .hdanc definition.",
        meta={
            "type_name": "hermes::fractal_relic::2.0",
            "contexts": ["SOP"],
            "license": "houdini-apprentice-noncommercial",
            "engine_export_allowed": False,
            "source": "hda/source/hermes_fractal_relic/build.py",
        },
    )
    _REGISTERED = True


__all__ = ["register_bundled_hdas"]
