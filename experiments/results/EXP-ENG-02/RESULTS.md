# EXP-ENG-02 — Record integrity: results (run 2026-11-27)

**Verdict: SUPPORTED** (H1: at least one open gap changes class under the
bookkeeping factors; the pre-registered falsifier "fewer than 1 gap changes
class" did not occur). The quantitative prediction "≥ 5 gaps change class" was
met in one cell (full history × re-evaluated verdict, no dedupe: 7 of 38).
It was **not** met by any single factor (maximum 4), and it was not met with
all three factors on (4). Dedupe alone changes no gap's class; it merges gaps.

This is an exact recomputation of the engine's own bookkeeping. It says
nothing about whether any paper's claim is true, and nothing about whether
the oracle's verdicts match a human reading (that is EXP-ENG-01, not run:
it needs human labels).

## Provenance

| item | value |
|---|---|
| design | `experiments/engine-oracle.md` § EXP-ENG-02 (unchanged) |
| repo commit read | `a3d5c55328cc671c4384d0a02eccb70c7d828b89` (main; `data/`, `hypotheses/`, `scripts/` identical to `d469d9d`) |
| history replayed | 18 engine commits that touched `data/claim_tree.json`, `1462daa` (2026-08-17) … `d469d9d` (2026-11-23) |
| code | `run.py` (stdlib only; reads blobs with `git show`; imports historical copies of `scripts/hypothesis_engine.py` from a temp dir; writes only to this folder) |
| raw outputs | `raw/summary.txt`, `raw/cells.json` (per gap × 16 cells), `raw/pairs.json` (715 pairs on current claims), `raw/validation.json`, `raw/non_gap_claims_that_become_gaps.json` |
| environment | Python 3.14.8; Intel Xeon @ 2.90 GHz, 4 vCPU shared with other jobs; runtime 3.1 s |
| seeds | none needed (deterministic) |

## Deviations from the design (recorded before results)

1. **The "stored" arm is better than the design's approximation.** The design
   proposed approximating historical verdicts by truncating
   `findings_log.jsonl`. The git history holds every run's corpus, claim
   tree and engine code. So each pair's "stored" verdict is recomputed
   with the engine version, corpus IDF and claim text of the run in which
   the pair was first recorded. Six engine versions occur; older ones have no
   IDF gate, and `corroboration()` is called with the arguments each version
   accepted. The claim text at test time is the snapshot text with that run's
   "(scope narrowed …)" suffix removed when the claim was reformulated in
   that run (stage 4 runs before stage 5).
2. **Validity check of the replay.** For claim-runs without a reformulation,
   the replayed signs reproduce the engine's recorded Δpassed/Δfailed exactly
   in 726 of 727 cases (201 of 202 cases with at least one new pair). The
   baseline cell (no dedupe, post-reformulation history, stored verdict)
   reproduces the engine's current passed/failed counts for 38 of 38 open
   gaps. Its class matches the registry for 38 of 38. The one mismatch is
   claim `a4a6a3fc54bac055` (an RVC claim that is not an open gap) at run 3
   (`252aec4`): the replay gives +1 where the engine recorded none. It is
   unexplained, and it means one non-gap claim appears as a gap in the
   baseline cell of the secondary table below.
3. **History factor.** "Post" means pairs first recorded after the claim's
   last reformulation, which is what the engine counts. "Full" means all pairs
   in `tested_against`, which `reformulate()` keeps but no longer counts.
   Runs that did not commit are invisible to the replay.
4. **Dedupe keys.** The design asked for title, DOI and arXiv id. A paper
   without a DOI or arXiv id in its URL falls back to its normalised title
   under the DOI and arXiv keys. Dedupe does two things. It merges current
   claims that are the same paper into one record. It also counts each other
   paper once, by the sign of its net vote (ties abstain), and drops votes
   from the claim's own paper.

## Results

Class under the engine's own `classify_gap` rule (≥ 2 tests; contested if
both signs and Beta mean in [0.3, 0.7]; contradicted if failed > passed). The
registry has 33 contested and 5 contradicted among the 38 claim-backed open
gaps.

