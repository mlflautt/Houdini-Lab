#!/usr/bin/env hython
"""Read-only Hython startup and node inventory probe for a loaded SideFX Labs package."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import hou

_CATEGORIES = (
    ("SOP", hou.sopNodeTypeCategory),
    ("OBJ", hou.objNodeTypeCategory),
    ("LOP", hou.lopNodeTypeCategory),
    ("DOP", hou.dopNodeTypeCategory),
    ("TOP", hou.topNodeTypeCategory),
    ("COP", hou.copNodeTypeCategory),
    ("CHOP", hou.chopNodeTypeCategory),
)


def _is_labs(name: str, description: str, library_path: str | None) -> bool:
    text = " ".join((name, description, library_path or "")).lower()
    return "labs::" in name.lower() or "gamedev::" in name.lower() or "sidefxlabs" in text


def _inventory() -> dict[str, list[dict[str, Any]]]:
    inventory: dict[str, list[dict[str, Any]]] = {}
    for label, category_factory in _CATEGORIES:
        entries = []
        for name, node_type in sorted(category_factory().nodeTypes().items()):
            definition = node_type.definition()
            library_path = definition.libraryFilePath() if definition is not None else None
            description = node_type.description()
            if not _is_labs(name, description, library_path):
                continue
            entries.append(
                {
                    "name": name,
                    "description": description,
                    "min_inputs": node_type.minNumInputs(),
                    "max_inputs": node_type.maxNumInputs(),
                    "library_path": library_path,
                }
            )
        inventory[label] = entries
    return inventory


def _license_mode() -> str:
    category = hou.licenseCategory()
    return category.name() if hasattr(category, "name") else str(category)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    inventory = _inventory()
    report = {
        "schema": "hermes.houdini.sidefx_labs_startup_probe",
        "schema_version": "1.0",
        "houdini_version": hou.applicationVersionString(),
        "license_mode": _license_mode(),
        "package_skiplist": os.environ.get("HOUDINI_PACKAGE_SKIPLIST", ""),
        "houdini_path": hou.getenv("HOUDINI_PATH"),
        "node_inventory": inventory,
        "counts": {category: len(entries) for category, entries in inventory.items()},
        "total_node_types": sum(len(entries) for entries in inventory.values()),
        "mutation_performed": False,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(rendered)
    print(rendered, end="")
    hou.exit(exit_code=0, suppress_save_prompt=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
