# Grinder Lane G002-B — Contract Adapter Registry

## Mission

Implement a pure registry for versioned project contract-adapter descriptors. Descriptors explain
how one named output contract may connect to another through an exact registered recipe or explicit
native fallback. This lane records composition knowledge; it does not execute recipes, inspect
Houdini, synthesize adapters, or silently prefer plugin/creative alternatives.

## Frozen execution contract

- Cycle state at dispatch: `ACCEPTED`
- Repository: `mlflautt/Houdini-Lab`
- Local root: `/Users/m1/houdini-g002-b`
- Base tag/commit: exact accepted values from `CYCLE_MANIFEST.md`
- Branch: `codex/grinder-g002-b-contract-adapters`
- Runtime: pure Python; H22.0.368 regression only
- License baseline: Houdini Apprentice non-commercial
- Depends on other lanes: none
- Merge authority: integration captain only

Stop on dirty/wrong base, placeholder manifest, or any need to change the recipe parser/catalog.

## Read before editing

Read `AGENTS.md`, architecture §5/§10, Horizon 3, the G002 manifest, this brief,
`recipes/{README.md,parser.py,catalog.py}`, `hermes_houdini/capabilities.py`, and the exact World
Seed, Material Foundry, Botanical Grammar, and Particle Calligraphy skill manifests. Treat every
sibling-lane path and existing recipe/skill as read-only.

## Startup preflight

Run repository identity/clean/base/remote checks, `gh`/SSH preflight, full pure tests, and Ruff
exactly as in Lane A.
If a documented capability/recipe version is absent, stop and report rather than inventing it.

## Owned paths

- `hermes_houdini/project_adapters.py`
- `project_contracts/__init__.py`
- `project_contracts/adapters/*.yaml`
- `project_contracts/README.md`
- `tests/unit/test_project_adapters.py`
- `docs/project-contract-adapters.md`
- `docs/grinder/receipts/G002-B.md`

Package-data registration is integration-owned. Do not edit recipes, skills, registries, exports,
pyproject, compiler/spec/observer, CLI, root docs, workflows, or another receipt.

## Required API and descriptor contract

Expose pure behavior equivalent to:

```text
normalize_adapter_record(value: Mapping, *, source: str = "") -> dict
load_adapter_record(path: str | Path) -> dict
build_adapter_registry(paths: Iterable[str | Path]) -> dict
resolve_adapter(registry: Mapping, *, from_contract: str, to_contract: str,
                version: str, build: str, license_mode: str,
                allowed_dependencies: Iterable[str]) -> dict
```

Every descriptor uses `hermes.houdini.project_adapter.v1` and the manifest fields. Exact semver is
mandatory. One—and only one—of exact `recipe` or named `native_fallback` is present. A descriptor
may state `evidence_status: pending`; registry presence is not certification. Canonical registry
order is `(adapter_id, version, source)` and includes a content SHA-256.

Resolution never uses latest, fuzzy names, aesthetic ranking, first-match, or plugin preference.
Return structured `resolved`, `missing`, `ambiguous`, or `incompatible` results with all candidate
identities. Build, license, optional dependency, context, risk, approval, fallback, and budget-effect
information must survive unchanged.

Create a small declarative set sufficient for the future dry Living Biome plan: world geometry to
Solaris import, procedural PBR channels to named material bindings, botanical geometry to a world
layer contract, and one motion geometry to a world layer contract. Point only to exact existing
recipes when their real declared contract fits. Otherwise name a future native fallback and mark
runtime evidence `pending`; never claim nonexistent execution proof. A future fallback name is a
required implementation dependency for G003, not executable G002 functionality.

## Implementation sequence

1. Audit exact existing recipe/skill IDs, versions, outputs, contexts, builds, dependencies, and
   risks; record the source path in each descriptor.
2. Add strict normalization and deterministic registry/hash behavior.
3. Test exact resolution plus duplicate, ambiguous, build/license, missing dependency, plugin
   fallback, malformed descriptor, and nondeterministic input-order cases.
4. Document why adapters are contract metadata rather than hidden executable code.
5. Run all gates and commit the receipt.

## Acceptance gates

```bash
.venv/bin/python -m pytest tests/unit/test_project_adapters.py -o addopts='' -q
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

All pure gates must pass. Hython/live/visual execution is `not_applicable`; source manifest audit is
not a live adapter claim.

## Receipt and handoff

Commit, push, and open the component PR with `G002-B.md`. Report exact descriptor IDs/versions,
registry hash, source audits, tests, all unresolved runtime evidence, and the integration-owned
package-data seam. Do not merge.

## Stop conditions and non-goals

Stop if a required connection needs a new actual graph recipe, cross-lane import, recipe-parser
change, plugin installation, Hython probe, or unverified capability claim. Those belong to an
amendment, integration, or G003—not an improvised descriptor.
