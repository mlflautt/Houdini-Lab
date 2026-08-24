"""Outside-Houdini bridge process.

Keep model/network work outside Houdini and expose only authenticated, structured
commands to the inside-Houdini package.
"""

from __future__ import annotations

from .auth import BridgeError, load_secret, make_secret, sign, verify

__version__ = "0.12.0"

__all__ = [
    "BridgeError",
    "load_secret",
    "make_secret",
    "sign",
    "verify",
    "__version__",
]
