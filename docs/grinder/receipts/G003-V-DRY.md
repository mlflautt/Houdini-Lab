# Grinder Receipt G003-V-DRY — Visual Audition Plan

- State: `dry-ready E — A/B/C stopped safely at USD frame contract; awaiting exact E approval`
- Branch: `codex/grinder-g003-v-visual-audition`
- Accepted protected-main base: `df476c1af5db0cda4b80d8cc7ff5bd384cb51389`
- Acceptance PR: `#25`
- Accepted-base final-main CI: `33094029963`, success
- Runtime target: Houdini Apprentice `22.0.368`, Python `3.13`, Karma CPU
- Live work performed: stopped A, B, and C proofs through registered call 8; no render launched

## Delivered planning code

- `hermes_houdini/g003_visual_audition.py`
- `hermes_houdini/g003_execution.py`
- `scripts/plan_g003_visual_audition.py`
- `scripts/run_g003_visual_audition.py`
- `tests/unit/test_g003_visual_audition.py`
- `tests/unit/test_g003_execution.py`
- `docs/G003_EXECUTION_RUNNER.md`

The module is Houdini-independent. It loads the exact registered skill contracts, emits one
canonical non-executing plan, refuses a dirty/drifted accepted source, refuses an existing or
out-of-project live root, preserves fixed method order, and leaves every approval and human field
false/null.

The execution layer is also import-safe without Houdini. It validates canonical authority, path
confinement, the exact 115-call/36-render contract, single-use dispatcher approvals, cancellation,
resource ceilings, frame restoration, exclusive writes, immutable stopped attempts, and null human
decisions. The Hython CLI retains the exact operator wording in the live receipt and exposes a
mutation-free `--preflight-only` mode for Codex, Hermes Agent, OpenCode, DeepSeek harnesses, or local
agents.

## Authoritative ignored manifest

- Path:
  `/Users/m1/Houdini Lab/.hermes/g003/plans/g003-v-20260827-e-manifest-sequential-source-cook.json`
- Canonical approval-subject SHA-256:
  `e7baa437bb0804adac5001c3cb4ab11efe550d6fa5d1f350e1b6cfd529377c3f`
- Exact file-byte SHA-256:
  `162c10c88c0c35ce677b77c030dde3e9864a9d3bb896c5726327f12c87140104`
- Planned live root:
  `/Users/m1/Houdini Lab/.hermes/g003/gate-v/g003-v-20260827-e`
- Live-root existence at planning time: absent
- Automatic execution: false

The approval-subject hash uses canonical compact JSON with its self-referential
`approval.manifest_sha256_subject` normalized to null. The file-byte hash covers the indented
on-disk JSON. Regeneration in two fresh temporary paths produced identical canonical and byte
hashes before the final manifest was written exclusively.

The earlier blocked-runtime manifest remains preserved at
`/Users/m1/Houdini Lab/.hermes/g003/plans/g003-v-20260827-a-manifest.json`. Its canonical hash
`c96c0cfcd17ac924cd521a78ce0ea237727f2e2041b26be5dc3fe09095806fdd` is superseded and is not a
valid live-approval subject.

The first license-ready A manifest also remains preserved. Its canonical hash
`e751eab063835132fa4d611def27a8e3ab476eca63cb35afc10769403c6e26ce` was approved and consumed by
the stopped A attempt described below; it is not reusable for B.

The license-ready B manifest also remains preserved at
`/Users/m1/Houdini Lab/.hermes/g003/plans/g003-v-20260827-b-manifest-license-ready.json`. Its
canonical hash `048c008a323790c6117088b4518a60149603f95343aca3cecc72401de40c6551` was approved with the exact
owner wording `proceed` and consumed by the stopped B attempt below; it is not reusable for C.

