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
  inequality) or is hedged twice over. A confidently-worded abstract with a
  meaningless number still gets staked — the staking-and-testing loop, not the
  parser, is what is supposed to catch that.
