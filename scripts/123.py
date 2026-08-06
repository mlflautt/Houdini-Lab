"""scripts/123.py — Houdini startup autostart (GUI only).

Fires on every Houdini launch (registered by the package). Starts the in-Houdini
dispatcher and registers the Python panel. Headless (hython) is detected and skipped.
"""
from __future__ import annotations


def main() -> None:
    try:
        import hou
    except ImportError:
        return  # not inside Houdini
    # Skip headless (hython/hbatch): autostart is GUI-only.
    if getattr(hou, "isUIAvailable", lambda: True)() is False:
        return
    import os

    if os.environ.get("HERMES_HOUDINI_AUTOSTART", "1") == "0":
        return
    # The dispatcher is lazy; starting it just wires the event-loop pump.
    try:
        from hermes_houdini.dispatcher import Dispatcher
        from hermes_houdini.policy import ApprenticePolicy

        disp = Dispatcher(policy=ApprenticePolicy())
        # Register a bounded event-loop callback (docs §12.6) if available.
        if hasattr(hou.ui, "addEventLoopCallback"):
            hou.ui.addEventLoopCallback(lambda: disp.pump(max_commands=4))
    except Exception:
        pass  # never break Houdini startup


if __name__ == "__main__":
    main()
else:
    main()
