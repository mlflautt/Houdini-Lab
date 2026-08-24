"""Pure graph-batch validation, diff, and provenance tests."""

from __future__ import annotations

import json

import pytest
from hermes_houdini.graph_batch import (
    MAX_BATCH_OPERATIONS,
    append_replay_record,
    validate_batch,
    validate_batch_options,
)
from hermes_houdini.graph_state import diff_snapshots


def _valid_operations():
    return [
        {
            "op": "create",
            "ref": "src",
            "parent_path": "/obj/HERMES_ASSET",
            "operator_type": "sphere",
            "name": "SRC",
            "exact_name": True,
            "position": [-2.0, 3.5],
            "parameters": {"radx": 2.0},
        },
        {
            "op": "create",
            "ref": "out",
            "parent_path": "/obj/HERMES_ASSET",
            "operator_type": "null",
        },
        {"op": "connect", "from": "src", "to": "out"},
        {"op": "set_flags", "target": "out", "display": True, "render": True},
        {"op": "set_comment", "target": "out", "comment": "Editable output contract"},
    ]


def test_validate_batch_accepts_bounded_allowlisted_graph_operations():
    normalized = validate_batch("asset.seed-01", _valid_operations())
    assert normalized == _valid_operations()


@pytest.mark.parametrize(
    ("operations", "message"),
    [
        ([{"op": "python", "code": "pass"}], "not allowed"),
        ([{"op": "connect", "from": "later", "to": "/obj/A"}], "unknown or later"),
        (
            [{"op": "create", "ref": "a", "parent_path": "obj", "operator_type": "box"}],
            "absolute Houdini path",
        ),
        ([{"op": "set_flags", "target": "/obj/A"}], "at least one flag"),
        (
            [
                {
                    "op": "create",
                    "ref": "a",
                    "parent_path": "/obj",
                    "operator_type": "geo",
                    "position": [0, float("inf")],
                }
            ],
            "finite JSON data",
        ),
        (
            [
                {
                    "op": "create",
                    "ref": "a",
                    "parent_path": "/obj",
                    "operator_type": "geo",
                    "exact_name": True,
                }
            ],
            "requires name",
        ),
        ([{"op": "set_comment", "target": "/obj/A", "comment": "x", "extra": 1}], "unknown keys"),
    ],
)
def test_validate_batch_rejects_unsafe_or_ambiguous_operations(operations, message):
    with pytest.raises(ValueError, match=message):
        validate_batch("batch-1", operations)


def test_validate_batch_enforces_operation_cap():
    operation = {
        "op": "set_comment",
        "target": "/obj/A",
        "comment": "bounded",
    }
    with pytest.raises(ValueError, match="exceeds"):
        validate_batch("batch-1", [operation] * (MAX_BATCH_OPERATIONS + 1))


def test_checkpoint_stem_cannot_escape_approved_checkpoint_directory():
    with pytest.raises(ValueError, match="checkpoint_stem"):
        validate_batch_options("Hermes batch", "../escape")
    validate_batch_options("Hermes batch", "asset_checkpoint")


def test_diff_snapshots_reports_created_deleted_and_field_changes():
    before = {
        "networks": {
            "/obj/G": {
                "nodes": {
                    "/obj/G/A": {"type": "box", "comment": "old"},
                    "/obj/G/OLD": {"type": "null", "comment": ""},
                }
            }
        }
    }
    after = {
        "networks": {
            "/obj/G": {
                "nodes": {
                    "/obj/G/A": {"type": "box", "comment": "new"},
                    "/obj/G/NEW": {"type": "sphere", "comment": ""},
                }
            }
        }
    }
    diff = diff_snapshots(before, after)
    assert [item["path"] for item in diff["created"]] == ["/obj/G/NEW"]
    assert [item["path"] for item in diff["deleted"]] == ["/obj/G/OLD"]
    assert diff["modified"][0]["fields"]["comment"] == {
        "before": "old",
        "after": "new",
    }


def test_replay_log_is_append_only_jsonl(tmp_path):
    path = tmp_path / "provenance" / "graph.jsonl"
    append_replay_record(str(path), {"batch_id": "one", "status": "success"})
    append_replay_record(str(path), {"batch_id": "two", "status": "rolled_back"})
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [record["batch_id"] for record in records] == ["one", "two"]
