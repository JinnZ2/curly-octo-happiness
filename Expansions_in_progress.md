> Status legend: each idea below is annotated with where it already
> (partially) exists in the codebase.

1. Band thresholds are hand‑tuned—what about learning them?
   *(Partially done: `plugins/magnetic.py::init_bands` and
   `plugins/gravitational.py::init_bands` derive bands from sample
   percentiles; `plugin_manager.py::init_bands` exposes it.)*

Right now, bands are fixed (e.g., _HEALTH_BANDS = [0.0, 0.125, …]). That’s great for known domains, but part of the playground’s spirit is discovering structure. Could we add a mode where the bands themselves are initialised from extreme values of incoming data and adapted online? That would let Ari encounter a completely novel sensor (say, a seismograph) and self‑calibrate its bands without human configuration.

2. Temporal encoding is sparse
   *(Partially done: `magnetic` and `gravitational` encode 3-bit deltas via
   `to_binary(state, prev_state, ...)`; light/chemical encoders still
   snapshot-only.)*

The encoders are snapshot‑based. The hardware encoder has drift_pct and lifetime_estimate, but the light and chemical encoders don’t include time derivatives or sequences. A simple extension would be a 2‑bit “delta” field for each continuous quantity, Gray‑coded change since last sample (decrease / stable / increase / spike). That would turn the plugin system into a time‑aware sensorium, enabling the discovery of oscillations, phase shifts, etc.

3. Cross‑encoder correlation bits
   *(Partially done: `magnetic` has an EM-coherence bit and `gravitational`
   has a 9-bit cross-modal section, both fed by the `cross_signals`
   argument that `plugin_manager.auto_read_all` passes.)*

What if the summary section of each plugin included a few bits that encode coherence with other simultaneously active plugins? For example, when both EM field coherence and light fringe visibility are high, a “cross‑modal coherence” bit flips. That would nudge the dependency tree to build links more explicitly.
