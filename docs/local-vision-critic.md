# Sprint 24 — Bounded Local Visual Critic

Sprint 24 adds an optional interpretive rung after structural validation and deterministic image
mechanics. It does not replace either gate and does not automate taste. The local critic may explain
likely visual problems and propose bounded next edits; only a human may choose a creative winner or
record a human rating.

## Contract

The pure-Python adapter in `hermes_houdini/local_critic.py` exposes three registered operations:

- `verification.local_critic.probe@1.0.0` reads `/api/tags` from an already-running Ollama service
  and can write a durable probe report;
- `verification.local_critic.run@1.0.0` sends one hashed critique packet and its PNG evidence;
- `verification.local_critic.calibrate@1.0.0` scores saved responses against known failures.
- `verification.local_critic.corpus.build@1.0.0` materializes deterministic PNGs, visual reports,
  and hashed critique packets for those failures.

Probe and inference are `external` operations even though the endpoint is local. The adapter accepts
only `http://127.0.0.1:<port>` with no path, credentials, query, or redirect target in configuration.
It never calls a pull endpoint, starts Ollama, or downloads a model. Inference requires
`enabled=true`, an already-installed exact allowlisted model, a bounded timeout, byte limits, and a
fresh output path. The initial allowlist is `qwen3-vl:4b`, `qwen3-vl:8b`, and
`qwen3-vl:8b-instruct`; unversioned `latest`, cloud models, and arbitrary registry names are rejected.

Ollama's official API documents `GET /api/tags` for installed-model discovery and JSON-schema
structured output on the chat API. Its official Qwen3-VL library identifies the 4B and 8B variants
as image-capable. The 8B model is the routine target on this 64 GB workstation; 4B remains a lighter
diagnostic alternative. Model installation is a separate, explicitly approved operation.

## Evidence and response policy

The input must be `hermes.multimodal_critique_packet@1.0`. Before transmission the adapter rereads
every artifact and verifies its byte count and SHA-256, preventing stale renders or code from being
rationalized after packet creation. Only PNG image evidence is encoded. Bounded text excerpts from
the graph, validation, and source artifacts provide intent context.

The response is schema-constrained and then validated again locally. It records:

- mechanical status and a closed list of mechanical issue labels;
- evidence-linked observations, uncertainties, and bounded suggested edits;
- model, loopback endpoint, packet and artifact hashes, prompt/request/response hashes, and runtime;
- explicit proof that no model download or service start occurred.

Every response is `available_unverified` until calibration passes. `winner` and `human_rating` are
always null, `automatic_ranking` is false, and decision authority remains `advisory_only`.

## Calibration gate

`tests/fixtures/local_critic_calibration.json` defines the minimum known failures: crushed black,
blown white, a missing comparison panel, and duplicate motion frames. The scorer consumes saved
responses tagged with `calibration_case_id`. All responses must use the real local-critique schema
and carry one identical model name/digest identity. Calibration passes only when every case is
present, recall is 100%, and precision is at least 80%. Missing a hard failure leaves the model
`available_unverified`.

The corpus is deliberately mechanical. It tests whether a model can reduce human troubleshooting,
not whether its taste is good. Future project-specific aesthetic rubrics must be learned from
explicit human annotations and must preserve candidates, lineage, and empty human-owned selection
fields.

## Current host acceptance

On 2026-08-24 the Ollama 0.32.15 client and service were present with nine installed text models,
but no exact allowlisted Qwen3-VL model. Sprint 24 therefore validates the
`available_no_allowlisted_model` state without starting a daemon or downloading Qwen3-VL. Live model
calibration remains pending explicit installation/run approval.

Acceptance evidence:

- 152 pure-Python tests pass and four Houdini-only tests skip outside Houdini;
- 33 Hython integration tests pass under Houdini Apprentice 22.0.368;
- `plugins/evidence/local-critic-host-probe-0.32.15.json` records the non-mutating host probe with
  SHA-256 `5216fb7c101f7af64bc5d2d4be11b4ddbce470685a418cebcfac84a4d73bd512`;
- `houdini_creative_dev-0.24.0-py3-none-any.whl` builds with SHA-256
  `c44a198383755512f0cdcea12314b4ad863aabbbb2bde32415dc0a2213edf4a8`.
