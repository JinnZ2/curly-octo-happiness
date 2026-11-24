# Experiments — hidden variable detection / causal discovery from residuals (`HVD`)

Status: PROPOSED · Date: 2026-11-24 · Read against
`hypotheses/hidden-variable-detection-causal-discovery-from-residuals.md` and
`hypotheses/RESEARCH_GAPS.md` at commit
`d469d9db381eabdbf8be22095dc712e79592ded7` (engine run 2026-11-23).

Nothing here is a result. **Checked (abstract)** = the source exists and its
abstract/landing page says what is quoted, as fetched 2026-11-24. Everything
else is **UNCHECKED**.

## 1. What the engine claims, and on what evidence

**The draft.** Node confidence 0.49; 5 surviving / 12 active / 0 refuted; 11
open gaps (all EMPIRICAL, `UNDER_STUDY`); 2 untested markers; no
hidden-variable suspects this run (the engine's own stage-6 scan is
calibrated to refuse rather than over-fire, per `design/hypothesis_engine.md`).

**What the evidence is.** As for every topic, each record counts lexical
polarity in other abstracts ([engine-oracle.md](engine-oracle.md)). Two of the
draft's top "supporting claims" are not about hidden variables at all: an
energy-distance time-series clustering paper (beta 0.80) and a wearable
anomaly-detection autoencoder (0.75). The draft's falsifier for the first
still reads "fails to reproduce the stated 2013 result" (the year of a cited
reference), a string generated before `result_anchor` was fixed and persisted
in `claim_tree.json`. The HVD gaps that are on topic are methods papers on
causal discovery with latent confounders, each reporting that its method
works on its own simulations.

**Sources checked (abstract level).**

