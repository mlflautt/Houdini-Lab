# Grinder Lane G002-I — Integration Captain

## Mission

Integrate the four accepted pure-kernel lanes, reconcile only the frozen mapping seams, and prove
one end-to-end dry Living Biome project through validate → plan → observe. Preserve ordinary lane
history, exact source identities, pending runtime evidence, and blank human decisions. Do not build
or cook the project.

## Required inputs and preflight

Start only with accepted manifest, exact frozen base/tag, clean integration worktree, four pushed
component heads/PRs, and four `ready` receipts. Verify Git/GitHub/SSH state, each head against its PR,
and every lane diff against ownership before merging. Return a scope or contract defect to its lane;
do not redesign it silently.

## Integration order

1. Merge A, then B, then C, then D with identifiable ordinary merge commits.
2. Run pure/Ruff after each merge and attribute any regression to the introducing lane.
3. Add `hermes_houdini/project_pipeline.py` as the only sibling-wiring module.
4. Add `scripts/plan_project.py` with explicit `validate`, `plan`, and `observe` subcommands; default
   help, no hidden output, no Houdini import, no execution mode.
5. Add package exports/data only as needed for wheel behavior; never widen arbitrary code modes.
6. Author `projects/living_biome/project.yaml` and README from exact existing catalog records. Keep
   Amber Mesa, Verdant Rift, and Lunar Basin in stable equal order with blank human fields. Select
   exact World Seed, Material Foundry, Botanical Grammar, and one motion capability versions; mark
   the motion capability as a dry technical fixture, not an accepted aesthetic direction. Preserve
   viable motion alternatives for the explicit G003 owner choice. Mark all unexecuted graph/data/
   pixel gates pending or not applicable with concrete reasons.
7. Add integration tests that validate/load/compile/observe in separate processes and compare
   canonical hashes. Exercise deliberate path, version, adapter ambiguity, cycle, budget,
   build/license, dependency, artifact, and human-field failures.
8. Run full gates, build/inspect the wheel, write `G002-I.md`, update shared docs, and open one
   protected-main PR. Tag/release only under separate authority.

## Integration-owned paths

- `hermes_houdini/project_pipeline.py`
- `scripts/plan_project.py`
- `tests/unit/test_project_pipeline.py`
- `projects/living_biome/*`
- `hermes_houdini/__init__.py` and narrow exports/package data as needed
- `pyproject.toml`, `README.md`, `CHANGELOG.md`, roadmap and Grinder navigation/status
- `docs/grinder/receipts/G002-I.md` and release evidence

Lane-owned files may be edited only for a documented cross-lane mismatch permitted by the manifest.
Attribute each repair and add regression coverage.

## Required CLI semantics

- `validate --project PATH --project-root ROOT`: print normalized spec/hash; no output write unless
  `--output` is an explicit unused confined path.
- `plan`: build the live repository capability catalog and adapter registry in pure Python, compile,
  print plan/hash, and exit nonzero on blockers; never execute.
- `observe`: consume explicit plan/runtime/execution/artifact inputs, print index/hash, and never
  discover a scene or artifact tree.
- No command imports `hou`, starts a process/server, changes frame/UI, writes cache/render/HIP, or
  grants an approval. `--execute`, arbitrary Python/VEX, and implicit latest are rejected/absent.

## Required evidence

```bash
.venv/bin/python -m pytest tests/unit -o addopts='' -q
.venv/bin/python -m ruff check .
.venv/bin/python scripts/plan_project.py --help
.venv/bin/python scripts/plan_project.py validate --project projects/living_biome/project.yaml --project-root "$PWD"
.venv/bin/python scripts/plan_project.py plan --project projects/living_biome/project.yaml --project-root "$PWD"
/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  -m pytest tests/hython -o addopts='' -q
git diff --check
```

Run validate/plan twice in fresh processes and record matching semantic hashes. The Hython suite is
regression proof only. Runtime project build, graph/data/pixel/plugin/model/human/downstream evidence
is not applicable to G002 and cannot be promoted.

## Release decision and handoff

The receipt reports base/integrated head/source lanes, exact tests and hashes, compiler blockers,
Living Biome stage/variant summary, wheel identity, PR/CI URLs, all pending/unrun gates, and every
captain repair. Merge only through protected main; verify final-main CI. G003 remains blocked until a
new manifest freezes this merged contract and the owner accepts its live scope.
