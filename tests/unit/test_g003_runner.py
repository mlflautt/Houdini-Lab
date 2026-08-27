"""Focused regressions for the G003 live runner's durable progress protocol."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _runner_module():
    path = Path(__file__).parents[2] / "scripts" / "run_g003_visual_audition.py"
    spec = importlib.util.spec_from_file_location("g003_runner_test_target", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_emit_preserves_postprocess_kind_without_colliding_with_event(capsys) -> None:
    runner = _runner_module()
    runner._emit("postprocess", kind="local_preview_encode", bytes=123)
    record = json.loads(capsys.readouterr().out)
    assert record == {
        "event": "postprocess",
        "kind": "local_preview_encode",
        "bytes": 123,
    }
