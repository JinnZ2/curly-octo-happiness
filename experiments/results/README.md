# Experiment results, run 2026-11-27

These are results for the laptop-CPU-tier experiments proposed under `experiments/`. Each folder holds:

- the code that was run;
- raw outputs in `raw/`;
- a `RESULTS.md` with provenance, deviations (listed before results), a verdict against the pre-registered prediction, and what the result does and does not establish.

Every run used repo commit `a3d5c55` (main). Environment: Python 3.14.8 and numpy 2.5.5, on a shared 4-vCPU Intel Xeon @ 2.90 GHz.

The verdicts are toy-scale or reduced-scale results. None of them is a claim about real models or real systems.

| experiment | issue | scale | verdict | one line |
|---|---|---|---|---|
| [EXP-ENG-02](EXP-ENG-02/RESULTS.md) | #61 | full | SUPPORTED | Bookkeeping factors change the class of open gaps. The "≥ 5 gaps" prediction was met in only 1 cell. |
| [EXP-CFA-05](EXP-CFA-05/RESULTS.md) | #47 | full | H1: AUROC supported, ECE not; H2: SUPPORTED | Answer-only beats the full HaluEval detector (0.856 vs 0.804 AUROC); length alone gives 0.958 on QA. |
| [EXP-HVD-02](EXP-HVD-02/RESULTS.md) | #64 | full (D1), operationalised (D2), BiKCD not run | SUPPORTED (D1) | Residual-correlation Type I is 1.00 under instantaneous coupling and 0.81–1.00 under aggregation; near α under wrong lag and mean shift. |
| [EXP-CSS-02](EXP-CSS-02/RESULTS.md) | #59 | full | FALSIFIED (partly) | Golden mean and coin recovered; period-3 fails at every T and L (ΔC = −0.667 bits), since states are merged by next-symbol morph only. |
| [EXP-RVC-05](EXP-RVC-05/RESULTS.md) | #71 | full (live index from reported figures) | SUPPORTED | Post-publication SR is lower for 7/7 factors; every reported live CI includes both 0 and 0.3; 17 years gives 23% power at SR 0.3. |
| [EXP-RVC-02](EXP-RVC-02/RESULTS.md) | #68 | phase 1 only | SUPPORTED for delay ≤ 2, FALSIFIED at delay 4 | I(D;R) beats log\|R\| when delay is short; it loses at delay 4, where plug-in bias dominates. |
| [EXP-HVD-01](EXP-HVD-01/RESULTS.md) | #63 | PILOT, H2 only | SUPPORTED (H2 first clause) | Lagged confounded pairs are recovered less often (+0.16 LPCMCI, +0.37 PCMCI+), mainly at a ≥ 0.8. |
| [EXP-HVD-04](EXP-HVD-04/RESULTS.md) | #66 | PILOT | falsifier not triggered; "only at longer sessions" FALSIFIED | Induced pairs are found above baseline (+0.23 / +0.25) even at Nt = 200; LPCMCI marks `<->` on only 5% of them. |

## Not run

These experiments stay UNCHECKED:

- **EXP-ENG-01, EXP-ENG-03:** need human labels.
- **EXP-RVC-01:** part (a) is a two-reader proof audit. Part (b) depends on the paper's definitions, so running it on mine would test my definitions.
- **EXP-HVD-03:** laptop or small-cluster tier. Not run in the time budget; J-PCMCI+ is available in tigramite, so it can be done later.
- **EXP-RVC-03:** source generator code unavailable; the M5 data needs a Kaggle login.
- **EXP-CFA-08:** needs a user study.
- **EXP-CFA-09:** PoC code availability UNCHECKED.
- **EXP-CFA-11:** needs LLM inference.
- **All GPU, cluster, human-annotator and wet-lab tier experiments.**
