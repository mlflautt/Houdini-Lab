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

## G001 / v0.35 interpretation

G001 targets routine live verification, but parallel lanes start independently at v0.30.0. Lane D
must not claim evidence from Lane A/B/C before integration. The integration captain populates the
candidate matrix from actual merged commands and artifacts.

| Evidence type / tier | G001 candidate requirement | Lane D status | Lane D provenance or reason |
|---|---:|---|---|
| Pure CI | required | `pass` only after recorded full pure/Ruff gates | documentation regression gate; exact result belongs in `docs/grinder/receipts/G001-D.md` |
| Hython read | required integrated | `not_applicable` | documentation-only lane; Lane B/integration owns live evidence |
| Graph edit | required integrated | `not_applicable` | documentation-only lane; no graph claim |
| Single-frame cook | required integrated | `not_applicable` | documentation-only lane; no cook claim |
| Frame range | required integrated | `not_applicable` | documentation-only lane; no range claim |
| PDG child process | required integrated | `not_applicable` | documentation-only lane; no child-process execution |
| Simulation | required integrated | `not_applicable` | documentation-only lane; no simulation execution |
| Viewport | authentic pass or explicit pending at cycle gate | `not_applicable` | documentation-only lane; no pixels produced |
| Karma | authentic pass or explicit pending at cycle gate | `not_applicable` | documentation-only lane; no render produced |
| Plugins disabled | required when plugin behavior is claimed | `not_applicable` | documentation-only lane; operations define the future comparison |
| Plugins enabled | required when plugin output is claimed | `not_applicable` | no plugin installed, enabled, or executed |
| Interactive bridge | separately reported | `not_applicable` | no live bridge run |
| Local model | optional/advisory unless release declares otherwise | `not_applicable` | no model needed for documentation mechanics |
| External model | optional and separately approved | `not_applicable` | no disclosure or network inference performed |
| Human aesthetic review | remains human-owned | `not_applicable` | Lane D has no creative candidate; integrated creative evidence may remain `pending` |
| Downstream-app review | required only for a downstream compatibility claim | `not_applicable` | Lane D makes no downstream-app claim |

For the integrated v0.35 candidate, convert a Lane D `not_applicable` row to the actual integrated
status. If a required runtime was not executed, use `pending` or `blocked`—never retain Lane D's
documentation-only rationale.

## Release sign-off

- Source commit: `[full SHA]`
- Matrix artifact SHA-256: `[hash after finalization]`
- Required rows and policy: `[release declaration]`
- Mechanical overall status: `[pass|warn|pending|blocked]`
- Human aesthetic status: `[pass|warn|pending|blocked|not_applicable]`
- Unaccepted warnings/residual risks: `[list]`
- Release owner and timestamp: `[identity/time]`
- Human decision record, if applicable: `[exact record; never inferred]`
