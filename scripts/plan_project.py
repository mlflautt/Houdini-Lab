#!/usr/bin/env python3
"""Validate, dry-plan, or observe one explicit Hermes Houdini project."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from hermes_houdini.project_pipeline import (
    load_and_plan_project,
    observe_project,
)
from hermes_houdini.project_spec import load_project_spec, project_spec_sha256


def _root(value: str) -> Path:
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError("project_root must be an existing directory")
    return path


def _confined_existing(value: str, *, root: Path, label: str) -> Path:
    candidate = Path(value).expanduser()
    candidate = candidate if candidate.is_absolute() else root / candidate
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must resolve beneath project_root") from exc
    if not resolved.is_file():
        raise ValueError(f"{label} must name an existing file")
    return resolved


def _confined_new(value: str, *, root: Path) -> Path:
    candidate = Path(value).expanduser()
    candidate = candidate if candidate.is_absolute() else root / candidate
    if candidate.exists() or candidate.is_symlink():
        raise ValueError("output must be a new path")
    parent = candidate.parent.resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as exc:
        raise ValueError("output parent must resolve beneath project_root") from exc
    return parent / candidate.name


def _read_json(value: str, *, root: Path, label: str) -> Any:
    path = _confined_existing(value, root=root, label=label)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must contain valid JSON: {exc}") from exc


def _emit(value: Mapping[str, Any], *, output: str | None, root: Path) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(rendered)
        return
    path = _confined_new(output, root=root)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(rendered)


def _add_project_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True, help="Explicit project YAML path")
    parser.add_argument("--project-root", required=True, help="Existing absolute project root")
    parser.add_argument("--output", help="Optional new output path confined beneath project root")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pure Hermes Houdini project validation, planning, and observation"
    )
    subparsers = parser.add_subparsers(dest="command")
    validate = subparsers.add_parser("validate", help="Normalize and hash one project")
    _add_project_args(validate)
    plan = subparsers.add_parser("plan", help="Compile one non-executable dry plan")
    _add_project_args(plan)
    observe = subparsers.add_parser("observe", help="Build an index from explicit dry inputs")
    _add_project_args(observe)
    observe.add_argument("--plan", required=True, help="Explicit plan JSON path")
    observe.add_argument("--runtime", help="Optional runtime identity JSON path")
    observe.add_argument("--execution-records", help="Optional execution-record list JSON path")
    observe.add_argument("--artifacts", help="Optional artifact list JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        root = _root(args.project_root)
        project_path = _confined_existing(args.project, root=root, label="project")
        if args.command == "validate":
            project = load_project_spec(project_path, project_root=root)
            payload = {
                "schema": "hermes.houdini.project_validation.v1",
                "project_sha256": project_spec_sha256(project),
                "project": project,
            }
            _emit(payload, output=args.output, root=root)
            return 0
        if args.command == "plan":
            bundle = load_and_plan_project(project_path, project_root=root)
            plan = bundle["plan"]
            _emit(plan, output=args.output, root=root)
            return 2 if plan["blockers"] else 0

        project = load_project_spec(project_path, project_root=root)
        plan_value = _read_json(args.plan, root=root, label="plan")
        if not isinstance(plan_value, Mapping):
            raise ValueError("plan must contain a JSON object")
        runtime = _read_json(args.runtime, root=root, label="runtime") if args.runtime else None
        if runtime is not None and not isinstance(runtime, Mapping):
            raise ValueError("runtime must contain a JSON object")
        records = (
            _read_json(args.execution_records, root=root, label="execution_records")
            if args.execution_records
            else []
        )
        artifacts = (
            _read_json(args.artifacts, root=root, label="artifacts")
            if args.artifacts
            else []
        )
        if not isinstance(records, list) or not all(isinstance(item, Mapping) for item in records):
            raise ValueError("execution_records must contain a JSON list of objects")
        if not isinstance(artifacts, list) or not all(
            isinstance(item, Mapping) for item in artifacts
        ):
            raise ValueError("artifacts must contain a JSON list of objects")
        index = observe_project(
            project,
            plan_value,
            project_root=root,
            runtime_identity=runtime,
            execution_records=records,
            artifacts=artifacts,
        )
        _emit(index, output=args.output, root=root)
        return 2 if index["blockers"] else 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
