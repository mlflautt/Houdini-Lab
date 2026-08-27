# Grinder Receipt G003-V-DRY — Visual Audition Plan

- State: `dry-ready — valid Apprentice runtime verified; awaiting exact live approval`
- Branch: `codex/grinder-g003-v-visual-audition`
- Accepted protected-main base: `df476c1af5db0cda4b80d8cc7ff5bd384cb51389`
- Acceptance PR: `#25`
- Accepted-base final-main CI: `33094029963`, success
- Runtime target: Houdini Apprentice `22.0.368`, Python `3.13`, Karma CPU
- Live work performed: none

## Delivered planning code

- `hermes_houdini/g003_visual_audition.py`
- `scripts/plan_g003_visual_audition.py`
- `tests/unit/test_g003_visual_audition.py`

The module is Houdini-independent. It loads the exact registered skill contracts, emits one
canonical non-executing plan, refuses a dirty/drifted accepted source, refuses an existing or
out-of-project live root, preserves fixed method order, and leaves every approval and human field
false/null.

## Authoritative ignored manifest

- Path:
  `/Users/m1/Houdini Lab/.hermes/g003/plans/g003-v-20260827-a-manifest-license-ready.json`
- Canonical approval-subject SHA-256:
  `e751eab063835132fa4d611def27a8e3ab476eca63cb35afc10769403c6e26ce`
- Exact file-byte SHA-256:
  `1c7dd3e3169aa134cc70a15b3c54b4bcc7c535c792a5def5534c85979a25e4c8`
- Planned live root:
  `/Users/m1/Houdini Lab/.hermes/g003/gate-v/g003-v-20260827-a`
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
samples, four threads, and 30 seconds per frame.

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
347 collected; 343 passed and 4 intentional Houdini-environment skips

'/Users/m1/Houdini Lab/.venv/bin/ruff' check --no-cache .
All checks passed!

git diff --check
pass

env HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json PYTHONPATH=. \
  /Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  -m pytest tests/hython/test_acceptance_probes.py -o addopts='' -q
3 passed in 0.22s
```

The first Ruff attempt without `--no-cache` could not create `.ruff_cache` in the external worktree
under the managed sandbox. Rerunning with Ruff's supported `--no-cache` mode passed and changed no
repository or global state. Pytest's cache warning was avoided in final collection with
`-p no:cacheprovider`; tests themselves passed.

## Evidence status

| Rung | Status | Evidence |
|---|---|---|
| acceptance/source | pass | exact protected-main base and successful CI |
| pure dry manifest | pass | deterministic canonical and byte hashes |
| registered capability identities | pass | exact four skill-loader identities |
| H22 build/license/operator probe | pass | Apprentice acquired; exact build, types, tuples, and unchanged scene state observed |
| graph edit and cook | pending | not authorized or run |
| scene save | pending | not authorized or run |
| Karma and pixels | pending | not authorized or run |
| preview/contact sheet | pending | no source pixels yet |
| external model/plugin | not applicable | absent from plan |
| human motion selection | pending | requires authentic Gate V review |

## Next stop

The runtime gate now passes. No graph, cook, render, or scene action may begin until the owner gives
explicit approval bound to canonical manifest hash
`e751eab063835132fa4d611def27a8e3ab476eca63cb35afc10769403c6e26ce` and exact live root
`/Users/m1/Houdini Lab/.hermes/g003/gate-v/g003-v-20260827-a`. Approval does not select a creative
winner and does not authorize continuation into downstream G003 lanes.
