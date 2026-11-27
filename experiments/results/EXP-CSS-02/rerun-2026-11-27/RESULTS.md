# EXP-CSS-02 rerun, 2026-11-27: after adding CSSR Phase III

This is a rerun, not a replacement. The original result and verdict are in [`../RESULTS.md`](../RESULTS.md) and stay as recorded. The pre-fix numbers in the tables below are read from [`../raw/summary.json`](../raw/summary.json) and were not recomputed.

## What changed in `reconstruct()`

`grounding/core/epsilon_machine.py` now implements CSSR phases I–III as described in Shalizi & Shalizi 2004, "Blind Construction of Optimal Nonlinear Recursive Predictors for Discrete Sequences", UAI 2004, pp. 504–511 ([arXiv:cs/0406011](https://arxiv.org/abs/cs/0406011), Fig. 1). I read the paper before relying on it.

- **Phase II test.** The default is now CSSR's own test. Each suffix is tested first against its parent's state, using a chi-squared homogeneity test of size α = 10⁻³ (the paper fixes α = 10⁻³ in its experiments). If that test rejects, the suffix joins the closest other state that passes. If every test rejects, it founds a new state. The old fixed total-variation rule is still available as `test="tv"` (`tolerance` 0.2).
- **Phase III (new).** Transient states are removed, keeping closed strongly connected components as the paper describes. States are then split until each symbol takes every history in a state to one state. The machine is therefore unifilar, and states are equivalent on their whole future rather than on the next symbol only.
- **State weights.** These are still counts of the deepest history layer. The paper does not specify how to estimate state probabilities, so this is our choice.

### How the method was chosen

I compared two arms on the full pre-registered grid:
1. TV + Phase III, my first patch;
2. chi-squared + Phase III.

Both fix period-3. TV + Phase III fails badly at large L. Biased coin at T = 10⁴, L = 10 gives a median of 622 states and ΔC = +8.2. Golden mean at T = 10³, L = 10 gives 99 states. A fixed TV threshold never tightens as n grows. It merges histories whose morphs really differ, such as even-process `011` (P(1) = 1/2) with `111` (P(1) ≈ 0.6), and splits sparse ones. Phase III then propagates those errors.

The chi-squared arm is the paper's method, and it is better or equal on every one of the four pre-registered cases. So it is the shipped default. Both arms are in [`raw/rows.json`](raw/rows.json). The first exploratory run lacked transient removal, and its numbers for both arms were identical to this run.

## Provenance

- **Code.**
  - Base: branch `fix/cssr-determinisation` off `main` 1181d9d.
  - Script: [`rerun.py`](rerun.py), which imports `gen`, `ANALYTIC`, the grid and the seed formula from [`../run.py`](../run.py) unchanged.
  - Summary: [`summarize.py`](summarize.py), with the same tolerance as before: \|ΔC\| ≤ 0.05 and \|Δh\| ≤ 0.02.
- **Grid.** 5 processes × T ∈ {10³, 10⁴, 10⁵} × L ∈ 2..10 × 50 seeds, the same as the original.
- **Runtime and environment.** 336 s on 3 workers. Python 3.14.8, stdlib only for the estimator, 4 shared vCPU.
- **Outputs.** [`raw/rows.json`](raw/rows.json), [`raw/summary.json`](raw/summary.json), [`raw/table.txt`](raw/table.txt).

## Before / after

Columns: mean ΔC = Ĉ − C, the fraction of 50 seeds within tolerance ("ok"), and the median number of states. "Old" is the pre-fix estimator; "new" is the shipped default (chi-squared + Phase III).

### Pre-registered cases, primary L = 2

| process | T | old ΔC / ok / states | new ΔC / ok / states |
|---|---|---|---|
| period-3 | 10³ | −0.667 / 0.00 / 2 | 0.000 / 1.00 / 3 |
| period-3 | 10⁵ | −0.667 / 0.00 / 2 | 0.000 / 1.00 / 3 |
| golden mean | 10⁴ | 0.000 / 1.00 / 2 | 0.000 / 1.00 / 2 |
| golden mean | 10⁵ | 0.000 / 1.00 / 2 | 0.000 / 1.00 / 2 |
| biased coin | 10⁴ | 0.000 / 1.00 / 1 | 0.000 / 1.00 / 1 |
| biased coin | 10⁵ | 0.000 / 1.00 / 1 | 0.000 / 1.00 / 1 |
| SNS | 10⁵ | −1.901 / 0.00 / 2 | −1.212 / 0.00 / 3 |

- **Period-3** recovers 3 states with \(C = \log_2 3 = 1.585\) and h = 0, in 50/50 seeds at every T and every L from 2 to 10 (old: 0/50 everywhere).
- **Golden mean and coin** are unchanged at L = 2 and L = 3 for every T. Their h errors at L = 2 are identical to the old estimator to 4 decimals.

### Larger L (from `raw/table.txt`)

| process | T, L | old ΔC / ok / states | new ΔC / ok / states | TV + III (not shipped) |
|---|---|---|---|---|
| biased coin | 10³, 5 | +0.353 / 0.06 / 3 | +0.052 / 0.68 / 1 | +2.608 / 0.04 / 15 |
| biased coin | 10⁴, 10 | +1.746 / 0.00 / 5 | +3.929 / 0.36 / 229 | +8.237 / 0.00 / 622 |
| biased coin | 10⁵, 10 | +1.161 / 0.00 / 6 | +3.188 / 0.16 / 90 | +7.976 / 0.00 / 803 |
| golden mean | 10³, 10 | +1.154 / 0.00 / 5 | +0.041 / 0.96 / 2 | +5.379 / 0.00 / 99 |
| golden mean | 10⁴, 10 | +0.271 / 0.30 / 3 | +0.226 / 0.88 / 2 | +3.058 / 0.26 / 38 |
| golden mean | 10⁵, 10 | 0.000 / 1.00 / 2 | +0.302 / 0.84 / 2 | 0.000 / 1.00 / 2 |
| SNS | 10⁵, 10 | −1.901 / 0.00 / 2 | −0.136 / 0.06 / 7 | −1.827 / 0.00 / 2 |
| even (not in the four) | 10⁵, 2 | −0.269 / 0.00 / 2 | +0.540 / 0.00 / 3 | +0.540 / 0.00 / 3 |
| even | 10⁵, 10 | +0.023 / 0.94 / 2 | +2.039 / 0.00 / 11 | +2.143 / 0.00 / 11 |

## Reported honestly

- **SNS still fails at every T and L.** It has infinitely many causal states, so no finite-L CSSR can recover it. The new estimator moves toward the true value as L and T grow: ΔC goes from −1.90 to −0.14 at T = 10⁵, L = 10, with h error 0.000. The old estimator stayed at 2 states and −1.90.
- **Large-L overfitting is a remaining weakness.**
  - At L = 10 the coin gets worse than before at T ≥ 10⁴ (mean ΔC +3.2 to +3.9, median 90–229 states). With about 2¹⁰ histories, false rejections at α = 10⁻³ found spurious states, and Phase III propagates them.
  - Golden mean at T = 10⁵, L = 10 drops from 1.00 to 0.84 for the same reason.
  - The paper bounds L by data size, \(L(N) \le \log N / (h + \varepsilon)\). Callers should stay well inside it; the in-repo callers (`hnd`, `damage`) default to L = 2.
- **The even process gets worse.** It was not one of the four acceptance cases, but it is in the grid.
  - A run of L ones leaves the parity unknown. That history is recurrent in the finite-L graph, so transient removal keeps it, and Phase III splits off a state for it and for the states leading into it.
  - Old ΔC −0.27 at L = 2 becomes +0.54, and the old 94% pass at L = 10, T = 10⁵ becomes 0%.
  - The paper says CSSR needs \(L_{\max} \ge 3\) for the even process. I have not checked whether the reference implementation counts state weights differently in a way that avoids this. **UNCHECKED.**

## Dependents of `reconstruct()`

- **`scripts/hypothesis_engine.py`.** It does not import `reconstruct`. An engine `--dry-run` on copies of `data/` and `hypotheses/` gave stdout and files identical to the pre-change run, apart from timestamps. No claim or scheduled-output files were changed.
- **`modules/hnd.py` / `modules/main.py` demo.** The real driver is still accepted. The demo's evidence line changes from "C_mu −0.77, h_mu −0.09" to "C_mu −0.42, h_mu −0.18". The "Primitive Roots" line differs between any two runs, because of set ordering.
- **`tests/test_epsilon_machine.py::test_conditioning_on_the_driver_simplifies_the_stream`.**
  - This test asserted that conditioning on noise *raises* C_mu. Under the new estimator, noise lowers C (2.20 → 1.44) and raises h (1.47 → 1.65), so the both-must-fall criterion still rejects it.
  - I replaced that assertion with the property the test's own docstring states: noise must not lower both. It holds on 30/30 seeds, and so do both driver assertions.
  - The old mechanism comment ("noise shatters histories") described the TV rule.
- **`grounding/core/damage.py`.**
  - `test_a_varying_signal_that_explains_the_residual_is_named` failed under chi-squared on its 200-sample stream.
  - Across 30 seeds, the culprit is named in 5/30 with chi-squared and 24/30 with TV (noise false positives 1/30 vs 2/30). At n ≥ 800 both give 30/30 with 0/30 false positives.
  - `DamageDetector.attribute` therefore pins `test="tv"`, with a dated comment, rather than weakening its test. Damage attribution now uses a different merge rule from HND, which goes against that docstring's "same standard of evidence". This is open for the maintainer to decide.

## Verdict for the fix

The acceptance criteria are met:
- period-3 recovers 3 states and \(C = \log_2 3\);
- golden mean and coin are unchanged at the primary L for every T;
- SNS is reported above;
- the test suite passes (375 passed, 2 skipped) after the one assertion change and the damage pin described above.

The original EXP-CSS-02 verdict, falsified (partly), stands as a statement about the estimator as it was.
