# EXP-CSS-02 — results (run 2026-11-27)

Design: `experiments/causal-states-and-statistical-complexity.md` § EXP-CSS-02 (issue #59).

## Provenance

- Repo commit: `a3d5c55328cc671c4384d0a02eccb70c7d828b89`. The estimator under test is `grounding.core.epsilon_machine.reconstruct` at that commit, with default `tolerance=0.2` and `min_count=2`.
- Environment: Python 3.14.8; Intel Xeon @ 2.90 GHz, 4 vCPU (shared with other jobs); 2 worker processes. Runtime 1059.7 s.
- Command: `python3 run.py 50 2`, then `python3 summarize.py`. Seeds: `1_000_003*seed + 97*T + len(proc)`, seeds 0–49. Every sequence has a 100-symbol burn-in.
- Raw output: `raw/rows.json` (one row per proc × T × seed × L) and `raw/summary.json`.

## Deviations (recorded before results)

1. **The design did not fix a primary L.** It said "L chosen by `equalized_history_length`", but for a single stream that function returns the base L. I report the full L ∈ {2…10} grid and treat **L = 2 (the library default) as primary** for the tolerance check. Other L values are reported, not hidden.
2. **No CSSR comparison.** No established CSSR implementation was available offline on this machine. Only the block-entropy baseline from the sketch was run.
3. **SNS analytic values were computed numerically**, not taken from a published table. I used the mixed-state recursion over n = number of 1s since the last 0, truncated at n = 2000, which gives \(h_\mu = 0.67787\) and \(C_\mu = 2.71147\) bits. Treat these as numerical values, not as checked against the literature (**UNCHECKED** against e.g. Crutchfield & Feldman). The other four processes have closed forms.
4. Pass criterion per run: \(|\Delta C| \le 0.05\) and \(|\Delta h| \le 0.02\). Below, "ok" is the fraction of the 50 seeds that pass.

**Dated note (2026-11-27) on the design.** The design says the simple nonunifilar source has "uncountably many causal states". That is wrong. Its causal states are countably infinite, one per n = number of 1s since the last 0. The prediction (finite-L estimators fail on it) is unaffected. The design text is left as written.

## Results

Mean error ± SD over 50 seeds (estimate − analytic):

| process | T | L | ΔC | Δh | ok | states (median) |
|---|---|---|---|---|---|---|
| biased coin | 10⁵ | 2 | +0.000 ± 0.000 | −0.000 ± 0.001 | 1.00 | 1 |
| period-3 | 10⁴, 10⁵ | every L 2–10 | **−0.667** ± 0.000 | +0.000 | **0.00** | **2** (true 3) |
| golden mean | 10⁴ | 2 | +0.000 ± 0.003 | −0.000 ± 0.003 | 1.00 | 2 |
| golden mean | 10⁵ | 2–10 | −0.000 ± 0.001 | +0.000 ± 0.001 | 1.00 | 2 |
| even | 10⁵ | 2 | −0.269 ± 0.002 | +0.142 ± 0.001 | 0.00 | 2 |
| even | 10⁵ | 10 | +0.023 ± 0.138 | +0.010 ± 0.001 | 0.94 | 2 |
| SNS | 10³–10⁵ | every L 2–10 | about −1.90 (−1.0 at T = 10³, L = 10) | about +0.011 | 0.00 | 2–4 |

The full grid, including T = 10³ and the block-entropy baseline, is in `raw/summary.json`. `summarize.py` prints L ∈ {2, 3, 5, 10}.

Other observations:

- **Large L overfits at small T.** At L = 10, ΔC is +1.2 to +1.9 bits for biased coin and golden mean at T = 10³. For biased coin it is still +1.16 at T = 10⁵.
- **Block-entropy baseline.** Its h error is similar to `reconstruct`'s. For even at T = 10⁵ it is +0.207 at L = 2 and +0.012 at L = 10. For SNS it is about 0.000 at L ≥ 5, better than `reconstruct`'s +0.011.

**Why period-3 fails (mechanism, checked by reading the code).** `reconstruct` groups histories by their next-symbol distribution only. There is no CSSR-style determinisation or recursion step that splits states whose successors differ. In period-3, two of the three causal states both emit 0 deterministically, so they get merged. The result is 2 states with \(C = H(2/3,1/3) = 0.918\) instead of \(\log_2 3 = 1.585\). This is the same 0.918 at every T and L, and \(h = 0\) is still exact. The same design merges SNS's infinitely many states into about 2.

## Verdict vs pre-registered prediction

Prediction: "H1 holds for finite-order processes; fails for the nonunifilar source at every T."
Explicit falsifier: "golden-mean C_μ outside tolerance at T = 10⁵".

**FALSIFIED (partly).**

- **The explicit falsifier was not triggered.** Golden mean is within tolerance in 50/50 seeds at T = 10⁵, for every L.
- **The SNS part holds.** SNS fails at every T and L, as predicted.
- **But "H1 holds for finite-order processes" is false.** Period-3 is finite-order, and it fails at every T and L with ΔC = −0.667 bits. This is a deterministic, seed-independent error, so it is not a power issue.
- **H0 as written is therefore met:** at least one process exceeds tolerance at T = 10⁵.
- The even process (infinite Markov order) was expected to fail. It does fail at L = 2, but passes 94% of seeds at L = 10, T = 10⁵. That is a better result than predicted, and it is not a failure of the estimator.

I report this as falsified because of a process I had classed as "finite-order, should pass". The falsifier I wrote down was narrower than the prediction it was meant to protect. That is a design weakness, noted here, not fixed in the design file.

## What this does and does not establish

- **Does:**
  - On these five toy processes, `reconstruct` at default settings matches analytic \(C_\mu\) and \(h_\mu\) for i.i.d. and golden-mean processes at T ≥ 10⁴, L = 2.
  - It under-counts causal states whenever distinct states share a next-symbol distribution (period-3, SNS). This is a structural property of the algorithm, not sampling noise.
  - \(C_\mu\) values from it are therefore lower bounds at best for such processes. They should not be compared with analytic values without checking for this.
- **Does not:**
  - Validate the estimator on real data.
  - Compare it with CSSR (not run).
  - Show whether a lower `tolerance` or a determinisation step would fix period-3 (not tested; the design fixed default settings).
  - Validate the SNS analytic values beyond my own numerical calculation.
