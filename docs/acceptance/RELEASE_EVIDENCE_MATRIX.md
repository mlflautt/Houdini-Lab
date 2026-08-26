# Release Evidence Matrix

This is the reusable release ledger for Hermes Houdini. Copy the blank matrix per release and bind
each populated cell to one immutable source commit, environment identity, command, artifact/hash,
reviewer, and time. Never replace it with one release-wide green check.

## Status vocabulary

| Status | Meaning |
|---|---|
| `pass` | applicable evidence ran, met its declared contract, and an authorized reviewer promoted it |
| `warn` | applicable evidence completed without a release-blocking failure but has a specific accepted caveat |
| `pending` | applicable evidence has not run, is awaiting review, or lacks promotable provenance |
| `blocked` | an applicable required gate cannot proceed or failed its contract |
| `not_applicable` | the release/lane makes no claim requiring the gate; a concrete reason is mandatory |

Mechanical overall status follows the accepted G001 contract: `blocked` if any required cell
blocks; otherwise `pending` if a required cell was not run; otherwise `warn` if an applicable cell
warns; otherwise `pass`. Human taste never participates in an automatic aggregate.

## Evidence identity and minimum provenance

Every applicable row records:

- repository/commit and dirty-state result;
- acceptance schema and tier, exact command, start time, duration, and exit state;
- macOS/architecture, Python, Houdini build/license, package/plugin inventory, and hardware identity
  when relevant;
- fixture/source revision, declared budget, observed metrics, artifact paths/bytes/SHA-256;
- warnings/errors, reviewer, review time, and status reason;
- dependencies on other evidence rows and any explicit human decision.

A path without a hash is not durable provenance. A hash without environment/source identity is not
runtime proof. A structurally valid image is not aesthetic approval.

## Blank reusable matrix

Replace bracketed fields; do not delete unrun rows.

| Evidence type / tier | Required? | Status | Provenance or pending/not-applicable reason | Promoter | Depends on |
|---|---:|---|---|---|---|
| Pure CI | `[yes/no]` | `pending` | `[commit; workflow/local command; Python; result; log/hash]` | technical reviewer | source identity |
| Hython read | `[yes/no]` | `pending` | `[command; H build/license/package inventory; no-cook proof; log/hash]` | Houdini technical reviewer | pure CI, environment identity |
| Graph edit | `[yes/no]` | `pending` | `[fixture; exact node types/connections/stable IDs; checkpoint/graph hashes]` | Houdini technical reviewer | Hython read, approval |
| Single-frame cook | `[yes/no]` | `pending` | `[node/scope/frame; budget/observed metrics; validation/hash]` | Houdini technical reviewer | graph edit |
| Frame range | `[yes/no]` | `pending` | `[inclusive range; per-frame/peak metrics; frame restoration; cache/hash]` | Houdini technical reviewer | graph edit |
| PDG child process | `[yes/no]` | `pending` | `[TOP/child commands; process identities; aggregate budgets; cleanup/hash]` | runtime/security reviewer | Hython read, process policy |
| Simulation | `[yes/no]` | `pending` | `[solver/substeps/range/cache policy; metrics; validation/hash]` | Houdini technical reviewer | graph edit, frame range |
| Viewport | `[yes/no]` | `pending` | `[viewer/viewport/camera/frame/resolution; authentic PNG/report hashes]` | visual-mechanics reviewer | graph/data, isolated UI |
| Karma | `[yes/no]` | `pending` | `[Karma CPU; frame/resolution/threads/time/bytes; render/report hashes]` | render reviewer | graph/data, external-process approval |
| Plugins disabled | `[yes/no]` | `pending` | `[isolated package path/skiplist; inventory; native fixture; hashes]` | plugin owner | Hython identity |
| Plugins enabled | `[yes/no]` | `pending` | `[exact package/build/checksum/operators; fixture and disable proof hashes]` | plugin owner | plugins-disabled baseline |
| Interactive bridge | `[yes/no]` | `pending` | `[loopback/auth/session/approval transcript hashes; cleanup]` | runtime/security reviewer | Hython identity, bridge policy |
| Local model | `[yes/no]` | `pending` | `[model/digest/calibration; packet/request/response/artifact hashes]` | model reviewer | authentic evidence, consent |
| External model | `[yes/no]` | `pending` | `[provider/model/data/consent/retention; hashes]` | model + privacy reviewer | authentic evidence, network approval |
| Human aesthetic review | `[yes/no]` | `pending` | `[reviewer; exact feedback; artifact hashes; rating/selection or reason pending]` | human artist/reviewer only | authentic stable-order evidence |
| Downstream-app review | `[yes/no]` | `pending` | `[app/build/import settings; input/output hashes; reviewer receipt]` | downstream-app owner | promoted source artifact |

