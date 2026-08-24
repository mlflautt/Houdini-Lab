"""Apprentice/license/path/risk policy (pure Python, no Houdini).

Centralizes every constraint the agent must respect so tool logic stays policy-free.
Pinned conservative defaults per docs/architecture.md §8.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field

from .schemas.command import CodeMode, RiskClass

# SideFX docs conflict on the Apprentice ceiling (1280x720 vs 1920x1080).
# Use the conservative value until the installed build is capability-checked.
APPRENTICE_DEFAULT_RESOLUTION = (1280, 720)
APPRENTICE_NONCOMMERCIAL = True


@dataclass
class ApprenticePolicy:
    """License + path + resolution policy. Source of truth for what is allowed."""

    license_mode: str = "houdini-apprentice-noncommercial"
    commercial_use: bool = False
    scene_extension: str = ".hipnc"
    hda_extension: str = ".hdanc"
    watermarked_renders: bool = True
    engine_export_allowed: bool = False
    third_party_renderer_allowed: bool = False
    render_ceiling: tuple[int, int] = APPRENTICE_DEFAULT_RESOLUTION
    allowed_roots: list[str] = field(default_factory=list)

    def add_allowed_root(self, root: str) -> None:
        root = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
        if root not in self.allowed_roots:
            self.allowed_roots.append(root)

    # --- license checks -------------------------------------------------
    def is_noncommercial(self) -> bool:
        return not self.commercial_use

    def validate_render_resolution(self, w: int, h: int) -> tuple[bool, str]:
        cw, ch = self.render_ceiling
        ok = (w <= cw) and (h <= ch)
        msg = "" if ok else (f"Resolution {w}x{h} exceeds Apprentice ceiling {cw}x{ch}.")
        return ok, msg

    def validate_operation(
        self, risk: RiskClass, code_mode: CodeMode, allow_arbitrary_code: bool
    ) -> tuple[bool, str]:
        # Registered external tools are part of safe mode's narrow allowlist. They still
        # require exact dispatcher approval and must enforce allow_external_process.
        if risk == RiskClass.HIGH and code_mode == CodeMode.SAFE:
            return False, f"Risk {risk.value} not permitted in safe mode."
        if allow_arbitrary_code and code_mode == CodeMode.SAFE:
            return False, "Arbitrary code disabled in safe mode."
        if allow_arbitrary_code and code_mode != CodeMode.PRIVILEGED_LOCAL:
            return False, "Arbitrary code only in privileged_local mode."
        if risk == RiskClass.EXTERNAL and not self.commercial_use:
            # external ops are allowed but must be gated by approval upstream
            return True, "external op allowed (approval required by dispatcher)"
        return True, ""

    # --- path checks ----------------------------------------------------
    def is_path_allowed(self, path: str) -> bool:
        if not self.allowed_roots:
            # No roots configured: deny by default (fail-closed).
            return False
        ap = os.path.realpath(os.path.abspath(os.path.expanduser(path)))
        return any(ap == r or ap.startswith(r + os.sep) for r in self.allowed_roots)

    def check_path(self, path: str) -> tuple[bool, str]:
        ok = self.is_path_allowed(path)
        return ok, "" if ok else f"Path '{path}' outside approved roots."

    def capability_report(self) -> dict:
        return {
            "license_mode": self.license_mode,
            "commercial_use": self.commercial_use,
            "scene_extension": self.scene_extension,
            "hda_extension": self.hda_extension,
            "watermarked_renders": self.watermarked_renders,
            "engine_export_allowed": self.engine_export_allowed,
            "third_party_renderer_allowed": self.third_party_renderer_allowed,
            "render_ceiling": list(self.render_ceiling),
            "allowed_roots": list(self.allowed_roots),
        }


def default_policy(allowed_roots: Iterable[str] = ()) -> ApprenticePolicy:
    p = ApprenticePolicy()
    for r in allowed_roots:
        p.add_allowed_root(r)
    return p
