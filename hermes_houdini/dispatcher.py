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
from dataclasses import dataclass

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


class Dispatcher:
    """Bounded command processor. Safe to construct without Houdini."""

    def __init__(self, policy: ApprenticePolicy | None = None,
                 queue: queue.Queue[CommandEnvelope] | None = None) -> None:
        self.policy = policy or ApprenticePolicy()
        self.queue: queue.Queue[CommandEnvelope] = queue or DEFAULT_QUEUE
        self.pending: list[CommandEnvelope] = []
        self.approval_required: list[str] = []  # request_ids needing approval

    # --- intake ---------------------------------------------------------
    def enqueue(self, env: CommandEnvelope) -> None:
        self.queue.put(env)

    # --- validation (no Houdini) ---------------------------------------
    def validate(self, env: CommandEnvelope) -> tuple[bool, str]:
        if not env.tool:
            return False, "missing tool name"
        entry = REGISTRY.resolve(env.tool)
        if entry is None:
            return False, f"unknown tool: {env.tool}"
        pol: Policy = env.policy or Policy()
        # Map entry.risk (string) to enum for policy check.
        risk = RiskClass(entry.risk)
        code_mode = CodeMode.SAFE  # default; dispatcher may be told otherwise
        ok, msg = self.policy.validate_operation(
            risk, code_mode, pol.allow_arbitrary_code
        )
        if not ok:
            return False, msg
        # Path check on any explicit output roots in arguments.
        for key in ("output_path", "path", "file_path"):
            if key in env.arguments:
                p_ok, p_msg = self.policy.check_path(str(env.arguments[key]))
                if not p_ok:
                    return False, p_msg
        # Approval gate for medium+ risk.
        if risk in (RiskClass.MEDIUM, RiskClass.HIGH, RiskClass.EXTERNAL):
            self.approval_required.append(env.request_id)
            return False, f"approval required for risk={risk.value}"
        return True, ""

    # --- execution (requires Houdini for HOM tools) --------------------
    def process_one(self, env: CommandEnvelope | None = None) -> DispatchOutcome:
        env = env or self.queue.get_nowait()
        ok, msg = self.validate(env)
        result = ToolResult(request_id=env.request_id, status=Status.SUCCESS)
        if not ok:
            result.status = Status.BLOCKED
            result.errors.append(msg)
            return DispatchOutcome(result, env)
        entry = REGISTRY.resolve(env.tool)
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


__all__ = ["Dispatcher", "DispatchOutcome", "DEFAULT_QUEUE"]
