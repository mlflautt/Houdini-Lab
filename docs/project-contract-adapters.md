# Project contract adapter registry

The project adapter registry is the Houdini-independent composition boundary for G002. It records
how one named output contract can connect to another without hiding a graph builder inside Python.
The compiler can review this metadata; a later explicitly approved runtime must still instantiate
the referenced recipe or implement the named native fallback.

## Public API

`hermes_houdini.project_adapters` exposes:

```python
normalize_adapter_record(value, *, source="") -> dict
load_adapter_record(path) -> dict
build_adapter_registry(paths) -> dict
resolve_adapter(
    registry,
    *,
    from_contract,
    to_contract,
    version,
    build,
    license_mode,
    allowed_dependencies,
) -> dict
```

All functions return plain JSON-shaped data and import without Houdini. Loading is explicit; the
module does not scan directories or consult the live recipe/capability registries.

## Descriptor contract

Every descriptor uses schema `hermes.houdini.project_adapter.v1` and contains:

- a lowercase dotted `adapter_id` and exact `X.Y.Z` version;
- exact `from_contract`, `to_contract`, `source_context`, and `target_context`;
- exactly one of `recipe: {id, version}` or a named `native_fallback`;
- `risk`, `approvals`, and a JSON-shaped `budget_effect`;
- exact `tested_builds`, `license_modes`, and `optional_dependencies`;
- `evidence_status` and explicit repository-relative `source_audit` paths.

Normalization rejects unknown or missing fields, imprecise versions, unsupported contexts/risk/
evidence states, duplicate list entries, non-finite or non-JSON budget values, and malformed
implementation references. It attaches the explicit load source and a canonical content SHA-256.
The content hash covers every normalized semantic field, including compatibility, approvals,
fallback, budget, evidence, audits, and source.

## Deterministic registry and resolution

`build_adapter_registry` accepts only caller-supplied paths. It sorts normalized records by
`(adapter_id, version, source)`, rejects duplicate identities, and hashes the full canonical
registry. Input iteration order cannot affect either records or the registry hash.

Resolution is exact on source contract, target contract, and adapter version. The result is one of:

- `resolved`: exactly one candidate exists and build, license, and dependencies are compatible;
- `missing`: no exact-version candidate exists;
- `ambiguous`: multiple exact candidates exist, with no first-match or preference behavior;
- `incompatible`: one exact candidate exists but build, license, or dependency requirements fail.

Every result carries the query and all relevant candidate identities. A resolved result preserves
the complete normalized descriptor. There is no `latest`, fuzzy-name lookup, aesthetic rank,
plugin preference, recipe execution, fallback synthesis, or certification inference.

## G002 source audit and evidence boundary

The two exact recipe references were audited against their current recipe YAML and skill manifest:

- World Seed outputs `three_native_worlds`; `lop.world_seed_atlas_stage@1.0.0` imports three exact
  SOP paths into a LOP stage.
- Material Foundry outputs `three_usd_material_cop_contracts`;
  `lop.procedural_material_foundry_stage@1.0.0` publishes the three COP materials and creates named
  bindings in a LOP stage.

Botanical Grammar and Particle Calligraphy have exact source skills/recipes, but no registered
recipe currently connects their selected geometry into the Living Biome world layer. Their named
G003 native fallbacks remain `pending` implementation dependencies. G002 performs no Hython, graph,
cook, viewport, render, plugin, model, or human-selection work, so those evidence classes are
`not_applicable` here. Source-manifest audit establishes metadata provenance only, not runtime proof.

Package-data registration and end-to-end compiler wiring are reserved for G002-I integration.
