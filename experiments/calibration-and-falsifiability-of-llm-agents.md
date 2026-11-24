# Experiments — calibration and falsifiability of LLM agents (`CFA`)

Status: PROPOSED · Date: 2026-11-24 · Read against
`hypotheses/calibration-and-falsifiability-of-llm-agents.md` and
`hypotheses/RESEARCH_GAPS.md` at commit
`d469d9db381eabdbf8be22095dc712e79592ded7` (engine run 2026-11-23). The engine
rewrites these files on its schedule; gap ids are permanent, text is not.

Nothing in this file is a result. Numbers attributed to papers come from their
abstracts or landing pages as fetched on 2026-11-24, and are marked **checked
(abstract)**; everything else is **UNCHECKED**. "Checked" means the source
exists and its abstract says what is quoted, not that the result is right.

## 1. What the engine claims, and on what evidence

**The draft.** Node confidence 0.45; 5 surviving / 23 active / 0 refuted
claims; 43 open gaps (20 claim-backed EMPIRICAL `UNDER_STUDY`, 23
escape-hatched METHODOLOGICAL `UNDEFINED`), 5 untested markers. The draft
makes no synthesis claim of its own. Each "supporting claim" is the first
sentence of one abstract, with a pass/fail record from cross-reading other
abstracts (see [engine-oracle.md](engine-oracle.md)).

