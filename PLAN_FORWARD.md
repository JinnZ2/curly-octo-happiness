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
*Completed later: `ThermalWorld` carries its own `VarietyMeter`, so the disturbance/response loop of a world is now measured, not only the sensor bus (see "A world worth regulating" below).*

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

## Phase 2 — World model becomes a good regulator — **2.1–2.3 SHIPPED**

**2.1 Causal-DAG grounding of worlds** — per Richens & Everitt (2024): make each world's causal structure explicit; score regulator quality by outcome entropy of claim resolutions. The claims tree *is* the homomorphic model the Good Regulator Theorem demands — make the homomorphism checkable (FDM roots as the invariant).
*Done in `grounding/core/regulator.py` (`CausalDAG`, `check_homomorphism`, `regulator_score`) + `BumpyWorld.causal_dag()` + `UnifiedAgent.regulator_check()` behind the `regulator` command. The check earns its keep immediately: Ari's dependency tree preserves only 25% of the world's causal edges, is missing the primitive roots `friction` and `v_t`, and has two **invented** roots — concepts that are sources in the model but have no cause in the world. Unmapped variables are handed to hidden-node detection and journalled rather than swallowed. Collapsing several world variables onto one concept counts as legitimate abstraction, not a broken edge; losing an exogenous root does not.*
*Correction made while wiring: the regulator score must be computed over claims that were actually **tested**, not over `status`. Each experiment evaluates its claim once, so the three-strikes status never resolves — scoring `status` reported a perfect 1.00 for an agent that had resolved nothing.*

**2.2 Allostatic bands** — percentile bands shift predictively ahead of regime change (use dream-recombination rollouts as the predictor) instead of reactively; log accumulated band-shift cost as "allostatic load."
*Done as `grounding/core/allostasis.py::AllostaticBands`: `reactive_update()` (homeostatic catch-up) vs `anticipate(forecast, blend=…)` (allostatic shift), with every shift charged to a cumulative `load` and `chronic()` flagging the pay-forever-fit-never pattern — load rising while coverage does not improve. Wired into `UnifiedAgent.anticipate_bands()` behind the `bands` command, using recombined prediction-error deltas as the rollout.*
*`miscoverage` is measured as band **utilisation** — under-range samples silently clamped into band 0, or bands nothing ever lands in — which is the requisite-variety measure from Phase 0 applied to one encoder's own repertoire. An earlier version counted samples above the top threshold as out of range; by the Gray-code convention the top band is open-ended, so those are covered by construction.*

**2.3 Antifragility as a claim type** — in the transition simulator, measure $\partial^2 f/\partial\sigma^2$ of yield-vs-stressor per topology (LINE should be concave, TORUS convex). "Convexity under bounded volatility" becomes a staked, falsifiable claim tracked by Beta posteriors.
*Done in `modules/transition.py` (`stress_path`, `run_stressed`, `convexity`, `antifragility_claim`, `regime_scan`, `antifragility_report`), measured under a mean-preserving two-point drought spread with common random numbers across σ so the second difference is curvature rather than noise.*
***The prediction is half falsified, and the claim machinery records it.*** LINE is concave as predicted. TORUS is **robust, not antifragile**: its water buffer absorbs the entire spread, so widening the spread neither gains nor costs it much (relative Jensen gap −0.0004). Both convexity claims come back refuted at the default operating point. Two things came out of measuring rather than asserting:
- *Curvature is regime-dependent, not a property of a topology.* A buffer that absorbs **small** stressors bends the response concave at the scale it covers; only a floor capping **large** damage bends it convex. `regime_scan` maps where each topology sits.
- *Convexity is not automatically antifragility.* LINE goes convex under heavy stress purely because yield has bottomed out at zero — losses stop growing because there is nothing left to lose. The measurement therefore carries a viability test, and reports Taleb's full triad (fragile / robust / antifragile) instead of a convexity binary.
- *Sensitivity checked:* strengthening the hormesis term does **not** flip TORUS convex — it makes it more concave, because the hormesis gain sits inside the buffer, so a wider spread only ever loses it. Antifragility here would need capacity built by the stressors that *exceed* the buffer, which is a different mechanism. Left unbuilt: searching for a mechanism that makes the prediction true would be rigging the measurement.

**2.4 SOC stress layer (optional)** — world variants where hidden variables accumulate stress and release in power-law avalanches; HND detects them by fitting $P(s)\sim s^{-\tau}$ tails in residual events.
*Not built — the plan marks it optional and it needs a new world variant rather than an upgrade to an existing one.*

## Phase 3 — Robotics embodiment layer — **3.1–3.2 SHIPPED**