The explicit-LOP-frame C manifest remains preserved at
`/Users/m1/Houdini Lab/.hermes/g003/plans/g003-v-20260827-c-manifest-explicit-lop-frame.json`.
Its canonical hash `e7b6af650d6e6d01677732d287f0fa1119733be8fcbff2b0b821e00c88771351` was approved with the exact
owner wording `proceed` and consumed by the stopped C attempt below; it is not reusable for E.

An unapproved D draft remains preserved at
`/Users/m1/Houdini Lab/.hermes/g003/plans/g003-v-20260827-d-manifest-sequential-source-cook.json`.
It was superseded before live authority because its external render policy did not separately
budget the 30-second husk ceiling and sequential source warm-up. No D root was created.

## Approved A execution and safe stop

The owner approved A with the words `proceed/approve: continue creative development`. The live
runner revalidated the exact hash, clean branch, accepted-base ancestry, fresh scene, Apprentice
build/license, 115 registered calls, untouched root, ffmpeg `9.0.1`, and all declared ceilings.

Calls 1–8 completed successfully: the Calligraphy object network, native recipe, temporal
validation, graph SVG/manifest, non-overwriting scene snapshot, Solaris recipe, and MaterialX
population. Call 9, `solaris.stage.validate`, stopped before any render because the animated SOP
Import was evaluated at frame 1, where Calligraphy intentionally has zero geometry. Exact failure:

```text
USD stage missing expected prims: /World/G003V/ParticleCalligraphy
```

The stop preserved 2,372,807 bytes of checkpoints, logs, graph evidence, validation, and a `.hipnc`
scene under `/Users/m1/Houdini Lab/.hermes/g003/gate-v/g003-v-20260827-a`. Peak RSS was 630,095,872
bytes. Render calls completed: zero. The A root will not be reused, resumed, or overwritten.

Read-only inspection of the saved graph proved the timing boundary: frame 1 has zero SOP points and
only `/World`; frame 2 has 270 points and the expected asset prim; frames 12 and 24 also contain the
expected asset prim. This isolated a validator-frame contract defect rather than a graph, recipe,
license, or SOP Import defect.

Commit `aba5ddd` adds explicit-frame evaluation to `solaris.stage.validate`, restores the caller's
frame in a `finally` boundary, passes the chosen frame from `lookdev.relic_stage`, and adds a Hython
regression whose source is empty at frame 1 and populated at frame 11. The regression passes and
confirms frame 1 is restored. B binds this corrected call shape and uses a fresh output root.

## Approved B execution and safe stop

The owner approved B with the exact word `proceed`. The permanent runner revalidated the canonical
hash, clean branch, accepted-base ancestry, fresh scene, Apprentice build/license, 115 registered
calls, untouched B root, ffmpeg `9.0.1`, and all declared ceilings. Calls 1–8 again succeeded and
call 9 again stopped on the absent animated asset prim. B preserved 2,364,068 bytes with peak RSS
627,179,520 bytes and launched zero render calls.

Read-only inspection of B's MaterialX checkpoint proved the graph and saved stage are correct:
frame 1 lacks the asset prim, while frame 24 contains 2,070 SOP points, 1,932 SOP primitives, and
`/World/G003V/ParticleCalligraphy`. The remaining defect was the evaluation API: changing the
global frame did not reliably bypass a LOP stage cached by the prior live calls. Houdini 22's
official `hou.LopNode.stage` contract accepts an explicit `frame` argument. The C fix now calls
`node.stage(frame=frame_value)` directly, never mutates global frame state, and extends the Hython
regression to cache an empty frame-1 stage before validating the populated frame-11 stage. C uses
a new manifest and untouched root.

## Approved C execution and safe stop

The owner approved C with the exact word `proceed`. The permanent runner again passed its complete
preflight. Calls 1–8 succeeded and call 9 stopped before any render on the same absent asset prim.
C preserved 2,364,078 bytes with peak RSS 626,556,928 bytes and launched zero render calls.