## Promotion authority

| Evidence | Who may promote | Cannot establish |
|---|---|---|
| Pure CI/schema/policy | technical reviewer or protected CI | Houdini runtime, pixels, taste |
| Hython/graph/cook/frame/PDG/simulation | Houdini technical reviewer | authentic interactive pixels or taste unless separately evidenced |
| Viewport/Karma mechanics | visual/render reviewer | aesthetic usefulness or downstream acceptance |
| Plugin disabled/enabled | plugin owner for exact package and exercised nodes | catalog-wide plugin safety |
| Interactive bridge | runtime/security reviewer | safety outside the tested mode/host |
| Local/external model | model reviewer; privacy reviewer also required for external disclosure | winner, human rating, or universal taste |
| Human aesthetic | identified human reviewer | mechanical correctness outside reviewed artifacts |
| Downstream app | owner/reviewer of the named app pipeline | other apps or future import settings |
| Release readiness | release owner, from the row statuses | authority to rewrite row evidence or infer missing gates |

## Drift and invalidation rules

Evidence is immutable; drift creates a new row/run rather than editing old provenance.

| Drift | Evidence invalidated |
|---|---|
| Code or dependency lock | pure CI and every runtime/model/downstream result executing or interpreting that code; rerun affected descendants |
| Fixture/recipe/HDA/skill or seed policy | graph and every dependent data/pixel/model/human/downstream cell for that fixture |
| Houdini build or license mode | all Hython, graph, cook, range, PDG, simulation, viewport, Karma, bridge, and plugin evidence |
| Package inventory or environment variables | all Houdini runtime evidence unless the difference is proven irrelevant and accepted as `warn`; plugin rows always rerun |
| Plugin version/checksum/load state | plugin-enabled row and all outputs using it; disabled baseline reruns if package discovery changed |
| Hardware/OS/architecture | performance baselines and process/render evidence; functional evidence is at least `warn` pending compatibility review |
| Camera/viewer/render settings | viewport/Karma and dependent model/human/downstream reviews |
| Artifact bytes/hash | that cell and every dependent model/human/downstream cell |
| Model/provider/prompt/schema/calibration | corresponding model evidence; human evidence remains bound to its original artifacts |
| Downstream app/build/import settings | downstream row only, unless it produces an artifact used elsewhere |
| Human feedback or candidate ordering | never rewrite prior review; append a new review/lineage record |

## G001 / v0.35 integrated candidate

This matrix binds the integrated code gates to source commit
`d9841f7fd01f5821374c9ff8045609694c6b5b4c`. The final acceptance packet is
`/private/tmp/hermes-v035-acceptance-20260825-03/acceptance-summary.json`: canonical semantic hash
`1945c004d4d3c555f03c7396dc7aebfc8ed4546d336b27d5f87ebd41b474c196`, file SHA-256
`be4e3d71f299d8ec19e15330a7811768befb6852ebc450f47e06caf64e753ea8`. It records a clean source
tree, package `0.35.0`, Python 3.13.10, Houdini Apprentice 22.0.368, SideFX Labs loaded, and MOPs
absent. Documentation-only changes after this source commit do not alter the tested package or
fixtures; any code, fixture, dependency, or runtime drift invalidates the affected evidence.

`Required? yes` below means that row must pass for the G001 technical exit. `report` means its
independent status must be preserved, while actual execution was not a G001 exit requirement.

