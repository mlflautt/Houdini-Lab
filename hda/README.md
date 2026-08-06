# HDA source-of-truth

`.hdanc` files are binary and not committed. Instead, each HDA is defined by a **build
script** that constructs it deterministically from native nodes, plus a manifest and tests.

## Layout
```
hda/source/<namespace>_<name>/
  build.py        # constructs the HDA from nodes (source of truth)
  manifest.yaml   # namespace, version, parms, help, icon
  tests/test_hda.py
```

## Naming
`hermes::biobloom_cluster::1.0`, `hermes::fractal_relic::2.0`, `hermes::audio_motion_field::1.1`.

## Promotion rule (docs §12.11, §21)
Promote to HDA only when a graph is stable, reusable, has a clear I/O contract, exposes
only useful controls, includes help + examples, and has regression tests. Always mark
Apprentice/non-commercial in HDA metadata.
