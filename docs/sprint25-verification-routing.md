# Sprint 25 — Verification Routing and Human Review Gates

Sprint 25 turns the verification ladder into a deterministic routing artifact. It decides what kind
of evidence or review comes next; it does not repair a graph, run a model, contact an external
provider, rank candidates, or choose a winner.

`verification.route@1.0.0` reads one or more structural reports, one deterministic visual report,
and optional local-probe, local-critique, and calibration reports. Every path must be inside an
explicit narrow `project_root`, every input is hashed into the result, and the output is a new JSON
artifact using `hermes.verification_route@1.0`.

## Routing contract

| Evidence state | Next action | Human review now? |
|---|---|---|
| Mechanical failure | Repair and rerun deterministic gates | Only for structural/pixel conflict |
| Mechanical warning | Bounded refinement, then reverify | No, unless final taste requested |
| Pass; local model unavailable | Continue, with local critique optional | No |
| Pass; local critic uncalibrated | Calibrate it or continue to human taste | No reduction in review |
| Calibrated critic disagrees | Preserve both reports | Yes |
| Final taste requested | Preserve candidates and lineage | Yes |

The mechanical gate is the worst normalized status across structural and pixel evidence. Model
output is never allowed to change it. A local critique is `calibrated` only when its complete model
identity exactly matches the identity in a passing Sprint 24 calibration report. A same-name model
with a different digest remains `available_unverified`.

## External and human boundaries

`external_critic_requested` and `allow_external` are policy inputs, not network actions. Without the
explicit allow flag, the route says `explicit_approval_required`. Even with it, any mechanical
failure yields `blocked_by_mechanical_gate`; otherwise the output only says
`eligible_advisory_only`. `execution_performed` remains false.

Human review triggers are narrow and named:

- a structural report passes while rendered pixels fail, or vice versa;
- a calibration-matched local critic disagrees with deterministic evidence;
- the workflow reaches an explicitly requested final taste choice.

If deterministic evidence still fails, a requested taste review is deferred until the mechanical
gate passes; the artist is not asked to judge a knowingly broken proof.

The route always stores `automatic_ranking=false`, `winner=null`, and `human_rating=null`. This
keeps troubleshooting automatable while preserving creative selection, rejected alternatives, and
uncertainty for the artist.

## Acceptance

The Sprint 23 staged reliquary's two structural reports and deterministic visual report all pass.
Routing them with Sprint 24's host probe produces `ready_with_optional_local_critic_unavailable`:
the work is mechanically ready, no model is required, and final taste remains available to the
human when desired. The tracked route is
`plugins/evidence/sprint25-verification-route-acceptance.json`, SHA-256
`0d05bab284e3be828bd55f10cf4440201b4f6aadd4845a02da991871325fd1e3`.

Verification completes with 158 pure-Python passes, four expected non-Houdini skips, 33 Hython
integration passes under Houdini Apprentice 22.0.368, clean Ruff and diff checks, and package wheel
`houdini_creative_dev-0.25.0-py3-none-any.whl` SHA-256
`2870a1cd6ece8a5084cd9d333d4160bc9216e727c1994005ec1b40f562eee2e2`.
