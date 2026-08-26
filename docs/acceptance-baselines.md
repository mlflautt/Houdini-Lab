# Acceptance Baselines and Compatibility Probes

Lane G001-C supplies pure comparison logic and a narrow read-only Hython adapter. These records are
safety and diagnostic gates. They do not execute an acceptance tier, grant an approval, rank
creative output, or infer artistic quality.

## Resource baseline record

`normalize_baseline(baseline)` accepts schema `hermes.houdini.acceptance.baseline.v1`. Every record
has a stable `baseline_id`, a separately incremented `baseline_version`, all nine resource ceilings,
and optional warning tolerances:

```json
{
  "schema": "hermes.houdini.acceptance.baseline.v1",
  "baseline_id": "fractal-relic-small-m1max-h22",
  "baseline_version": "1.0.0",
  "budgets": {
    "points": 3000000,
    "primitives": 3000000,
    "peak_memory_bytes": 536870912,
    "cook_seconds": 90.0,
    "cache_bytes": 1073741824,
    "frames": 1,
    "width": 1280,
    "height": 720,
    "render_samples": 64
  },
  "tolerances": {
    "default_warning_fraction": 0.1,
    "metrics": {"cook_seconds": 0.2}
  }
}
```

The warning threshold is `budget * (1 - warning_fraction)`. A per-metric fraction overrides the
default. Tolerance is the warning band below a hard ceiling, not permission to exceed that ceiling.
For example, a 10% warning fraction on 1,000 points yields a warning threshold of 900 and a hard
violation only above 1,000.

`evaluate_baseline(baseline, observed)` returns a plain mapping. Each metric has one exact outcome:

- `missing`: no observation was supplied;
- `within_budget`: finite, non-negative, and below the warning threshold;
- `warning`: at or above the warning threshold but not above the hard ceiling;
- `hard_violation`: above the declared ceiling;
- `invalid`: negative, non-numeric, wrong integer shape, or non-finite.

The top-level manifest-compatible status is mechanical: invalid or hard violations are `blocked`;
otherwise missing data is `pending`; otherwise warnings produce `warn`; otherwise the status is
`pass`. `approval_granted` is always false. Invalid non-finite inputs are rendered as strings so the
mapping remains legal canonical JSON with `allow_nan=False`.

### Versioning and calibration

Treat calibration and regression as different activities:

1. Calibrate on the pinned Houdini build, license, fixture revision, machine class, package set, and
   cold/warm-cache condition. Retain the raw observations and choose an explicit safety ceiling.
2. Increment `baseline_version` whenever a ceiling, warning tolerance, fixture, measurement method,
   build, package inventory, or machine class changes. Do not silently replace an older baseline.
3. During regression, compare like with like. A warning is a request to inspect variance or drift;
   it is not proof of a defect. A hard violation blocks only the governed acceptance decision and
   never auto-approves a larger run.

Cook time and peak memory vary with thermals, background pressure, cache warmth, OS/Houdini patch,
and hardware. Calibrate enough repetitions to describe that variance, preserve individual samples,
and use the tolerance band for known noise. Do not loosen thresholds from a single slow observation.
Counts, frames, cache bytes, and render settings can still drift deterministically and remain
independent fields rather than being folded into one score.

## Compatibility expectation and pure diff

`normalize_expectation(expectation)` requires a context, exact Houdini category, exact operator
type, required and optional parameter mappings, and an inclusive tested build range. Parameter
specifications may declare a `type`, a safely observable `default`, both, or neither for presence
only. Required and optional names cannot overlap.

`compare_compatibility(expectation, observation)` is pure. Its result always names the live Houdini
build and license and reports deterministic structured diffs for:

- an out-of-range build or context/category/operator identity drift;
- a missing operator;
- a missing required parameter;
- parameter type or safely observable default drift;
- a live parameter that was not declared required or optional.

Optional parameters may be absent, but any parameter present in the live operator definition must be
declared to keep the expectation complete. A `compatible` boolean is included for convenience, but
the human-readable `diffs` are the governing evidence.

## Read-only Hython adapter

`probe_compatibility(expectation, *, output_path=None)` lazily imports `hou` and reads only node-type
categories and parameter templates. It does not create scene nodes, cook, clear or save a HIP,
change the frame, touch selection, inspect panes, or mutate UI state. It returns the same plain
mapping as the pure comparison plus `mutation_performed: false`.

No file is written by default. When `output_path` is explicit, the adapter creates exactly that JSON
file with exclusive-create mode; it does not create parent directories or overwrite an artifact.
Supported context tokens are `SOP`, `OBJ`, `LOP`, `DOP`, `TOP`, `COP`, `CHOP`, and `APEX` when the
installed `hou` build exposes that category.

The pinned H22 expectation in `tests/hython/test_acceptance_probes.py` came from a read-only
definition probe on Houdini Apprentice `22.0.368`:

```bash
/Applications/Houdini/Houdini22.0.368/Frameworks/Houdini.framework/Versions/22.0/Resources/bin/hython \
  -c 'import hou; print(hou.sopNodeTypeCategory().nodeTypes()["box"].parmTemplates())'
```

The test independently proves the Box SOP match, a deliberate missing/type/default mismatch, stable
repeat output, explicit-only artifact writing, and unchanged frame, HIP path, and scene node set.

## Truthful interpretation

These tools report definitions and declared ceilings only. They make no graph construction,
geometry correctness, pixel fidelity, render success, or human-review claim. Those evidence rungs
must remain `not_applicable` for a standalone Lane C report and be supplied by the appropriate
acceptance tiers after integration.
