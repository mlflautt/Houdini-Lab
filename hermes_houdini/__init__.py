"""Hermes Houdini package — inside-Houdini agentic substrate.

All HOM (`hou`) access is lazy: this package imports without Houdini installed so
pure-Python logic (schemas, policy, ids, registry) is unit-testable. HOM calls live
inside functions guarded by :func:`has_hou`.
"""

from __future__ import annotations

__version__ = "0.30.0"

import importlib.util

_HOU_AVAILABLE = importlib.util.find_spec("hou") is not None


def has_hou() -> bool:
    """True when the `hou` module is importable (inside Houdini / hython)."""
    return _HOU_AVAILABLE


def get_hou():
    """Return the `hou` module, raising a clear error if unavailable."""
    if not _HOU_AVAILABLE:
        raise RuntimeError("hou module not available. This operation requires Houdini/hython.")
    import hou

    return hou


__all__ = ["has_hou", "get_hou", "__version__"]