**3.1 CBF-QP safety layer** (~50 lines + a QP solver) over the stewardship simulator: safe sets as claims — $h(x) = T_{max} - T(x)$, plus cold-environment coupled CBFs $h_1 = E_{bat}-E_{min}$, $h_2 = T_{min}-T_{ambient}$. "Repurposed component" ⇒ recompute $h$ on degraded dynamics — provably safe repurposing, not just plausible.
*Done in `grounding/core/safety.py` (`Barrier`, `SafetyFilter`, `safety_claim`, `thermal_barriers`, `battery_barrier`) + `UnifiedAgent.safety_check()` behind the `safety` command.*
***No QP solver dependency.*** The constraint $L_f h + L_g h\,u \ge -\alpha(h)$ is linear in $u$ and the objective is a Euclidean projection, so a single constraint has the closed-form half-space projection and several are handled by Dykstra's alternating projections — stdlib, and honest about its limits (`converged` and `feasible` are both reported). Infeasibility is surfaced as *a finding about the system*, not a solver failure: freezing with no battery to spare genuinely has no safe control, and the filter says so instead of returning a number.
*Safe sets are staked as claims with machine-checkable refutation ($h < 0$ observed), so "this component stayed safe" accumulates a Beta-posterior track record. A **falsified** safety claim raises an algedonic signal — Phase 1's channel carrying Phase 3's evidence.*
*Two modelling notes, both in the source:* heating is taken proportional to current rather than $i^2$ to keep the dynamics control-affine (a real resistive part would need dissipated power as the control, or a nonlinear program); and `VirtualComponent.apply_stress` now takes the ambient temperature, because the component's temperature previously ignored it entirely — the cold-environment barrier could never have bound, which would have made it theatre.

**3.2 Failure-mode → fallback-controller catalog** — the diode→conductor / drift→sensor / open→antenna table becomes a runtime-assurance simplex catalog: each failure mode ships with a repurposed capability AND its recomputed safety envelope.
*Done as `FallbackCatalog` + `UnifiedAgent._build_fallback_catalog()` behind the `fallback` and `catalog` commands. The existing repurpose table supplied the capabilities; what each entry gains is the envelope its **degraded** dynamics support, so a fallback can be refused at a state where the capability plainly exists. The same shorted diode is offered as a conductor at 20 °C and refused at 60 °C, because a part at health 0.25 has a recomputed ceiling of 44.6 °C rather than the nominal 125 °C.*
*Three distinct refusals, because they mean different things: no catalogued fallback (this failure has no known repurposing), outside the recomputed envelope (capability exists, not at this state), and no feasible control (the envelope admits the state but the degraded barriers cannot be satisfied together from here).*

**3.3 Flow-matching policy on 1-D worlds** — π0-style $\mathcal L_{FM}$ with 10-step Euler decode, conditioned on a "parts vector" from the repurposing engine; evaluate zero-shot transfer when a component is swapped (field-repair proxy benchmark, toy scale).

**3.4 Latent world-model + CEM planner** — V-JEPA 2-AC pattern at toy scale: learn $P(z_{t+1}|z_t,a)$, plan $\arg\min_a\|z_{t+H}-z_{goal}\|$; gives falsification agents the ability to attack *plans*, not just states.

**3.5 HND × self-model damage detection** — hook HND onto any learned dynamics residual $|\dot x - \hat f_\theta(x,u)|$; Lipson-style damage→relearn loop in the sandbox. — **SHIPPED, with a caveat that matters**
*Done as `grounding/core/damage.py::DamageDetector` — detection (a Welch-t changepoint on the residual stream) and attribution (which interoceptive signal explains it, by the Phase 0 ε-machine criterion) kept deliberately separate, wired via `UnifiedAgent.damage_scan()` behind the `damage` command. Detection without attribution is a reported state, not an error: the model can know it is wrong without knowing why, and naming an innocent component is worse than admitting ignorance.*
*Three corrections found by measuring rather than reasoning:*
- *The agent had **no body in the loop at all** — component health did not affect the dynamics, so the residual carried zero information about the hardware and there was nothing to detect. Commands now reach the world through `actuator_efficiency()`.*
- *Damage does not have to **raise** the residual. A weakened actuator moves the body less, so its prediction errors get* smaller*. A signed test misses that entirely; the statistic is absolute.*
- *The threshold is a **Welch t, not a Cohen's d**. Actuator failure here separates the per-sample residual distributions by under 1σ while shifting the mean unmistakably — thresholding per-sample separation would miss every real failure.*
***The caveat:*** BumpyWorld's residual is non-stationary even with healthy hardware — position wanders, so error magnitude drifts and the changepoint test fires on a perfectly good model. The detector is validated on synthetic streams with a stationary baseline; *this* world does not provide one. What makes it safe to wire up anyway is the attribution gate: the false positives come back `unattributed`, and relearning requires a named culprit, so a noisy detector never resets a good model. A world with bounded state, or a residual statistic normalised by excursion, is the real fix and is not built.
*Also fixed here, found while chasing the above:* `WorldModel.update` used plain LMS with a fixed rate against an **unbounded** position, so a long run diverged — weights reached ~1e190 after ~240 steps, silently corrupting the regulator score, curiosity signal and every claim outcome downstream. It is normalised LMS now, and the model actually converges (w₀ → 0.99, the true coefficient).

