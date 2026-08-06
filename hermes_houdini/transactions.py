"""Transaction + checkpoint manager (inside Houdini, needs `hou`).

Two layers (docs §4.9):
1. Interactive undo grouping via hou.undos.group for bounded UI edits.
2. Durable checkpoints via incremented .hipnc saves before medium/high-risk work.

Undo is NOT durable rollback; checkpoints are.
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any

from . import get_hou


def undo_group(label: str, fn: Callable[[], Any]) -> Any:
    """Run `fn` inside a bounded undo group."""
    hou = get_hou()
    with hou.undos.group(label):
        return fn()


_VERSION_RE = re.compile(r"v(\d+)")


def next_checkpoint_path(base_path: str) -> str:
    """Given a .hipnc base path, return the next incremented version path."""
    base, _ = os.path.splitext(base_path)
    m = _VERSION_RE.search(base)
    if m:
        start = int(m.group(1))
        prefix = base[: m.start()]
        verlen = len(m.group(1))
        i = start
        while os.path.exists(f"{prefix}{i:0{verlen}d}.hipnc"):
            i += 1
        return f"{prefix}{i:0{verlen}d}.hipnc"
    # no version present: append v001
    i = 1
    while os.path.exists(f"{base}_v{i:03d}.hipnc"):
        i += 1
    return f"{base}_v{i:03d}.hipnc"


def save_checkpoint(output_dir: str, stem: str = "hermes") -> str:
    """Save an incremented .hipnc checkpoint in `output_dir`; return its path."""
    hou = get_hou()
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.join(output_dir, stem)
    path = next_checkpoint_path(base + "_v001.hipnc")
    hou.hipFile.save(path)
    return path


__all__ = ["undo_group", "save_checkpoint", "next_checkpoint_path"]
