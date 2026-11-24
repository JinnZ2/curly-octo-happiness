# Experiments — causal states and statistical complexity (`CSS`)

Status: PROPOSED · Date: 2026-11-24 · Read against
`hypotheses/causal-states-and-statistical-complexity.md`,
`hypotheses/RESEARCH_GAPS.md`, `data/engine_report.md` and
`data/hidden_variables.jsonl` at commit
`d469d9db381eabdbf8be22095dc712e79592ded7` (engine run 2026-11-23).

Nothing here is a result. **Checked (abstract)** = the source exists and its
abstract/landing page says what is quoted, as fetched 2026-11-24.

## 1. What the engine claims, and on what evidence

**The draft.** Node confidence 0.60; 2 surviving / 0 active / 0 refuted
claims; 1 open gap (CSS_001); the engine's topic clock is `UNDERIVABLE`
("2 claims cannot support an elasticity; need 4"), so the engine itself says
a null hidden-variable scan on this topic means nothing this run. Most of
the topic's retrieved abstracts went to the unknown journal as unfalsifiable,
and many are off topic (Bekenstein–Hawking entropy, Rényi entropy power
inequalities, trade-network entropy, market troughs).

**The two surviving claims.**

| claim | source | status |
|---|---|---|
| "Neurons ... convey the results of those computations through the statistical structure of their output spike trains." (3 passed / 0 failed) | [The Computational Structure of Spike Trains](https://www.semanticscholar.org/paper/1f98df1950c76bde046f7402273fe1b2fc222895) | UNCHECKED; not a gap id |
| CSS_001: "The entropy rate h of a natural language quantifies the complexity underlying the language." (3 / 1) | [Entropy Rate Estimation for English via a Large Cognitive Experiment Using Mechanical Turk](https://www.semanticscholar.org/paper/166b53765f33d7e5881e7dc73ae481c65fcf6bdc) (Ren, Takahashi, Tanaka-Ishii, *Entropy* 2019) | **checked (abstract)**: a large-scale Shannon guessing experiment on MTurk, estimating English h ≈ 1.22 bits per character |

**What the evidence is.** CSS_001's extracted sentence is a definition, not a
result: that h "quantifies complexity" is a convention (and in computational
mechanics, h_μ measures randomness while C_μ measures structure, so the
sentence is contestable as worded). The draft's falsifier reads "fails to
reproduce the stated 1951 result" (Shannon's 1951 experiment, an identifier);
it is a persisted pre-fix string. Re-running the engine's oracle on today's
corpus, all 4 of CSS_001's recorded test pairs now abstain
(`oracle_audit.py`, flag `verdict_now_zero`), and its cross-reads include
papers on Bekenstein–Hawking entropy and atrial fibrillation. The record
"3 corroborating / 1 contradicting" is therefore not reproducible from the
current data.

## 2. What science needs to be known

### 2a. Gaps the engine recorded

- **CSS_001** (Protocol R): does the source's result hold under its stated
  conditions, and what separates agreeing and disagreeing sources?
- **Topic-level UNDERIVABLE:** too few in-scope claims to fit the topic
  clock. This is a corpus-coverage fact, not a scientific question; it is
  not empirically testable as stated (see map).

### 2b. Gaps I identify

1. **The measurable claim in CSS_001 is the number, not the sentence.** The
   testable proposition is "the entropy rate of (a specified) English text
   source is ≈ 1.22 bits/character under (specified) alphabet and
   estimator". Everything turns on the specification:
   - **alphabet** (26 letters + space, or with case/punctuation): bits per
     character are not comparable across alphabets without conversion — a
     structural check, not an empirical one;
   - **source** (which texts; Shannon used one book);
   - **estimator**: guessing-game bounds, compression, n-gram block
     entropies, and LM cross-entropy each estimate h with different biases.
     LM cross-entropy on held-out text is an upper bound on h for a
     stationary ergodic source (up to sampling error); guessing-game
     estimates rest on extrapolation and on participants' predictive skill.
2. **Estimator validity on known processes.** Before estimating h or C_μ on
   real data, an estimator should recover them where they are known.
   `experiments/sketches/entropy_rate_check.py` shows that the golden-mean
   and even processes have the same h_μ = 2/3 bit and C_μ ≈ 0.918 bit but
   block-entropy estimates converge at L = 2 for one and slowly for the
   other, and that plug-in estimates are biased low at short samples. The
   repo's `grounding/core/epsilon_machine.py` (CSSR phases I–II only; its
   own docstring says "read it comparatively, not as an absolute") is tested
   in `tests/test_epsilon_machine.py` qualitatively: a fair coin gives
   C_μ < 0.05 and h_μ > 0.95, and a period-6 stream gives C_μ > 0.5 (its
   analytic C_μ is log₂6 ≈ 2.585 bits). No test compares it with analytic
   values on a process with both structure and randomness.
3. **"Quantifies complexity" needs a definition before it is testable.** If
   it means h is a useful predictor of some other measured property of
   languages (learnability, processing difficulty), that is a separate,
   testable claim; as written it is definitional.

## 3. Experiments

### EXP-CSS-01 — Is h ≈ 1.22 bits/char consistent with model-based upper bounds on the same text?

**Gap:** CSS_001.

- **H1:** for text drawn from the same distribution and alphabet as the
  source's experiment, the per-character cross-entropy of at least one public
  language model is below 1.22 − 2·SE (SE = the source's reported uncertainty;
  UNCHECKED, read from the paper). Because cross-entropy upper-bounds h,
  this would show the 1.22 estimate overstates h.
- **H0:** all measured model cross-entropies are ≥ 1.22 − 2·SE (consistent
  with, not confirming, the source's value).
- **Variables.** Cross-entropy in bits per character on the source's 27-symbol
  alphabet (lowercase letters + space, if that is what the source used;
  UNCHECKED). For subword models, total log-loss over the passage divided by
  the character count after mapping to the alphabet; the mapping must be
  applied **before** scoring (score the normalised text), otherwise the
  model is charged for case and punctuation it was not asked to predict.
- **Design.** (a) Obtain the source's passages if released (UNCHECKED),
  otherwise sample 200 passages from a public-domain English corpus matched
  to its genre. (b) Estimators: PPM-style compression (e.g. `xz`/`zstd` at
  max as weak upper bounds), n-gram block entropy with Miller–Madow
  correction and extrapolation, and 3 open LMs of increasing size, with
  long context. (c) Held-out discipline: exclude texts likely in model
  pretraining or measure contamination (lower loss on memorised text would
  bias the bound below h of the *source*, not of the passage).
- **Prediction.** H1 holds for the largest model (modern LMs are strong
  character predictors), while compression estimates are above 1.22.
  **Falsified if** every LM's bound is ≥ 1.22 − 2·SE on uncontaminated text.
- **Analysis.** Bootstrap over passages; report the estimate–context-length
  curve; all values on the same alphabet.
- **Threats.** Contamination; alphabet mismatch; the source's estimator
  targets the limit h, while a finite-context LM gives an upper bound on a
  finite-order conditional entropy (which still upper-bounds h).
- **Tier:** single GPU (scoring only; a laptop suffices for ≤ 1B models).
- **Establishes / does not.** H1 would show the guessing-game estimate is not
  tight. H0 is uninformative about whether 1.22 is correct: an upper bound
  above an estimate is consistent with it. Neither result bears on whether h
  "quantifies complexity".

### EXP-CSS-02 — Do the repo's h_μ / C_μ estimators recover known values?

**Gap:** identified in 2b(2); supports CSS_001 and the topic generally.

- **H1:** on processes with analytic h_μ and C_μ (golden mean, even process,
  simple nonunifilar source, a period-3 process, a biased coin), the repo's
  `reconstruct()` recovers C_μ within 0.05 bit and h_μ within 0.02 bit/symbol
  at sample length T ≥ 10⁴, for history lengths L chosen by
  `equalized_history_length`.
- **H0:** error exceeds those tolerances for at least one process at
  T = 10⁵ (estimator inconsistent or biased for that class).
- **Design.** 5 processes × T ∈ {10³, 10⁴, 10⁵} × L ∈ {2, …, 10} × 50 seeds.
  Compare with block-entropy estimates (sketch) and, if available, an
  established CSSR implementation. Expected failure: the even process
  (infinite Markov order) and the nonunifilar source (uncountably many
  causal states) should defeat any finite-L estimator; the prediction is
  that they do, and the experiment documents how.
- **Prediction.** H1 holds for finite-order processes; fails for the
  nonunifilar source at every T. **Falsified if** the estimator recovers C_μ
  for the golden-mean process outside tolerance at T = 10⁵.
- **Tier:** laptop CPU.
- **Establishes / does not.** Whether numbers from this estimator can be
  compared to analytic values (numerical agreement on toy processes). Does
  not validate it on real data, where the true process class is unknown.
- **Sketch:** `python experiments/sketches/entropy_rate_check.py`
  (block-entropy baseline on golden-mean and even processes).

## 4. Gap → experiment map

| gap | experiment / reason |
|---|---|
| CSS_001 | EXP-CSS-01 (the measurable number); EXP-CSS-02 (estimator validity); the definitional sentence itself needs a definition first (what property "complexity" should predict) |
| topic UNDERIVABLE (not a gap id) | not empirically testable: it records that the engine's queries returned too few in-scope claims. Remedy is query coverage in `config/topics.json`, which this PR does not touch |

CSS_001 also depends on EXP-ENG-01/02: its recorded split is not
reproducible on the current corpus.