| Evidence type / tier | Required? | Status | Provenance or pending/not-applicable reason | Promoter | Depends on |
|---|---:|---|---|---|---|
| Pure CI | yes | `pass` | final native acceptance: 225 passed in 4.39s; standalone restricted run: 221 passed, 4 skipped; Ruff and whitespace pass | technical reviewer | clean source identity |
| Hython read | yes | `pass` | no-cook `/obj` read plus exact H22 `Sop/box` compatibility; frame 1 and dirty state preserved | Houdini technical reviewer | pure CI, build/license identity |
| Graph edit | yes | `pass` | 38 stable-ID native nodes; no forced cook; rebuildable `.hipnc`, 408,264 bytes, SHA-256 `dfcdef5fd206875b1b1d295e40d21160f9db58525bf87bd68d17fb5f9106ba97` | Houdini technical reviewer | Hython read, accepted G001 graph envelope |
| Single-frame cook | yes | `pass` | frame 1; 8 points, 6 primitives, 3,544 bytes; 0.000848s cook; resource baseline pass; frame restored | Houdini technical reviewer | graph edit |
| Frame range | yes | `pass` | inclusive frames 1–3; each 8 points/6 primitives/3,544 bytes; 0.001029s aggregate cook; baseline pass; frame restored | Houdini technical reviewer | graph edit |
| PDG child process | report | `pending` | adapter and refusal tests pass; no separate external-process authorization was supplied and no child ran | runtime/security reviewer | Hython read, external-process approval |
| Simulation | report | `pending` | managed Solver fixture and refusal tests pass; no separate simulation authorization was supplied and no simulation ran | Houdini technical reviewer | graph edit, simulation approval |
| Viewport | report | `pending` | adapter requires separate `--allow-viewport`; final Hython packet had no interactive viewer and produced no PNG | visual-mechanics reviewer | graph/data, isolated UI approval |
| Karma | report | `pending` | adapter requires separate `--allow-karma`; no v0.35 render/external-process authorization was supplied and no render ran | render reviewer | graph/data, render and external-process approval |
| Plugins disabled | conditional | `not_applicable` | G001 makes no plugin-behavior claim; package inventory only reports current state | plugin owner | Hython identity |
| Plugins enabled | conditional | `not_applicable` | SideFX Labs was discoverable but no plugin node/output was exercised or certified by G001 | plugin owner | plugins-disabled proof when a plugin claim exists |
| Interactive bridge | report | `not_applicable` | G001 validates the local acceptance CLI, not a bridge roundtrip; v0.30 bridge proof is not relabeled as v0.35 evidence | runtime/security reviewer | bridge-specific request |
| Local model | no | `not_applicable` | no model is needed for these mechanical infrastructure gates | model reviewer | authentic evidence, consent |
| External model | no | `not_applicable` | no disclosure, endpoint, or external inference was requested | model + privacy reviewer | explicit network approval |
| Human aesthetic review | no | `not_applicable` | infrastructure release has no creative candidate, rating, or winner to judge | human artist/reviewer only | authentic creative candidates |
| Downstream-app review | no | `not_applicable` | G001 makes no Blender, Resolve, or other consumer compatibility claim | downstream-app owner | promoted source artifact |

## Release sign-off

- Source commit: `d9841f7fd01f5821374c9ff8045609694c6b5b4c`
- Matrix artifact SHA-256: recorded after finalization in `docs/grinder/receipts/G001-I.md` to avoid
  embedding a self-invalidating file hash
- Required rows and policy: core pure/Hython/graph/single/range gates; independent status reporting
  for PDG, simulation, viewport, Karma, plugin, bridge, model, human, and downstream evidence
- Mechanical overall status: `pass`
- Human aesthetic status: `not_applicable` — no creative candidate exists in this infrastructure release
- Unaccepted warnings/residual risks: PDG, simulation, viewport, and Karma execution remain pending;
  self-hosted runner activation remains blocked by its separate threat-model checklist
- Release owner and timestamp: integration captain technical sign-off, `2026-08-25` America/Chicago
- Human decision record, if applicable: none; no rating, winner, or continuation choice was inferred
