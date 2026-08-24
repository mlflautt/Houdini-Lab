"""Manifest-first loading for skills stored in ``skills/<skill-id>``.

Skill ids contain dots and are intentionally not Python package names. This loader
validates the YAML contract, imports ``skill.py`` by path, and invokes its bounded
``plan`` function without importing Houdini.
"""

from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by bare Hython integration
    yaml = None  # type: ignore


class SkillError(ValueError):
    """Raised for an invalid skill manifest, module, or invocation."""


_REQUIRED_FIELDS = {
    "id",
    "version",
    "summary",
    "contexts",
    "inputs",
    "risk",
    "checkpoint",
    "cook_budget",
    "steps",
    "verification",
    "outputs",
    "rollback",
    "license",
    "houdini",
}


@dataclass(frozen=True)
class SkillDefinition:
    root: Path
    manifest: dict[str, Any]
    module: ModuleType

    @property
    def id(self) -> str:
        return str(self.manifest["id"])

    @property
    def version(self) -> str:
        return str(self.manifest["version"])

    def plan(self, **arguments: Any) -> list[dict[str, Any]]:
        resolved = _resolve_inputs(self.manifest["inputs"], arguments)
        result = self.module.plan(**resolved)
        if not isinstance(result, list) or not all(isinstance(call, dict) for call in result):
            raise SkillError(f"skill {self.id} plan() must return a list of command objects")
        for index, call in enumerate(result):
            if not isinstance(call.get("tool"), str) or not isinstance(call.get("arguments"), dict):
                raise SkillError(f"skill {self.id} command {index} is not a tool envelope")
        return result


def discover_skills(skills_root: str | Path) -> list[SkillDefinition]:
    root = Path(skills_root)
    return [load_skill(path.parent) for path in sorted(root.glob("*/skill.yaml"))]


def load_skill(path: str | Path) -> SkillDefinition:
    root = Path(path).resolve()
    manifest_path = root / "skill.yaml"
    module_path = root / "skill.py"
    if not manifest_path.is_file() or not module_path.is_file():
        raise SkillError(f"skill requires skill.yaml and skill.py: {root}")
    text = manifest_path.read_text(encoding="utf-8")
    if yaml is not None:
        manifest = yaml.safe_load(text)
    else:
        try:
            # JSON is a strict YAML 1.2 subset. Bundled manifests deliberately use
            # that subset so Houdini's stock Python can load skills without a global
            # PyYAML installation or an injected PYTHONPATH.
            manifest = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SkillError(
                "PyYAML is required for non-JSON YAML skill manifests; bundled skills "
                "must remain JSON-compatible"
            ) from exc
    if not isinstance(manifest, dict):
        raise SkillError(f"skill manifest must be a YAML object: {manifest_path}")
    _validate_manifest(root, manifest)

    safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", str(manifest["id"]))
    module_name = f"_hermes_skill_{safe_id}_{abs(hash(str(root)))}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise SkillError(f"unable to load skill module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "plan", None)):
        raise SkillError(f"skill module has no callable plan(): {module_path}")
    return SkillDefinition(root=root, manifest=manifest, module=module)


def _validate_manifest(root: Path, manifest: dict[str, Any]) -> None:
    missing = sorted(_REQUIRED_FIELDS.difference(manifest))
    if missing:
        raise SkillError(f"skill manifest missing fields: {missing}")
    skill_id = manifest["id"]
    if not isinstance(skill_id, str) or not re.fullmatch(
        r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", skill_id
    ):
        raise SkillError(f"invalid skill id: {skill_id}")
    if root.name != skill_id:
        raise SkillError(f"skill directory '{root.name}' must match id '{skill_id}'")
    version = str(manifest["version"])
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SkillError(f"skill {skill_id} has invalid semver: {version}")
    if not isinstance(manifest["contexts"], list) or not manifest["contexts"]:
        raise SkillError(f"skill {skill_id} must declare contexts")
    if manifest["risk"] not in {"read_only", "low", "medium", "high", "external"}:
        raise SkillError(f"skill {skill_id} has invalid risk")
    if not isinstance(manifest["inputs"], dict):
        raise SkillError(f"skill {skill_id} inputs must be an object")
    for name, spec in manifest["inputs"].items():
        if not isinstance(spec, dict):
            raise SkillError(f"skill input {name} must be an object")
        _validate_input_schema(name, spec)


def _validate_input_schema(name: str, spec: dict[str, Any]) -> None:
    if "type" not in spec and "enum" not in spec:
        raise SkillError(f"skill input {name} requires type or enum")
    if "min" in spec and "max" in spec and spec["min"] > spec["max"]:
        raise SkillError(f"skill input {name} has min greater than max")
    if "default" in spec:
        _validate_value(name, spec["default"], spec)


def _resolve_inputs(specs: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = set(arguments).difference(specs)
    if unknown:
        raise SkillError(f"unknown skill inputs: {sorted(unknown)}")
    resolved: dict[str, Any] = {}
    for name, spec in specs.items():
        if name in arguments:
            value = arguments[name]
        elif "default" in spec:
            value = spec["default"]
        else:
            raise SkillError(f"missing required skill input: {name}")
        _validate_value(name, value, spec)
        resolved[name] = value
    return resolved


def _validate_value(name: str, value: Any, spec: dict[str, Any]) -> None:
    expected = spec.get("type")
    valid = True
    if expected == "string":
        valid = isinstance(value, str)
    elif expected == "integer":
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif expected == "number":
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected == "boolean":
        valid = isinstance(value, bool)
    if not valid:
        raise SkillError(f"skill input {name} must be {expected}")
    if "enum" in spec and value not in spec["enum"]:
        raise SkillError(f"skill input {name} must be one of {spec['enum']}")
    if "min" in spec and value < spec["min"]:
        raise SkillError(f"skill input {name} must be >= {spec['min']}")
    if "max" in spec and value > spec["max"]:
        raise SkillError(f"skill input {name} must be <= {spec['max']}")


__all__ = ["SkillDefinition", "SkillError", "discover_skills", "load_skill"]
