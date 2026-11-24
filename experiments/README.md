# experiments/

Experiment designs for the hypothesis engine's open research gaps. **Every
entry is PROPOSED. Nothing in this directory is a result.**

- **Read against:** `hypotheses/` and `data/` at commit
  `d469d9db381eabdbf8be22095dc712e79592ded7` (engine run of 2026-11-23,
  committed 2026-11-23 18:11 UTC).
- **Written:** 2026-11-24.
- The engine rewrites `hypotheses/` and `data/` on its schedule. Gap ids are
  permanent (`RESEARCH_GAPS.md` never renumbers), so the mapping below stays
  valid, but gap text, records, and which ids are open will drift. Re-check
  against the current `RESEARCH_GAPS.md` before running anything.
- This directory is outside `data/` and `hypotheses/` so the engine's commits
  never touch it, and nothing here modifies the engine, its config, or its
  generated files.

## How to read these files

Each topic file has: (1) what the engine claims and on what evidence, with
sources marked **checked (abstract)** where I opened the landing page on
2026-11-24 and **UNCHECKED** otherwise; (2) what would need to be known,
split into (a) gaps the engine recorded and (b) gaps I identified; (3)
experiments, each with hypothesis and null, operationalised variables,
design, pre-registered prediction and falsifier, analysis plan, threats,
feasibility tier, and what a result would and would not establish; (4) a
gap → experiment map.

"Checked" means a source exists and says what is quoted; it never means the
source's result is right. Mathematical validity, structural/dimensional
checks, numerical agreement, and empirical support are kept separate
throughout.

**Read [engine-oracle.md](engine-oracle.md) first.** The engine's
"corroborating / contradicting" records come from lexical polarity in other
abstracts, its claims are abstract first sentences (mostly motivation), and
the read-only audit finds duplicate papers testifying for and against
themselves. EXP-ENG-01/02/03 test whether the gap records mean anything;
the topic experiments test the science and stand without them.

## Counts

