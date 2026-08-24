"""Tool / recipe / HDA registry (pure Python, no Houdini).

Indexes bounded operations by name+version so the dispatcher can resolve and the
orchestrator can select before inventing a new network.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


def _version_key(version: str) -> tuple[Any, ...]:
    """Sort numeric dotted versions correctly while retaining deterministic fallbacks."""
    parts = version.split(".")
    if parts and all(part.isdigit() for part in parts):
        return (0, *(int(part) for part in parts))
    return (1, version)


@dataclass
class Entry:
    name: str
    version: str
    handler: Callable[..., Any]
    kind: str  # tool | recipe | hda
    risk: str = "low"
    doc: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


class Registry:
    def __init__(self) -> None:
        self._entries: dict[str, Entry] = {}

    def _key(self, name: str, version: str) -> str:
        return f"{name}@{version}"

    def register(
        self,
        name: str,
        version: str,
        handler: Callable[..., Any],
        kind: str = "tool",
        risk: str = "low",
        doc: str = "",
        meta: dict[str, Any] | None = None,
    ) -> None:
        self._entries[self._key(name, version)] = Entry(
            name, version, handler, kind, risk, doc, meta or {}
        )

    def resolve(self, name: str, version: str | None = None) -> Entry | None:
        if version:
            return self._entries.get(self._key(name, version))
        # Latest numeric dotted version wins (1.10.0 correctly sorts after 1.2.0).
        candidates = [e for e in self._entries.values() if e.name == name]
        if not candidates:
            return None
        return sorted(candidates, key=lambda entry: _version_key(entry.version))[-1]

    def list(self, kind: str | None = None) -> list[Entry]:
        return [e for e in self._entries.values() if kind in (None, e.kind)]

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": e.name,
                "version": e.version,
                "kind": e.kind,
                "risk": e.risk,
                "doc": e.doc,
                "meta": e.meta,
            }
            for e in sorted(self._entries.values(), key=lambda e: (e.kind, e.name))
        ]


# Global registry instance imported by tools and dispatcher.
REGISTRY = Registry()


def tool(name: str, version: str = "1.0.0", risk: str = "low", doc: str = ""):
    """Decorator to register a function as a tool."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY.register(name, version, fn, kind="tool", risk=risk, doc=doc or fn.__doc__ or "")
        return fn

    return deco


__all__ = ["Registry", "REGISTRY", "Entry", "tool"]
