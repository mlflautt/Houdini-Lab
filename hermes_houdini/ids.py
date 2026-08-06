"""Stable Hermes node identifiers (pure Python, no Houdini).

Node names/paths change; attach a persistent ID via userData so the agent references
nodes programmatically. Format: HOU-<CTX>-<short_hash>, e.g. HOU-SOP-7f03b91a.
"""
from __future__ import annotations

import hashlib

CTX_CODES = {
    "Sop": "SOP", "Obj": "OBJ", "Lop": "LOP", "Dop": "DOP",
    "Top": "TOP", "Cop": "COP", "Chop": "CHOP", "Apex": "APEX",
}


def ctx_code(category: str) -> str:
    """Map a Houdini network category name to a stable 3-letter code."""
    code = CTX_CODES.get(category)
    if code:
        return code
    # try uppercasing a known prefix
    for k, v in CTX_CODES.items():
        if category.lower().startswith(k.lower()):
            return v
    return category[:3].upper()


def make_id(category: str, seed: str = "") -> str:
    """Create a stable Hermes id for a node in `category`.

    `seed` (e.g. node name + parent path) makes the id deterministic for the same
    logical node, so replays resolve to the same id.
    """
    h = hashlib.sha256(f"{category}:{seed}".encode()).hexdigest()[:8]
    return f"HOU-{ctx_code(category)}-{h}"


def tag_kwargs(role: str, created_by: str = "", manifest_version: str = "1") -> dict[str, str]:
    """Build the userData dict to attach to a Hermes-managed node."""
    return {
        "hermes_id": "",  # filled per-node after creation
        "hermes_role": role,
        "hermes_created_by": created_by,
        "hermes_manifest_version": manifest_version,
    }


__all__ = ["make_id", "ctx_code", "tag_kwargs"]