| topic | prefix | open gaps | mapped to an experiment | reason only | experiments |
|---|---|---|---|---|---|
| [calibration and falsifiability of LLM agents](calibration-and-falsifiability-of-llm-agents.md) | CFA | 43 | 39 (incl. 4 duplicates) | 4 (CFA_017, 021, 045, 050) | 15 |
| [hidden variable detection / causal discovery from residuals](hidden-variable-detection-causal-discovery-from-residuals.md) | HVD | 11 | 10 | 1 (HVD_011) | 4 |
| [causal states and statistical complexity](causal-states-and-statistical-complexity.md) | CSS | 1 | 1 | 0 (+ topic-level UNDERIVABLE: not empirically testable) | 2 |
| [requisite variety and cybernetic regulation](requisite-variety-and-cybernetic-regulation.md) | RVC | 6 | 6 | 0 | 5 |
| [cross-cutting: the engine's oracle](engine-oracle.md) | ENG | (all 61) | — | — | 3 |
| **total** | | **61** | **56** | **5** | **29** |

## Experiment index

| experiment | topic | gaps | tier | status |
|---|---|---|---|---|
| EXP-ENG-01 oracle verdict vs human stance | ENG | all 38 claim-backed | laptop + ~1–2 annotator-days | PROPOSED |
| EXP-ENG-02 record integrity (duplicates, reformulation reset, IDF drift) | ENG | all 38 claim-backed | laptop | PROPOSED |
| EXP-ENG-03 does the extracted sentence carry the claim | ENG | all 61 | laptop + ~0.5 annotator-day | PROPOSED |
| EXP-CFA-01 elicitation method & prompt sensitivity | CFA | 001, 030, 047 | single GPU | PROPOSED |
| EXP-CFA-02 instruction tuning vs calibration; label smoothing | CFA | 018, 033 | single GPU | PROPOSED |
| EXP-CFA-03 threshold transfer across models/domains | CFA | 009, 019, 046, 049 | single GPU | PROPOSED |
| EXP-CFA-04 abstention incentives vs post-hoc thresholds | CFA | 006, 012, 013, 032 | single GPU | PROPOSED |
| EXP-CFA-05 HaluEval detector replication + shortcut ablation | CFA | 048, 015, 052 | laptop CPU | PROPOSED |
| EXP-CFA-06 trajectory-level agent confidence | CFA | 022, 037, 039, 051 | single GPU / small cluster | PROPOSED |
| EXP-CFA-07 correlated multi-agent confidence, debate, herding | CFA | 014, 024, 029, 035, 044 | single GPU | PROPOSED |
| EXP-CFA-08 calibrated confidence → calibrated reliance | CFA | 020 | laptop (reanalysis) + field (user study) | PROPOSED |
| EXP-CFA-09 verifiable-authorization PoC adversarial harness | CFA | 054, 040, 041, 016 | laptop CPU | PROPOSED |
| EXP-CFA-10 agent security controls, red-team variance, monitors | CFA | 008, 011, 028 | single GPU / API | PROPOSED |
| EXP-CFA-11 efficiency hallucination in code optimisation | CFA | 053 | laptop CPU (+ inference) | PROPOSED |
| EXP-CFA-12 multimodal hallucination mitigation, seed variance | CFA | 010, 031 | cluster | PROPOSED |
| EXP-CFA-13 longitudinal mandate stability | CFA | 034 | single GPU / API | PROPOSED |
| EXP-CFA-14 K8s ops measurement-substrate reproducibility | CFA | 023 | cluster | PROPOSED |
| EXP-CFA-15 deception in a hidden-role game with ground truth | CFA | 007 | single GPU | PROPOSED |
| EXP-HVD-01 latent-confounder TS discovery benchmark | HVD | 001, 002, 003, 005, 007, 008, 009 | cluster (reduced grid: laptop) | PROPOSED |
| EXP-HVD-02 residual-based detection: Type I under non-latent alternatives | HVD | 010 | laptop CPU | PROPOSED |
| EXP-HVD-03 latent contexts & wrong domain knowledge | HVD | 004, 006 | laptop / small cluster | PROPOSED |
| EXP-HVD-04 hide nodes in NetSim fMRI simulations | HVD | 001, 003, 009 | laptop CPU | PROPOSED |
| EXP-CSS-01 English h ≈ 1.22 bpc vs LM upper bounds | CSS | 001 | single GPU (laptop for small LMs) | PROPOSED |
| EXP-CSS-02 do h_μ / C_μ estimators recover known values | CSS | 001 (+ topic) | laptop CPU | PROPOSED |
| EXP-RVC-01 GART: proof audit + computable-proxy check | RVC | 001 | desk + laptop | PROPOSED |
| EXP-RVC-02 does a measured variety margin predict failure | RVC | 005, 006 | laptop (sim) + field | PROPOSED |
| EXP-RVC-03 retail lift overstatement: replicate, find condition | RVC | 004 | laptop CPU | PROPOSED |
| EXP-RVC-04 What-If World score reliability | RVC | 002 | single GPU / cluster | PROPOSED |
| EXP-RVC-05 factor Sharpe decay, with power stated | RVC | 003 | laptop CPU | PROPOSED |

## Highest-value cheap experiments

1. **EXP-ENG-01** (laptop + annotators). Decides whether any of the 38
   claim-backed "splits" is evidence of disagreement between papers. If the
   oracle does not agree with human stance labels, the gap records are a
   reading list, not evidence, and that changes how every gap should be read.
   The annotation sheet is generated by `sketches/oracle_audit.py`.
2. **EXP-CFA-05** (laptop CPU, minutes of compute). Replicates a reported
   HaluEval detector (AUROC 0.835, checked abstract) and tests whether
   answer-only features reach the same AUROC. A shortcut result would bound
   what HaluEval-only detection numbers mean.
3. **EXP-HVD-02** (laptop CPU). Tests whether residual-based hidden-confounder
   detectors are specific, i.e. whether they reject under non-latent causes of
   residual dependence (instantaneous edges, temporal aggregation). The
   stdlib sketch already shows the toy version of the failure. This bears on
   the engine's own stage 6 and the repo's `modules/hnd.py` as well as
   HVD_010.

## Sketches

`sketches/` holds offline, stdlib-only scripts. They are sketches, not
results; any numbers they print describe toy generators or the engine's
own data, not the world.

| sketch | supports | what it does |
|---|---|---|
| `oracle_audit.py` | EXP-ENG-01/02 | re-runs the engine's `corroboration()` read-only over every recorded pair; flags duplicates, template tokens, IDF drift; writes an annotation sheet; scores κ against human labels |
| `calibration_metrics.py` | all EXP-CFA | ECE (width/mass bins), Brier, AUROC, AURC, bootstrap, consistency-resampling null for ECE |
| `latent_confounder_sim.py` | EXP-HVD-02 | VAR residual-correlation test under null / hidden driver / instantaneous edge |
| `entropy_rate_check.py` | EXP-CSS-01/02 | block-entropy estimates vs analytic h_μ, C_μ for golden-mean and even processes |
| `variety_sim.py` | EXP-RVC-01/02 | regulation game; asserts H(E) ≥ H(D) − I(D;R) ≥ H(D) − H(R) on every run |

Run any of them with `python experiments/sketches/<name>.py` from the repo
root. `tests/test_experiment_sketches.py` runs their self-checks (stdlib
only, so it passes in the tier-0 CI job) and asserts the audit leaves `data/`
untouched.

## Gap index (all 61 open ids at the commit above)

| gap | topic | experiment(s) | note |
|---|---|---|---|
| CFA_001 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-01 |  |
| CFA_006 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-04 |  |
| CFA_007 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-15 | operationalise "deception" first (Protocol M step built in) |
| CFA_008 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-10 |  |
| CFA_009 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-03 |  |
| CFA_010 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-12 |  |
| CFA_011 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-10 |  |
| CFA_012 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-04 |  |
| CFA_013 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-04 |  |
| CFA_014 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-07 |  |
| CFA_015 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-05 | duplicate of CFA_048 (same paper) |
| CFA_016 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-09 | duplicate of CFA_054 (same paper) |
| CFA_017 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-09 | needs a definition first (standards proposal; no measurable claim) |
| CFA_018 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-02 |  |
| CFA_019 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-03 |  |
| CFA_020 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-08 |  |
| CFA_021 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | — | not in topic scope (3D Gaussian splats); not assigned |
| CFA_022 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-06 |  |
| CFA_023 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-14 |  |
| CFA_024 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-07 |  |
| CFA_028 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-10 |  |
| CFA_029 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-07 |  |
| CFA_030 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-01 |  |
| CFA_031 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-12 |  |
| CFA_032 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-04 |  |
| CFA_033 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-02 |  |
| CFA_034 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-13 |  |
| CFA_035 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-07 |  |
| CFA_037 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-06 |  |
| CFA_039 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-06 |  |
| CFA_040 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-09 | duplicate of CFA_054 (same paper) |
| CFA_041 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-09 | duplicate of CFA_054 (same paper) |
| CFA_044 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-07 |  |
| CFA_045 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | — | not in topic scope (Yiddish LM; no calibration claim); not assigned |
| CFA_046 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-03 |  |
| CFA_047 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-01 |  |
| CFA_048 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-05 |  |
| CFA_049 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-03 |  |
| CFA_050 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | — | needs a definition first (architecture; read its stated hypotheses, then Protocol M) |
| CFA_051 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-06 |  |
| CFA_052 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-05 | empirical baseline only; mathematics needs a desk audit |
| CFA_053 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-11 |  |
| CFA_054 | [CFA](calibration-and-falsifiability-of-llm-agents.md) | EXP-CFA-09 |  |
| CSS_001 | [CSS](causal-states-and-statistical-complexity.md) | EXP-CSS-01, EXP-CSS-02 | the extracted sentence is definitional; the testable part is the reported h value |
| HVD_001 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-01, EXP-HVD-04 |  |
| HVD_002 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-01 |  |
| HVD_003 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-01, EXP-HVD-04 |  |
| HVD_004 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-03 |  |
| HVD_005 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-01 |  |
| HVD_006 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-03 |  |
| HVD_007 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-01 |  |
| HVD_008 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-01 |  |
| HVD_009 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-01, EXP-HVD-04 |  |
| HVD_010 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | EXP-HVD-02 |  |
| HVD_011 | [HVD](hidden-variable-detection-causal-discovery-from-residuals.md) | — | not in topic scope (seizure detection); not assigned |
| RVC_001 | [RVC](requisite-variety-and-cybernetic-regulation.md) | EXP-RVC-01 | theorem: proof audit (desk) + proxy experiment; not empirically testable itself |
| RVC_002 | [RVC](requisite-variety-and-cybernetic-regulation.md) | EXP-RVC-04 | scope leak; tested on its own terms |
| RVC_003 | [RVC](requisite-variety-and-cybernetic-regulation.md) | EXP-RVC-05 | scope leak; source UNCHECKED |
| RVC_004 | [RVC](requisite-variety-and-cybernetic-regulation.md) | EXP-RVC-03 | scope leak; tested on its own terms |
| RVC_005 | [RVC](requisite-variety-and-cybernetic-regulation.md) | EXP-RVC-02 | needs a definition first; operationalisation is Phase 0 |
| RVC_006 | [RVC](requisite-variety-and-cybernetic-regulation.md) | EXP-RVC-02 | needs a definition first; operationalisation is Phase 0 |

The 7 untested markers listed in RESEARCH_GAPS.md (5 CFA, 2 HVD) are not
gap ids and are not mapped.
