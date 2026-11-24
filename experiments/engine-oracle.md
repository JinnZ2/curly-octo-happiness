# Cross-cutting: is the engine's evidence what it says it is?

Status: PROPOSED · Date: 2026-11-24 · Read against engine output at commit
`d469d9db381eabdbf8be22095dc712e79592ded7` (engine run of 2026-11-23).

Every claim-backed gap in `hypotheses/RESEARCH_GAPS.md` (38 of 61 ids; the
other 23 are escape-hatched METHODOLOGICAL gaps with no live claim) is defined
by a record such as "3 corroborating / 2 contradicting readings, beta 0.57".
Before anyone spends lab or GPU time on a "split", it is worth knowing whether
the split measures disagreement between papers at all. The three experiments
here test that. They are prerequisites for the per-topic experiments, not
substitutes for them: the per-topic experiments test the *world*; these test
the *instrument that pointed at* those questions.

## What the oracle is (read from the code, not inferred)

From `scripts/hypothesis_engine.py` at the commit above:

- A claim is `"On topic {topic}, {title} reports: {first sentence of abstract}"`
  (`distill_claim`). The first sentence of an abstract is usually motivation,
  e.g. CFA_048: "LLMs can generate fluent yet unsupported content". The
  engine's design doc and `RESEARCH_GAPS.md` both say this.
- A test (`corroboration`) passes when another same-topic abstract shares at
  least 2 of the claim's non-topic tokens carrying at least 10 bits of IDF,
  and the sentences containing those tokens contain more words from
  `CORROBORATION_MARKERS` ("support", "consistent", "reproducible", ...) than
  from `CONTRADICTION_MARKERS` ("fail", "cannot", "does not", ...). It fails
  in the opposite case. This is lexical polarity, not stance.
- `Claim.reformulate()` (`grounding/core/claims.py`) resets `passed`/`failed`
  to 0 but keeps `tested_against`, so the record displayed on a reformulated
  gap counts only the testimony that came in *after* the latest
  reformulation.

These are structural facts about the instrument. They do not show that any
verdict is wrong; they show what a verdict is made of.

## What the read-only audit sketch reports

`experiments/sketches/oracle_audit.py` re-runs the engine's own
`corroboration()` over every recorded (claim, finding) pair and writes an
annotation sheet. It does not write to `data/` or `hypotheses/`. On the
commit above it reports (this is output of a sketch describing the engine's
data, not a finding about any paper):

| flag | pairs | what it means |
|---|---|---|
| recorded pairs | 515 over 38 claim-backed gaps | from `claim.tested_against`, joined to `findings_log.jsonl` |
| `title_tok` | 294 | at least one shared token occurs only in the claim's title, not its extracted sentence |
| `template_tok` | 124 | a shared token is `report`, which comes from the template word "reports:" |
| `verdict_now_zero` | 91 | the oracle, re-run on today's corpus IDF, abstains on a pair that once counted (path dependence) |
| `same_title` | 8 | the "independent" source is the same paper under another URL |

The `same_title` cases are the clearest: one paper ("Cryptographically
verifiable authorization for autonomous AI agents", arXiv 2607.21325,
checked to exist) appears as four gap ids (CFA_016, CFA_040, CFA_041,
CFA_054) from three indexes, and its copies are recorded as
**contradicting each other** (6 pairs, all verdict −1). RVC_001 (the GART
preprint) counts its own journal version (Entropy 28(11):1182) as a
corroboration, and CFA_048 counts its own DOI copy (CFA_015) the same way.

---

## EXP-ENG-01 — Does the oracle's verdict agree with human stance labels?

**Gaps:** every claim-backed gap (CFA_001, 019–024, 028, 037, 039–041, 044,
048–054; HVD_001–011; CSS_001; RVC_001–006). Prerequisite for interpreting
any of their "split" records.

- **Hypothesis H1:** the oracle's ±1 verdicts agree with expert stance labels
  above chance: Cohen's κ > 0.4 ("moderate"), with the 95% CI excluding 0.2.
- **Null H0:** κ ≤ 0.2, i.e. the oracle's polarity is not a usable proxy for
  whether paper B supports, contradicts, or does not address the claim of
  paper A.
- **Variables.** Unit: one recorded (claim, other-abstract) pair. Oracle
  label ∈ {+1, −1, 0} from `oracle_audit.py` (`verdict_now`). Human label ∈
  {+1 supports, −1 contradicts, 0 does not address / different subject},
  assigned against (i) the extracted first-sentence claim **and separately**
  (ii) the source paper's main stated result, because the two can differ.
- **Design.** All 515 pairs (or, if annotator time is short, a stratified
  sample of 200 by topic × oracle verdict, which preserves the κ estimate's
  stratification). Two annotators per pair, blind to the oracle verdict and
  to each other; a third resolves disagreements. Pair order randomised with a
  fixed seed. Annotators read the abstract, not only the triggering sentence.
