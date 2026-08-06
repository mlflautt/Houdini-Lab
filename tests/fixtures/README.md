# Test fixtures

Small `.hipnc` fixtures for hython integration / golden tests (docs §17.4). Binary files are
gitignored; this directory holds only manifests describing each fixture and a `.gitkeep`.

| Fixture | Build | Purpose |
|---------|-------|---------|
| `empty.hipnc` | H22 | baseline empty scene |
| `simple_sop.hipnc` | H22 | one box → null |
| `animated.hipnc` | H22 | time-dependent transform |
| `broken_dep.hipnc` | H22 | missing file dependency |
| `locked_hda.hipnc` | H22 | locked HDA instance |

Record the exact Houdini build used to create each fixture here and regenerate when the
pinned build changes.
