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

_SAFE_STEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def undo_group(label: str, fn: Callable[[], Any]) -> Any:
    """Run `fn` inside a bounded undo group."""
    hou = get_hou()
    with hou.undos.group(label):
        return fn()


def next_checkpoint_path(base_path: str) -> str:
    """Given a .hipnc base path, return the next incremented version path."""
    base, extension = os.path.splitext(base_path)
    extension = extension or ".hipnc"
    m = re.fullmatch(r"(.*)_v(\d+)", base)
    if m:
        prefix = m.group(1)
        num = m.group(2)
        verlen = len(num)
        i = int(num) + 1
        while os.path.exists(f"{prefix}_v{i:0{verlen}d}{extension}"):
            i += 1
        return f"{prefix}_v{i:0{verlen}d}{extension}"
    # no version present: append _v001
    i = 1
    while os.path.exists(f"{base}_v{i:03d}{extension}"):
        i += 1
    return f"{base}_v{i:03d}{extension}"


def save_checkpoint(output_dir: str, stem: str = "hermes") -> str:
    """Save an incremented .hipnc checkpoint in `output_dir`; return its path."""
    if not isinstance(stem, str) or not _SAFE_STEM.fullmatch(stem):
        raise ValueError("stem must be a safe 1-64 character filename stem")
    hou = get_hou()
    os.makedirs(output_dir, exist_ok=True)
    first = os.path.join(output_dir, stem + "_v001.hipnc")
    path = first if not os.path.exists(first) else next_checkpoint_path(first)
    original_name = hou.hipFile.name()
    hou.hipFile.save(path, save_to_recent_files=False)
    hou.hipFile.setName(original_name)
    return path


def restore_checkpoint(path: str, original_name: str | None = None) -> None:
    """Load a durable checkpoint and optionally restore the prior in-memory HIP name."""
    hou = get_hou()
    hou.hipFile.load(path, suppress_save_prompt=True, ignore_load_warnings=True)
    if original_name:
        hou.hipFile.setName(original_name)


__all__ = ["undo_group", "save_checkpoint", "restore_checkpoint", "next_checkpoint_path"]
