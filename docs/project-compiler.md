# Deterministic project compiler

`hermes_houdini.project_compiler.compile_project` is the pure G002 compiler kernel. It accepts an
already normalized project mapping, a capability-catalog mapping, and an iterable of normalized
adapter-record mappings. It never loads YAML, imports the project-specification or adapter lanes,
touches Houdini, mutates a graph, cooks, writes a cache, renders, ranks variants, or executes its
result.

```python
compile_project(
    spec,
    capability_catalog=catalog,
    adapter_records=records,
) -> dict
```

All inputs must be finite JSON-shaped data. A caller programming error, such as passing a list in
place of `spec` or embedding a non-JSON object, raises `ValueError` with a deterministic path.
Failures in an otherwise JSON-shaped project contract return a plan with `status: blocked` and
structured `blockers`; they do not escape as compiler tracebacks.

## Frozen compiler seam

The input project uses schema `hermes.houdini.project.v1`. The compiler reads the exact
compatibility identity (`houdini_build`, `license_mode`, `package_version`, optional dependencies,
and permitted native fallbacks), `budgets.stage`, `budgets.aggregate`, ordered
`capability_instances`, ordered `variants`, `output_contracts`, `evidence_gates`, and
`human_decisions`.

Each capability instance names:

- `instance_id`, `capability_id`, exact `capability_version`, and `context`;
- a named `parent_contract` and `output_contracts`, either a port-to-contract mapping or ordered
  `{port, contract_id}` records;
- `inputs`, keyed by input port. A binding names `contract_id`, `from_port`, and normally
  `from_instance_id`. A changed contract also requires exact `adapter_version` and may constrain
  `adapter_id`;
- ordered `variant_scope` and `dependencies`;
- explicit `scope.graph_edit`, `scope.cook`, `scope.cache`, and `scope.render`;
- finite nonnegative `budget`, pending `approvals`, requested evidence, and any explicitly
  permitted native fallbacks.

The capability catalog uses its existing `records` shape. Resolution keys are exactly
`(capability_id, version)`; there is no latest-version or list-order rule. The catalog's package
version, each capability's context, tested Houdini build, license, optional dependencies, declared
outputs, risk, approvals, and fallback metadata participate in review.

Adapter records use `hermes.houdini.project_adapter.v1` metadata. Resolution requires exact source
and target contracts, version, contexts, build, and license. If `adapter_id` is supplied by the
binding it also matches exactly. Zero records block as `missing_adapter`; more than one compatible
exact record blocks as `ambiguous_adapter`. The selected record and its SHA-256 remain in the
contract binding so review does not depend on a registry lookup changing later.

## Plan contract and determinism

The output schema is `hermes.houdini.project_plan.v1`. It contains:

- canonical SHA-256 identities for the full normalized spec, full catalog, deterministically sorted
  adapter-record set, every adapter record, and the requested compatibility identity;
- deterministic stage IDs derived only from project, instance, and variant identity;
- stable topological order and explicit dependency/contract edges;
- exact capability identity, context, parent and output contracts, input bindings, and selected
  adapter bytes;
- explicit graph-edit/cook/cache/render scopes, checkpoint boundaries, budgets, risk, approvals,
  evidence, and native fallback;
- aggregate resource requests and the original stage/aggregate limits;
- variants and human decisions in source order, including null human-owned fields;
- structured blockers and warnings; and
- `automatic_execution: false`, `automatic_ranking: false`, and `winner: null` unconditionally.

`plan_sha256` is canonical JSON SHA-256 over the complete plan excluding only `plan_sha256` itself.
Mapping key order and adapter input order cannot change it. Semantic list order remains meaningful:
capability, variant, evidence, and human-decision ordering is preserved.

Variant-scoped instances expand into one stage per variant. Dependencies bind like variants when
possible and otherwise bind to a shared stage. Stable source order breaks topological ties, so a
disconnected graph remains reviewable and repeatable. Medium/high-risk stages and any declared
graph edit, cook, cache, or render operation receive a `before_stage` checkpoint boundary. Adapter
risk and budget effects are folded into the consuming stage and aggregate.

## Deliberate blockers

Compilation blocks:

- missing or ambiguous exact capabilities and adapters;
- dependency cycles and unavailable dependency stages;
- undeclared parent, input, output, or project-output contracts;
- multiple unresolved output providers;
- capability or adapter context, Houdini build, license, or package drift;
- unavailable optional dependencies unless exactly one named native fallback is both advertised and
  explicitly permitted by the project/instance/binding;
- stage or aggregate resource overflow, including adapter budget effects; and
- automatic ranking, a prefilled winner, or prefilled human-owned variant judgments.

Pending evidence and approval records are valid in a successful dry plan. `planned` means only that
the supplied contracts cohere within declared limits. It is not graph, geometry, cook, visual,
render, model, or human evidence, and it cannot grant execution permission. A future execution
surface must independently validate policy, approvals, current bytes and compatibility, checkpoint,
cook scope, and evidence requirements before acting.

## Integration assumptions

Lane C intentionally has no imports from Lane A or B. Integration supplies their normalized plain
mappings directly. Package exports, YAML discovery, CLI wiring, execution/resume, and project
fixtures belong to the integration lane. If integration changes a field name or normalized mapping
shape, it must reconcile that public seam explicitly; the compiler must not inspect sibling Python
types or select a fuzzy compatibility path.
