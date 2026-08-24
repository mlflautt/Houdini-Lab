"""Event-loop dispatcher (inside Houdini).

Network/worker threads must never mutate the scene directly. Pattern (docs §4.4):
listener validates -> enqueue plain envelope -> event-loop callback processes ONE bounded
command -> HOM op -> JSON result. Long cooks become jobs (handled by cook.py) rather than
blocking the channel.

This module is import-safe without Houdini (queue + validation only). HOM-side execution
delegates to the registered tool handlers, which import `hou` lazily.
"""

from __future__ import annotations

import queue
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .execution import reset_current_envelope, set_current_envelope
from .policy import ApprenticePolicy
from .registry import REGISTRY
from .schemas.command import (
    CodeMode,
    CommandEnvelope,
    Policy,
    RiskClass,
    Status,
    ToolResult,
)

DEFAULT_QUEUE: queue.Queue[CommandEnvelope] = queue.Queue()


@dataclass
class DispatchOutcome:
    result: ToolResult
    envelope: CommandEnvelope


@dataclass
class PendingApproval:
    approval_id: str
    envelope: CommandEnvelope
    risk: RiskClass
    created_at: float
    expires_at: float


class ApprovalStore:
    """Short-lived, single-use approvals for exact stored command envelopes."""

    def __init__(self, ttl_seconds: float = 300.0, max_pending: int = 100) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_pending = max_pending
        self._pending: dict[str, PendingApproval] = {}
        self._by_request: dict[str, str] = {}

    def request(self, envelope: CommandEnvelope, risk: RiskClass) -> PendingApproval:
        self._purge()
        existing_id = self._by_request.get(envelope.request_id)
        if existing_id and existing_id in self._pending:
            return self._pending[existing_id]
        if len(self._pending) >= self.max_pending:
            raise RuntimeError("approval queue is full")
        now = time.monotonic()
        approval = PendingApproval(
            approval_id=secrets.token_urlsafe(18),
            envelope=envelope,
            risk=risk,
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        self._pending[approval.approval_id] = approval
        self._by_request[envelope.request_id] = approval.approval_id
        return approval

    def take(self, approval_id: str) -> PendingApproval:
        self._purge()
        approval = self._pending.pop(approval_id, None)
        if approval is None:
            raise KeyError("approval not found, expired, or already consumed")
        self._by_request.pop(approval.envelope.request_id, None)
        return approval

    def deny(self, approval_id: str) -> PendingApproval:
        return self.take(approval_id)

    def describe(self) -> list[dict[str, Any]]:
        self._purge()
        now = time.monotonic()
        return [
            {
                "approval_id": item.approval_id,
                "request_id": item.envelope.request_id,
                "tool": item.envelope.tool,
                "risk": item.risk.value,
                "expires_in_seconds": round(max(0.0, item.expires_at - now), 3),
            }
            for item in sorted(self._pending.values(), key=lambda value: value.created_at)
        ]

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [
            approval_id for approval_id, item in self._pending.items() if item.expires_at <= now
        ]
        for approval_id in expired:
            item = self._pending.pop(approval_id)
            self._by_request.pop(item.envelope.request_id, None)


class Dispatcher:
    """Bounded command processor. Safe to construct without Houdini."""

    def __init__(
        self,
        policy: ApprenticePolicy | None = None,
        queue: queue.Queue[CommandEnvelope] | None = None,
        approvals: ApprovalStore | None = None,
    ) -> None:
        # Importing the bounded built-ins runs their @tool decorators. Do this here
        # rather than relying on callers to know an undocumented import order.
        from . import tools as _builtin_tools  # noqa: F401

        self.policy = policy or ApprenticePolicy()
        self.queue: queue.Queue[CommandEnvelope] = queue or DEFAULT_QUEUE
        self.pending: list[CommandEnvelope] = []
        self.approvals = approvals or ApprovalStore()

    # --- intake ---------------------------------------------------------
    def enqueue(self, env: CommandEnvelope) -> None:
        self.queue.put(env)

    # --- validation (no Houdini) ---------------------------------------
    def validate(self, env: CommandEnvelope, approval_granted: bool = False) -> tuple[bool, str]:
        if not env.tool:
            return False, "missing tool name"
        entry = REGISTRY.resolve(env.tool)
        if entry is None:
            return False, f"unknown tool: {env.tool}"
        pol: Policy = env.policy or Policy()
        # Map entry.risk (string) to enum for policy check.
        risk = RiskClass(entry.risk)
        code_mode = CodeMode.SAFE  # default; dispatcher may be told otherwise
        ok, msg = self.policy.validate_operation(risk, code_mode, pol.allow_arbitrary_code)
        if not ok:
            return False, msg
        # Houdini graph paths (usually named `path` or `node_path`) are not filesystem
        # paths. Only explicitly file-oriented arguments go through root allowlisting.
        for key in (
            "output_path",
            "output_dir",
            "file_path",
            "dest_dir",
            "checkpoint_dir",
            "log_path",
            "manifest_path",
            "result_path",
            "scene_path",
        ):
            if key in env.arguments:
                p_ok, p_msg = self.policy.check_path(str(env.arguments[key]))
                if not p_ok:
                    return False, p_msg
        # Approval gate for medium+ risk.
        if not approval_granted and risk in (RiskClass.MEDIUM, RiskClass.HIGH, RiskClass.EXTERNAL):
            return False, f"approval required for risk={risk.value}"
        return True, ""

    # --- execution (requires Houdini for HOM tools) --------------------
    def process_one(
        self, env: CommandEnvelope | None = None, approval_granted: bool = False
    ) -> DispatchOutcome:
        env = env or self.queue.get_nowait()
        if not env.request_id:
            env.request_id = uuid.uuid4().hex
        if env.tool in {"approval.list", "approval.grant", "approval.deny"}:
            return self._process_approval_command(env)

        ok, msg = self.validate(env, approval_granted=approval_granted)
        result = ToolResult(request_id=env.request_id, status=Status.SUCCESS)
        if not ok:
            result.status = Status.BLOCKED
            result.errors.append(msg)
            entry = REGISTRY.resolve(env.tool)
            if entry is not None and msg.startswith("approval required"):
                approval = self.approvals.request(env, RiskClass(entry.risk))
                result.data["approval"] = {
                    "approval_id": approval.approval_id,
                    "tool": env.tool,
                    "risk": approval.risk.value,
                    "expires_in_seconds": self.approvals.ttl_seconds,
                }
            return DispatchOutcome(result, env)
        entry = REGISTRY.resolve(env.tool)
        token = set_current_envelope(env)
        try:
            out = entry.handler(**env.arguments)
            if isinstance(out, ToolResult):
                out.request_id = env.request_id
                return DispatchOutcome(out, env)
            if isinstance(out, dict):
                result.data = out
            elif isinstance(out, list):
                result.data = {"items": out}
            return DispatchOutcome(result, env)
        except Exception as exc:  # surface structurally
            result.status = Status.ERROR
            result.errors.append(f"{type(exc).__name__}: {exc}")
            return DispatchOutcome(result, env)
        finally:
            reset_current_envelope(token)

    def _process_approval_command(self, env: CommandEnvelope) -> DispatchOutcome:
        result = ToolResult(request_id=env.request_id, status=Status.SUCCESS)
        try:
            if env.tool == "approval.list":
                result.data = {"pending": self.approvals.describe()}
                return DispatchOutcome(result, env)
            approval_id = str(env.arguments.get("approval_id", ""))
            if not approval_id:
                raise ValueError("approval_id is required")
            if env.tool == "approval.deny":
                denied = self.approvals.deny(approval_id)
                result.data = {
                    "approval_id": approval_id,
                    "decision": "denied",
                    "denied_request_id": denied.envelope.request_id,
                }
                return DispatchOutcome(result, env)
            if env.tool == "approval.grant":
                approved = self.approvals.take(approval_id)
                outcome = self.process_one(approved.envelope, approval_granted=True)
                outcome.result.data.setdefault("approval", {})
                outcome.result.data["approval"].update(
                    {
                        "approval_id": approval_id,
                        "decision": "granted",
                    }
                )
                return DispatchOutcome(outcome.result, env)
            raise ValueError(f"unknown approval command: {env.tool}")
        except Exception as exc:
            result.status = Status.ERROR
            result.errors.append(f"{type(exc).__name__}: {exc}")
            return DispatchOutcome(result, env)

    # --- event-loop hook (call from hou.ui.addEventLoopCallback) -------
    def pump(self, max_commands: int = 4) -> list[DispatchOutcome]:
        """Process a bounded number of queued commands. Cheap; safe for event loop."""
        outcomes: list[DispatchOutcome] = []
        for _ in range(max_commands):
            try:
                env = self.queue.get_nowait()
            except queue.Empty:
                break
            outcomes.append(self.process_one(env))
        return outcomes


__all__ = [
    "ApprovalStore",
    "Dispatcher",
    "DispatchOutcome",
    "PendingApproval",
    "DEFAULT_QUEUE",
]
