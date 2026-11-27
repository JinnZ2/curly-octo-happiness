# EXP-HVD-01 — results, PILOT, H2 only (run 2026-11-27)

Design: `experiments/hidden-variable-detection-causal-discovery-from-residuals.md` § EXP-HVD-01 (issue #63). Gaps: HVD_001, 002, 003, 005, 007, 008, 009.

**This is a PILOT** of the reduced grid the design itself names for the laptop tier ("a × lag × T, linear only, 3 methods"). Only 2 methods were available, so only H2 is tested.

## Provenance

- Repo commit: `a3d5c55328cc671c4384d0a02eccb70c7d828b89`.
- Environment: Python 3.14.8, numpy 2.5.5, tigramite 5.2.10.1; Intel Xeon @ 2.90 GHz, 4 vCPU (shared); 2 worker processes. Runtime 1730 s.
- Commands: `python3 run.py 20 2`, then `python3 summarize.py`.
  - Dataset seed: `seed*7919 + int(100a)*31 + 7*lag + T`.
  - Summary bootstrap: seed 0, 2000 reps, resampling seeds within each cell.
- Raw output: `raw/rows.json` (720 datasets × 2 methods) and `raw/summary.json` (per-cell rates and contrasts).

## Deviations (recorded before results)

1. **H1 not tested.** H1 compares LPCMCI with SVAR-FCI, and SVAR-FCI is not in tigramite. I did not port it. H1 stays **UNCHECKED**.
2. **H3 not tested.** H3 needs neural/score-based and MDL methods, plus nonlinear mechanisms. None were run, so H3 stays **UNCHECKED**.
3. **Reduced grid.**
   - Run: a ∈ {0.2, 0.5, 0.8, 0.95} × latent lag ∈ {0, 1, 2} × T ∈ {200, 1000, 5000}, linear-Gaussian, N_obs = 5, continuous.
   - Fixed: ρ_Z = 0.5. Because persistence is fixed, **H2's second clause ("the gap grows with confounder persistence") is not testable here.**
   - Not run: nonlinear mechanisms, N_obs ∈ {10, 20}, discretised data.
4. **20 seeds per cell, not 50**, for runtime under a shared CPU. Full scale at 50 seeds would need about 2.5× this runtime, roughly 72 min on 2 cores, for this reduced grid alone. The full factorial is cluster-tier, as the design says.
5. **Metric.** The design's primary metric is PAG-F1 against the true PAG, which I did not compute. Instead:
   - Primary: adjacency recall on the one induced latent-confounded pair, X1(t−lag) ↔ X3(t), checked at exactly that lag (lag 0: either direction).
   - Descriptive: LPCMCI's rate of `<->` marks on that pair.
   - Context: false-positive rate on 6 truly non-adjacent pairs with no latent path.

   Checking only the exact lag means an edge found at a neighbouring lag counts as a miss. That likely deflates recall at high autocorrelation.
6. **No mixed-effects model, no Holm correction.** Only one primary (H2) was tested. Contrasts are simple differences with bootstrap CIs.
7. Fixed settings: ParCorr, `tau_max = 3`, `pc_alpha = 0.01` for both methods.

## Results

### H2 contrast, pooled over a and T (12 cells per lag)

Adjacency recall on the induced pair:

| method | lag 0 | lag 1 | lag 2 | recall(lag 0) − recall(lag 1, 2) [95% CI] | FPR on null pairs |
|---|---|---|---|---|---|
| LPCMCI | 0.950 | 0.917 | 0.662 | **+0.160** [+0.125, +0.194] | 0.015 |
| PCMCI+ | 1.000 | 0.750 | 0.508 | **+0.371** [+0.350, +0.390] | 0.003 |

LPCMCI `<->` marks on the induced pair, lag 0 minus lagged: −0.044 [−0.096, +0.010]. On this measure the lagged pairs are *not* worse.

### Per cell

Adjacency recall shown as LPCMCI | PCMCI+, with LPCMCI's `<->` rate in parentheses.

| T | a | lag 0 | lag 1 | lag 2 |
|---|---|---|---|---|
| 200 | 0.2 | 1.00 \| 1.00 (0.00) | 0.95 \| 1.00 (0.20) | 1.00 \| 1.00 (0.10) |
| 200 | 0.5 | 1.00 \| 1.00 (0.10) | 1.00 \| 1.00 (0.20) | 0.85 \| 0.40 (0.30) |
| 200 | 0.8 | 0.90 \| 1.00 (0.15) | 0.85 \| 0.45 (0.60) | 0.45 \| 0.10 (0.35) |
| 200 | 0.95 | 0.75 \| 1.00 (0.50) | 0.90 \| 0.00 (0.60) | 0.05 \| 0.00 (0.00) |
| 1000 | 0.2 | 1.00 \| 1.00 (0.00) | 1.00 \| 1.00 (0.00) | 1.00 \| 1.00 (0.15) |
| 1000 | 0.5 | 1.00 \| 1.00 (0.05) | 1.00 \| 1.00 (0.15) | 1.00 \| 1.00 (0.85) |
| 1000 | 0.8 | 1.00 \| 1.00 (0.50) | 1.00 \| 1.00 (0.65) | 0.30 \| 0.05 (0.15) |
| 1000 | 0.95 | 0.80 \| 1.00 (0.80) | 0.50 \| 0.10 (0.50) | 0.10 \| 0.10 (0.10) |
| 5000 | 0.2 | 1.00 \| 1.00 (0.00) | 1.00 \| 1.00 (0.00) | 1.00 \| 1.00 (0.05) |
| 5000 | 0.5 | 1.00 \| 1.00 (0.55) | 1.00 \| 1.00 (0.80) | 1.00 \| 1.00 (0.80) |
| 5000 | 0.8 | 1.00 \| 1.00 (0.45) | 1.00 \| 1.00 (0.10) | 0.95 \| 0.10 (0.15) |
| 5000 | 0.95 | 0.95 \| 1.00 (0.05) | 0.80 \| 0.45 (0.35) | 0.25 \| 0.35 (0.20) |

Per-cell contrasts with CIs are in `raw/summary.json`. The lag gap is concentrated at high autocorrelation, a ≥ 0.8. At a ∈ {0.2, 0.5} with T ≥ 1000, recall is 1.0 at every lag (ceiling), so the contrast there is 0.

## Verdict vs pre-registered prediction

Prediction: "H2 holds for all methods."
Falsifier: "lagged recall ≥ contemporaneous recall for ≥ half the methods."

**PILOT, SUPPORTED for H2's first clause, on adjacency recall.**

- Both methods show lower recall on lagged confounded pairs, pooled: +0.16 and +0.37, with CIs excluding 0. The falsifier is not triggered.
- Qualifier: the gap is not present in every cell. It is zero at low autocorrelation (ceiling) and concentrated at a ≥ 0.8.
- On LPCMCI's bidirected-mark rate the direction is reversed and not distinguishable from 0. So "lagged confounding is harder" holds for detecting the dependence, not for labelling it latent.
- "Gap grows with persistence": **UNCHECKED** (ρ_Z fixed).
- H1, H3: **UNCHECKED**.

## What this does and does not establish

- **Does:** on a 5-variable linear-Gaussian toy, at 20 seeds per cell, LPCMCI and PCMCI+ miss a lagged latent-confounded adjacency more often than a contemporaneous one when the observed series are strongly autocorrelated (a ≥ 0.8).
- **Does not:**
  - Test the persistence effect, nonlinear data, larger graphs or discretised data.
  - Test SVAR-FCI (H1) or the neural/MDL methods (H3).
  - Give PAG-F1.
  - Show anything about real systems.
  - Rule out an artefact of the exact-lag recall definition (deviation 5), which could inflate the lag gap at high a.
