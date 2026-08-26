# Hermes Houdini Project Specification v1

`hermes.houdini.project.v1` is the pure, human-readable intent boundary for a composed Houdini
project. It records what a caller intends to compile without discovering capabilities, selecting an
adapter, choosing a variant, importing Houdini, or executing work.

The implementation is `hermes_houdini/project_spec.py`. Its public API is:

```python
normalize_project_spec(value: Mapping, *, project_root: str | Path) -> dict
load_project_spec(path: str | Path, *, project_root: str | Path) -> dict
project_spec_sha256(normalized: Mapping) -> str
```

`load_project_spec` reads only the explicit file supplied by the caller with `yaml.safe_load`; it
never searches a directory. Both loading and normalization require an absolute `project_root`.
The result contains only canonical JSON-shaped values. Lists retain source order, while the hash
sorts mapping keys and covers every semantic field.

## Top-level fields

The top-level mapping is closed: missing or unknown fields are rejected.

| Field | Contract |
|---|---|
| `schema` | Exactly `hermes.houdini.project.v1`. |
| `project_id` | Non-empty stable identifier. |
| `title` | Non-empty human title. |
| `brief` | Non-empty creative brief. |
| `references` | Ordered local reference records. |
| `compatibility` | Exact Houdini, license, package, and optional-dependency identity. |
| `roots` | Project-relative `project`, `assets`, `cache`, and `renders` roots. |
| `seed_policy` | Fixed reproducibility policy and non-negative integer seed. |
| `timeline` | Explicit inclusive frame range and positive finite FPS. |
| `budgets` | Complete aggregate and per-instance resource ceilings. |
| `capability_instances` | Ordered exact-version capability requests; no registry lookup occurs here. |
| `variants` | Zero alternatives or at least three equal-status alternatives in source order. |
| `output_contracts` | Named, context-declared outputs and their project-relative artifact paths. |
| `evidence_gates` | Explicit required/optional evidence records and current five-state status. |
| `human_decisions` | Blank append-only decision slots for a future human-review record. |
| `automatic_ranking` | Must be the Boolean `false`. |
| `winner` | Must be `null`. |

## Nested records

Each reference has `reference_id`, `path`, and `description`. Reference IDs are unique and order is
semantic.

`compatibility` has `houdini_build`, `license_mode`, `package_version`, and
`optional_dependencies`. A Houdini build is an exact numeric build such as `22.0.368`. Package and
dependency versions use exact SemVer, never `latest`, a range, or an omitted version. Each optional
dependency has a unique `dependency_id` and exact `version`.

`roots` has exactly `project`, `assets`, `cache`, and `renders`. `project` may normalize to `.`, while
the other roots must name a location below the project root.

`seed_policy` has exactly `mode: fixed` and `seed`. Runtime-generated or floating seeds are outside
this schema. `timeline` has `start_frame`, `end_frame`, and `fps`; frames are non-negative integers,
the end cannot precede the start, and FPS must be finite and greater than zero.

`budgets.aggregate` and every `budgets.stages[].limits` record contain all of:

- `points`, `primitives`, `peak_memory_bytes`, `cache_bytes`, `frames`, `width`, `height`, and
  `render_samples` as non-negative integers;
- `cook_seconds` as a finite non-negative number.

Each stage budget has one `instance_id`. Stage IDs are unique and must match the capability-instance
IDs exactly, so no requested stage inherits an undeclared resource ceiling.

Every `capability_instances` record contains:

- unique `instance_id`, exact `capability_id` and `capability_version`;
- a declared `context` from `SOP`, `OBJ`, `LOP`, `DOP`, `TOP`, `COP`, `CHOP`, or `APEX`;
- JSON-shaped `inputs`, preserved without capability-specific interpretation;
- ordered `output_contracts`, `variant_scope`, `dependencies`, and `requested_evidence` ID lists.

Those IDs must resolve inside the project mapping. The parser verifies reference integrity and
output ownership/context but deliberately does not verify that a capability or adapter exists. DAG
cycles and compatibility with a catalog remain compiler concerns.

Every variant has `variant_id`, `title`, `description`, `human_rating`, and
`selected_for_continuation`. IDs are unique. The two human-owned fields must remain `null`; list
position does not imply rank.

Every output contract has unique `contract_id`, `producer_instance_id`, declared `context`, `name`,
and project-relative `artifact_path`. The producer must exist, list the contract in its own outputs,
and declare the same context.

Every evidence gate has unique `gate_id`, `evidence_type`, Boolean `required`, and one status from
`pass`, `warn`, `pending`, `blocked`, or `not_applicable`. Capability evidence requests must point to
declared gates. A parsed `pass` is recorded intent/state only; parsing does not produce evidence.

Every human decision has unique `decision_id`, `prompt`, `winner`, and
`selected_for_continuation`. Both ownership fields must remain `null`. Future human reviews are
append-only records outside this lane and must not rewrite the source alternatives.

## Path confinement and portability

The specification file itself must resolve beneath `project_root`. Embedded reference, root, and
artifact paths must be relative. They are resolved with symlinks against the absolute project root;
absolute paths and traversal or symlink escapes are rejected. Accepted values serialize back as
normalized relative POSIX paths. Absolute checkout or home paths therefore never enter the
normalized mapping or its hash.

Paths are not discovered and need not exist during normalization. Their existence, bytes, and
artifact hashes belong to later evidence/runtime layers.

## Canonical hash

`project_spec_sha256` encodes the normalized mapping as UTF-8 JSON with sorted mapping keys, compact
separators, preserved list order, Unicode preserved, and NaN/Infinity forbidden. SHA-256 covers all
fields, including null human slots and alternatives; only mapping source order is insignificant.
Callers should normalize before hashing.

## Failure modes and boundaries

Normalization raises `ValueError` with a deterministic field path for malformed contracts,
including:

- a non-object YAML root, unknown/missing fields, non-string object keys, or non-JSON YAML values;
- recursive aliases, unexpected alias-derived types, NaN, or Infinity;
- an unknown schema, invalid/duplicate IDs, non-exact versions, or undeclared contexts;
- absolute paths, source/embedded traversal, or symlink escape;
- non-fixed seeds, missing/negative/non-finite budgets, frame inversion, or invalid FPS;
- unresolved project-local IDs, mismatched output ownership/context, or missing stage budgets;
- fewer than three declared alternatives;
- automatic ranking, a winner, a human rating, or a selected continuation.

Successful validation does **not** prove capability availability, adapter availability, DAG
acyclicity, Houdini/plugin compatibility, execution approval, graph/data correctness, visual
quality, artifact existence, or human preference. Those remain separate compiler, runtime,
evidence, and human-review gates.
