# EXP-HVD-04 — results, PILOT (run 2026-11-27)

Design: `experiments/hidden-variable-detection-causal-discovery-from-residuals.md` § EXP-HVD-04 (issue #66). Gaps: HVD_001, HVD_003, HVD_009.

**This is a PILOT** (reduced scale; see deviations). It is not the pre-registered full run.

## Provenance

- Repo commit: `a3d5c55328cc671c4384d0a02eccb70c7d828b89`.
- Environment: Python 3.14.8, numpy 2.5.5, scipy 1.18.1, tigramite 5.2.10.1; Intel Xeon @ 2.90 GHz, 4 vCPU (shared); 2 worker processes. Runtime 1253 s.
- Data: NetSim (Smith et al. 2011), [FMRIB NetSim page](https://www.fmrib.ox.ac.uk/datasets/netsim/), `sims.tar.gz` sha256 `fec5040650e40c059dbe76199c9efb38e61aa414c5ca4a8841822633a7981a21`. The design's "availability UNCHECKED" is now resolved: the data is public and was downloaded on 2026-11-27.
- Commands: `python3 run.py /tmp/netsim 10 2`, then `python3 summarize.py`. Methods are deterministic. The summary bootstrap uses seed 0 and 2000 reps, resampling (sim, subject) units.
- Raw output: `raw/rows.json` (438 jobs, one per sim × subject × eligible node) and `raw/summary.json`.

## Deviations (recorded before results)

1. **PILOT scale.** 10 of 50 subjects per simulation. Full scale would need about 5× the 21 min runtime here, roughly 1.75 h on 2 cores, plus sim4.
2. **sim4 (50 nodes) excluded** for runtime.
3. **Methods.** LPCMCI and PCMCI+ only, both ParCorr, `tau_max = 1`, `pc_alpha = 0.01`, fixed in the script before running. SVAR-FCI is not in tigramite, and the neural/MDL methods of EXP-HVD-01 were not run. "Methods as in EXP-HVD-01" is therefore covered for 2 methods, one of which (PCMCI+) ignores latents.
4. **Operationalisation (mine, fixed in the `run.py` docstring before running).**
   - Network orientation: `net[i, j] ≠ 0` read as i → j.
   - Eligible node: one with ≥ 2 children.
   - Induced pair: two children of the deleted node that are not directly connected.
   - Recall: the fraction of induced pairs output as adjacent (any mark, lag ≤ 1).
   - Density-matched random baseline: the adjacency rate on control pairs in the same run. Control pairs are non-adjacent in the true net and not both neighbours of the deleted node.
   - LPCMCI's rate of `<->` marks on induced pairs is reported descriptively. No bidirected-mark baseline was computed.
5. **"Report results per sampling rate".** I report per session length (Nt) and per simulation. I did not tabulate TR per simulation from the NetSim documentation, so sampling-rate stratification is only approximate here (**UNCHECKED**).
6. **Excluded sims:** sim14 and sim16 have no eligible node with both an induced and a control pair. In total, 408 of 438 jobs enter the summary.

## Results

Recall on induced pairs vs control-pair baseline, mean over rows; the diff CI resamples (sim, subject) units.

| stratum | rows | LPCMCI recall / baseline | LPCMCI diff [95% CI] | LPCMCI `<->` on induced | PCMCI+ recall / baseline | PCMCI+ diff [95% CI] |
|---|---|---|---|---|---|---|
| all | 408 | 0.335 / 0.110 | **+0.225** [+0.174, +0.273] | 0.05 | 0.362 / 0.114 | **+0.248** [+0.198, +0.302] |
| Nt = 50 | 20 | 0.20 / 0.00 | +0.20 [+0.05, +0.40] | 0.00 | 0.20 / 0.00 | +0.20 [+0.05, +0.40] |
| Nt = 100 | 20 | 0.00 / 0.00 | 0.00 [0, 0] | 0.00 | 0.00 / 0.025 | −0.025 [−0.075, 0] |
| Nt = 200 | 288 | 0.255 / 0.095 | **+0.160** [+0.112, +0.214] | 0.03 | 0.269 / 0.078 | **+0.191** [+0.140, +0.251] |
| Nt = 1200 | 40 | 0.725 / 0.087 | **+0.638** [+0.502, +0.750] | 0.10 | 0.775 / 0.037 | **+0.738** [+0.612, +0.846] |
| Nt = 2400 | 20 | 0.55 / 0.10 | +0.45 [+0.25, +0.675] | 0.20 | 0.80 / 0.575 | +0.225 [−0.025, +0.475] |
| Nt = 5000 | 20 | 0.95 / 0.60 | +0.35 [+0.20, +0.525] | 0.15 | 0.95 / 0.525 | +0.425 [+0.20, +0.625] |

`summarize.py` prints the per-simulation table, which is also stored in `raw/summary.json`. sim13 is the only simulation with a negative point estimate for both methods: LPCMCI −0.089, PCMCI+ −0.071, CIs reaching 0.

Observations:

- **Both methods pick up the induced dependence.** Recall is above baseline overall, and at Nt = 200 and Nt = 1200 with CIs well clear of 0.
- **PCMCI+ does at least as well as LPCMCI.** It assumes no latents, so detecting the induced pair as *adjacent* is not evidence of latent-awareness. It is the dependence a confounder induces.
- **LPCMCI rarely marks the induced pair as bidirected:** 5% of induced pairs overall, at most 20% at Nt = 2400. Latent recognition proper is weak in this pilot.
- **Baselines rise at long sessions.** At Nt = 2400 and 5000 the false-adjacency rate on control pairs reaches 0.5–0.6, for both methods at α = 0.01. Long BOLD series yield many spurious adjacencies here, which shrinks the margin even though recall approaches 1.

## Verdict vs pre-registered prediction

Prediction: "Above-baseline recall for constraint-based methods only at the longer session lengths."
Falsified if: "all methods are at baseline."

**PILOT. Explicit falsifier not triggered; the "only at longer session lengths" clause is FALSIFIED at pilot scale.**

- Both methods are above baseline overall (+0.23 and +0.25).
- They are also above baseline at Nt = 200 (+0.16 [+0.11, +0.21] and +0.19 [+0.14, +0.25]), which is not a "longer" session.
- The effect is largest at Nt = 1200.
- H1's specific claim, that methods recover the *bidirected edge*, is weakly supported at most. LPCMCI emits `<->` on 5% of induced pairs, and no bidirected baseline was computed.

## What this does and does not establish

- **Does:** at pilot scale on NetSim's simulated BOLD data, deleting a common parent leaves a dependence between its children that LPCMCI and PCMCI+ both detect as adjacency above the control-pair rate. LPCMCI seldom labels it as latent-confounded. On long sessions, false adjacencies are common at these settings.
- **Does not:**
  - Establish recovery from real fMRI (ground truth unknown, as the design says).
  - Separate the effect by TR or sampling rate (UNCHECKED).
  - Cover SVAR-FCI or the neural/MDL methods.
  - Show that LPCMCI identifies latents: adjacency is not a bidirected-edge claim.
  - Count as the full run: 10 of 50 subjects, and sim4 excluded.