| gap | source | what its abstract says |
|---|---|---|
| HVD_001 | [Causal Discovery in High-Dimensional Time Series with Latent Confounders via Score-Based Diffusion Models](https://www.semanticscholar.org/paper/8be603b3e42d906489745267446de3078512bda4) (Torres, 2025) | "Causal-Diff": identifies graphs under partial observability with sparsity and temporal masking; reports beating baselines on SHD and orientation accuracy, synthetic and fMRI |
| HVD_002 | [Causal discovery from time-series discrete data in the presence of latent confounders](https://www.semanticscholar.org/paper/c1cc59c9eae56b382d6b533dc76b6ec45c16ba20) (Chen et al., 2026) | TRTCD (tensor-rank based) recovers structure up to a Markov equivalence class with latent confounders |
| HVD_003 | [High-recall causal discovery for autocorrelated time series with latent confounders](https://www.semanticscholar.org/paper/311c8cc775770257d43b6e4e26f6b6470d0cb02a) (Gerhardus & Runge, NeurIPS 2020) | LPCMCI: order-independent, sound and complete in the oracle case; higher recall than existing methods in simulations |
| HVD_005 | [Causal discovery for time series with latent confounders](https://www.semanticscholar.org/paper/b6d7bb52558a5ff924fdb995c7f849e5c7feb65b) (Reiser, 2022) | an evaluation of LPCMCI: much better than random, far from optimal; best on auto-dependencies, worst on lagged ones |
| HVD_010 | [Learning Kernelized Hypothesis for Hidden Confounder Detection](https://www.semanticscholar.org/paper/c06977bd0c67e2417773881919f1669845c25522) (Chen et al., 2026) | BiKCD: tests for hidden confounding by comparing higher-order regression and OLS coefficients in a learned kernel space; oracle risk bound and Type-I control |

HVD_004, 006, 007, 008, 009, 011 are **UNCHECKED**. Note that HVD_005 is
itself an independent evaluation of HVD_003's method, and its abstract-level
finding (worst on lagged dependencies) is the kind of separating condition
Protocol R asks for. The engine's cross-reading did not surface it as such.

## 2. What science needs to be known

### 2a. Gaps the engine recorded

11 ids, all Protocol R ("replicate under stated conditions; vary the
separating condition"). The engine names no separating condition.

### 2b. Gaps I identify

1. **Identifiability limits are part of the claim.** With latent
   confounders, constraint-based methods (FCI-family, LPCMCI) output a PAG
   (partial ancestral graph), not a DAG; "recovering the graph" means
   recovering an equivalence class. Comparing methods by SHD against the true
   DAG penalises correct uncertainty. Every benchmark here must score against
   the **true PAG** (or the true MAG's equivalence class), as well as edge
   recall/precision.
2. **Residual correlation is not specific to latent variables.** An
   unmodelled contemporaneous edge, a mis-specified lag, measurement
   aggregation in time, or non-stationarity all leave correlated residuals.
   `experiments/sketches/latent_confounder_sim.py` shows the toy version: a
   residual test rejects at the same rate under a hidden driver and under a
   plain instantaneous X→Y edge. Any "detect hidden variables from residuals"
   claim must report its false-positive rate under these alternatives, not
   only under independence. This also bears on the engine's own stage 6 and
   the repo's `modules/hnd.py`.
3. **Method claims are evaluated on the authors' own simulators.** The
   separating conditions most likely to flip results: autocorrelation
   strength, lagged vs contemporaneous confounding, confounder persistence,
   nonlinearity, sample length T, variable count, discretisation (HVD_002,
   HVD_007), and faithfulness violations near cancellation.
4. **Real-data ground truth.** fMRI claims (HVD_001) need data where the
   structure is known; simulated BOLD (NetSim) is the standard proxy, and
   hiding observed nodes creates latent confounders with known positions.
5. **Hyperparameter tuning on ground truth.** If α (CI-test level), lag
   maximum, or sparsity penalty is tuned against the true graph, reported
   performance is optimistic. Pre-fix or tune on a separate generator seed.
6. **Scope leaks.** HVD_011 (epileptic seizure detection with a graph
   attention network) and the two top "supporting claims" are not causal
   discovery work.

## 3. Experiments

Shared conventions: ground truth from simulation or semi-simulation only;
methods via maintained open implementations where they exist (`tigramite`
for PCMCI/PCMCI+/LPCMCI/J-PCMCI+; `causal-learn` for FCI variants; authors'
code for Causal-Diff, TRTCD, BiKCD, LNML; availability UNCHECKED);
hyperparameters fixed before the main runs on a separate tuning seed set; 50
seeds per cell unless stated.

### EXP-HVD-01 — Latent-confounder time-series discovery: one benchmark, the separating conditions varied

**Gaps:** HVD_001, HVD_002, HVD_003, HVD_005, HVD_007, HVD_008, HVD_009.

- **H1 (HVD_003 as stated):** at matched false-positive rate, LPCMCI's
  adjacency recall exceeds SVAR-FCI's by ≥ 0.1 when autocorrelation a ≥ 0.7.
- **H2 (HVD_005's condition):** every method's recall on **lagged**
  confounded edges is lower than on contemporaneous ones, and the gap grows
  with confounder persistence.
- **H3 (HVD_001, 009, 008, 007):** the neural/score-based and MDL methods
  match or beat LPCMCI on PAG-F1 under nonlinearity, and do not under linear
  Gaussian data (where constraint-based methods are well specified).
- **H0s:** no recall difference (H1); no lag effect (H2); method ranking
  independent of nonlinearity (H3).
- **Factorial design.** autocorrelation a ∈ {0.2, 0.5, 0.8, 0.95} × latent
  confounder lag ∈ {0, 1, 2} × confounder persistence ρ_Z ∈ {0, 0.5, 0.9} ×
  mechanism ∈ {linear-Gaussian, additive nonlinear} × T ∈ {200, 1000, 5000}
  × N_obs ∈ {5, 10, 20} × data type ∈ {continuous, discretised to 3 levels
  (for HVD_002/007)}. 50 seeds per cell is ~2.6×10⁵ datasets; run a
  fractional factorial (resolution IV) first.
- **Metrics.** PAG-F1 against the true PAG (via the true MAG), adjacency
  precision/recall, orientation precision on circle/arrowhead marks, runtime.
- **Controls.** PCMCI+ (assumes no latents) as a "what if you ignore
  latents" baseline; a random-graph baseline matched for density.
- **Pre-registered predictions.** H1 holds for a ≥ 0.8; H2 holds for all
  methods; H3 holds for at most one neural method. **Falsifiers:** H1
  falsified if the recall difference CI includes 0 at a = 0.95; H2 if lagged
  recall ≥ contemporaneous recall for ≥ half the methods; H3 if neural methods
  win on linear-Gaussian data.
- **Analysis.** Mixed-effects model of PAG-F1 with method × condition
  interactions, seed as random effect; Holm correction over the three
  primaries; full per-cell tables released.
- **Threats.** Implementation differences across codebases (wrap all in one
  harness; check each reproduces its paper's headline simulation first);
  faithfulness near-violations at random coefficients (report the
  minimum-partial-correlation distribution).
- **Tier:** cluster for the full grid; a reduced grid (a × lag × T, linear
  only, 3 methods) runs on a laptop CPU in hours.
- **Establishes / does not.** Which method works under which stated
  conditions on synthetic data. Does not establish performance on any real
  system.

### EXP-HVD-02 — Residual-based hidden-confounder detection: Type I error under non-latent alternatives

**Gaps:** HVD_010 (primary); premise of the engine's stage 6 and `modules/hnd.py`.

- **H1:** a confounder detector that is calibrated under independence
  (Type I ≈ α when there is neither a latent variable nor a contemporaneous
  edge) has Type I error ≫ α under each non-latent alternative that produces
  residual dependence: (i) instantaneous X→Y, (ii) wrong lag order, (iii)
  temporal aggregation (sampling every k-th step), (iv) a mean shift
  (non-stationarity).
- **H0:** Type I ≤ 2α under all four alternatives (the detector is specific).
- **Design.** Bivariate and 5-variable VAR generators with and without a
  hidden AR driver, crossed with the four alternatives; T ∈ {200, 1000};
  1,000 reps per cell (gives a ±1.4-point SE on a 5% rate). Detectors: VAR
  residual correlation (the sketch), BiKCD (code UNCHECKED), the repo's
  `HiddenNodeDetector` with `acceptance="epsilon_machine"`.
- **Pre-registered prediction.** The residual-correlation test fails
  specificity under (i) and (iii) (the sketch already shows (i) in a toy);
  BiKCD's coefficient-comparison test is specific under (i) only if its
  kernel space separates the mechanisms (no prediction). **Falsified if**
  Type I ≤ 2α for all detectors under all alternatives.
- **Analysis.** Rejection rates with Wilson intervals; power under the latent
  alternative; ROC of each detector's statistic discriminating latent from
  non-latent residual dependence.
- **Tier:** laptop CPU (stdlib sketch provided; full version minutes–hours).
- **Establishes / does not.** Whether "hidden variable" detections from
  residuals are specific. A specific detector on these generators is not
  shown to be specific on real data.
- **Sketch:** `python experiments/sketches/latent_confounder_sim.py`.

### EXP-HVD-03 — Latent contexts and domain knowledge: what happens when the prior is wrong?

**Gaps:** HVD_004, HVD_006.

- **H1 (HVD_004, multiple datasets with latent contexts):** pooling datasets
  that differ by an unobserved context variable, a context-aware method
  (J-PCMCI+-style, which models context nodes) has higher PAG-F1 than
  per-dataset discovery or naive pooling.
- **H2 (HVD_006, domain knowledge):** adding background-knowledge
  constraints improves F1 when the constraints are correct, and degrades it
  more than proportionally when a fraction f of them are wrong.
- **H0s:** no difference among pooling strategies; F1 linear in f.
- **Design.** Generators with M ∈ {3, 10, 30} datasets, context affecting
  1–3 mechanisms; knowledge sets with f ∈ {0, 0.1, 0.25, 0.5} wrong
  constraints, drawn at random and also adversarially (wrong where the data
  are weakest). 50 seeds.
- **Prediction.** H1 for M ≥ 10; H2's degradation is super-linear for
  adversarial errors. **Falsified if** context-aware F1 ≤ pooled F1 at M = 30,
  or F1 is linear in f for both error types.
- **Tier:** laptop CPU / small cluster.
- **Does not establish** how often real domain knowledge is wrong.

### EXP-HVD-04 — Semi-synthetic real-data validation: hide nodes in fMRI simulations

**Gaps:** HVD_001 (its fMRI claim), HVD_003, HVD_009.

- **H1:** on NetSim simulated BOLD networks (Smith et al. 2011, public;
  availability UNCHECKED), deleting one observed node that is a common parent
  of ≥ 2 others creates a latent confounder whose bidirected edge methods
  recover with recall above the density-matched random baseline.
- **H0:** recall of the induced bidirected edges is at the random baseline.
- **Design.** All NetSim simulations with ≥ 5 nodes; every eligible node
  deleted in turn; methods as in EXP-HVD-01 with fixed hyperparameters.
- **Prediction.** Above-baseline recall for constraint-based methods only at
  the longer session lengths. **Falsified if** all methods are at baseline.
- **Threats.** NetSim's BOLD forward model smooths in time, which aliases
  lags (relevant to EXP-HVD-02 (iii)); report results per sampling rate.
- **Tier:** laptop CPU.
- **Does not establish** recovery from real fMRI, where ground truth is
  unknown.

## 4. Gap → experiment map (all 11 HVD ids)

| gap | experiment / reason |
|---|---|
| HVD_001 | EXP-HVD-01 (H3), EXP-HVD-04 |
| HVD_002 | EXP-HVD-01 (discretised arm) |
| HVD_003 | EXP-HVD-01 (H1), EXP-HVD-04 |
| HVD_004 | EXP-HVD-03 (H1) |
| HVD_005 | EXP-HVD-01 (H2) — HVD_005 is an evaluation of HVD_003's method; treated as the separating-condition hypothesis |
| HVD_006 | EXP-HVD-03 (H2) |
| HVD_007 | EXP-HVD-01 (mixed/discretised arm; source UNCHECKED) |
| HVD_008 | EXP-HVD-01 (H3; source UNCHECKED) |
| HVD_009 | EXP-HVD-01 (H3), EXP-HVD-04 (source UNCHECKED) |
| HVD_010 | EXP-HVD-02 |
| HVD_011 | not in topic scope: seizure detection with an attention-based GCN, admitted on shared vocabulary. Its claim (detection accuracy on EEG) is testable on public EEG datasets, but not as hidden-variable detection; not assigned |

All 11 also depend on EXP-ENG-01/02 for whether their recorded split means
anything. The 2 untested markers (nonlinear causal discovery in time series;
a helmet-detection YOLO model, which is a scope leak) are not gap ids.
