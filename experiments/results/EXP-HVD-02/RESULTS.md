# EXP-HVD-02 — results (run 2026-11-27)

Design: `experiments/hidden-variable-detection-causal-discovery-from-residuals.md` § EXP-HVD-02 (issue #64). Gap: HVD_010.

## Provenance

- Repo commit: `a3d5c55328cc671c4384d0a02eccb70c7d828b89`. The detector under test is `modules/hnd.py` `HiddenNodeDetector` at that commit.
- Environment: Python 3.14.8, numpy 2.5.5; Intel Xeon @ 2.90 GHz, 4 vCPU (shared). Runtime 395.9 s.
- Command: `python3 run.py 1000 1000`, i.e. 1000 reps per cell for D1 and 1000 for D2. Seeds are fixed per cell: `default_rng(10000*d + 10*T + regime_index)` for D1, `default_rng(777000 + 10*T + regime_index)` for D2.
- Raw output: `raw/results.json` (`d1`, `d2`, `roc`, `env`).

## Deviations (recorded before results)

1. **BiKCD not run.** Its code availability is UNCHECKED and I did not reimplement it. The design's "no prediction" clause for BiKCD therefore stays **UNCHECKED**.
2. **HiddenNodeDetector operationalisation is mine.** The design did not say how a residual-based detector with candidate series should be scored.
   - Residuals: X2's VAR(1) residual.
   - Candidate "C": contemporaneous X1 in every regime (an observed variable, not a latent), plus the true latent Z in the `hidden` regime.
   - Call: `scan(threshold=0.1, acceptance="epsilon_machine")`.
   - Outcomes reported: "returned", "unverified" (too few samples for the ε-machine check, so kept but flagged), and "accepted".
   - Bivariate only.

   A different operationalisation could give different D2 results.
3. **Generator parameters are mine** (fixed before running; see the `run.py` docstring): latent ρ = 0.7 with loading 0.8; instantaneous effect 0.8; wrong lag = true VAR(2) fitted as VAR(1); aggregation k = 3; mean shift +1.0 at T/2.

   Different strengths would change the rates for (ii) and (iv) in particular.
4. **5-variable case (D1):** all 10 pairs tested with Bonferroni correction, family-wise "detect".

## Results

### D1, VAR residual correlation (Fisher z, α = 0.05)

Rejection rate with Wilson 95% CI; 1000 reps per cell.

| regime | d=2, T=200 | d=2, T=1000 | d=5, T=200 | d=5, T=1000 |
|---|---|---|---|---|
| null (Type I) | 0.052 [0.040, 0.068] | 0.052 [0.040, 0.068] | 0.061 [0.048, 0.078] | 0.048 [0.036, 0.063] |
| hidden (power) | 1.00 [0.996, 1] | 1.00 | 1.00 | 1.00 |
| (i) instantaneous | **1.00** [0.996, 1] | **1.00** | **1.00** | **1.00** |
| (ii) wrong lag | 0.046 [0.035, 0.061] | 0.054 [0.042, 0.070] | 0.062 [0.049, 0.079] | 0.050 [0.038, 0.065] |
| (iii) aggregation k=3 | **0.94** [0.92, 0.95] | **1.00** | **0.81** [0.78, 0.83] | **1.00** |
| (iv) mean shift | 0.070 [0.056, 0.088] | 0.089 [0.073, 0.108] | 0.057 [0.044, 0.073] | 0.072 [0.058, 0.090] |

**ROC.** This is the AUC of the D1 statistic (the max over pairs of the Fisher |z| of the residual correlation) for "hidden" vs each regime. Against null, wrong lag and shift it is ≥ 0.9999; against aggregation it is 0.99–1.0.

Against instantaneous the AUC is 0.000–0.011. Instantaneous coupling produces *larger* residual correlation than the latent does here. So a detector that flags "latent" on large |r| ranks the non-latent case above the latent one: the statistic orders the two cases, but in the wrong direction for this purpose.

### D2, HiddenNodeDetector (ε-machine acceptance), bivariate

1000 reps; rates with Wilson CIs in `raw/results.json`.

| regime / candidate | T=200 returned (all "unverified") | T=200 accepted | T=1000 returned | T=1000 accepted |
|---|---|---|---|---|
| hidden / true Z | 0.912 | 0.000 | 0.000 | 0.000 |
| (i) instantaneous / X1 | 0.843 | 0.000 | 0.000 | 0.000 |
| every other regime / X1 | 0.000 | 0.000 | 0.000 | 0.000 |

What happens at each length:

- **T = 200.** The ε-machine check is skipped for lack of samples, so candidates are kept but marked unverified. At this length the detector flags the true latent (91%) and the observed instantaneous parent (84%) at similar rates. It does not separate the two.
- **T = 1000.** The ε-machine criterion rejects every candidate, including the true Z. Under this operationalisation it has zero power and zero false positives, so its specificity is not informative.

## Verdict vs pre-registered prediction

Prediction: "The residual-correlation test fails specificity under (i) and (iii)."
Falsified if: "Type I ≤ 2α for all detectors under all alternatives."

**SUPPORTED** for D1.

- **(i):** Type I = 1.00 under instantaneous coupling.
- **(iii):** Type I = 0.81–1.00 under aggregation.
- **Size:** null Type I is 0.048–0.061, close to α, so the test is calibrated under independence as H1 requires.

Narrower than H1:

- H1 claimed Type I ≫ α under *each* of the four alternatives. Under my generators, (ii) wrong lag (0.046–0.062) and (iv) mean shift (0.057–0.089) stay near α, at most 1.8α. So **H1 as written in full is not supported for (ii) and (iv).** Only the pre-registered prediction, which named (i) and (iii), is.
- The wrong-lag misspecification here does not create contemporaneous residual dependence, which is consistent with that result. Mean shift might at larger shifts, which were not tested.
- D2 gives no evidence of specificity. It either cannot judge the candidates (T = 200) or rejects everything (T = 1000).
- BiKCD: UNCHECKED.

## What this does and does not establish

- **Does:** on these linear-Gaussian toy generators, a residual-correlation "hidden confounder" signal cannot tell a latent common cause from an instantaneous observed edge or from temporal aggregation. The repo's HiddenNodeDetector, as operationalised here, does not resolve this. At short T it keeps both as "unverified"; at longer T it rejects even the true latent.
- **Does not:**
  - Show the same on real data or nonlinear systems.
  - Show anything about BiKCD.
  - Rule out a different HiddenNodeDetector configuration (threshold, tolerance, history length) that separates these cases.
  - Rule out larger misspecifications for (ii) and (iv).
