# EXP-RVC-02 — results, phase 1 only (run 2026-11-27)

Design: `experiments/requisite-variety-and-cybernetic-regulation.md` § EXP-RVC-02 (issue #68). Gaps: RVC_005, RVC_006.

## Provenance

- Repo commit: `a3d5c55328cc671c4384d0a02eccb70c7d828b89`.
- Environment: Python 3.14.8, numpy 2.5.5, scikit-learn 1.9.1; Intel Xeon @ 2.90 GHz, 4 vCPU (shared). Runtime 463.6 s.
- Command: `python3 experiments/results/EXP-RVC-02/run.py`.
  - A first attempt under a 1200 s `timeout` was killed by the timeout after 3 of 8 strata, on a heavily loaded CPU. The re-run is deterministic, and its first 3 strata are identical to the killed run's printed output.
- Seeds:
  - Regulator runs: `1000*delta + 100*m_idx + 10*eps_idx + 3*c + s`, s ∈ {0, 1, 2}.
  - Repertoire subset: seed 1.
  - Random outcome table: seed 0.
  - CV folds and bootstraps: seed 42 per stratum.
- Raw output: `raw/results.json` (`summary` per stratum; `rows` = 960 regulator runs).

## Deviations (recorded before results)

1. **Phase 2 (field data) not run.** It needs a partner SOC dataset or hand-coded World Bank IEG appraisal documents with two coders (human labels). Phase 2, and with it the prediction "in field data the sign holds but the effect is small", stays **UNCHECKED**. The design's power clause (odds ratio 1.5 per bit, power ≥ 0.8) applies to phase 2 and was not evaluated.
2. **New simulator instead of an extension.** The design said to extend `experiments/sketches/variety_sim.py`. I wrote a standalone simulator (`run.py`) with the three requested extensions: response delay, a non-injective outcome table, and a capacity limit. The sketch is untouched. All game parameters were fixed in the docstring before running.
3. **"Within a deadline"** is operationalised as the same step. A disturbance that gets no response (over capacity) fails unless d = 0.
4. **I(D;R) is a plug-in estimate** from 8000 (d, r) pairs, with no bias correction. "No response" counts as an extra R symbol.
5. **Comparison metric:** held-out log-loss per disturbance, from 5-fold CV over regulators (120 per stratum), with a 2000-rep bootstrap CI over regulators. The slope CI uses 500 bootstrap reps.

## Results

The game has 8 disturbance classes, H(D) = 3 bits, and k = 2 disturbances per step. There are 120 regulators per (table, delay) stratum.

"Δ log-loss" is log-loss(I(D;R) margin) − log-loss(log|R| margin), in nats per disturbance. **Negative means I(D;R) predicts better.** The slope is the logistic coefficient of failure on I(D;R) − H(D), per bit.

| table | delay | I(D;R) range (bits) | Δ log-loss [95% CI] | slope on margin [95% CI] | Spearman(fail, margin) |
|---|---|---|---|---|---|
| latin (injective) | 0 | 0–3.0 | **−0.0245** [−0.0440, −0.0087] | −1.51 [−1.68, −1.36] | −0.94 |
| latin | 1 | 0–0.78 | **−0.0071** [−0.0109, −0.0040] | −2.99 [−3.22, −2.85] | −0.95 |
| latin | 2 | 0–0.23 | **−0.0026** [−0.0037, −0.0016] | −5.94 [−6.43, −5.67] | −0.96 |
| latin | 4 | 0–0.03 | **+0.0005** [+0.0003, +0.0007] | −0.55 [−0.56, −0.55] | −0.79 |
| random (non-injective) | 0 | 0–2.75 | −0.0145 [−0.0346, +0.0020] | −1.67 [−1.92, −1.46] | −0.74 |
| random | 1 | 0–0.71 | **−0.0045** [−0.0092, −0.0002] | −3.74 [−4.13, −3.49] | −0.67 |
| random | 2 | 0–0.21 | **−0.0024** [−0.0045, −0.0004] | −8.60 [−9.58, −7.95] | −0.69 |
| random | 4 | 0–0.02 | **+0.0029** [+0.0015, +0.0044] | −0.59 [−0.62, −0.57] | −0.65 |

Log-loss for H(R) − H(D) is in the json. It is close to log|R| in every stratum.

What the table shows:

- **Margin and failure.** Failure falls as the margin rises in all 8 strata; the slope CI excludes 0 every time.
- **I(D;R) vs log|R|.** I(D;R) beats log|R| at delays 0–2: 6/6 point estimates, and 5/6 CIs exclude 0 (random, δ = 0 does not). At delay 4, log|R| predicts better in both tables, with CIs excluding 0.
- **Size of the advantage.** It is small in absolute terms, and it shrinks monotonically with delay: −0.0245 → −0.0071 → −0.0026 → +0.0005 nats per disturbance (latin).
- **Why it reverses at delay 4.** The class persists with probability 0.5 per step, so after 4 steps true I(D;R) is at most about 0.03 bits. That is comparable to the plug-in bias, roughly \((|D|-1)(|R|-1)/(2N\ln 2) \approx 0.005\) bits per run. The I(D;R) margin is then mostly estimator noise, while log|R| still carries the capacity information.

## Verdict vs pre-registered prediction (phase 1)

Prediction for simulation: "H1 holds in simulation". The design adds that the margin predicts failure in the injective case by construction and loses predictive power as delay grows.

Falsifiers:

- **Margin coefficient CI includes 0:** not met. The slope CI excludes 0 in all strata.
- **"log|R| predicts as well as I(D;R)":** not met at delay ≤ 2, **met at delay 4.**

**Verdict: SUPPORTED for delay ≤ 2, FALSIFIED at delay 4.**

- The pre-registration did not say up to which delay H1 should hold. So I report both halves rather than pick one.
- The shrinking advantage matches the stated expectation ("loses predictive power as delay grows").
- The reversal at delay 4 is a measurement limit of the plug-in I(D;R), not a property of regulation. That is itself a finding about the pipeline.

## What this does and does not establish

- **Does:** in this toy regulation game, a plug-in I(D;R) − H(D) margin computed from (d, r) logs orders regulators by failure rate. It beats a capability count when responses are informative, including with a non-injective outcome table and capacity limits. It stops beating the count once delay drives true I(D;R) toward the estimator's bias. This checks the measurement pipeline only, as the design says.
- **Does not:**
  - Say anything about real SOC or project data (phase 2 UNCHECKED).
  - Say anything about Ashby's law, which is a theorem in its own setting.
  - Show that the effect sizes transfer: they depend on game parameters I chose.
  - Say anything about bias-corrected estimators (not run).