| dedupe | history | verdict | gaps whose class changes (of 38) | which |
|---|---|---|---|---|
| off | post | stored | 0 (baseline) | — |
| off | post | now | 1 | CSS_001 |
| off | full | stored | 4 | CFA_023, CFA_024, CFA_028, CFA_054 |
| off | full | now | **7** | CFA_023, CFA_028, CFA_040, CFA_041, CFA_054, CSS_001, RVC_006 |
| title | post | stored | 0 | — |
| title | post | now | 1 | CSS_001 |
| title | full | stored | 3 | CFA_023, CFA_024, CFA_028 |
| title | full | now | 4 | CFA_023, CFA_028, CSS_001, RVC_006 |
| doi | post / full | stored / now | 0 / 1 / 3 / 4 | same as title |
| arxiv | post / full | stored / now | 0 / 1 / 3 / 4 | same as title |

Marginal effects, each factor alone, from the baseline:

- **Verdict re-evaluation (now vs stored): 1 gap.** CSS_001 goes from 3
  corroborating / 1 contradicting to 0 / 0 under today's code and IDF. Every
  one of its four recorded pairs now abstains.
- **History (full vs post): 4 gaps.** Examples: CFA_023 goes from contested
  1/1 to contradicted 3/9. CFA_024 goes from contradicted 0/2 to contested
  14/16. The engine's gap list is computed after `reformulate()` resets the
  counts, so most of the record it holds (`tested_against`) does not enter
  the classification.
- **Dedupe: 0 class changes, but the number of distinct gaps falls.** Under
  the title key, CFA_040, CFA_041 and CFA_054 are one claim (38 → 36
  distinct gaps, together with RVC_001 merging with a non-gap claim of its
  own journal version). Under the DOI key only CFA_041 and CFA_054 merge.
  Under the arXiv key only CFA_040 and CFA_041 merge. So the key changes the
  answer, as the design anticipated.

Self-pairs: 10 recorded pairs are a paper tested against a copy of itself (same
normalised title). Eight have verdict −1: the CFA_040/041/054 cluster and one
non-gap claim. Two have verdict +1: CFA_048 and RVC_001 corroborated by
their own copies. The cluster's six self-contradiction pairs all predate the
claims' last reformulation. They already drop out of the engine's current
counts and reappear only under full history. Dedupe removes them in every
cell.

Secondary: claims that are not open gaps but classify as one in a cell. There
are 11–13 such claims under any full-history cell, and 1–2 under post-history
cells (the 1 is the unexplained replay mismatch above). Details are in
`raw/non_gap_claims_that_become_gaps.json`.

## Against the pre-registered predictions

| prediction | outcome |
|---|---|
| CFA_016/040/041/054 cluster collapses to one claim | **partly**. CFA_016 is no longer a claim-backed gap at this commit (escape-hatched), so the cluster among open gaps is CFA_040/041/054. It collapses to one claim under the title key, and to two claims under the DOI or arXiv key. |
| its self-contradiction pairs vanish | **yes** under any dedupe; they are already absent from the post-reformulation counts |
| ≥ 5 gaps change class | **met in 1 of 15 non-baseline cells** (7 gaps, history × verdict without dedupe); not met by any single factor or with all three on |
| falsifier: fewer than 1 gap changes class | **not triggered** (up to 7 change) |

## What this does and does not establish

- **Does establish (exact, on this repo's data):** the engine's gap list is
  not a stable function of its own evidence record. Which history is
  counted, which code and IDF score a pair, and how papers are identified
  each move gaps between contested, contradicted and not-a-gap. History moves
  the most here.
- **Does not establish:** that any gap is wrong or right about the
  literature. Whether the oracle's ±1 verdicts mean agreement or
  disagreement between papers is EXP-ENG-01's question, and that experiment
  needs human stance labels (not run). Which bookkeeping is "correct" is a
  design decision for the engine; this run does not modify the engine.
