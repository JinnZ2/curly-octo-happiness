# EXP-CFA-05 — results (run 2026-11-27)

Design: `experiments/calibration-and-falsifiability-of-llm-agents.md` § EXP-CFA-05 (issue #47). Gaps: CFA_048, CFA_015, CFA_052.

## Provenance

- Repo commit: `a3d5c55328cc671c4384d0a02eccb70c7d828b89`.
- Environment: Python 3.14.8, numpy 2.5.5, scipy 1.18.1, scikit-learn 1.9.1; Intel Xeon @ 2.90 GHz, 4 vCPU (shared).
- Runtimes: `run.py` 2656 s; `calibrated_auroc.py` 540 s.
- Data: [RUCAIBox/HaluEval](https://github.com/RUCAIBox/HaluEval) `data/` at commit `b7253db3cdaa0ab2c382f92b26b390109174f77e`. Full sha256 in `raw/input_sha256.txt`; prefixes:
  - qa: `89ed139e…`
  - dialogue: `9c461df2…`
  - summarization: `86d2561e…`
  - general: `73302cd9…`

  There are 64,507 examples: 20,000 per paired task (10,000 items × right/hallucinated) plus 4,507 general. 18.1% of the general subset is labelled hallucinated, which matches the repo's description.
- Source being replicated: [doi:10.69987/aimlr.2025.60401](https://doi.org/10.69987/aimlr.2025.60401) (abstract only). It reports:
  - 30k-unigram TF-IDF + 11 overlap/length features, LinearSVC, domain-conditional Platt scaling: AUROC 0.835, ECE 0.009 (15 bins).
  - Raw sigmoid: AUROC 0.822, ECE 0.080.
- Commands:
  - `python3 run.py /tmp/halueval`
  - `python3 calibrated_auroc.py /tmp/halueval`, a post-hoc supplement (see deviation 6).
- Seeds:
  - Random splits: 0–4. Paired split: 100.
  - LinearSVC `random_state` = split seed.
  - Bootstraps: `default_rng(seed + 1000)`.
- Raw output: `raw/results.json` (30 fits: 6 splits × 5 models, per-domain metrics) and `raw/calibrated_auroc.json`.

## Deviations (recorded before results)

1. **The source's 11 hand features and its splits are not published** in the abstract, and code availability is UNCHECKED. I defined:
   - 5 length features: answer chars, answer tokens, context tokens, query tokens, answer/context ratio.
   - 6 overlap features: see `hand_features` in `run.py`.
   - Splits: 60/20/20 train/validation/test. Platt scaling is fitted per domain on validation. C = 1.

   A replication gap could therefore come from preprocessing differences, as the design's threats section anticipates.
2. **The general subset is included** as a fourth domain. It has no knowledge context and is not 50/50. Its per-domain results are reported separately.
3. **AUROC CIs** come from a cluster bootstrap over HaluEval items, so the two answers to one question resample together. 1000 reps pooled, 500 per domain, 200 for the ablations.
4. **ECE null.** Each ECE is compared with the 95th percentile of ECE under consistency resampling (labels drawn from the model's own p, 200 reps).
5. **Answer-only model:** TF-IDF on the answer text plus answer length (2 features). No question or context.
6. **Post-hoc supplement.** `run.py` computes pooled AUROC on the raw SVM score. The design's detector outputs domain-conditional Platt probabilities, and per-domain scaling changes the pooled ranking. After seeing the main results I added `calibrated_auroc.py`, which refits the same `full` and `answer_only` models with identical splits and seeds and reports pooled AUROC of the calibrated p. Its raw-score AUROCs reproduce `run.py` to 4 decimals. Both numbers are reported; the calibrated one is the closer match to the design's detector.

## Results

### Pooled test set

| model | random splits, raw-score AUROC: mean (range), 95% CI per split ≈ ±0.007 | random, calibrated-p AUROC | paired split, raw [CI] | paired, calibrated | ECE (15 bins), random mean (range) | ECE paired |
|---|---|---|---|---|---|---|
| full | 0.804 (0.798–0.808) | 0.814 (0.810–0.818) | 0.859 [0.854, 0.865] | 0.865 | 0.024 (0.018–0.030) | 0.012 |
| answer-only | 0.856 (0.853–0.859) | 0.869 (0.867–0.873) | 0.870 [0.864, 0.876] | 0.884 | 0.015 (0.013–0.017) | 0.010 |
| length-only | 0.716 (0.713–0.718) | – | 0.718 [0.712, 0.724] | – | 0.025 | 0.025 |
| overlap-only | 0.743 (0.738–0.747) | – | 0.744 [0.737, 0.750] | – | 0.041 | 0.044 |
| shuffled labels | 0.504 (0.500–0.513) | – | 0.496 [0.492, 0.499] | – | 0.008 | 0.002 |

- **ECE noise floor.** The 95th-percentile ECE of a perfectly calibrated model with these predictions is 0.014–0.015. Full-model ECE exceeds it on all 5 random splits but not on the paired split (0.012 vs 0.014).
- **Raw sigmoid ECE** (no Platt) for the full model is 0.065 on random splits. That is comparable to the source's raw 0.080.

### Per domain, raw-score AUROC

Random-split mean (paired split in parentheses):

| domain | full | answer-only | answer-only − full | length-only | overlap-only |
|---|---|---|---|---|---|
| QA | 0.939 (0.955) | 0.908 (0.917) | −0.031 (−0.038) | **0.958** (0.962) | 0.930 (0.932) |
| dialogue | 0.714 (0.793) | 0.821 (0.838) | **+0.107** (+0.045) | 0.711 (0.713) | 0.635 (0.640) |
| summarization | 0.700 (0.808) | 0.872 (0.896) | **+0.172** (+0.088) | 0.722 (0.726) | 0.649 (0.655) |
| general | 0.576 (0.577) | 0.576 (0.581) | −0.000 (+0.004) | 0.499 (0.500) | 0.468 (0.425) |

Paired-split per-domain CIs for full and answer-only are in `raw/results.json`. For example, full dialogue is 0.793 [0.782, 0.803] and full summarization is 0.808 [0.797, 0.820].

What the tables show:

- On QA, the length features alone (0.958) beat the full detector (0.939).
- On dialogue and summarization, dropping the context and question *improves* AUROC by 0.10–0.17 on random splits.
- The paired split, where both answers to an item fall on the same side, gives a *higher* full-model AUROC than the random splits (0.859 vs 0.804). A possible explanation, not tested: on random splits the same context appears in training with the opposite label, which makes context TF-IDF features noise.

## Verdict vs pre-registered predictions

**H1, replication.** Prediction: "replicates within 0.03 AUROC on random splits", with AUROC ≥ 0.80 and ECE ≤ 0.02.
Falsifier: "AUROC < 0.80 on the paired split for all subsets".

**SUPPORTED for AUROC, not for ECE. The falsifier was not triggered.**

- Calibrated-p AUROC averages 0.814 against the source's 0.835: a gap of −0.021, within 0.03. Raw-score AUROC averages 0.804 (−0.031), just outside 0.03 for the raw score.
- Paired-split subsets: QA 0.955 and summarization 0.808 are ≥ 0.80; dialogue 0.793 and general 0.577 are below.
- ECE ≤ 0.02 holds on the paired split (0.012) and on 2 of 5 random splits. It fails on 3 of 5 (up to 0.030), above the 0.014–0.015 noise floor.
- With my features I do not reproduce the source's 0.009.

**H2, shortcut.** Prediction: "answer-only within 0.05 [of full] on at least the QA subset".
Falsifier: "answer-only AUROC < full − 0.10 on all subsets".

**SUPPORTED.**

- On QA, answer-only is within 0.05 of full: −0.031 random, −0.038 paired. Length-only *exceeds* full on QA (+0.019).
- Pooled, answer-only beats full by +0.05 on random splits and +0.011 on the paired split (calibrated: +0.055 and +0.019).
- No subset has answer-only < full − 0.10. H0 for H2 is rejected.
- The design's broader H2 also asks for length/overlap-only within 0.05 of full. That holds on QA only. Pooled, length-only is 0.09 below full and overlap-only 0.06 below.

## What this does and does not establish

- **Does:**
  - On HaluEval, a TF-IDF + linear SVM detector of this kind reaches roughly the reported AUROC.
  - A model that never sees the question or the knowledge context does as well or better, and length alone nearly saturates QA.
  - So high AUROC on these HaluEval subsets is achievable from properties of the generated answers. A detector's score here is not, by itself, evidence that it checks answers against the source. This bounds what the CFA_048/CFA_015 result can mean.
- **Does not:**
  - Show the source's exact pipeline (features, splits, preprocessing unknown) has the same shortcut.
  - Show hallucination detection is impossible.
  - Show that LLM-based detectors share the shortcut.
  - Say anything about CFA_052's mathematics, which needs a separate desk audit and stays UNCHECKED.
  - Establish that the paired-split increase has the explanation offered above; it is untested.
