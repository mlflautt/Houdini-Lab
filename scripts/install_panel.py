"""scripts/install_panel.py — one-time Python Panel registration.

Run from Houdini's Python Shell:
    exec(open(r"/path/to/houdini-creative-dev/scripts/install_panel.py").read())
"""

from __future__ import annotations


def install() -> str:
    import hou

    pypanel = "/path/to/houdini-creative-dev/panels/hermes_houdini.pypanel"
    # Register the panel definition; user picks New Pane Tab Type > Hermes Houdini.
    try:
        hou.ui.registerPaneTabType("Hermes Houdini", pypanel)
        return "registered Hermes Houdini panel"
    except Exception as exc:  # API varies by build
        return f"panel registration skipped: {exc}"


if __name__ == "__main__":
    print(install())
else:
    try:
        print(install())
    except Exception:
        pass
