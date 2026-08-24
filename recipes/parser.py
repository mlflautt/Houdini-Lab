"""Recipe parser (pure Python, no Houdini).

Loads a declarative graph recipe YAML, validates structure, and renders it into a list of
bounded tool calls. The dispatcher/Houdini package executes those calls.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hermes_houdini.expressions import validate_hscript_expression

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


class RecipeError(ValueError):
    """Raised when a recipe is malformed or receives invalid inputs."""


@dataclass
class Recipe:
    id: str
    version: str
    summary: str
    contexts: list[str]
    inputs: dict[str, Any] = field(default_factory=dict)
    references: dict[str, Any] = field(default_factory=dict)
    nodes: list[dict[str, Any]] = field(default_factory=list)
    connections: list[list[Any]] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def render(self, parent_path: str, **overrides: Any) -> list[dict[str, Any]]:
        """Return ordered tool-call dicts with template vars substituted."""
        self.validate()
        ctx = self._resolve_inputs(parent_path, overrides)
        calls: list[dict[str, Any]] = []
        id_to_path = {ref_id: str(_subst(path, ctx)) for ref_id, path in self.references.items()}
        for n in self.nodes:
            params = {k: _subst(v, ctx) for k, v in (n.get("params") or {}).items()}
            expressions = {k: _subst(v, ctx) for k, v in (n.get("expressions") or {}).items()}
            name = str(_subst(n.get("name") or n["id"], ctx))
            id_to_path[n["id"]] = f"{parent_path.rstrip('/')}/{name}"
            calls.append(
                {
                    "tool": "node.create",
                    "arguments": {
                        "parent_path": parent_path,
                        "operator_type": n["type"],
                        "name": name,
                        "category": (self.contexts[0] if self.contexts else "Sop"),
                        "role": str(_subst(n.get("role", n["id"]), ctx)),
                        "parameters": params,
                        "expressions": expressions,
                        "comment": str(_subst(n.get("comment", ""), ctx)),
                    },
                }
            )
        for conn in self.connections:
            src, src_out, dst, dst_in = conn
            calls.append(
                {
                    "tool": "node.connect",
                    "arguments": {
                        "from_path": id_to_path[src],
                        "to_path": id_to_path[dst],
                        "output_index": int(src_out),
                        "input_index": int(dst_in),
                    },
                }
            )
        return calls

    def render_fragment(
        self,
        parent_path: str,
        *,
        ref_prefix: str = "",
        position_offset: tuple[float, float] = (0.0, 0.0),
        **overrides: Any,
    ) -> dict[str, Any]:
        """Render a recipe as a composable ``graph.apply_batch`` fragment.

        Node ids become batch-local refs, external references remain absolute paths, and
        node positions are translated without changing the recipe source. The result is
        pure JSON data and can be combined with other recipe fragments atomically.
        """
        self.validate()
        if ref_prefix and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,47}", ref_prefix):
            raise RecipeError("ref_prefix must be empty or a safe 1-48 character prefix")
        if (
            not isinstance(position_offset, tuple)
            or len(position_offset) != 2
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in position_offset
            )
        ):
            raise RecipeError("position_offset must be two finite numbers")
        ctx = self._resolve_inputs(parent_path, overrides)
        refs: dict[str, str] = {
            ref_id: str(_subst(path, ctx)) for ref_id, path in self.references.items()
        }
        operations: list[dict[str, Any]] = []
        category = _category_name(self.contexts[0])
        for node in self.nodes:
            ref = f"{ref_prefix}{node['id']}"
            name = str(_subst(node.get("name") or node["id"], ctx))
            position = _subst(node.get("position", [0.0, 0.0]), ctx)
            if (
                not isinstance(position, list)
                or len(position) != 2
                or any(
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    for value in position
                )
            ):
                raise RecipeError(f"node {node['id']} position must resolve to two finite numbers")
            operation = {
                "op": "create",
                "ref": ref,
                "parent_path": parent_path,
                "operator_type": node["type"],
                "name": name,
                "exact_name": bool(node.get("exact_name", True)),
                "category": category,
                "role": str(_subst(node.get("role", node["id"]), ctx)),
                "position": [
                    float(position[0]) + float(position_offset[0]),
                    float(position[1]) + float(position_offset[1]),
                ],
                "parameters": _subst(node.get("params") or {}, ctx),
                "expressions": _subst(node.get("expressions") or {}, ctx),
                "comment": str(_subst(node.get("comment", ""), ctx)),
            }
            operations.append(operation)
            refs[node["id"]] = ref
        for source, source_output, target, target_input in self.connections:
            operations.append(
                {
                    "op": "connect",
                    "from": refs[source],
                    "to": refs[target],
                    "output_index": int(source_output),
                    "input_index": int(target_input),
                }
            )
        for node in self.nodes:
            flags = node.get("flags") or {}
            if flags:
                operations.append(
                    {
                        "op": "set_flags",
                        "target": refs[node["id"]],
                        **{key: bool(_subst(value, ctx)) for key, value in flags.items()},
                    }
                )
        return {
            "recipe": {"id": self.id, "version": self.version},
            "operations": operations,
            "refs": refs,
            "outputs": {output: refs[output] for output in self.outputs},
        }

    def validate(self) -> None:
        """Validate graph structure without importing Houdini."""
        if not self.id or "." not in self.id:
            raise RecipeError("recipe id must be '<context>.<name>'")
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            raise RecipeError(f"recipe {self.id} has invalid semver: {self.version}")
        if not self.contexts:
            raise RecipeError(f"recipe {self.id} must declare at least one context")

        node_ids: list[str] = []
        allowed_node_keys = {
            "id",
            "type",
            "name",
            "role",
            "params",
            "expressions",
            "position",
            "comment",
            "flags",
            "exact_name",
        }
        for index, node in enumerate(self.nodes):
            if not isinstance(node, dict):
                raise RecipeError(f"node {index} must be an object")
            if not node.get("id") or not node.get("type"):
                raise RecipeError(f"node {index} requires id and type")
            unknown = set(node) - allowed_node_keys
            if unknown:
                raise RecipeError(f"node {index} has unknown keys: {sorted(unknown)}")
            if "params" in node and not isinstance(node["params"], dict):
                raise RecipeError(f"node {index} params must be an object")
            if "expressions" in node and (
                not isinstance(node["expressions"], dict)
                or any(
                    not isinstance(name, str) or not name or not isinstance(expression, str)
                    for name, expression in node["expressions"].items()
                )
            ):
                raise RecipeError(f"node {index} expressions must map parameter names to strings")
            overlap = set(node.get("params") or {}).intersection(node.get("expressions") or {})
            if overlap:
                raise RecipeError(
                    f"node {index} parameters cannot be both literal and expression: {sorted(overlap)}"
                )
            for name, expression in (node.get("expressions") or {}).items():
                try:
                    placeholders = set(re.findall(r"\{\{(\w+)\}\}", expression))
                    unknown_placeholders = placeholders.difference(self.inputs)
                    if unknown_placeholders:
                        raise ValueError(
                            f"node {index} expression {name} has unknown inputs: "
                            f"{sorted(unknown_placeholders)}"
                        )
                    validate_hscript_expression(
                        re.sub(r"\{\{\w+\}\}", "0", expression),
                        f"node {index} expression {name}",
                    )
                except ValueError as exc:
                    raise RecipeError(str(exc)) from exc
            if "position" in node and (
                not isinstance(node["position"], list) or len(node["position"]) != 2
            ):
                raise RecipeError(f"node {index} position must have two components")
            if "flags" in node:
                flags = node["flags"]
                if not isinstance(flags, dict) or not flags:
                    raise RecipeError(f"node {index} flags must be a non-empty object")
                unknown_flags = set(flags) - {"display", "render", "bypass"}
                if unknown_flags:
                    raise RecipeError(f"node {index} has unknown flags: {sorted(unknown_flags)}")
                if any(not isinstance(value, bool) for value in flags.values()):
                    raise RecipeError(f"node {index} flag values must be booleans")
            if "exact_name" in node and not isinstance(node["exact_name"], bool):
                raise RecipeError(f"node {index} exact_name must be a boolean")
            node_ids.append(str(node["id"]))
        if len(node_ids) != len(set(node_ids)):
            raise RecipeError(f"recipe {self.id} contains duplicate node ids")

        ref_ids = set(self.references)
        overlap = ref_ids.intersection(node_ids)
        if overlap:
            raise RecipeError(f"reference ids overlap node ids: {sorted(overlap)}")
        known_ids = set(node_ids) | ref_ids
        for index, connection in enumerate(self.connections):
            if not isinstance(connection, list) or len(connection) != 4:
                raise RecipeError(f"connection {index} must be [src, src_out, dst, dst_in]")
            src, _src_out, dst, _dst_in = connection
            if src not in known_ids:
                raise RecipeError(f"connection {index} references unknown source: {src}")
            if dst not in node_ids:
                raise RecipeError(f"connection {index} references unknown destination: {dst}")
        for output in self.outputs:
            if output not in node_ids:
                raise RecipeError(f"output references unknown node: {output}")

    def _resolve_inputs(self, parent_path: str, overrides: dict[str, Any]) -> dict[str, Any]:
        unknown = set(overrides).difference(self.inputs)
        if unknown:
            raise RecipeError(f"unknown recipe inputs: {sorted(unknown)}")
        ctx: dict[str, Any] = {"parent_path": parent_path}
        for name, spec in self.inputs.items():
            if not isinstance(spec, dict):
                raise RecipeError(f"input {name} must be an object")
            if name in overrides:
                value = overrides[name]
            elif name == "parent_path":
                value = parent_path
            elif "default" in spec:
                value = spec["default"]
            else:
                raise RecipeError(f"missing required recipe input: {name}")
            _validate_input(name, value, spec)
            ctx[name] = value
        return ctx


def _subst(value: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(value, str):
        exact = re.fullmatch(r"\{\{(\w+)\}\}", value)
        if exact and exact.group(1) in ctx:
            return ctx[exact.group(1)]
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(ctx.get(m.group(1), m.group(0))), value)
    if isinstance(value, list):
        return [_subst(item, ctx) for item in value]
    if isinstance(value, dict):
        return {key: _subst(item, ctx) for key, item in value.items()}
    return value


def _category_name(context: str) -> str:
    names = {
        "SOP": "Sop",
        "OBJ": "Object",
        "LOP": "Lop",
        "DOP": "Dop",
        "TOP": "Top",
        "COP": "Cop",
        "CHOP": "Chop",
    }
    return names.get(context.upper(), context)


def _validate_input(name: str, value: Any, spec: dict[str, Any]) -> None:
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
        raise RecipeError(f"input {name} must be {expected}")
    if "enum" in spec and value not in spec["enum"]:
        raise RecipeError(f"input {name} must be one of {spec['enum']}")
    if "min" in spec and value < spec["min"]:
        raise RecipeError(f"input {name} must be >= {spec['min']}")
    if "max" in spec and value > spec["max"]:
        raise RecipeError(f"input {name} must be <= {spec['max']}")


def load_recipe(path: str | Path) -> Recipe:
    text = Path(path).read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        try:
            # JSON is a strict YAML 1.2 subset. Bundled recipes intentionally stay
            # JSON-compatible so bare hython can validate them without global installs.
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "PyYAML is required for non-JSON YAML recipes (pip install pyyaml)"
            ) from exc
    if not isinstance(data, dict):
        raise RecipeError(f"recipe must contain a YAML object: {path}")
    recipe = Recipe(
        id=data["id"],
        version=str(data.get("version", "0.0.0")),
        summary=data.get("summary", ""),
        contexts=list(data.get("contexts", [])),
        inputs=data.get("inputs", {}),
        references=data.get("references", {}),
        nodes=list(data.get("nodes", [])),
        connections=list(data.get("connections", [])),
        outputs=list(data.get("outputs", [])),
        meta=data.get("meta", {}),
    )
    recipe.validate()
    return recipe


__all__ = ["Recipe", "RecipeError", "load_recipe"]
