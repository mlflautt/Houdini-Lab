#!/usr/bin/env python3
"""Inspect a plugin record, package JSON, or installed tree without loading Houdini."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes_houdini.plugin_registry import (
    audit_package_json,
    audit_plugin_archive,
    inventory_plugin_tree,
    load_plugin_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="optional new JSON report path")
    sub = parser.add_subparsers(dest="command", required=True)

    manifest = sub.add_parser("manifest", help="validate a repository plugin record")
    manifest.add_argument("path", type=Path)

    package = sub.add_parser("package", help="audit a Houdini package JSON")
    package.add_argument("path", type=Path)
    package.add_argument("--plugin-root", type=Path, required=True)
    package.add_argument("--expected-name", required=True)

    tree = sub.add_parser("tree", help="inventory an installed package tree")
    tree.add_argument("plugin_root", type=Path)

    archive = sub.add_parser("archive", help="audit a ZIP before extraction")
    archive.add_argument("path", type=Path)
    archive.add_argument("--top-level", action="append", required=True)
    return parser


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "manifest":
        return load_plugin_manifest(args.path.resolve())
    if args.command == "package":
        return audit_package_json(
            args.path.resolve(),
            plugin_root=args.plugin_root.resolve(),
            expected_name=args.expected_name,
        )
    if args.command == "tree":
        return inventory_plugin_tree(args.plugin_root.resolve())
    if args.command == "archive":
        return audit_plugin_archive(args.path.resolve(), expected_top_levels=set(args.top_level))
    raise AssertionError(f"unknown command: {args.command}")


def main() -> int:
    args = _parser().parse_args()
    report = _run(args)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        output = args.out.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
