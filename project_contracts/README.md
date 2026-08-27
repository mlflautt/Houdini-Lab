# Project contract adapters

This directory contains declarative `hermes.houdini.project_adapter.v1` records. An adapter
describes one exact, versioned connection between two named project contracts. It is composition
metadata, not executable code: loading or resolving a record never imports Houdini, queries the
recipe catalog, instantiates a graph, cooks, renders, or implements a fallback.

Each record declares exact source and target contracts and contexts, one exact recipe reference or
one named future native fallback, compatibility constraints, risk and approval metadata, budget
effects, dependencies, source-audit paths, and evidence state. `pending` means precisely that no
runtime adapter execution has been established by this registry.

## Bundled G002 records

| Adapter | Exact implementation reference | Source audit | Runtime evidence |
|---|---|---|---|
| `project.world_geometry_to_solaris@1.0.0` | `lop.world_seed_atlas_stage@1.0.0` | World Seed skill and LOP recipe | `pending` |
| `project.pbr_channels_to_material_bindings@1.0.0` | `lop.procedural_material_foundry_stage@1.0.0` | Material Foundry skill and LOP recipe | `pending` |
| `project.botanical_geometry_to_world_layer@1.0.0` | `g003.native_merge_botanical_world_layer` | Botanical Grammar skill and SOP recipe | `pending`; future fallback |
| `project.motion_geometry_to_world_layer@1.0.0` | `g003.native_merge_motion_world_layer` | Particle Calligraphy skill and SOP recipe | `pending`; future fallback |

The future fallback names are G003 implementation dependencies. Their presence in this directory
does not register, certify, or execute them.

Package-data registration for these YAML files is intentionally integration-owned by G002-I.
