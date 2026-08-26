# Grinder Cycle G002 — Horizon 3 Project Compiler Kernel

- State: `PROPOSED — DO NOT LAUNCH`
- Manifest version: `1.0-draft`
- Proposed on: `2026-08-26`
- Target horizon: Horizon 3, project compiler and compositional graphs
- Repository: `mlflautt/Houdini-Lab`
- Candidate base tag: `v0.35.0` (`PENDING PUBLICATION — DO NOT LAUNCH`)
- Candidate base commit: `8bb50a9a78bd870ba0d256fbb52c7aa904d21efa`
- Integration branch after acceptance: `codex/grinder-g002-integration`
- Target runtime: pure Python 3.11+; regression on Houdini Apprentice 22.0.368
- Release intent: compiler foundation for the `v0.40` band; no package-version promise

## Acceptance boundary

This proposal is reviewable but not dispatchable. The owner must first authorize and verify
publication of tag `v0.35.0` at the exact candidate base commit above, then accept this manifest.
Acceptance will change the candidate fields to a frozen base without changing lane scope. No lane
may begin from PR head `f45a55f422f93f39f21a120c4142e21a7384129f` or an arbitrary newer `main`.

## Outcome

Create the pure, deterministic project-contract kernel that can turn a human-readable multi-skill
project specification into a reviewable, checkpointed execution DAG and coherent evidence/drift
index. G002 plans projects but does not mutate Houdini. The first integrated fixture dry-compiles
the future Living Biome Shot with three equal-status directions and blank human-owned decisions.

G002 exists to freeze stable composition contracts before the live G003 project. It must not hide
skill graphs behind a monolithic Python builder or treat a valid plan as runtime/visual proof.

## Required integrated deliverables

1. Versioned `hermes.houdini.project.v1` specification parsing and canonical hashing.
2. Versioned, declarative contract-adapter records that point to registered recipes or explicit
   native fallbacks without executing them.
3. A deterministic compiler that resolves capability instances and adapters into an acyclic,
   checkpointed dry DAG with budgets, approvals, contexts, outputs, and evidence gates.
4. A project observer/drift index schema spanning planned nodes/contracts, artifacts, evidence,
   runtime compatibility, unresolved human decisions, and preserved alternatives.
5. One integration CLI that performs `validate`, `plan`, or `observe` only; the default is help and
   no command cooks, mutates a graph, starts Houdini, or creates an artifact unless an explicit
   fresh output path is supplied.
6. A dry Living Biome specification selecting exact existing capability versions while retaining
   three named biome variants, `human_rating: null`, `selected_for_continuation: null`, and no winner.
7. Complete pure tests, clean import without Houdini, full regression tests, documentation, and
   committed lane/integration receipts.

## Non-goals

- No Houdini graph mutation, cook, simulation, PDG child, viewport capture, or Karma render.
- No new creative skill, HDA, VEX template, plugin, bridge surface, runner, or arbitrary code mode.
- No execution scheduler, background worker, automatic resume, cache write, or artist-scene edit.
- No automatic adapter synthesis, creative ranking, winner, human rating, or taste score.
- No G003 implementation, package tag/release, workflow change, or public runner activation.
- No requirement that different Houdini cooks be byte-identical; compiler hashes cover canonical
  plans and declared source identities only.

## Lane DAG

```text
frozen G001 base
  +-- G002-A project specification --------+
  +-- G002-B contract adapter registry ----+--> G002-I integration --> dry Living Biome plan
  +-- G002-C deterministic DAG compiler ---+
  +-- G002-D observer and drift index ------+
```

All four lanes are independent. A lane consumes only the frozen plain-mapping contracts below,
never another lane branch. Integration performs imports and the end-to-end pipeline wiring.

## Ownership matrix

| Lane | Owned implementation paths | Owned tests/docs | Must not edit |
|---|---|---|---|
| A | `hermes_houdini/project_spec.py` | `tests/unit/test_project_spec.py`, `tests/fixtures/projects/g002-*.yaml`, `docs/project-specification.md`, `docs/grinder/receipts/G002-A.md` | adapters, compiler, observer, shared metadata |
| B | `hermes_houdini/project_adapters.py`, `project_contracts/__init__.py`, `project_contracts/adapters/*.yaml` | `tests/unit/test_project_adapters.py`, `project_contracts/README.md`, `docs/project-contract-adapters.md`, `docs/grinder/receipts/G002-B.md` | spec, compiler, observer, recipe parser, shared metadata |
| C | `hermes_houdini/project_compiler.py` | `tests/unit/test_project_compiler.py`, `docs/project-compiler.md`, `docs/grinder/receipts/G002-C.md` | spec, adapters, observer, execution/runtime modules, shared metadata |
| D | `hermes_houdini/project_observer.py` | `tests/unit/test_project_observer.py`, `docs/project-observer.md`, `docs/grinder/receipts/G002-D.md` | spec, adapters, compiler, live observation/HOM, shared metadata |
| I | `hermes_houdini/project_pipeline.py`, `scripts/plan_project.py`, `tests/unit/test_project_pipeline.py`, `projects/living_biome/*` | package exports/data, root docs, roadmap, release/cycle metadata, `docs/grinder/receipts/G002-I.md` | lane history and inferred evidence |

