# Optional Houdini plugin registry

This directory records externally installed Houdini packages; it does not vendor or silently load
them. Every record pins source, checksum, exact Houdini build, license, permissions, Apprentice
verdict, bounded fixtures, and rollback. The pure auditor in
`hermes_houdini/plugin_registry.py` can inspect these records and installed package trees without
importing Houdini or executing plugin code.

An `allowed` verdict means only that the plugin class is eligible for an Apprentice experiment.
It does not certify the entire package. Certification is node-specific and requires an isolated
startup, fixture cooks, visual proof, and a verified skipped-package launch.

Validate a record without Houdini:

```bash
.venv/bin/python scripts/audit_houdini_plugin.py manifest \
  plugins/sidefx-labs-22.0.368.json
```

After an explicitly approved install, run `scripts/probe_sidefx_labs.py` once normally and once
with `HOUDINI_PACKAGE_SKIPLIST=SideFXLabs22.0.json`. The `.json` suffix is required by the pinned
Houdini 22.0.368 build even though current documentation also describes basename matching. The two read-only reports establish package-loaded
and rollback baselines before any fixture graph is authored.

MOPs 1.12 uses a different boundary: `plugins/mops-1.12.json` pins the upstream tag, commit,
deterministic source-archive checksum, LGPL-3.0 license, and four certified node types. The payload
lives under ignored `plugins/vendor/` and is loaded only for an isolated Hython process by setting
`MOPS` and prepending that root to `HOUDINI_PATH`. Do not copy its package JSON into global Houdini
preferences. See [`../docs/mops-kinetic-reliquary.md`](../docs/mops-kinetic-reliquary.md).
