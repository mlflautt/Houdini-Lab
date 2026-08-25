"""Per-command execution context available to registered tool handlers."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from .schemas.command import CommandEnvelope

_CURRENT_ENVELOPE: ContextVar[CommandEnvelope | None] = ContextVar(
    "hermes_current_envelope", default=None
)
_CURRENT_RUNTIME_STATE: ContextVar[dict[str, Any] | None] = ContextVar(
    "hermes_current_runtime_state", default=None
)


def current_envelope() -> CommandEnvelope | None:
    return _CURRENT_ENVELOPE.get()


def current_runtime_state() -> dict[str, Any]:
    """Return dispatcher-owned, read-only state visible to the active tool call."""
    return dict(_CURRENT_RUNTIME_STATE.get() or {})


def set_current_envelope(envelope: CommandEnvelope) -> Token:
    return _CURRENT_ENVELOPE.set(envelope)


def reset_current_envelope(token: Token) -> None:
    _CURRENT_ENVELOPE.reset(token)


def set_current_runtime_state(state: dict[str, Any]) -> Token:
    return _CURRENT_RUNTIME_STATE.set(dict(state))


def reset_current_runtime_state(token: Token) -> None:
    _CURRENT_RUNTIME_STATE.reset(token)


__all__ = [
    "current_envelope",
    "current_runtime_state",
    "reset_current_envelope",
    "reset_current_runtime_state",
    "set_current_envelope",
    "set_current_runtime_state",
]
