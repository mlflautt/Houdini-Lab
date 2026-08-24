"""Pure transaction path validation."""

from __future__ import annotations

import pytest
from hermes_houdini.transactions import save_checkpoint


def test_checkpoint_stem_cannot_traverse(tmp_path):
    with pytest.raises(ValueError, match="safe"):
        save_checkpoint(str(tmp_path), "../escape")
