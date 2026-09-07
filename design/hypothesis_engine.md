# Hypothesis Engine — Design Doc

An autonomous, **stdlib-only, deterministic** research pipeline for
`curly-octo-happiness`. It explores free scholarly APIs, stakes claims in the
repo's epistemic machinery, tests them by cross-source verification,
reformulates failures (with escape hatches), scans for hidden variables, and
consolidates surviving claims into hypothesis drafts. No LLM in the loop, so it
runs free on GitHub runners.

## Pipeline

```
                 config/topics.json
                        |
                        v
   +--------------------------------------------+
   | 1. EXPLORE   arXiv | Semantic Scholar | Crossref
   |     (urllib, timeouts, log-and-continue)   |
   +--------------------------------------------+
                        v
   | 2. LOG     data/findings_log.jsonl (dedup by hash)
   |          + EpisodicMemory append
                        v
   | 3. CLAIM   distill -> Claim(text, falsification, scope, reference_class)
   |            classify_falsifiability:
   |              unfalsifiable -----> data/unknown_journal.jsonl
   |              else ------------> DependencyTree (stake)
                        v
   | 4. TEST    cross-source corroboration/contradiction heuristics
   |            pass -> conf +0.1, fail -> conf -0.2
   |            persist data/claim_tree.json (reload next run)
                        v
   | 5. MODIFY  failed claims -> reformulate() (narrowed scope)
   |            reformulation_count >= 3 -> ESCAPE HATCH -> unknown journal
                        v
   | 6. HIDDEN  residual = |beta_confidence - 0.5| per topic
   |            trigger: mean|residual| >= 0.1 AND |pearson r| > 0.5
   |            -> data/hidden_variables.jsonl (hidden_variable_suggestion)
                        v
   | 7. CONSOLIDATE  hypotheses/<topic-slug>.md (regenerated each run)
   |                 + data/engine_report.md (stdout too)
   +--------------------------------------------+
```

## Stage mapping to repo philosophy

| Stage | Repo concept |
|---|---|
| 3. claim | **Claim staking** — every finding becomes a `Claim` with an explicit falsification condition, scope, and reference class before entering the tree. |
| 4. test | **Falsification-first testing** — with no world available, the engine uses cross-source verification as the test oracle: independent corroboration raises confidence, contradiction lowers it. |
| 5. modify | **Escape hatches** — failed claims are `reformulate()`d with narrower scope; at 3 reformulations the claim exits the tree into the unknown journal rather than being infinitely patched. |
| 3/5 | **Unknown journal** — unfalsifiable or escape-hatched content is preserved, flagged, never silently deleted. |
| 6. hidden | **Hidden-node detection** (mirrors `modules/hnd.py`) — residuals and candidate series are put on one shared `TimeGrid` of equal-*time* buckets (equal-count buckets would make volume constant by construction, and so untestable), each claim placed by the date of the finding it was staked from and weighted by the precision of its own Beta posterior. The candidates are `findings_volume` and `source_diversity`. A candidate must survive: ≥ `MIN_BUCKETS` occupied buckets, ≥ `MIN_STANDING_TESTS` standing test outcomes, mean\|residual\| ≥ 0.1, residual spread ≥ `RESIDUAL_SPREAD_FLOOR`, partial correlation against the clock (collinear candidates are refused outright), and a positive `description_length_gain` in bits over the effective sample size. |
| 2. log | **Episodic memory** — findings are appended to a persistent memory index (`data/episodic_memory.json`; repo `EpisodicMemory` used when importable). |

## Config reference (`config/topics.json`)

```json
{
  "topics": [
    {
      "name": "<human-readable topic name>",
      "queries": ["<query string 1>", "..."],
      "sources": ["arxiv", "semantic_scholar", "crossref"]
    }
  ]
}
```

- `name` — used for scoping claims, hypothesis file slugs, and hidden-variable grouping.
- `queries` — each is sent to every listed source.
- `sources` — subset of `arxiv`, `semantic_scholar`, `crossref`.

**Adding a topic:** append an entry and commit; the next scheduled run picks it up.

## CLI

```
python scripts/hypothesis_engine.py [--config config/topics.json] [--dry-run]
    [--max-per-topic N] [--data-dir DIR] [--hypotheses-dir DIR] [--sample FILE]
```

- `--dry-run` — skips all network access and uses `scripts/sample_findings.json` (5 entries, 2 topics). Used by CI smoke tests.
- `--max-per-topic N` — caps results per query per source.
- `--data-dir` / `--hypotheses-dir` / `--sample` — redirect the outputs and the
  sample corpus; the tests use these to run against a tmpdir.

