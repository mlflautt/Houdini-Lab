# Apprentice constraints (summary)

Every tool, project manifest, cache, asset, render, and publish operation must stay aware of
the Apprentice license boundary. See `docs/architecture.md` §8 for full detail.

| Constraint | Value |
|------------|-------|
| Commercial use | **No** |
| Scene format | `.hipnc` |
| HDA format | `.hdanc` |
| HDAs with Houdini Engine | **Not allowed** |
| Third-party renderers | **Not allowed** (Karma CPU / Mantra only) |
| Renders | Restricted + watermarked |
| License | Node-locked (not floatable) |
| Render resolution ceiling | **1280×720** (conservative; verify installed build) |

## Enforcement in this repo
- `hermes_houdini/policy.py::ApprenticePolicy` is the single source of truth.
- `validate_render_resolution()` rejects above ceiling.
- `is_path_allowed()` / `check_path()` enforce approved roots (fail-closed).
- `hda.create_from_subnet` marks `noncommercial` userData.
- Project `project.toml` records `[license]` block (see `projects/template`).

## Upgrade path
Keep tool logic independent of `.hipnc` naming, isolate license checks, don't hard-code
render ceilings in skills. Moving to Indie/FX later must remain possible — but do **not**
automate license conversion.
