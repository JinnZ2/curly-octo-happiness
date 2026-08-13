# Plan Forward — curly-octo-happiness × Complexity Engineering / Cybernetics / Robotics

Date: 2026-08-13. Basis: repo deep-read (Notes 01–05) + three research briefs (Notes 06),
all in [`design/notes/`](design/notes/00_INDEX.md).
Framing: the repo already implements proto-versions of all three fields' core machinery. This plan formalizes them in dependency order.

---

## Phase 0 — Ground the existing heuristics in validated theory (small, high-value) — **SHIPPED**

**0.1 HND acceptance criterion via ε-machines** *(complexity)* — **done**
Current HND flags hidden variables when Pearson |r| > 0.5 on residuals. Upgrade: fit causal-state reconstruction (CSSR — tractable on the repo's finite-alphabet Gray-coded bitstreams) before/after adding a candidate hidden node. Accept the node iff statistical complexity $C_\mu = H[\mathcal S]$ *and* entropy rate $h_\mu$ both drop. Replaces an ad-hoc threshold with Crutchfield's minimality theorem.
*Shipped in `grounding/core/epsilon_machine.py` + `HiddenNodeDetector.scan(acceptance="epsilon_machine")`, opt-in so existing callers keep the correlation behaviour. The correlation thresholds became a candidate generator; the ε-machine is the acceptance test, and rejects land in `hnd.rejected`.*
*Two deviations from the sketch, both documented in the source:* (a) only CSSR phases I–II are implemented — no determinisation — so $C_\mu$ is a lower bound and the numbers are only meaningful comparatively; (b) the augmented machine needs a shorter history budget than the baseline (`equalized_history_length`), because a richer conditioning alphabet inflates $C_\mu$ for a purely finite-sample reason. Without that correction the criterion rejected genuine drivers 40% of the time; with it, 39/40 over a seed sweep, with echo variables and noise rejected 40/40. The test is also data-hungry — it separates driver from echo 6/20 times at 60 samples and 19/20 at 300 — so below a sample-density floor it abstains, leaving the candidate *untested* (`hnd.unverified`) rather than refuted.

**0.2 GAE scoring via structural complexity** *(complexity)* — **done**
Compute Sinha–de Weck $C = C_1 + C_2C_3$ ($C_3$ = normalized graph energy) on the dependency-tree DSM alongside C/N/L/R. Use betweenness-centrality variance under *targeted* node removal (Barabási attack tolerance) to trigger TORUS/ICOSAHEDRON recommendations — quantifying why distributed forms are resilient rather than asserting it.
*Shipped in `modules/gae.py`: `graph_energy` (numpy when available, a stdlib Jacobi solver otherwise, so `modules/` keeps networkx as its only hard dependency), and four new always-reported metrics — `graph_energy`, `structural_complexity`, `hub_concentration`, `attack_tolerance`. Score adjustment is behind `complexity_scoring=True` so existing scores stay comparable; when on, `fragility = hub_concentration × (1 − attack_tolerance)` boosts TORUS/ICOSAHEDRON. A 9-node star gets +24; a 9-node ring gets nothing.*

**0.3 Requisite-variety meter** *(cybernetics)* — **done**
Track $H(\text{disturbance codewords})$ vs $H(\text{agent response repertoire})$ per world; alarm when the margin $V(D) - V(R)$ approaches zero. Wire the alarm to band-width auto-expansion (the physics-discovery loop already amplifies variety; give it the missing trigger signal).
*Shipped as `grounding/core/variety.py::VarietyMeter` (Shannon or Ashby-counting variety, optional window) wired into `plugins/physics_discovery.py`: `variety_status(stream)` measures the stream's disturbance variety at 32-bin reference resolution against the codewords the loaded encoders can actually produce, and `run_full_discovery(trigger="variety"|"either")` builds an encoder on that alarm. The two triggers catch different failures — novelty says "I have never seen this", variety says "I can no longer tell these apart" — and only the second fires on in-range data the bands have gone too coarse for.*
*Not done: `grounding/worlds/` is untouched — the meter is wired to the sensor bus, not yet to a world's disturbance/response loop.*

## Phase 1 — Cybernetic architecture (VSM instantiation) — **SHIPPED**

Implemented in `grounding/core/vsm.py` (`ViableSystem`, `Signal`,
`AlgedonicSignal`, `SecondOrderGuard`) and `grounding/core/mentor.py`
(`TeachbackMentor`), wired into `unified_playground.py` behind the commands
`vsm`, `pain`, `self-check`, `explain … :: …`, `teachback … :: …`, `confirm`,
`correct … :: …`, `learned`. Tests in `tests/test_vsm.py`.

**1.1 VSM mapping** — structurally instantiate Beer's five systems:
- S1 = worlds/plugins (autonomous units staking claims)
- S2 = harmony-field trust dynamics + confidence propagation
- S3 = claims/epistemics engine; **S3\* = GAE/HND/FDM as the audit channel**
- S4 = physics-discovery loop + dreams + UnknownJournal horizon scan
- S5 = mentor/governance adjudicating the S3/S4 (exploit/explore) homeostat — the existing self-model error signal is exactly the bid variable S4 needs

*Done as `UnifiedAgent._build_vsm()`: the mapping is a registry signals actually route through, not a comment. S2 damps reports from healthy units; S3 spends attention only on what the audit channel calls actionable.*

**1.2 Algedonic channel** — diagnostic-critical events (thermal-runaway quarantine bit already exists in hardware encoder) must bypass trust-field mediation straight to S5/mentor. Generalize the quarantine override into a first-class `AlgedonicSignal` routed in unified_playground.
*Done. Every `Signal` carries the `path` it travelled, so "it bypassed mediation" is checkable per message: `route()` records S1→S2→S3→S5 and can be attenuated at any hop, `raise_algedonic()` records S1→S5 and consults no mediator. `hardware_scan()` runs every experiment step, so the quarantine override no longer waits for an operator to run `check` on the right component. Added beyond the sketch: the channel is rate-guarded — `saturated()` reports when pain has become the weather, which is itself a diagnosis (either the units are failing en masse or the threshold is too low to mean anything).*

**1.3 Teachback claims (Pask)** — mentor interaction becomes falsifiable: agent reconstructs the mentor's explanation as a claim; mentor confirmation resolves it through the existing Beta-posterior machinery. Concepts are only "learned" after teachback survives.
*Done as `TeachbackMentor`. Two design calls the sketch did not anticipate:* (a) the automatic word-overlap check only votes where it can — reciting the explanation back is decisively **not** reconstruction, but low overlap cannot distinguish "missed it" from "paraphrased in synonyms", so it abstains and waits for the mentor (the same posture as Phase 0's untested-is-not-refuted); (b) a reworded reconstruction goes through `claim.reformulate()` rather than starting a fresh claim, so retrying until something sticks trips the existing escape-hatch counter — and an escape-hatched concept is never `learned()` however good the fourth wording looks.

**1.4 Second-order guard** — cross-validate self-model claims against independent diagnostic streams (HND) to prevent self-confirming self-descriptions (von Foerster eigenvalue drift).
*Done as `SecondOrderGuard`, which keeps history because the failure it exists to catch is invisible in a snapshot: confidence climbing monotonically while independent error refuses to fall. It also flags plain overconfidence. `UnifiedAgent.self_model_check()` feeds it node confidence against world-model error, normalised `err/(1+err)` (raw `avg_error` is in world units, not a probability) and held back until there are ≥5 independent observations to compare against.*

## Phase 2 — World model becomes a good regulator

**2.1 Causal-DAG grounding of worlds** — per Richens & Everitt (2024): make each world's causal structure explicit; score regulator quality by outcome entropy of claim resolutions. The claims tree *is* the homomorphic model the Good Regulator Theorem demands — make the homomorphism checkable (FDM roots as the invariant).

**2.2 Allostatic bands** — percentile bands shift predictively ahead of regime change (use dream-recombination rollouts as the predictor) instead of reactively; log accumulated band-shift cost as "allostatic load."
*Files: plugins/magnetic.py, gravitational.py (init_bands), playground5_dream.py.*

**2.3 Antifragility as a claim type** — in the transition simulator, measure $\partial^2 f/\partial\sigma^2$ of yield-vs-stressor per topology (LINE should be concave, TORUS convex). "Convexity under bounded volatility" becomes a staked, falsifiable claim tracked by Beta posteriors.
*Files: modules/transition.py.*

**2.4 SOC stress layer (optional)** — world variants where hidden variables accumulate stress and release in power-law avalanches; HND detects them by fitting $P(s)\sim s^{-\tau}$ tails in residual events.

## Phase 3 — Robotics embodiment layer

**3.1 CBF-QP safety layer** (~50 lines + a QP solver) over the stewardship simulator: safe sets as claims — $h(x) = T_{max} - T(x)$, plus cold-environment coupled CBFs $h_1 = E_{bat}-E_{min}$, $h_2 = T_{min}-T_{ambient}$. "Repurposed component" ⇒ recompute $h$ on degraded dynamics — provably safe repurposing, not just plausible.

**3.2 Failure-mode → fallback-controller catalog** — the diode→conductor / drift→sensor / open→antenna table becomes a runtime-assurance simplex catalog: each failure mode ships with a repurposed capability AND its recomputed safety envelope.

**3.3 Flow-matching policy on 1-D worlds** — π0-style $\mathcal L_{FM}$ with 10-step Euler decode, conditioned on a "parts vector" from the repurposing engine; evaluate zero-shot transfer when a component is swapped (field-repair proxy benchmark, toy scale).

**3.4 Latent world-model + CEM planner** — V-JEPA 2-AC pattern at toy scale: learn $P(z_{t+1}|z_t,a)$, plan $\arg\min_a\|z_{t+H}-z_{goal}\|$; gives falsification agents the ability to attack *plans*, not just states.

**3.5 HND × self-model damage detection** — hook HND onto any learned dynamics residual $|\dot x - \hat f_\theta(x,u)|$; Lipson-style damage→relearn loop in the sandbox.

**3.6 Neuromorphic encoding alignment** — event-camera Δ-threshold + refractory rule as the adaptive-band update; positions Gray-coded bitstreams as the sensor-fusion bus for scavenged/degrading hardware.

## Phase 4 — Contribution back (novel, unfilled niches)

- **Field-repair robotics dataset/benchmark:** (failure mode, repurposed function, safety envelope) tuples for VLA recovery behavior — a gap in OXE/Droid, acute in cold, parts-scarce environments.
- **Gray-code token embeddings:** verified open niche (Notes 03); Hamming-smooth codes for STE-stable ultra-low-bit tokens.
- **Complexity-instrumented falsification playground:** ε-machine acceptance + graph-energy topology scoring + antifragility claim type = a citable methodology paper.

## Status
Phases 0 and 1 are implemented and tested (`tests/test_epsilon_machine.py`, `tests/test_variety.py`, `tests/test_vsm.py`, the Phase 0 blocks in `tests/test_sds.py`, and the variety tests in `tests/test_plugins.py`); `cd modules && python main.py` runs the diagnostic pipeline with both Phase 0 upgrades enabled, and `python unified_playground.py` exposes the Phase 1 channels. Phases 2–4 are still plan.

Separately, `scripts/hypothesis_engine.py` (design doc `design/hypothesis_engine.md`) implements the research-pipeline half of Phase 4's "contribution back" — it stakes and tests literature claims in this same machinery on a weekly schedule.

## Sequencing rationale
Phase 0 sharpens what exists with no new subsystems. Phase 1 reorganizes control flow (cheap, mostly routing). Phase 2 deepens world fidelity. Phase 3 adds embodiment. Phase 4 packages results. Each phase yields falsifiable claims testable inside the repo itself — the plan eats its own cooking.
