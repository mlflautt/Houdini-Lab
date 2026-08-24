# Sprint 20 — SideFX Labs integration

Sprint 20 makes optional Houdini plugins auditable and reversible before they become creative
dependencies. It does not treat a successful package load as certification of the entire catalog.
The certified surface is always the exact nodes exercised by bounded fixture graphs.

## Pinned candidate

The official SideFX package index was re-queried on 2026-08-24. The selected package is the
**SideFX Labs 22.0 Production Build**, version `22.0.368`, because it exactly matches the installed
Houdini `22.0.368` production build. The available `22.0.421` daily package is intentionally not
selected.

| Field | Pinned value |
|---|---|
| Package | `SideFXLabs22.0` |
| Version | `22.0.368` |
| Download bytes | `199090831` |
| Installed bytes | `326876190` |
| Checksum | `sha-256=mkoIk692DUaxIis/+6UUhGETyoSB5Hpl2lO1s8dOh9U=` |
| Target | macOS arm64, Houdini 22.0.368, Apprentice |
| Install scope | `$HOUDINI_USER_PREF_DIR/packages` |
| Disable launch | `HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json` |

The repository record is [`../plugins/sidefx-labs-22.0.368.json`](../plugins/sidefx-labs-22.0.368.json).
It conservatively declares possible native binaries, network access, and external executables
because Labs is a large mixed toolset. A fixture may prove that a selected node does not use those
capabilities; the package-level record must not imply that every tool is offline or pure HDA code.
The upstream `LICENSE.md` has permissive BSD-like terms and is recorded by name rather than assigned
an uncertain SPDX identifier.

## Implemented repository gate

`hermes_houdini.plugin_registry` is pure Python and performs no install or plugin load. It provides:

- strict manifest validation for exact build, OS, architecture, license modes, permissions,
  checksums, rollback, and bounded fixtures;
- a central Apprentice policy that blocks renderer and Engine plugin classes, conditions native
  binaries on ABI/platform/signature checks, and permits graph-visible non-binary tools as candidates;
- read-only Houdini package JSON auditing with hashes and enabled-state capture;
- installed-tree inventory for HDAs, Python, VEX, viewer states, shelves, and native binaries;
- refusal to follow a symlink that escapes the declared plugin root.

`scripts/audit_houdini_plugin.py` exposes these checks without importing Houdini.
`scripts/probe_sidefx_labs.py` is the Hython-side read-only startup and node inventory probe.

## Measured pre-install baseline

The live Hython probe ran against Houdini 22.0.368 Apprentice before installation. It found only
three preexisting `labs::` node types shipped with the base application: two ZibraVDB SOPs and one
ZibraVDB LOP. No full `SideFXLabs22.0` package was registered. The compact evidence record is
[`../plugins/evidence/sidefx-labs-preinstall-22.0.368.json`](../plugins/evidence/sidefx-labs-preinstall-22.0.368.json).

An in-sandbox Hython attempt hit the known Apple-silicon Qt/NEON false failure; the approved native
read-only launch then completed cleanly. This environmental failure is not attributed to Labs.

## Installed package audit

The user explicitly approved installation on 2026-08-24. The older 22.0.368 Installer could see
the live package index but failed to disambiguate the production and daily packages sharing the
name `SideFXLabs22.0`. Its `--offline-installer` option expected a full Houdini ISO wrapper rather
than the package ZIP. The exact production archive was therefore downloaded from the signed URL in
SideFX's official index, verified against the pinned base64 and hex SHA-256 values, audited for ZIP
traversal and exact top-level entries, then extracted without overwrite into Houdini's supported
user package directory. The root-owned application bundle was not modified.

The installed audit reports 2,087 files, one HDA library, 74 Python files, three viewer-state files,
ten shelf files, and three native binaries. All three binaries are Windows x86-64 DLLs; no macOS DSO
is present or loaded. The package JSON is enabled only for Houdini 22.0 and resolves its content
through `$HOUDINI_PACKAGE_PATH`.

