"""Command envelope + structured result schemas (pure Python, no Houdini).

These mirror the protocol described in docs/architecture.md §5. A command is a bounded,
schema-validated request; a result is structured JSON-serializable data the agent consumes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

PROTOCOL_VERSION = "1.0"


class RiskClass(str, Enum):
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTERNAL = "external"


class Status(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    BLOCKED = "blocked"  # denied by policy/approval


class CodeMode(str, Enum):
    SAFE = "safe"
    DEVELOPMENT = "development"
    PRIVILEGED_LOCAL = "privileged_local"


@dataclass
class Policy:
    """Per-command safety/resource policy. Enforced by validation + cook controllers."""

    allow_network: bool = False
    allow_external_process: bool = False
    allow_overwrite: bool = False
    allow_arbitrary_code: bool = False
    max_seconds: float = 20.0
    max_points: int = 1_000_000
    max_voxels: int = 0
    max_frames: int = 1
    max_resolution: tuple[int, int] = (1280, 720)
    risk: RiskClass = RiskClass.LOW

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk"] = self.risk.value
        d["max_resolution"] = list(self.max_resolution)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Policy:
        d = dict(d)
        d["risk"] = RiskClass(d.get("risk", "low"))
        d["max_resolution"] = tuple(d.get("max_resolution", (1280, 720)))
        return cls(**d)


@dataclass
class CommandEnvelope:
    """A bounded, validated request from the orchestrator/agent to the Houdini package."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    tool_version: str = "1.0.0"
    request_id: str = ""
    session_id: str = ""
    project_id: str = ""
    policy: Policy | None = None
    expected: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "project_id": self.project_id,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "arguments": self.arguments,
            "expected": self.expected,
        }
        d["policy"] = (self.policy or Policy()).as_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CommandEnvelope:
        policy = Policy.from_dict(d.get("policy", {})) if d.get("policy") else None
        return cls(
            tool=d["tool"],
            arguments=d.get("arguments", {}),
            tool_version=d.get("tool_version", "1.0.0"),
            request_id=d.get("request_id", ""),
            session_id=d.get("session_id", ""),
            project_id=d.get("project_id", ""),
            policy=policy,
            expected=d.get("expected", {}),
        )


@dataclass
class ChangedNode:
    hermes_id: str = ""
    path: str = ""
    change: str = ""  # created | modified | deleted | bypassed


@dataclass
class CookInfo:
    scope: str = ""
    seconds: float = 0.0
    points: int = 0
    primitives: int = 0


@dataclass
class ToolResult:
    request_id: str = ""
    status: Status = Status.SUCCESS
    changed_nodes: list[ChangedNode] = field(default_factory=list)
    cook: CookInfo | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    checkpoint: str | None = None
    artifacts: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "changed_nodes": [asdict(n) for n in self.changed_nodes],
            "cook": asdict(self.cook) if self.cook else None,
            "warnings": self.warnings,
            "errors": self.errors,
            "checkpoint": self.checkpoint,
            "artifacts": self.artifacts,
            "data": self.data,
        }
