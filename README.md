# Houdini Creative Dev

A local-first **agentic Houdini development repository** for building Hermes-driven
Houdini skills and creative procedural projects — graph-first, Apprentice/non-commercial
aware, and built so the node graph stays the primary executable artifact.

This repo hosts:
- the **Hermes↔Houdini bridge** (outside-Houdini authenticated process + small inside-Houdini package),
- **graph recipes** (declarative, versioned subgraphs),
- **HDAs** (`.hdanc` source-of-truth via build scripts + tests),
- **VEX templates** (approved, curated wrangle snippets),
- **agentic skills** (manifest + module that compose tools/recipes into creative procedures),
- **creative project scaffolding** (`projects/template`).

> **Source of truth for design:** [`docs/architecture.md`](docs/architecture.md) — the
> *Hermes Houdini Apprentice: Agentic Architecture and Development Guide*, integrated here.

---

## Architecture

```
Hermes conversation / project agent
        │ intent, references, constraints, approvals
        v
Hermes Houdini Orchestrator
  - procedural planner · recipe selector · context resolver
  - Apprentice policy gate · cook/render budget manager · provenance
        │ structured tool calls
        v
Local Bridge Process (outside Houdini)
  - localhost transport · schema validation · session auth
  - path allowlists · timeouts/cancellation · log aggregation
        │ bounded JSON commands
        v
Hermes Houdini Package (inside Houdini)
  - event-loop dispatcher · tool/recipe registry · stable-ID service
  - checkpoint manager · cook/cache controller · visual observer · validation
        ├──────────────┬──────────────┬──────────────┐
        v              v              v              v
Interactive Houdini  hython/background  PDG/TOP local   Project artifacts
                   jobs               jobs           (.hipnc/.hdanc/
                                                    renders/caches/USD)
```

Transport is kept separate from Houdini semantics: every operation is an ordinary typed
Python function, callable through MCP, a CLI harness, `hython` integration tests, a Python
Panel, or direct import.

---

## Quick start

### 1. Clone + install dev tooling
```bash
git clone https://github.com/mlflautt/houdini-creative-dev.git
cd houdini-creative-dev
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"      # ruff, pytest
```

### 2. Wire the Houdini package (inside Houdini 22, Apprentice/Indie/FX)
Install the package JSON so Houdini finds the Python lib + startup script:
```bash
# packages/hermes_houdini.json lives in ~/Library/Preferences/houdini/X.Y/packages/
# or point HOUDINI_PATH at the repo root. See packages/hermes_houdini.json.
```
On launch, `scripts/123.py` starts the in-Houdini dispatcher and registers the panel.

### 3. Run the outside-Houdini bridge (optional, for remote/agent use)
```bash
python -m bridge.server --port 8765   # binds 127.0.0.1, requires session secret
python -m bridge.client --port 8765    # from the agent side
```

### 4. Tests
```bash
pytest tests/unit -q                  # pure Python, no Houdini needed
pytest tests/hython -q                # requires hython on PATH (skipped otherwise)
```

---

## Repository layout

| Path | Purpose |
|------|---------|
| `hermes_houdini/` | Inside-Houdini package: dispatcher, registry, inspector, transactions, cook, observation, validation, policy, stable IDs, tool impls |
| `bridge/` | Outside-Houdini authenticated JSON transport (server/client/auth) |
| `recipes/` | Declarative graph recipes (YAML) |
| `skills/` | Agentic skills: manifest + module + shared `_lib` |
| `hda/` | HDA source-of-truth (build scripts) + regression tests |
| `vex/` | Approved VEX templates |
| `panels/` | Minimal Hermes Python Panel |
| `scripts/` | `123.py` autostart, `install_panel.py` |
| `packages/` | `hermes_houdini.json` Houdini package definition |
| `tests/` | `unit/` (no Houdini), `hython/` (needs Houdini), `fixtures/` |
| `projects/template/` | Project skeleton (`project.toml` + folders) |
| `docs/` | Integrated architecture guide + conventions + apprentice constraints + curriculum |
| `manifests/` | Capability + provenance manifests |

---

## License & Apprentice note

Code here is **MIT** licensed. However, any Houdini scene (`.hipnc`) or HDA (`.hdanc`)
**produced** through this system remains governed by the **Houdini Apprentice /
Non-Commercial** license: non-commercial use only, watermarked renders, HDAs not usable
with Houdini Engine, no third-party renderers. Keep `license.mode` explicit in every
project manifest and never imply an export removes that restriction.

See [`docs/apprentice-constraints.md`](docs/apprentice-constraints.md).