**3.6 Neuromorphic encoding alignment** — event-camera Δ-threshold + refractory rule as the adaptive-band update; positions Gray-coded bitstreams as the sensor-fusion bus for scavenged/degrading hardware. — **SHIPPED**
*Done as `grounding/core/events.py` (`EventEncoder`, `reconstruct`, `fidelity_claim`), wired via `UnifiedAgent.event_encode()` behind the `events` command. Events carry Gray-coded band indices, so the bus is the one the plugin encoders already speak — driven by change instead of by the clock.*
*The threshold is a **band** change with a value hysteresis, not a raw value distance.* The first version used a uniform distance, which lost 53% of band crossings: the repo's bands are equal-occupancy and therefore unevenly spaced in value, so a uniform threshold silently misses crossings exactly where the signal spends its time. An event camera's threshold *is* its quantisation step, so the band edge is the faithful analogue.
*Reporting every band change is lossless by construction and still saves 82% of the traffic on a slow signal — that is the case the stewardship line cares about, where the constraint is a radio budget rather than compute. Everything past that is a trade, and `fidelity_claim` stakes it: hysteresis 0.5 saves 94% at 10% band error and the claim is **refuted**. `retune()` drives the event rate toward a target as a control loop, and the demo shows the trap — it converges on the rate while the band error climbs to ~30%, which is what "retuning without re-staking the fidelity claim" costs.*
*Honest limit: on a fast noisy stream (the agent's own prediction error) lossless encoding saves only ~18%. Event coding wins on slow signals, and the module says so rather than reporting a compression ratio without its error.*


## Phase 4 — Contribution back (novel, unfilled niches)

- **Field-repair robotics dataset/benchmark:** (failure mode, repurposed function, safety envelope) tuples for VLA recovery behavior — a gap in OXE/Droid, acute in cold, parts-scarce environments.
- **Gray-code token embeddings:** verified open niche (Notes 03); Hamming-smooth codes for STE-stable ultra-low-bit tokens.
- **Complexity-instrumented falsification playground:** ε-machine acceptance + graph-energy topology scoring + antifragility claim type = a citable methodology paper.

## Principles the build converged on

These were not in the plan. Each was reached separately, in different phases,
usually by getting it wrong first — which is the only reason they are worth
writing down as principles rather than as preferences.

**Abstain rather than guess when the evidence cannot support a verdict.**
Derived four times independently:
- Phase 0.1 — below a sample-density floor the ε-machine criterion leaves a
  candidate *untested* (`hnd.unverified`) rather than refuted.
- Phase 1.3 — the teachback overlap check votes only where a lexical measure
  can support a verdict; low overlap cannot separate "missed it" from
  "paraphrased in synonyms", so it waits for the mentor.
- Phase 3.5 — damage detection reports `unattributed` rather than naming the
  best-correlated component, because naming an innocent part is worse than
  admitting ignorance.
- `dormancy` — `NEVER_FOLDED` is neither proof of death nor evidence of
  dormancy. A seed's silence and a corpse's silence are identical to any
  measure of flux, so the structural channel is reported separately.

The recurring failure mode is the same each time: a measurement that cannot
distinguish two cases reporting one of them anyway. Four independent
derivations make this the repo's central epistemic commitment, not a habit.

**Derive the shape; disclose the free parameters.** An interior optimum
asserted as a Gaussian bump moves wherever its centre is put. `coupling`
computes the MSF class from the node dynamics instead, and reports Class II
(a threshold, no optimum) for this repo's own thermal units — refusing to
invent the penalty the framework would have liked. `dormancy` takes the
*shape* of Ellis & Roberts and of Landauer without claiming their constants,
and says so on every reading. The test is whether changing a constant changes
the verdict: if it does, the verdict was the constant.

**State what a measurement destroys.** `SeedState.lost` names magnitude,
history and phase explicitly; `events.fidelity_claim` stakes compression so
any bandwidth saving has its band error measured rather than assumed;
`transition`'s viability test refuses to call convexity-while-ruined
antifragility. A lossy step that does not enumerate its losses is
indistinguishable from a lossless one in the record.

**A guess with a default is still a guess.** `fold` used to treat whichever
term came first as the energy budget, which made the answer depend on dict
insertion order. It now refuses and asks. Silent defaults for things only the
caller knows are the quietest way for an assumption to become a result.

## A world worth regulating (added after Phases 0–3)

The recurring bottleneck across every phase was not the machinery but the
substrate. `BumpyWorld` has unbounded state, a non-stationary residual even with
healthy hardware, and — until 3.5 — no body in the loop at all, so the ε-machine
criterion, the changepoint test and the homomorphism check were all pointed at
something that could not hold still long enough to be measured.

`grounding/worlds/thermal.py` closes all three. Hold a part in a temperature band
against mean-reverting cold: bounded (temperature relaxes toward ambient rather
than accumulating), stationary under a fixed policy, control-affine so the CBF
barriers are exactly right for it, and embodied — heater efficiency is a plant
parameter, and `ThermalModel` recovers the true plant to three decimals with the
damage-sensitive gain identifiable to ±0.1.

Two results worth carrying forward:

- **The causal DAG is checked against the code.** `causal_dag()` and `step()` are
  cross-validated by finite-difference sensitivity — both that every declared
  edge is a real dependence, and that undeclared dependences do not exist. A DAG
  that cannot be wrong about the code it describes is not a model of it.
- **Persistent excitation is not optional.** A controller that sets the heater as
  a deterministic function of ambient makes the plant *unidentifiable*: the
  learned gain reads ~0.25 against a true 6.0, forever. Dither 0.4 recovers it
  (residual 0.001, gain 5.999). This is the rigorous version of the repo's
  explore-when-your-model-is-bad rule — exploration here is not curiosity, it is
  the precondition for having a model at all, and a regulator that stops
  exploring loses the ability to notice its own body changing.

Damage detection, which BumpyWorld could not support, works here: 1 false
positive in 12 seeds against 11 detections, and the culprit is *named* rather
than left unattributed. That last part needed a second attribution test —
component health steps between two levels, and the ε-machine criterion is nearly
blind to a signal with no dynamics, so `DamageDetector` now picks a two-sample
test for level signals and the causal-state test for continuous ones.

Also added: a practical-significance floor (`min_shift`). On a well-converged
model the residual is so small and steady that a meaningless wobble is many
standard errors wide — statistical significance without effect size is the
large-n trap, and the caller is the only one who knows what counts as a real
change for their signal.

**Still open on the detector:** repeated online scanning inflates false positives,
because sequential testing is not single testing. A proper sequential test
(CUSUM with a calibrated threshold) is the fix and is not built.

## Status
Phases 0, 1, 2.1–2.3, 3.1–3.2, 3.5 and 3.6 are implemented and tested, plus `ThermalWorld` (above) (`tests/test_epsilon_machine.py`, `tests/test_variety.py`, `tests/test_vsm.py`, `tests/test_regulator.py`, `tests/test_safety.py`, the Phase 0 and 2.3 blocks in `tests/test_sds.py`, and the variety tests in `tests/test_plugins.py`); `cd modules && python main.py` runs the diagnostic pipeline with both Phase 0 upgrades enabled, and `python unified_playground.py` exposes the Phase 1–3 channels (`vsm`, `pain`, `self-check`, `regulator`, `bands`, `safety`, `fallback`, `catalog`, `ambient`, teachback). Phase 2.4, Phases 3.3/3.4 and Phase 4 are still plan. **3.3 and 3.4 are the first items that genuinely need a dependency** — a flow-matching policy and a learned latent planner want the `ml` extra. The tier rule in `pyproject.toml` is what keeps that from eroding the core: extras add capability, they never replace it, and `grounding/` stays stdlib so the stewardship line still runs where there is nothing to install.

Worth reading together: Phase 2 produced the roadmap's first **falsified** predictions — TORUS is robust rather than antifragile, and Ari's dependency tree preserves a quarter of the world's causal structure. Both were staked as claims and refuted by measurement, which is the repo working as designed rather than the plan failing.

Separately, `scripts/hypothesis_engine.py` (design doc `design/hypothesis_engine.md`) implements the research-pipeline half of Phase 4's "contribution back" — it stakes and tests literature claims in this same machinery on a weekly schedule.

## Sequencing rationale
Phase 0 sharpens what exists with no new subsystems. Phase 1 reorganizes control flow (cheap, mostly routing). Phase 2 deepens world fidelity. Phase 3 adds embodiment. Phase 4 packages results. Each phase yields falsifiable claims testable inside the repo itself — the plan eats its own cooking.