Workflow: `.github/workflows/hypothesis-engine.yml` (Mondays 06:17 UTC, plus
`workflow_dispatch`). The offline test suite gates the networked run.

## Operational notes

- **Idempotency:** findings are deduplicated by a SHA-256 hash of
  `source|title|url`; re-running with the same findings changes nothing. The
  claim tree is persisted in `data/claim_tree.json` and reloaded each run.
- **Rate limits:** the engine sleeps 1s between API calls and caps results;
  Semantic Scholar is unauthenticated (100 req / 5 min shared). Failures are
  logged and the run continues.
- **Timeouts:** every network call goes through `_fetch()` with a 20s timeout.
- **Artifacts & commits:** the workflow uploads `data/` + `hypotheses/` as
  artifacts and commits them back with message
  `chore(engine): weekly research digest <date>`.
- **Issue on new hypotheses:** if `data/engine_report.md` contains the marker
  `NEW HYPOTHESIS` (≥3 surviving claims on a topic), the workflow opens an
  issue with the report body.

## Limitations

- **Heuristic claim extraction** — claims are template-distilled
  ("On topic {topic}, {title} reports: {first sentence of abstract}"), not
  semantically parsed. False positives are expected and handled by staking +
  testing rather than by better parsing.
- **No LLM in the loop** — fully deterministic; quality is bounded by keyword
  overlap, negation heuristics, and shallow numeric extraction.
- **Cross-source "testing" is weak evidence** — corroboration is not
  replication; hypothesis drafts are starting points for human review.
- Crossref/abstract availability varies; findings without abstracts produce
  thin claims that tend to route to the unknown journal.
- **Stage 6 gates on quantities, not conventions.** Large residuals alone are
  not a hidden variable. The first live run (2026-08-17) reported
  `source_diversity` at r=−0.72 on seven claims; it was an artifact, and the
  fix is four measurements rather than four thresholds:

  | Problem | What was wrong | The physics | The measure |
  |---|---|---|---|
  | Alignment | residuals zipped to candidates by list position — claim-stake order against chronological order; reordering the same data moved r from −0.72 to +0.46 | — | one shared `TimeGrid`; each claim placed by its finding's date |
  | Weighting | an untested claim and one tested 20 times to a dead heat both read `beta_confidence` 0.5 | Fisher information; Gauss-Markov minimum-variance weighting | `beta_precision` = 1/Var(Beta), linear in test count (12 against 172) |
  | Confounding | `findings_volume` correlates with elapsed time at **0.876**, and accumulating evidence drifts with time too | Reichenbach's common cause | `weighted_partial` controls for the clock; collinear candidates are refused, not scored |
  | Threshold | α = 0.05 is a convention, and |r| > 0.5 fires on 46% of random orderings at n = 7 | Rissanen's MDL (Schwarz/BIC form) | `description_length_gain` in bits, charged against Kish's `effective_sample_size` |

  Two further notes, because the tempting summary is wrong. **MDL alone would
  not have caught this** — it scores the false positive at +2.3 bits. Its job
  is removing the arbitrary threshold, not doing the rejecting. And **weighting
  alone cannot catch it either**: when every claim is equally uninformative the
  weights are merely equal, so an absolute floor (`MIN_STANDING_TESTS`) is
  needed on top — a residual built from an untouched Beta(1,1) prior is not a
  measurement at all. Replaying the live corpus, every topic is refused and
  each gate earns its keep on a different one.
- **Every gate being principled did not make the scan correct.** After the four
  measures above were in, the scan still fired on **36% of corpora containing no
  driver at all**. Two were bugs in the MDL accounting — `k=1` when conditioning
  on the clock fits two parameters, and no `log2(m)` charge for picking the best
  of *m* candidates, which had been silently dropped along with the permutation
  test's Bonferroni correction. The rest was the absence of a floor on effective
  sample size. Run `python scripts/hypothesis_engine.py --calibrate`:

  | n_eff floor | false pos | 95% upper | power |
  |---|---|---|---|
  | none | 19.6% | 21.4% | 65.6% |
  | 4.0 | 10.6% | 12.0% | 64.5% |
  | **5.0** | **3.4%** | **4.2%** | **58.6%** |
  | 6.0 | 0.4% | 0.7% | 38.8% |
  | 8.0 | 0.0% | 0.2% | 4.8% |

  `calibrate_scan` returns the *loosest* floor holding the target rate, judged
  on the Wilson upper bound rather than the point estimate, and refuses a target
  it cannot resolve with the trials given — the same contract as
  `SequentialDamageDetector.calibrate_from`. It also corrected a guess: 6.0 was
  chosen by eye because it is where the rate first rounds to zero, and it costs
  20 points of power for nothing. **A gate tightened past its target is not
  safer, only deafer.** Read the power column before trusting any suggestion:
  even calibrated, the scan misses about two real drivers in five.
