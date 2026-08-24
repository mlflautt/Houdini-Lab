"""scripts/123.py — Houdini startup autostart (GUI only).

Fires on every Houdini launch (registered by the package). Starts the authenticated
interactive runtime and event-loop dispatcher. Headless (hython) is detected and skipped.
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
    try:
        from bridge.auth import load_secret
        from hermes_houdini.dispatcher import Dispatcher
        from hermes_houdini.policy import default_policy
        from hermes_houdini.runtime import InteractiveRuntime

        existing = getattr(hou.session, "hermes_runtime", None)
        if existing is not None and existing.is_running:
            return
        port = int(os.environ.get("HERMES_HOUDINI_INTERNAL_PORT", "8766"))
        roots = [
            root
            for root in os.environ.get("HERMES_HOUDINI_ALLOWED_ROOTS", "").split(os.pathsep)
            if root
        ]
        runtime = InteractiveRuntime(
            secret=load_secret(),
            port=port,
            dispatcher=Dispatcher(policy=default_policy(roots)),
        )
        runtime.start()

        def pump() -> None:
            runtime.pump(max_commands=4)

        hou.ui.addEventLoopCallback(pump)
        # Dynamic hou.session attributes persist for this process but are not saved
        # into the HIP, which makes them suitable for runtime handles.
        hou.session.hermes_runtime = runtime
        hou.session.hermes_runtime_callback = pump
        hou.session.hermes_runtime_error = ""
        hou.ui.setStatusMessage(f"Hermes Houdini runtime listening on 127.0.0.1:{runtime.port}")
    except Exception as exc:
        # Never abort Houdini startup, but keep the failure inspectable.
        hou.session.hermes_runtime_error = f"{type(exc).__name__}: {exc}"


if __name__ == "__main__":
    main()
else:
    main()
