"""Shared skill helpers (pure Python where possible; HOM optional)."""

from __future__ import annotations

from typing import Any

from hermes_houdini.schemas.command import CommandEnvelope


def build_envelope(tool: str, arguments: dict[str, Any], **meta: Any) -> CommandEnvelope:
    """Convenience to construct a command envelope from inside a skill step."""
    return CommandEnvelope(tool=tool, arguments=arguments, **meta)


def attribute_contract() -> dict[str, Any]:
    """Default attribute contract for a generated form graph (docs §7.7)."""
    return {
        "point": {
            "id": "integer stable instance identifier",
            "pscale": "float instance scale",
            "orient": "quaternion instance orientation",
            "Cd": "vector display/debug color",
            "variant": "integer asset variant",
        },
        "primitive": {
            "name": "string semantic piece name",
            "material": "string material assignment token",
        },
    }


__all__ = ["build_envelope", "attribute_contract"]
