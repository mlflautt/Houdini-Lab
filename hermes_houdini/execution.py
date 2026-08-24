"""Per-command execution context available to registered tool handlers."""

from __future__ import annotations

from contextvars import ContextVar, Token

from .schemas.command import CommandEnvelope

_CURRENT_ENVELOPE: ContextVar[CommandEnvelope | None] = ContextVar(
    "hermes_current_envelope", default=None
)


def current_envelope() -> CommandEnvelope | None:
    return _CURRENT_ENVELOPE.get()


def set_current_envelope(envelope: CommandEnvelope) -> Token:
    return _CURRENT_ENVELOPE.set(envelope)


def reset_current_envelope(token: Token) -> None:
    _CURRENT_ENVELOPE.reset(token)


__all__ = ["current_envelope", "reset_current_envelope", "set_current_envelope"]