## Node inventory and certified fixtures

Enabled startup completed cleanly under Houdini 22.0.368 Apprentice and exposed 450 matching node
types: 416 SOP, 18 TOP, nine LOP, four OBJ, two DOP, and one COP. This inventory is descriptive, not
a catalog-wide certification.

Exactly three graph-visible node types are certified:

| Fixture | Exact Labs type | Observed contract | Cook |
|---|---|---|---|
| Artifact curvature | `labs::measure_curvature::3.1` | 1,152 points; `Cd`, `concavity`, `convexity` | 0.250 s |
| Terrain cartography | `labs::terrain_analysis::1.0` | 4,225 points; `Cd`, `slope` | 0.160 s |
| Motion/instancing | `labs::instance_attributes::1.0` | 64 points; `orient`, `pscale`, `scale` | 0.154 s |

The source-of-truth graphs are
[`../recipes/sop/sidefx_labs_acceptance_gallery.yaml`](../recipes/sop/sidefx_labs_acceptance_gallery.yaml)
and [`../recipes/lop/sidefx_labs_acceptance_stage.yaml`](../recipes/lop/sidefx_labs_acceptance_stage.yaml).
They preserve native sources and downstream nodes, named output contracts, stable Hermes roles,
explicit seeds, and empty human ratings. The Hython runner is
[`../scripts/run_sprint20_acceptance.py`](../scripts/run_sprint20_acceptance.py).

The final gallery contains 6,657 points and 4,865 primitives. The first render correctly triggered
a crop warning; the recipe was refined with a diagnostic torus, watermark-safe elevations, and a
wider camera. The final 768x432 Karma CPU image passed blank/exposure, three-panel presence, and
crop checks with no flags. No aesthetic winner is authored.

## Verified disable and removal boundary

Houdini 22.0.368 did not honor the extensionless value
`HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0`, despite current documentation describing basename
matching. Both the exact filename and absolute path forms worked. The verified reversible launch is:

```bash
HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json hython
```

That launch returned the Labs inventory from 450 types to the three base ZibraVDB types and exited
cleanly. Removing the installed package is a separate destructive operation: delete or quarantine
only `SideFXLabs22.0.json` and `SideFXLabs22.0/` under `$HOUDINI_USER_PREF_DIR/packages` after a new
explicit approval.

The compact committed result is
[`../plugins/evidence/sidefx-labs-acceptance-22.0.368.json`](../plugins/evidence/sidefx-labs-acceptance-22.0.368.json).
Full local evidence includes the `.hipnc`, graph SVGs, package inventories, validation manifests,
render, deterministic visual report, and hashed critique packet under
`.hermes/sprint20-acceptance-20260824-c/`.

Sprint 20 closure passed 133 pure-Python tests with four environment-gated skips, all 30 Hython
integration tests, Ruff, diff whitespace validation, and a `0.20.0` wheel build. Sprint 20.1 then
normalized every bundled skill manifest to JSON-compatible YAML and added a standard-library JSON
fallback to the skill loader. Bare Hython no longer needs PyYAML or an injected `PYTHONPATH`.

## Sprint result

Sprint 20 is complete in package `0.20.0`. Labs is an optional, reversible construction dependency;
only the three exact node types above are certified. Sprint 21 subsequently reused exactly those
types in capability-gated World Seed branches while retaining a functioning native-only launch.
See [`labs-enhanced-world-seed-atlas.md`](labs-enhanced-world-seed-atlas.md).

## Sources

- [SideFX Labs package installation](https://www.sidefx.com/docs/houdini/licensing/install_labs_packages.html)
- [Houdini Installer command reference](https://www.sidefx.com/docs/houdini/ref/utils/installer.html)
- [SideFX Labs product page](https://www.sidefx.com/products/sidefx-labs/)
- [SideFX Labs source and license](https://github.com/sideeffects/SideFXLabs)