**What the evidence is.** The records are lexical: shared tokens plus
counts of words like "support" vs "fail" in the sentences that contain them.
The audit sketch finds, among others, that one paper indexed under four gap
ids (CFA_016/040/041/054) is recorded as contradicting itself, and that
CFA_048 is corroborated by its own DOI copy (CFA_015). The extracted
sentences are almost all motivation ("LLMs can generate fluent yet
unsupported content"; "Tool-using agents ... need to be both useful and
safe"). So the CFA draft is best read as a curated reading list of 2024–2026
work on LLM confidence, abstention and agent safety, with no evidence about
which of those papers' results hold.

**Sources checked (abstract level, 2026-11-24).**

| gap | source | what its abstract/landing page says |
|---|---|---|
| CFA_001 | [On Verbalized Confidence Scores for LLMs](https://www.semanticscholar.org/paper/4fd8ded3fd8942fb9e8a557ac37722b9f7add8b8) (Yang, Tsai, Yamada, 2024) | reliability of verbalized confidence depends strongly on the prompt; some prompts elicit well-calibrated scores |
| CFA_006 | [I-CALM](http://arxiv.org/abs/2604.03904v1) (Zong et al.) | on GPT-5 mini / PopQA, prompts that elicit confidence and reward abstention reduce false answers among answered items, trading coverage |
| CFA_015 (= CFA_048) | [Hallucination Detection and Confidence Calibration ... HaluEval](https://doi.org/10.69987/aimlr.2025.60401) (Reed & Mason, AIMLR 6(4), 2025) | best system AUROC 0.835, F1 0.751, ECE 0.009, linear SVM on TF-IDF + overlap/length features with domain-conditional Platt scaling |
| CFA_018 | [Calibrated Language Models and How to Find Them with Label Smoothing](https://www.semanticscholar.org/paper/4c04624c0a0c0c5c45a67a85829db08818ac03bb) (Huang, Lu, Zeng, 2025) | instruction tuning degrades calibration; label smoothing helps, less so for large-vocabulary models |
| CFA_020 | [From Calibrated Confidence to Calibrated Reliance](https://doi.org/10.1145/3843742) (Wang & Hu, ACM TSC) | 35,670 HAIID interactions; model calibration does not ensure calibrated human reliance; confidence remapping can reduce display–outcome misalignment |
| CFA_021 | [Calibrated Per-Carrier Confidence ... Gaussian-Splat Assets](https://doi.org/10.31224/7689) (Attri) | 3D graphics, not LLMs: per-primitive confidence, ECE 0.0006–0.0016 across four scenes |
| CFA_030 | [Calibrating the Confidence of LLMs by Eliciting Fidelity](http://arxiv.org/abs/2404.02655v2) (Zhang et al.) | plug-and-play estimator; 6 RLHF models, 4 MCQA datasets; proposes metrics IPR and CE |
| CFA_044 | [Confidence Composition for Multiagent LM Systems](https://www.semanticscholar.org/paper/35bcf942450e50382abea4f20844bf5c4adb2c2c) (Elahi, Curry, Di Eugenio, 2026) | gated fusion improves AUARC and Brier over single-agent and debate baselines on five benchmarks; a shared-dependence discount helps log-odds fusion |
| CFA_054 (= 016/040/041) | [Cryptographically verifiable authorization for autonomous AI agents](http://arxiv.org/abs/2607.21325v3) (Llambí-Morillas & Fernández-Fernández) | authorization as a verifiable relation; Groth16 zk-SNARK proof of concept |
| cross-read | [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1) (Zhang, Xiong, Wu) | trajectory-level calibrator (HTC); lowest ECE on out-of-domain GAIA for the general calibrator |

All other CFA sources (CFA_007–014, 017, 019, 022–024, 028, 029, 031–035,
037, 039, 040/041 alternate URLs, 045–047, 049–053) are **UNCHECKED**: they
are listed in RESEARCH_GAPS.md with URLs, but I did not open them.

## 2. What science needs to be known

### 2a. Gaps the engine recorded

43 ids. The engine's protocol for the 20 EMPIRICAL ones is Protocol R
(replicate under stated conditions, then vary the separating condition); for
the 23 METHODOLOGICAL ones, Protocol M (operationalise, then test once). The
engine does not name any separating condition for any CFA gap; all its
"splits" come from the lexical oracle.

### 2b. Gaps I identify

1. **"Calibrated" is under-specified across the cluster.** ECE values are
   not comparable across papers without the binning scheme, bin count, the
   unit (token, answer, trajectory), the correctness judge, and the
   finite-sample null. Plug-in ECE is biased upward at small n (the
   `calibration_metrics.py` sketch shows a perfectly calibrated synthetic
   predictor with non-zero ECE, and a bootstrap CI that excludes its own point
   estimate). Without a consistency-resampling null, "ECE 0.009" (CFA_015)
   and "ECE 0.0006" (CFA_021) cannot be ranked or tested.
2. **Correctness labels are a hidden variable.** Many calibration results
   use an LLM judge or string match to decide "correct". Judge error is
   correlated with confidence (hard items are both low-confidence and
   judge-ambiguous), which can make a miscalibrated model look calibrated or
   the reverse. No CFA source in the checked set reports judge–human
   agreement.
3. **Calibration vs discrimination vs selective risk are different claims.**
   Temperature scaling can improve ECE without changing AUROC; abstention
   papers (CFA_006, 009, 013) are about risk–coverage, not ECE. Several
   experiments below exist to stop those being conflated.
4. **Prompt and seed variance.** CFA_001's own result is that verbalized
   confidence depends on the prompt. Any single-prompt result in this
   cluster has an unmeasured variance term.
5. **Agent-level vs answer-level.** "Agentic calibration" (trajectory success
   probability) needs a defined outcome (task success under a fixed
   evaluator) and a defined time of prediction (before acting, mid-trajectory,
   after). Unspecified in the extracted claims.
6. **Scope leaks.** CFA_021 (3D Gaussian splats) and CFA_045 (a Yiddish LM)
   entered on the word "calibrated"/"benchmark"; they are not claims about LLM
   agent calibration. CFA_016/040/041/054 are one paper.
7. **Falsifiability of the engine's falsifiers.** Persisted falsification
   strings such as "fails to reproduce the stated 3.5 result" (claim
   `64cda870547bd0fa`, CFA_024) were generated before `result_anchor` was
   fixed and are still in `claim_tree.json`; the "result" they name may be an
   identifier. Each experiment below states its own falsifier instead.

## 3. Experiments

Shared conventions for every CFA experiment unless overridden:

- **Metrics** from `experiments/sketches/calibration_metrics.py`: ECE (15
  equal-width **and** 15 equal-mass bins, both reported), Brier, AUROC, AURC;
  "miscalibrated" means observed ECE exceeds the 95th percentile of the
  consistency-resampling null, not ECE > 0.
- **Correctness:** exact match where the dataset allows; otherwise an LLM
  judge **plus** human labels on a random 200-item audit subset, with
  judge–human κ reported. Results conditional on judge κ < 0.7 are flagged.
- **Seeds:** ≥ 3 decoding seeds and ≥ 3 paraphrased prompts per condition;
  variance across them is reported as a result, not averaged away.
- **Models:** open-weight where possible, pinned by hash, with base and
  instruction-tuned variants of the same family (e.g. Llama-3.x-8B,
  Qwen2.5-7B, OLMo-2-7B, whose released training stages make base→SFT→DPO
  comparisons possible). Model availability as of 2026-11 is UNCHECKED.
- **Stats:** paired comparisons on the same items (paired bootstrap over items,
  10k resamples); Holm correction across the primary contrasts listed per
  experiment.

---

### EXP-CFA-01 — Confidence elicitation method and prompt sensitivity

**Gaps:** CFA_001, CFA_030, CFA_047.

- **H1:** across models and datasets, the ranking of elicitation methods by
  ECE (verbalized; token probability of the answer; sampling consistency over
  k = 10 samples; the fidelity-style estimator of CFA_030) is unstable under
  prompt paraphrase: Kendall's W across paraphrases < 0.5.
- **H0:** method ranking is stable (W ≥ 0.7) and one method dominates.
- **Variables.** Confidence per item from each method; correctness (exact
  match); prompt paraphrase id (5 per method, written before seeing results).
- **Design.** 4 models × 2 variants (base/instruct where the method permits)
  × 4 methods × 5 paraphrases × 3 seeds on TriviaQA (open-domain), SciQ / MMLU
  (MCQA, to match CFA_030's setting), 2,000 items each.
  Sample size: at n = 2,000 the SE of ECE is roughly 0.005–0.01, enough to
  resolve ECE differences of ~0.02 between methods (rough; confirm in pilot).
- **Prediction.** Verbalized confidence has the largest paraphrase variance
  (CFA_001's own abstract); sampling consistency has the best AUROC.
  **Falsified if** W ≥ 0.7 for every model–dataset cell.
- **Controls / ablations.** Temperature-scaled token probability as a
  post-hoc baseline; a constant-confidence baseline (base rate) to anchor ECE.
- **Threats.** Answer-extraction errors on verbalized formats; MCQA letter
  bias; contamination of TriviaQA in pretraining (affects accuracy, less so
  ranking).
- **Tier:** single GPU (≈ 4 models × 10⁵ generations; a few GPU-days).
- **Establishes / does not.** A stable ranking would support picking one
  method as default. Instability would show single-prompt calibration claims
  are under-determined. Neither says anything about agents acting over many
  steps (EXP-CFA-06).

### EXP-CFA-02 — Does instruction tuning degrade calibration, and does label smoothing prevent it?

**Gaps:** CFA_018, CFA_033.

- **H1 (CFA_018 as stated):** ECE(instruct) − ECE(base) > 0 on the same
  items, and fine-tuning with label smoothing ε ∈ {0.05, 0.1} reduces that
  difference, less for larger vocabularies.
- **H0:** no difference after controlling for accuracy change.
- **Design.** (a) Observational: base vs instruct pairs from 3 families on
  MMLU + MedMCQA (psychiatry subject, to match CFA_033's domain; dataset
  availability UNCHECKED). (b) Interventional: SFT a small base model
  (≤ 1.5B) on a public instruction set with ε ∈ {0, 0.05, 0.1}, 3 seeds each.
- **Key control.** Accuracy changes with tuning, and ECE depends on accuracy;
  compare ECE at matched accuracy (stratify items) and report Brier
  decomposition (reliability vs resolution).
- **Prediction.** H1 holds in (a) for ≥ 2 of 3 families; in (b) ε = 0.1
  reduces ECE gap by ≥ 30% relative. **Falsified if** the base–instruct ECE
  gap's 95% CI includes 0 for all families, or smoothing has no effect beyond
  seed variance.
- **Threats.** Instruct models answer in different formats; use logit-based
  confidence on the answer token for both. For CFA_033 (psychiatric QA in
  small models), the clinical question (is it safe to deploy?) is out of
  scope; this measures calibration only.
- **Tier:** single GPU (part b is small-model SFT, hours per run).
- **Does not establish** that calibration on MCQA transfers to free-form
  clinical answers.

### EXP-CFA-03 — Do confidence thresholds transfer across models and domains?

**Gaps:** CFA_049, CFA_019, CFA_046, CFA_009.

- **H1:** a confidence threshold τ chosen to hit target selective risk r* on
  model A / domain X misses r* by more than 2 points when applied to model B
  or domain Y (CFA_049's "model-specific thresholds"); recalibrating per
  model restores it.
- **H0:** |achieved risk − r*| ≤ 2 points under transfer.
- **Design.** 4 models × 3 domains (customer-service-style intent QA, e.g.
  public Banking77-derived QA; security triage text classification; general
  QA). Fit τ on a calibration split, evaluate on held-out splits of the same
  and other cells. Also evaluate a three-way route (execute/confirm/block,
  CFA_019) and a cost-weighted escalation policy (CFA_046), with costs fixed
  before data are seen.
- **Prediction.** Cross-model transfer fails for ≥ half the pairs; within-model
  cross-domain transfer fails less often. **Falsified if** transfer error ≤ 2
  points for ≥ 80% of pairs.
- **Analysis.** Achieved risk with Clopper–Pearson CI per cell; conformal
  risk control as a reference method with a finite-sample guarantee under
  exchangeability; report where exchangeability is violated (cross-domain).
- **Threats.** Label noise in public intent datasets; cost choices drive
  routing results, so pre-register them.
- **Tier:** single GPU.
- **Does not establish** that any threshold is safe for production mobile or
  SOC agents (CFA_019, CFA_046); it measures transfer on public proxies.

### EXP-CFA-04 — Abstention incentives vs post-hoc thresholding

**Gaps:** CFA_006, CFA_013, CFA_032, CFA_012.

- **H1:** prompting with an explicit scoring rule that rewards abstention
  (CFA_006) yields a risk–coverage curve that **dominates** post-hoc
  thresholding of the same model's confidence (lower AURC), i.e. the prompt
  changes what the model knows to abstain on, not only where it stops.
- **H0:** the prompted operating point lies on or below the post-hoc curve;
  incentives move coverage along the curve without improving it.
- **Design.** PopQA (as in CFA_006) and TriviaQA; 3 open models + 1 API model
  if available; conditions: forced answer, abstention allowed, abstention
  with stated penalty for wrong answers (3 penalty levels). For every
  condition compute the post-hoc curve from the forced-answer confidences.
  For CFA_012 (statistically calibrated validation gates), add split
  conformal abstention at α ∈ {0.05, 0.1} and test empirical coverage on a
  shifted test set (different entity popularity bins).
- **Prediction.** Prompted points lie within the post-hoc curve's bootstrap
  band (H0) for most cells. **Falsified (H0)** if the prompted point has
  lower selective risk than the post-hoc curve at equal coverage, CI
  excluding 0, in ≥ 2 models.
- **Threats.** Abstention phrasing detection; the penalty prompt may change
  answer style, which changes exact-match accuracy; use a judge with audit.
- **Tier:** single GPU.
- **Establishes / does not.** Distinguishes "better abstention" from "more
  abstention". Does not test CFA_013's or CFA_032's architectures, whose
  claims are UNCHECKED and need their code.

### EXP-CFA-05 — HaluEval detector replication and shortcut ablation

**Gaps:** CFA_048, CFA_015 (same paper), CFA_052.

- **H1 (replication):** a linear SVM on TF-IDF + overlap/length features with
  domain-conditional Platt scaling reaches AUROC ≥ 0.80 and ECE ≤ 0.02 on a
  held-out HaluEval split (the source reports 0.835 / 0.009, checked
  abstract).
- **H2 (shortcut):** an **answer-only** model (no question, no knowledge
  context), and a model on length/overlap features alone, each reach AUROC
  within 0.05 of the full detector. If so, the benchmark's labels are
  predictable from generation artifacts, and the detector's score is not
  evidence that it detects unsupported content.
- **H0 for H2:** answer-only AUROC < full AUROC − 0.10.
- **Design.** HaluEval QA, dialogue, summarization (public). 5 random
  train/test splits, plus one **paired split** that keeps the hallucinated
  and correct answers to the same question on the same side (prevents
  question-level leakage). Ablations: full; answer-only; length-only;
  overlap-only; shuffled labels (sanity floor at 0.5).
- **Prediction.** H1 replicates within 0.03 AUROC on random splits; H2 holds
  (answer-only within 0.05) on at least the QA subset. **H1 falsified** if
  AUROC < 0.80 on the paired split for all subsets; **H2 falsified** if
  answer-only AUROC < full − 0.10 on all subsets.
- **Analysis.** AUROC with DeLong or bootstrap CI; ECE against the
  consistency-resampling null; per-domain results reported separately, since
  "domain-conditional" calibration uses domain labels at test time.
- **Threats.** If the source's preprocessing differs, the replication can
  fail for trivial reasons; contact authors (UNCHECKED whether code is
  public). For CFA_052 (a mathematical analysis of hallucination dynamics,
  UNCHECKED), this experiment only supplies an empirical baseline; its
  mathematics needs a separate desk audit.
- **Tier:** laptop CPU (TF-IDF + SVM on ~30k items runs in minutes).
- **Establishes / does not.** A shortcut result would bound what any
  HaluEval-only detector result means. It does not show hallucination
  detection is impossible, nor that LLM-based detectors share the shortcut.

### EXP-CFA-06 — Trajectory-level confidence for tool-using agents

**Gaps:** CFA_037, CFA_039, CFA_051, CFA_022.

- **H1:** a confidence estimate produced **before the final action** from
  trajectory features (internal-state probe, CFA_039; experience-based,
  CFA_037; fast "system-1" relevance model, CFA_051) predicts task success
  with ECE below that of the agent's final verbalized confidence, at matched
  AUROC.
- **H0:** no trajectory method beats verbalized end-of-run confidence by more
  than seed variance.
- **Design.** Two public agent benchmarks with programmatic success checks
  (e.g. a web/search QA benchmark with exact answers and a tool-use benchmark
  such as τ-bench or AppWorld; availability UNCHECKED). One open agent
  scaffold, 2 open models, 5 seeds, ~500 tasks each. Prediction time fixed at
  step k = 50% of median trajectory length and at the final step, both
  reported. For CFA_022 (experience reuse), add a condition in which the
  agent has a memory of prior solved tasks, and measure whether confidence
  stays calibrated on near-duplicate vs novel tasks.
- **Prediction.** Trajectory methods improve AUROC; ECE differences are
  within noise after temperature scaling. **Falsified if** trajectory ECE <
  verbalized ECE with CI excluding 0 after both are temperature-scaled on the
  same calibration split.
- **Threats.** Success checkers can be wrong; audit 100 trajectories by hand.
  Seeds and tool latency create non-exchangeable runs; split by task, not by
  run.
- **Tier:** single GPU to small cluster (≈ 10⁴ agent runs).
- **Does not establish** calibration on open-ended tasks without checkers.

### EXP-CFA-07 — Correlated confidence in multi-agent systems: composition, debate, herding

**Gaps:** CFA_044, CFA_014, CFA_029, CFA_035, CFA_024.

- **H1:** confidence signals from multiple instances of the same base model
  are positively correlated in error (Yule's Q > 0 between agents' errors),
  so naive aggregation (averaging, majority with summed confidence) is
  overconfident; a dependence-discounted fusion (CFA_044) reduces ECE.
- **H2 (herding, CFA_035):** when an agent is shown a peer's answer with a
  randomly assigned high vs low confidence, its switch rate depends on the
  displayed confidence even when the peer's answer is wrong.
- **H0:** error correlation ≈ 0; displayed peer confidence has no effect on
  switching beyond the peer answer itself.
- **Design.** 3 agents × {same model, three different models} on MMLU-Pro /
  GSM8K-style items (~1,500). Conditions: independent answers; one-round
  debate (CFA_014); disagreement-structure UQ (CFA_029); fused confidence.
  For H2, a randomised 2×2 (peer correct/wrong × displayed confidence
  high/low), ~1,000 items per cell. For CFA_024 (LLMs evaluating LLMs),
  compare a multi-agent judge panel to human labels on 300 items.
- **Prediction.** Q > 0.3 for same-model ensembles; debate improves accuracy
  less than majority vote at equal compute (CFA_014's extracted sentence
  says vanilla debate often underperforms majority vote; UNCHECKED beyond
  that sentence); displayed confidence shifts
  switch rate by ≥ 10 points. **Falsified if** Q's CI includes 0 for
  same-model ensembles, or the displayed-confidence effect CI includes 0.
- **Threats.** Order effects in debate transcripts; randomise speaker order.
- **Tier:** single GPU.
- **Does not establish** how humans should weigh agent ensembles.

### EXP-CFA-08 — From calibrated confidence to calibrated reliance

**Gap:** CFA_020.

- **H1:** among human decisions with AI advice, the probability of accepting
  the advice is not a calibrated function of the AI's displayed confidence:
  the reliance curve P(accept | displayed c) differs from P(AI correct | c)
  by more than 0.05 (the source's "calibration–reliance gap"); a monotone
  remapping of displayed confidence reduces team error.
- **H0:** the reliance curve tracks the accuracy curve within 0.05.
- **Design.** (a) Re-analysis of HAIID (the dataset the source used; public
  availability UNCHECKED): estimate both curves with isotonic regression,
  bootstrap by participant. (b) Pre-registered online study: 3 arms
  (raw confidence, remapped confidence, no confidence), ~200 participants per
  arm, between-subjects, a task with ground truth (e.g. image or text
  classification), payment for accuracy.
- **Power (b).** Detecting a 5-point difference in team accuracy at
  baseline ~75% with 80% power needs roughly 1,100 participant-decisions per
  arm; 200 participants × 20 trials gives 4,000 with clustering (ICC to be
  estimated in pilot).
- **Prediction.** Gap > 0.05 in (a); remapping improves team accuracy in (b).
  **Falsified if** (a) gap ≤ 0.05 across confidence bins, or (b) no arm
  difference with adequate power.
- **Threats.** Online-participant attention; task familiarity; the source's
  "simulated team MSE" is not a human result, so (b) is new evidence rather
  than a replication of it.
- **Tier:** laptop for (a); field (IRB + participant payments) for (b).

### EXP-CFA-09 — Does the verifiable-authorization proof of concept reject what it should?

**Gaps:** CFA_054 (primary), CFA_040, CFA_041, CFA_016 (duplicates: the same
paper indexed from arXiv, Semantic Scholar and Frontiers).

- **H1:** the published proof of concept (Groth16 zk-SNARK binding agent,
  request, context and policy; checked abstract) accepts every valid request
  and rejects every request from a pre-registered attack set: wrong agent,
  replayed proof, altered request fields, policy downgrade, context swap.
- **H0:** at least one attack class is accepted.
- **Design.** Obtain the PoC code (UNCHECKED whether released). Build a test
  harness with ≥ 1,000 valid and ≥ 1,000 adversarial requests per attack
  class, generated with fixed seeds. Measure false accept/reject and proof
  generation/verification latency.
- **Prediction.** Zero false accepts for the classes the circuit encodes;
  replay accepted unless a nonce is bound (a design question, not a
  cryptographic one). **Falsified if** any false accept for a class the paper
  claims to cover.
- **Threats.** Groth16 soundness assumes a correct trusted setup; a test
  harness cannot test that assumption, only the circuit's constraints.
- **Tier:** laptop CPU.
- **Establishes / does not.** Tests the PoC's implementation against its own
  claims; says nothing about whether agents should be authorised this way,
  or about calibration. This gap is in the CFA topic only through the word
  "falsifiable" in its title.

### EXP-CFA-10 — Agent security controls, red-team claims, and monitors under a fixed benchmark

**Gaps:** CFA_011, CFA_008, CFA_028.

- **H1:** on a public prompt-injection benchmark (AgentDojo), adding
  zero-trust-style controls (tool allow-lists, per-tool credentials,
  human confirm on writes; CFA_011) reduces attack success rate (ASR) by
  ≥ 50% relative while reducing benign task utility by ≤ 10 points.
- **H2 (CFA_008, red-team reproducibility):** per-scenario attack success
  reported from single exploratory runs has high run-to-run variance: the
  fraction of scenarios whose success flips across 5 seeds is ≥ 20%.
- **H3 (CFA_028):** a trajectory monitor (Agent-ToM-style or a simple LLM
  judge baseline) detects covert sabotage with AUROC ≥ 0.8 on long-horizon
  trajectories, and its AUROC falls with trajectory length.
- **H0s:** no ASR reduction beyond seed noise; flip rate < 5%; monitor AUROC
  independent of length.
- **Design.** AgentDojo suites, 2 models, 5 seeds, controls on/off. For H3,
  a public sabotage-trajectory dataset if one exists (UNCHECKED); otherwise
  generate trajectories with planted side tasks and known labels.
- **Tier:** single GPU / API budget.
- **Does not establish** security of any production deployment.

### EXP-CFA-11 — Efficiency hallucination in LLM code optimization

**Gap:** CFA_053.

- **H1:** when asked to optimise already-optimised code, LLMs propose
  changes and claim speedups that measurement does not support: the
  fraction of claimed-faster patches with a measured speedup < 1.05× (95% CI)
  is > 50%.
- **H0:** claimed speedups are confirmed in ≥ 80% of cases.
- **Design.** 200 functions from public, well-optimised code (e.g. standard
  library or benchmark-suite kernels) plus 200 deliberately slow versions as
  a positive control. 3 models × 3 seeds. Measure runtime with repeated
  timing (≥ 30 runs, pinned CPU, warmup), check functional equivalence with
  the existing tests. Record the model's stated speedup and its confidence.
- **Prediction.** H1 on the optimised set; claims confirmed on the slow set.
  **Falsified if** confirmed-rate ≥ 80% on the optimised set.
- **Threats.** Timing noise on shared machines; use a dedicated runner and
  report the noise floor.
- **Tier:** laptop CPU (+ model inference).

### EXP-CFA-12 — Multimodal hallucination mitigation: replication with seed variance

**Gaps:** CFA_010, CFA_031.

- **H1:** the reported gains of phase-wise self-reward (CFA_010) and
  confidence-calibrated RL for grounding (CFA_031) on POPE/CHAIR-style
  metrics exceed the seed-to-seed standard deviation of the baseline by ≥ 2×.
- **H0:** gains are within 2 SD of baseline seed variance.
- **Design.** Re-run baseline fine-tuning with 5 seeds to estimate variance;
  re-run each method with released code (UNCHECKED) for 3 seeds.
- **Tier:** cluster (RL fine-tuning of a VLM).
- **Does not establish** which mechanism causes any gain.

### EXP-CFA-13 — Longitudinal mandate stability of agent personas

**Gap:** CFA_034.

- **H1:** agents initialised with a mandate ("preserve capital") violate it
  at a rate that rises with episode length, measured by a rule-based
  violation detector on actions (not on text).
- **H0:** violation rate is constant in episode length (slope CI includes 0).
- **Design.** A simulated trading environment with a fixed price process
  (historical returns replayed), 3 models × 3 mandates × episodes of 10, 50,
  200 decisions × 20 seeds. Violations defined before running (e.g. position
  > X% of capital, leverage > 1).
- **Tier:** single GPU / API.
- **Does not establish** anything about real financial deployment.

### EXP-CFA-14 — Reproducibility of a Kubernetes operations measurement substrate

**Gap:** CFA_023.

- **H1:** under the substrate's own protocol (fault injection on a local
  cluster), repeated runs of the same agent on the same fault produce
  outcome metrics (time-to-mitigate, success) whose coefficient of variation
  is < 20%, which is the precondition for the paper's claim that it makes
  operations claims falsifiable.
- **H0:** CV ≥ 20% for most fault classes.
- **Design.** Local `kind` cluster, the paper's fault set (UNCHECKED), 10
  repeats per (agent, fault).
- **Tier:** cluster (or a large single machine).

### EXP-CFA-15 — Deception rate in a hidden-role game with ground truth

**Gap:** CFA_007.

- **H1:** in an Among-Us-style game, LLM impostor agents make statements
  that are false given the game log at a rate distinguishable from crewmate
  agents', and other agents' accusations are better than chance at
  identifying impostors.
- **Operationalisation first (Protocol M):** "deception" = a statement about
  game state contradicted by the engine log; "strategic" = the false
  statement concerns the speaker's own location/actions. Defined before data.
- **Design.** Open game simulator (the source's, if released, UNCHECKED),
  100 games × 3 models, fixed seeds.
- **Tier:** single GPU.
- **Does not establish** intent or deception outside the game.

## 4. Gap → experiment map (all 43 CFA ids)

| gap | class | experiment / reason |
|---|---|---|
| CFA_001 | EMP | EXP-CFA-01 |
| CFA_006 | METH | EXP-CFA-04 |
| CFA_007 | METH | EXP-CFA-15 (operationalise deception first) |
| CFA_008 | METH | EXP-CFA-10 (H2) |
| CFA_009 | METH | EXP-CFA-03 |
| CFA_010 | METH | EXP-CFA-12 |
| CFA_011 | METH | EXP-CFA-10 (H1) |
| CFA_012 | METH | EXP-CFA-04 (conformal arm) |
| CFA_013 | METH | EXP-CFA-04 |
| CFA_014 | METH | EXP-CFA-07 |
| CFA_015 | METH | duplicate of CFA_048 (same paper, DOI vs Semantic Scholar) → EXP-CFA-05 |
| CFA_016 | METH | duplicate of CFA_054 → EXP-CFA-09 |
| CFA_017 | METH | needs a definition first: a proposed portable authorization standard; no measurable claim until a reference implementation and threat model exist. Route through Protocol M; if one appears, extend EXP-CFA-09's harness |
| CFA_018 | METH | EXP-CFA-02 |
| CFA_019 | EMP | EXP-CFA-03 |
| CFA_020 | EMP | EXP-CFA-08 |
| CFA_021 | EMP | not in topic scope: 3D Gaussian-splat asset confidence, admitted on shared words ("calibrated", "confidence"). A replication would re-run AURA on public 3DGS scenes (single GPU), but it does not bear on LLM agents; not assigned |
| CFA_022 | EMP | EXP-CFA-06 (memory arm) |
| CFA_023 | EMP | EXP-CFA-14 |
| CFA_024 | EMP | EXP-CFA-07 (judge-panel arm) |
| CFA_028 | EMP | EXP-CFA-10 (H3) |
| CFA_029 | METH | EXP-CFA-07 |
| CFA_030 | METH | EXP-CFA-01 |
| CFA_031 | METH | EXP-CFA-12 |
| CFA_032 | METH | EXP-CFA-04 (architecture UNCHECKED; tested only as an abstention method if code exists) |
| CFA_033 | METH | EXP-CFA-02 |
| CFA_034 | METH | EXP-CFA-13 |
| CFA_035 | METH | EXP-CFA-07 (H2) |
| CFA_037 | EMP | EXP-CFA-06 |
| CFA_039 | EMP | EXP-CFA-06 |
| CFA_040 | EMP | duplicate of CFA_054 → EXP-CFA-09 |
| CFA_041 | EMP | duplicate of CFA_054 → EXP-CFA-09 |
| CFA_044 | EMP | EXP-CFA-07 |
| CFA_045 | METH | not in topic scope: a Yiddish LM and benchmark, with no calibration or falsifiability claim in its extracted sentence; not assigned |
| CFA_046 | METH | EXP-CFA-03 |
| CFA_047 | METH | EXP-CFA-01 |
| CFA_048 | EMP | EXP-CFA-05 |
| CFA_049 | EMP | EXP-CFA-03 |
| CFA_050 | EMP | needs a definition first: an architecture ("temporal operating layer") with author-stated hypotheses (UNCHECKED). Read the paper's hypotheses, then Protocol M; no experiment is designable from the abstract's first sentence |
| CFA_051 | EMP | EXP-CFA-06 |
| CFA_052 | EMP | EXP-CFA-05 (empirical baseline only; its mathematics needs a desk audit) |
| CFA_053 | EMP | EXP-CFA-11 |
| CFA_054 | EMP | EXP-CFA-09 |

All 20 EMPIRICAL ids also depend on EXP-ENG-01/02 for whether their
recorded split means anything.

The 5 untested markers (ESG extraction benchmark; security-task calibration;
MameLoshnLM v2; serendipity workflows; on-premise medical hallucination
detection) are not gap ids and are not mapped. The security-task paper would
slot into EXP-CFA-03 if it is read and found relevant.
