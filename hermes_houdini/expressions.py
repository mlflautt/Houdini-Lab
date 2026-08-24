"""Tiny safe subset for registered HScript parameter expressions.

This is intentionally not a general expression or code execution surface. It exists for readable
graph contracts such as per-point attribute extraction and fractional-frame Time Shift nodes.
"""

from __future__ import annotations

import re
from typing import Any

_SAFE_CHARACTERS = re.compile(r"[A-Za-z0-9_$.,()\" +*/-]+\Z")
_QUOTED_IDENTIFIER = re.compile(r'"[A-Za-z_][A-Za-z0-9_]*"')
_VARIABLE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ALLOWED_VARIABLES = {"FF", "PT"}
_ALLOWED_FUNCTIONS = {"point"}


def validate_hscript_expression(value: Any, label: str = "expression") -> str:
    """Validate one expression in the minimal registered geometry/time subset."""
    if not isinstance(value, str) or not 1 <= len(value) <= 160:
        raise ValueError(f"{label} must be a 1-160 character string")
    if not _SAFE_CHARACTERS.fullmatch(value) or any(token in value for token in ("..", "//")):
        raise ValueError(f"{label} contains unsafe HScript syntax")
    variables = set(_VARIABLE.findall(value))
    if not variables <= _ALLOWED_VARIABLES:
        raise ValueError(
            f"{label} uses unsupported variables: {sorted(variables - _ALLOWED_VARIABLES)}"
        )
    scrubbed = _QUOTED_IDENTIFIER.sub("", value)
    scrubbed = _VARIABLE.sub("", scrubbed)
    identifiers = set(_IDENTIFIER.findall(scrubbed))
    if not identifiers <= _ALLOWED_FUNCTIONS:
        raise ValueError(
            f"{label} uses unsupported functions or identifiers: "
            f"{sorted(identifiers - _ALLOWED_FUNCTIONS)}"
        )
    return value


__all__ = ["validate_hscript_expression"]