- **A topic clock separates "found nothing" from "could not look."** Adapted
  from `JinnZ2/Simulators` `claim-record`, whose clock field is
  `shelf_life = time_constant / |coupling|` with coupling a *dimensionless*
  elasticity — dimensionless because a raw partial derivative carries units and
  a time divided by one of those is not a time. Here τ is the topic's median
  interval between findings and coupling is d(log beta_confidence)/d(log local
  volume). It reports the same three states that spec does, and on the live
  corpus (2 runs, 36 claims) three topics derive — shelf lives 1.40, 2.98 and
  2.49 years — while the fourth, holding two claims, is `UNDERIVABLE`.

  Two details that were wrong on the first attempt and are worth keeping
  written down. Volume must be counted in a window of the topic's *own* τ
  rather than per calendar year: a year is arbitrary, and degenerate whenever a
  topic's whole span is shorter than one, because every claim then sees the
  same count and no elasticity exists. And the elasticity has to be fitted to
  `beta_confidence` itself, not to `|residual|` — the absolute value discards
  direction, so a topic whose claims split cleanly for and against reads as
  perfectly insensitive when it is nothing of the kind. τ across the four real
  topics spans 0.082 to 0.783 years, a tenfold range, which is the measured
  form of the reason one calendar grid cannot serve them all.
- **The archival hazard is not measurable from this corpus yet.** Applying the
  stipulated 0.06/year hazard from `Simulators` `observer-exclusion` drops
  r(volume, calendar time) from 0.554 to 0.150 and lifts the pre-2015 share of
  the corpus from 15.3% to 42.2% — i.e. much of the "exponential growth" the
  clock control exists to screen off may be the index forgetting rather than
  the field adopting. That figure is *borrowed, not measured*: 0.06/year is a
  hazard for physical surviving artifacts, and arXiv does not lose papers at
  6%/year. Two ways to measure it properly were tried and both are blocked
  today — querying the APIs for year-binned population counts (the sandbox
  network policy denies both hosts; it would work from the Action, which
  already reaches them) and capture–recapture between the two sources (exactly
  **one** title overlaps across 139 findings, so Lincoln–Petersen returns
  N≈4500 with a useless interval). Overlap grows as the corpus accumulates, so
  this becomes derivable later. Until then the honest state is `UNDERIVABLE`,
  and the borrowed number must not be applied as if measured.
- **ε-machine acceptance is the destination, and the corpus is not there yet.**
  `modules/hnd.py::accept_by_epsilon_machine` is the criterion this scan should
  eventually use — keep a candidate only if conditioning on it drops *both*
  C_mu and h_mu, which tests whether it shortens the description rather than
  whether it correlates. It needs `MIN_SAMPLES_PER_HISTORY · bands^history`
  observations: 30 at the coarsest useful setting (2 bands, history 1), 240 at
  4 bands and history 2. At ~9 claims per topic per run that is roughly 4
  weekly runs for the first and ~27 for the second. The correlational criterion
  above is the small-sample stopgap, and it should be replaced, not extended,
  once the accumulated corpus can support the real test.
- **Retractions are appended, never deleted.** Landauer's principle, in the
  form `grounding/core/dormancy.py` already argues it: erasure is the
  irreversible operation, computation is not. Deleting a withdrawn suggestion
  would destroy the fact that the engine ever made it, which is exactly what a
  reader needs to judge the log — a record that silently loses its mistakes is
  indistinguishable from one that never made any. `retract()` appends a
  withdrawal and `standing_suggestions()` is what downstream consumers read, so
  both states stay recoverable. Same discipline as the reformulation counter.
- **Reformulation resets the evidence the residual scan reads.** `stage_modify`
  runs before `stage_hidden`, and `Claim.reformulate()` zeroes `passed`/`failed`
  by design — a restated claim does not inherit the old wording's track record.
  In the first live run that left 26 of 35 claims at `beta_confidence` exactly
  0.5, so two whole topics carried no residual information at all while the
  report's test counts (217/225) described activity that no longer stood in the
  tree. The report now states both numbers.
- **The unfalsifiability test is lexical.** A claim is routed to the unknown
  journal when its abstract contains no measurable anchor (number, percentage,
  inequality) or is hedged twice over.
