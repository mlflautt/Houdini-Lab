# `simulate.mpm_matter_sculpture@1.0.0`

Builds one editable Houdini 22 SOP MPM network containing granular-like, elastic-like, and
viscous-like source volumes. The three sources interact in one deterministic proxy solve above an
explicit tilted collider and ground plane. Names describe creative starting behavior; they are not
claims of calibrated physical identity.

The normal skill is intentionally limited to 24 frames and 150,000 particles. Its File Cache uses
`filemode=none`, and the MPM Solver's disk checkpoints remain disabled. Each frame updates a durable
progress manifest before the next cook, so an interrupted validation records its completed frames.
Actual cache writes and the roadmap's one-million-particle ceiling require a separate approved job.

The public output Switch selects native particles or a native MPM Surface. It is an artist choice,
not automatic ranking. Human rating slots stay empty, and optional visual/model verification remains
advisory.

The final Houdini 22.0.368 acceptance cooked all 24 frames in 2.80 seconds after kernel warm-up,
retained 1,643 particles, measured 1.795 units of centroid motion, and completed every progress
entry without creating its configured cache directory. The final 768×432 Karma evidence passed the
deterministic visual gate after two preserved camera-framing iterations.