Paths in braces or globs are narrow ownership declarations. Existing files are read-only unless
listed. Every lane may create only its own receipt in `docs/grinder/receipts/`.

## Frozen cross-lane contracts

All public boundaries are plain JSON-shaped mappings and import without Houdini.

### Normalized project specification

Schema `hermes.houdini.project.v1` contains exactly these top-level concepts:

- `project_id`, `title`, `brief`, and project-relative `references`;
- exact `compatibility` for Houdini build, license, package, and optional dependencies;
- `roots` for project/assets/cache/renders, confined beneath an explicit absolute project root at
  load time but serialized project-relative;
- fixed `seed_policy`, explicit `timeline`, aggregate and stage `budgets`;
- ordered `capability_instances`, each with instance ID, exact capability ID/version, context,
  inputs, output contracts, variant scope, dependencies, and requested evidence;
- three or more stable-order `variants` when alternatives are declared, with blank human fields;
- `output_contracts`, `evidence_gates`, and `human_decisions`.

Normalization rejects unknown schema/version, traversal/absolute embedded paths, duplicate IDs,
implicit latest versions, missing budgets, invalid frame ranges, non-finite values, automatic
ranking, or any non-null winner/rating/continuation value not supplied through a separate future
human-review record. Canonical JSON and SHA-256 exclude no semantic field.

### Adapter record

Schema `hermes.houdini.project_adapter.v1` contains `adapter_id`, semver `version`, exact
`from_contract` and `to_contract`, source/target contexts, recipe ID/version or named native
fallback, risk, approvals, budget effect, tested builds, optional dependencies, and evidence state.
Registry resolution is exact-version only and reports zero, one, or ambiguous matches; it never
chooses by taste or silently selects a plugin path.

### Compiler input/output

Lane C exposes a pure function accepting already normalized `spec`, `capability_catalog`, and
`adapter_records`. It must not import Lane A or B. Output schema
`hermes.houdini.project_plan.v1` contains source hashes, deterministic stage IDs, topological order,
explicit dependency edges, contract bindings/adapters, contexts/parent contracts, checkpoints,
cook scopes, budgets, approvals, evidence gates, human decision slots, blockers/warnings, and
`automatic_execution: false`.

The compiler blocks cycles, missing/ambiguous exact capabilities, missing/ambiguous adapters,
context mismatch, budget overflow, license/build mismatch, undeclared outputs, and dependency
fallbacks not explicitly permitted by the spec.

### Observer index

Lane D accepts already normalized project/plan mappings plus optional execution records and current
runtime identity. Output schema `hermes.houdini.project_index.v1` preserves planned stages,
contracts, alternatives, artifacts/hashes, evidence states, pending approvals/human decisions, and
structured drift. Absence of execution is `pending`, never failure or pass. It performs no file
discovery outside supplied roots and no HOM/UI operation.

## Integration order and seams

1. Integrate A, B, C, D in order using identifiable ordinary commits.
2. Reconcile imports only in `project_pipeline.py`; lanes remain independently testable.
3. Add the CLI, package-data registration for adapter YAML, and the dry Living Biome fixture.
4. Prove canonical repeatability in separate processes and deliberate failures for cycle,
   ambiguity, path traversal, build/license drift, budget overflow, and missing evidence.
5. Run full pure/Ruff/Hython regression; Hython establishes import compatibility only, not a live
   project claim.
6. Populate G002-I receipt and open one protected-main integration PR.

## Required gates

```bash
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
.venv/bin/python scripts/plan_project.py --help
.venv/bin/python scripts/plan_project.py validate --project projects/living_biome/project.yaml
.venv/bin/python scripts/plan_project.py plan --project projects/living_biome/project.yaml
/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  -m pytest tests/hython -o addopts='' -q
git diff --check
```

The integrated plan must hash identically across two clean Python processes. G002 runtime, graph,
cook, pixel, plugin, model, and human evidence are `not_applicable` with concrete reasons; full
Hython regression remains required because the package must still import and existing live tests
must not regress.

## Cycle exit gate

G002 becomes `VERIFIED` only when a fresh process validates and dry-compiles the Living Biome
fixture, produces a stable DAG and observer index, diagnoses all deliberate mismatch fixtures, and
passes protected CI. The result remains a plan, not a built scene. G003 stays `PROPOSED` until the
G002 contracts and source commit are merged and frozen.

## Acceptance phrase

After the candidate tag/SHA are published and frozen, the owner may authorize dispatch with:

> Accept Grinder Cycle G002 and launch lanes A-D from the frozen G001 release.