- **"The staking-and-testing loop will catch it" was false, and the
  2026-09-07 run is the proof.** The design leaned on stage 4 to correct a
  bad claim from stage 3. Stage 4 could not, for two reasons measured on that
  run's 123-abstract corpus.

  First, *the oracle never read the claim*. `corroboration` counted
  agreement markers anywhere in the other abstract, so its verdict was a pure
  function of that abstract's prose: all 52 abstracts that spoke handed the
  **identical** verdict to every claim they were paired with, and each topic's
  claims converged on one score (0.80/0.80/0.80/0.78/0.78/0.78). The relevance
  gate did not help — `distill_claim` writes the topic name into the claim
  text, so overlap on topic words is guaranteed by construction, and the gate
  admitted **53.5% of pairs drawn from different topics**.

  The fix is that the claim now enters the decision twice. Shared tokens are
  the claim's own subject with topic vocabulary removed, weighted by
  information content (`idf_map`), and polarity is read only in the sentences
  of the other abstract that discuss that shared subject. `MIN_SUBJECT_BITS` is
  measured, not chosen: `calibrate_corroboration` returns the loosest gate
  holding 5% cross-topic testimony on the Wilson upper bound, and it overrode
  an eyeballed 12.0 in favour of 10.0 — the same correction `calibrate_scan`
  made to its own guess, for the same reason. `--calibrate-oracle` prints the
  curve. The null is cross-topic pairs, which is a **proxy** and named as one
  in the code: the collisions that actually corrupted the drafts were *inside*
  a single topic.

  | | before | after |
  |---|---|---|
  | cross-topic pairs admitted | 53.5% | 3.1% |
  | within-topic confidence spread (sd) | 0.032–0.087 | 0.039–0.124 |
  | verdict varies with the claim | never | yes |

  Second, and the deeper point: **stage 4 can only refute a claim that
  something argues against.** Three de novo protein-binder papers were
  retrieved into "hidden variable detection / causal discovery from residuals"
  by keyword match on *latent* (the product name Latent-X) and *discovery*
  (drug discovery). They are a mutually consistent cluster, so they corroborate
  each other honestly and climbed to that topic's top three claims. No amount
  of testing removes off-topic evidence, because more of it agrees. That is why
  `in_scope` sits at stake time rather than being left to the loop.
- **Belonging is a phrase test, not a keyword test.** Single words cannot make
  the call at any threshold: measured on the live corpus, the three leaked
  papers carry *more* topic vocabulary (9.15 bits) than genuinely on-topic work
  such as "Discovery of Causal Additive Models in the Presence of Unobserved
  Variables" (8.13 bits). Requiring an adjacent stemmed pair separates the
  technical phrase from the coincidence — "causal discovery" is a subject,
  "causal" plus "drug discovery" is a collision — and it exiles all three leaks
  while keeping every real causal-discovery paper in that topic. The phrase
  tokenizer is deliberately **separate** from `_tokens`, which stage 4 is
  calibrated against; widening one would silently move every number measured
  for the other.

  The cost is real, one-directional, and worth stating: a paper whose
  vocabulary never lands adjacent is refused, which on the live corpus wrongly
  exiles a few — notably "Hallucination, abstention, and computable
  inseparability", because the query "hallucination calibration abstention" is
  a keyword bag whose adjacent pairs are artifacts rather than phrases. Scope
  refusals are journalled under the flag `off-scope`, never dropped:
  under-inclusion leaves a record a reader can overturn, over-inclusion
  silently rewrites the drafts.
- **A number is not automatically a result.** `MEASURABLE.findall(...)[0]` took
  the first digit anywhere in the abstract, which produced live falsification
  conditions reading "fails to reproduce the stated 2013 result" (a citation
  year), "the stated 1951 result" (Shannon's experiment), "the stated 2.0
  result" (SQuAD 2.0) and "the stated 10 result" (the @10 of OOD@10). An
  identifier names a thing; only a measurement has a value a replication can
  miss. `result_anchor` declines years and name-bound numbers, prefers a
  percentage, and otherwise takes a number standing near a word that marks it
  as an outcome.
- **The digit rule is what gates out the theory literature, and that is a
  standing decision rather than a defect.** After scope filtering, 65 of 123
  live abstracts belong to their topic; only 15 of those carry a result number.
  The rest are theory and method papers — "Detecting hidden confounding in
  observational data using multiple environments", "Reconstruction of
  Epsilon-Machines in Predictive Frameworks and Decisional States", "Divergent
  Predictive States", "Leveraging Environmental Correlations: The
  Thermodynamics of Requisite Variety" — whose abstracts contain **no numbers
  at all**, so nothing is being mis-parsed. They make falsifiable claims that
  are not numeric ones, and `grounding.core.epistemics` accepts any non-trivial
  textual falsification condition; the numeric anchor is this engine's
  narrowing, not the framework's. Widening it is a real option and is left
  open deliberately: it would roughly quadruple what the tree can hold on
  theory-heavy topics, at the cost of falsification conditions no cross-source
  test can currently check.