The full native regression then reproduced the live sequence rather than substituting a simple
Switch SOP. It proved Particle Calligraphy is stateful: after frame restoration, a direct jump to
frame 24 does not replay frames 1–23, even if the target SOP and LOP are individually forced.
The E contract therefore declares `source_start_frame`, sequentially cooks every source frame
through the requested target, invalidates the exact upstream SOP Import LOP, composes the stage,
and restores the original frame. Every sparse render call carries the same source path, warm-up
start, target frame, and matching `policy.max_frames`; the pure manifest validator rejects any
drift in those fields. A Hython regression using the actual Particle Calligraphy graph now passes
after caching an empty frame-1 USD stage and validating the populated frame-24 stage.

## Exact planned creative evidence

Stable order:

1. `motion.particle_calligraphy@1.0.0`, seed `5201`, silent fixture, three-candidate comparison.
2. `generate.differential_growth@1.0.0`, seed `2401`, ellipse preview input, memory-only native
   Solver, rest-versus-grown comparison.
3. `motion.kinetic_reliquary@1.1.0`, seed `22012`, 24 copies, `mops_available: false`, native-only
   layered presentation.

All three use frames `1–24` and render frames `2,4,6,8,10,12,14,16,18,20,22,24`. The manifest
contains 115 registered calls: 37 Particle Calligraphy, 40 Differential Growth, and 38 Kinetic
Instances. Exactly 36 calls launch one-frame Karma CPU renders at `640×360`, at most 16 path-traced
samples, four threads, a 30-second husk ceiling, and a 35-second total call ceiling. Before each
sparse frame, the registered render tool
sequentially evaluates its declared source from frame 1 through the target; 468 source-frame cooks
are explicit across the three methods rather than relying on hidden simulation state.

The global ceilings are 20 minutes aggregate render time, 4 GiB peak memory, 1 GiB output, and zero
retained disk cache. Capability ceilings remain 100,000 points/primitives for calligraphy, 50,000
for differential growth, and 20,000 for kinetic instances.

Postprocessing plans three local six-fps H.264 previews using
`/opt/homebrew/bin/ffmpeg` `9.0.1`, a fixed-order `1280×240` final-frame contact sheet, companion
labels JSON, and a static labeled HTML review index. Those actions are local, non-networked, and
remain unexecuted. Technical materials/colors aid legibility only and do not imply preference.

## Runtime and compatibility evidence

Official Houdini references were retrieved for SOP Import LOP, Camera LOP, Dome Light LOP, Karma
Render Settings LOP, and USD Render ROP. Every planned LOP/ROP type already exists in registered
recipes tested against build `22.0.368`; no new operator type or arbitrary HOM/VEX was introduced.

The accepted read-only live probe used:

```text
HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json
PYTHONPATH=.
/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython
```

The first attempt stopped before importing `hou` because no license could be acquired:

```text
No licenses could be found to run this application.
Please check for a valid license server host
```

Read-only diagnostics at that time verified:

- `hserver` and `sesinetd` processes are running;
- hserver build is `22.0.368` and points to `https://www.sidefx.com/license/sesinetd`;
- the server is reachable, but `sesictrl print-server` and `print-license` report
  `You are not logged into the license server. [Error L01]`;
- no used license is present; and
- no runtime probe mutated a scene, frame, graph, package, preference, or license configuration.

After the owner reactivated Apprentice, the same mutation-free Hython probe passed. Current evidence
is:

- Hython reports build `22.0.368` and `licenseCategoryType.Apprentice`;
- the active Houdini Apprentice 22.0 entitlement is acquired by `m1@M1` and expires
  `05-sep-2026`;
- SOP Import LOP, Dome Light LOP, Camera LOP, Karma Render Settings LOP, and USD Render ROP are
  available;
- exact tuple interfaces are Camera LOP `t`/`r`, Karma Render Settings LOP `resolution`, and USD
  Render ROP `res_user`;