- **Sample size.** With 200 pairs and three categories, the SE of κ is
  roughly 0.04–0.06 at κ ≈ 0.3–0.5 (Fleiss' large-sample formula), enough to
  separate 0.2 from 0.4. This is a rough planning figure; compute the actual
  CI by bootstrap over pairs.
- **Pre-registered prediction.** κ(oracle, human-vs-first-sentence) < 0.2,
  and κ(oracle, human-vs-main-result) lower still. Rationale: the markers
  fire on problem statements ("existing methods fail to ...") as often as on
  results. **Falsified if** κ > 0.4 with CI lower bound > 0.2.
- **Analysis.** κ with bootstrap CI; confusion matrix; per-flag breakdown
  (does `same_title`/`template_tok`/`title_tok` predict disagreement?);
  inter-annotator κ reported first. If inter-annotator κ < 0.6, the task is
  ill-posed and the oracle cannot be scored against it; report that instead.
- **Confounds / threats.** Annotators who know the engine may anchor on
  marker words: give annotators the abstract without highlighting. Stance is
  often "different subject" (0), which a three-way κ penalises differently
  from a sign error; also report the sign-agreement rate on pairs both label
  non-zero.
- **Tier:** laptop CPU + about 1–2 annotator-days.
- **What a result establishes.** A positive result (κ > 0.4) licenses reading
  split records as weak evidence of disagreement. A negative result means the
  RESEARCH_GAPS records are not evidence about the papers; the gaps remain
  useful as a reading list, and the per-topic experiments below stand on
  their own. **Does not establish** whether any claim is true.
- **Sketch:** `python experiments/sketches/oracle_audit.py --sheet pairs.csv`,
  fill the `human` column, then `--labels pairs.csv` prints κ.

## EXP-ENG-02 — Record integrity: duplicates, reformulation resets, IDF drift

**Gaps:** all 38 claim-backed gaps; specifically the duplicate cluster
CFA_016/040/041/054, CFA_015/048, and RVC_001.

- **Hypothesis H1:** at least one open gap changes class (contested ↔
  contradicted ↔ not a gap, using the engine's own `classify_gap` rule) when
  its record is recomputed with (a) one vote per paper (dedupe by normalised
  title/DOI), (b) the full test history instead of the post-reformulation
  history, and (c) verdicts re-evaluated under the current IDF.
- **Null H0:** no gap changes class under (a)–(c) singly or jointly; the
  records are robust to these bookkeeping choices.
- **Design.** Deterministic replay, no network. For each gap: compute
  passed/failed under the 2×2×2 factorial of {dedupe on/off} × {full vs
  post-reformulation history} × {stored vs re-evaluated verdict}. Since
  per-pair verdicts are not stored, the "stored" arm is approximated by
  re-running `corroboration()` under the IDF of the corpus as of each
  finding's log date (reconstructable by truncating `findings_log.jsonl`).
- **Pre-registered prediction.** The CFA_016/040/041/054 cluster collapses to
  one claim, and its self-contradiction pairs vanish; ≥ 5 gaps change class.
  **Falsified if** fewer than 1 gap changes class.
- **Analysis.** A table of class changes per factor; report each factor's
  marginal effect. No statistics needed: this is an exact recomputation.
- **Threats.** The replay approximates historical IDF; state it. Changing the
  dedupe key (title vs DOI vs arXiv id) can change results; report all three.
- **Tier:** laptop CPU, hours.
- **What it establishes.** Whether the gap list is a stable function of the
  literature or of indexing and bookkeeping. **Does not establish** anything
  about the papers' claims. If adopted, the fix belongs in the engine, which
  this PR does not modify.

## EXP-ENG-03 — Does the extracted sentence carry the paper's claim?

**Gaps:** all 61 ids (escape-hatched ones included, since their extracted
sentence is what was reformulated three times).

- **Hypothesis H1:** for most gaps, the extracted first sentence is
  background or motivation rather than the source's result, so the gap's
  "Question" ("does the result ... hold") is about a sentence the paper does
  not argue for.
- **Null H0:** in ≥ 50% of gaps the first sentence states the paper's main
  result or a falsifiable claim the paper tests.
- **Design.** Two annotators label each of the 61 extracted sentences as
  {result, method, background/motivation, definition}, reading the full
  abstract; for each they also copy the abstract's main-result sentence.
  Then re-stake the main-result sentence through the engine *in a temp dir*
  (`--data-dir /tmp/... --hypotheses-dir /tmp/...`, per CLAUDE.md) and
  compare the resulting record with the current one.
- **Pre-registered prediction.** > 70% background/motivation (from reading
  the claim column of RESEARCH_GAPS.md, nearly every sentence is
  motivational). **Falsified if** ≤ 50%.
- **Tier:** laptop + about half an annotator-day.
- **What it establishes.** Whether gap ids should be read as "this paper"
  (a reading-list entry) or "this claim" (a hypothesis). Per-topic files below
  take the first reading and design experiments around each source's
  **stated result** (checked where marked), not around the extracted
  sentence.
