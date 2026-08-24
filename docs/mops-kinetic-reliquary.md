# Sprint 22 — MOPs kinetic reliquary

Sprint 22 tests whether MOPs makes motion-graphics falloffs more legible while preserving a native
Houdini baseline. MOPs is not installed globally: v1.12 is pinned to commit
`65c4cff83003a51b31edbefa1dd1a11bd3ac3c25` under the ignored project-local plugin root and loaded
only through an isolated `MOPS`/`HOUDINI_PATH` process environment.

The audited checkout contains 45 HDA libraries, two Python files, two shelf files, and no native
binaries. The upstream base package is LGPL-3.0 and documents Houdini 18+ with any license type.
See the [MOPs v1.12 release](https://github.com/toadstorm/MOPS/releases/tag/v1.12),
[requirements/wiki](https://github.com/toadstorm/MOPS/wiki), and
[upstream license](https://github.com/toadstorm/MOPS/blob/v1.12/LICENSE).

## Graph contract

One native Circle/Add point source and one packed Copy to Points source drive four retained branches:

1. native Transform SOP motion;
2. `MOPS::Plain_Falloff::1.0` plus `MOPS::Transform_Modifier::1.1`;
3. time-varying `MOPS::Noise_Falloff::1.4` plus the same transform boundary;
4. moving `MOPS::Shape_Falloff::1.5` plus the same transform boundary.

Every packed branch contains exactly 24 points/primitives and exposes `P`, `orient`, `scale`, `v`,
`seed`, and `variant_id`. Validation hashes those ordered attributes at frames 1, 12, and 24;
digests must be deterministic and different across time. The native branch is Switch input zero.

Presentation occurs only after those verified packed contracts: each branch is unpacked and given
a distinct review color, then merged for Karma. This makes visual identity clearer without changing
the source motion data.

When `mops_available=false`, the optional recipe is replaced by
`sop.kinetic_reliquary_mops_unavailable@1.0.0`; no MOPs HDA is instantiated and
`OPTIONAL_MOPS_UNAVAILABLE` documents the missing capability.

## Live acceptance

Houdini 22.0.368 Apprentice loaded all four exact types from the isolated v1.12 checkout. The four
branches passed graph, attribute, packed-count, resource, and three-frame digest validation. The
crop-safe 640x360 Karma proof has four present panels at all three frames, no visual flags, and no
duplicate image hashes. A separate zero-MOPs bare-Hython run passed the native fallback.

Evidence:

- registry: `plugins/mops-1.12.json`
- compact record: `plugins/evidence/mops-acceptance-22.0.368.json`
- local enabled run: `.hermes/sprint22-acceptance-20260824-g/`
- local zero-MOPs run: `.hermes/sprint22-native-fallback-20260824-a/`
- saved scene: `kinetic_reliquary_sprint22_live_final_v001.hipnc`

MOPs Plus remains outside scope. No paid component, global Houdini preference, renderer, telemetry,
or background service was installed.