- the required remaining parameters were also found: `soppath`, `primpath`, `enable_pathprefix`,
  `pathprefix`, `focalLength`, `camera`, `samplesperpixel`, `pathtracedsamples`, `renderer`,
  `loppath`, `rendersettings`, `outputimage`, `husk_timelimit`, and `maxthreads`;
- frame, HIP path, and the complete root-child list were identical before and after inspection; and
- `tests/hython/test_acceptance_probes.py` passed all three read-only tests in `0.22s`.

No graph, cook, save, render, package, preference, or license mutation was performed. The fresh
manifest records this passing runtime observation and is the sole live-approval subject.

## Verification

```text
env PYTHONPATH=. '/Users/m1/Houdini Lab/.venv/bin/python' -m pytest -q -p no:cacheprovider
352 passed, 4 sandbox socket skips in 5.23s

'/Users/m1/Houdini Lab/.venv/bin/ruff' check --no-cache .
All checks passed!

git diff --check
pass

env HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json PYTHONPATH=. \
  /Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  -m pytest tests/hython/test_acceptance_probes.py -o addopts='' -q
3 passed in 0.22s

env HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json PYTHONPATH=. \
  /Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  -m pytest \
    tests/hython/test_integration.py::test_relic_lookdev_skill_builds_materialx_and_validates_usd_stage_without_render \
    tests/hython/test_integration.py::test_particle_calligraphy_lookdev_recooks_declared_source_after_temporal_validation \
  -o addopts='' -q
2 passed in 3.61s

env HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json PYTHONPATH=. \
  /Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  scripts/run_g003_visual_audition.py \
  --manifest '/Users/m1/Houdini Lab/.hermes/g003/plans/g003-v-20260827-e-manifest-sequential-source-cook.json' \
  --approved-manifest-sha256 e7baa437bb0804adac5001c3cb4ab11efe550d6fa5d1f350e1b6cfd529377c3f \
  --preflight-only
pass; 115 calls, 36 renders, clean head d138bac, Apprentice 22.0.368, ffmpeg 9.0.1,
fresh scene, absent E root, mutation_performed=false
```

The first Ruff attempt without `--no-cache` could not create `.ruff_cache` in the external worktree
under the managed sandbox. Rerunning with Ruff's supported `--no-cache` mode passed and changed no
repository or global state. Pytest's cache warning was avoided in final collection with
`-p no:cacheprovider`; tests themselves passed.

## Evidence status

| Rung | Status | Evidence |
|---|---|---|
| acceptance/source | pass | exact protected-main base and successful CI |
| pure dry manifest | pass | deterministic E canonical and byte hashes; fresh E root absent |
| registered capability identities | pass | exact four skill-loader identities |
| portable live-runner preflight | pass | pure contract plus clean Hython/dispatcher/runtime/tool preflight; no mutation |
| H22 build/license/operator probe | pass | Apprentice acquired; exact build, types, tuples, and unchanged scene state observed |
| graph edit and cook | partial/stopped | eight calls passed in A/B/C; all stopped at call 9 |
| scene save | pass for stopped A/B/C | non-overwriting partial Calligraphy `.hipnc` scenes preserved |
| Karma and pixels | pending | A/B/C were authorized but stopped before render; E is not yet authorized |
| preview/contact sheet | pending | no source pixels yet; A/B/C postprocessing did not run |
| external model/plugin | not applicable | absent from plan |
| human motion selection | pending | requires authentic Gate V review |

## Next stop

The runtime gate now passes. No graph, cook, render, or scene action may begin until the owner gives
explicit approval bound to canonical manifest hash
`e7baa437bb0804adac5001c3cb4ab11efe550d6fa5d1f350e1b6cfd529377c3f` and exact live root
`/Users/m1/Houdini Lab/.hermes/g003/gate-v/g003-v-20260827-e`. Approval does not select a creative
winner and does not authorize continuation into downstream G003 lanes.
