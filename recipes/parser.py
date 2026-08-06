"""Recipe parser (pure Python, no Houdini).

Loads a declarative graph recipe YAML, validates structure, and renders it into a list of
bounded tool calls. The dispatcher/Houdini package executes those calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass
class Recipe:
    id: str
    version: str
    summary: str
    contexts: list[str]
    inputs: dict[str, Any] = field(default_factory=dict)
    nodes: list[dict[str, Any]] = field(default_factory=list)
    connections: list[list[Any]] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def render(self, parent_path: str, **overrides: Any) -> list[dict[str, Any]]:
        """Return ordered tool-call dicts with template vars substituted."""
        ctx = {"parent_path": parent_path}
        ctx.update(overrides)
        calls: list[dict[str, Any]] = []
        id_to_name: dict[str, str] = {}
        for n in self.nodes:
            params = {
                k: _subst(v, ctx) for k, v in (n.get("params") or {}).items()
            }
            name = n.get("name") or n["id"]
            id_to_name[n["id"]] = name
            calls.append({
                "tool": "node.create",
                "arguments": {
                    "parent_path": parent_path,
                    "operator_type": n["type"],
                    "name": name,
                    "category": (self.contexts[0] if self.contexts else "Sop"),
                    "role": n.get("role", n["id"]),
                    "parameters": params,
                },
            })
        for conn in self.connections:
            src, src_out, dst, dst_in = conn
            calls.append({
                "tool": "node.connect",
                "arguments": {
                    "from_path": f"{parent_path}/{id_to_name[src]}",
                    "to_path": f"{parent_path}/{id_to_name[dst]}",
                    "input_index": int(dst_in),
                },
            })
        return calls


def _subst(value: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(ctx.get(m.group(1), m.group(0))), value)
    return value


def load_recipe(path: str | Path) -> Recipe:
    if yaml is None:
        raise RuntimeError("PyYAML required to parse recipes (pip install pyyaml)")
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Recipe(
        id=data["id"], version=str(data.get("version", "0.0.0")),
        summary=data.get("summary", ""), contexts=list(data.get("contexts", [])),
        inputs=data.get("inputs", {}), nodes=list(data.get("nodes", [])),
        connections=list(data.get("connections", [])),
        outputs=list(data.get("outputs", [])), meta=data.get("meta", {}),
    )


__all__ = ["Recipe", "load_recipe"]
