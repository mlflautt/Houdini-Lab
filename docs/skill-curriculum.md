# Creative skill curriculum

Ten stages from graph literacy to a cross-tool creative pipeline. Full text in
`docs/architecture.md` §14; this lists the stages and the first creative skills to build.

1. **Graph literacy & scene inspection** — three-forms scene via typed tools.
2. **Procedural modeling** — relic generator, modular architecture, alien botanical, terrain, abstract sculpture, ornamental, CNC-ready.
3. **Attributes & VEX** — growth fields, attraction/repulsion, layered noise, generative color, point-cloud choreography.
4. **Motion & audio-reactive** — beat-driven pulses, spectrum fields, visualizers for generated music, MIDI/OSC-controlled HDAs (your music workflow).
5. **Materials, Copernicus, lookdev** — alien surfaces, weathering, procedural glyphs, texture/mask outputs for ComfyUI.
6. **Simulation** — Vellum membranes, RBD fracture, sparse Pyro, FLIP liquid sculpture.
7. **Solaris & USD** — assemble worlds, variant sets, reusable USD components, light/camera rigs.
8. **PDG & variation** — 100 form variants, contact sheets, HDA seed validation, training datasets.
9. **HDA authoring** — namespaces/versions, help, examples, backward compat, source expansion.
10. **Cross-tool pipeline** — Houdini → Blender → ComfyUI → DaVinci Resolve, archived with provenance.

## First implementation roadmap (sprints)
0. Install + capability manifest · 1. Bridge + read-only inspection · 2. Foundational graph editing
· 3. Cook/observation/validation · 4. First skill (`model.fractal_relic` / `world.biobloom_cluster` /
`motion.audio_reactive_field`) · 5. Recipe + HDA system · 6. Local PDG variations · 7. Simulation recipe
· 8. Solaris + lookdev.

## First acceptance test
From a clean Apprentice scene, Hermes must: report build/Python/license/renderer; set+validate
`$JOB`; inspect+summarize graph; checkpoint `.hipnc`; build a readable three-forms SOP network
with stable IDs; expose ≥3 controls + 1 seed; cook display chain within budget; return diff/metrics/
cook time; capture viewport + graph image; Karma CPU preview (Apprentice-compliant); verify no
source overwrite + non-commercial; save versioned `.hipnc`; replay command log into a clean scene
with equivalent results.
