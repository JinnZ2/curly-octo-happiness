# EXP-RVC-05 — results (run 2026-11-27)

Design: `experiments/requisite-variety-and-cybernetic-regulation.md` § EXP-RVC-05 (issue #71). Gap: RVC_003.

## Provenance

- Repo commit at run time: `a3d5c55` (main).
- Environment: Python 3.14.8, numpy 2.5.5, scipy 1.18.1; Intel Xeon @ 2.90 GHz, 4 vCPU (shared with other jobs). Runtime 29.6 s.
- Data: Kenneth French Data Library (CRSP 202609 build), downloaded 2026-11-27. sha256 of the zips:
  - 5 factors (2x3): `17d7a575…`
  - Momentum: `27ed60e5…`
  - ST reversal: `7ddb68bb…`
  - LT reversal: `baad3163…`
  - FF3: `b03d39e4…`

  Full hashes: `raw/input_sha256.txt`.
- Live index figures are from López de Prado (2023), *Causal Factor Investing* (Cambridge Element), [PDF](https://resolve.cambridge.org/core/services/aop-cambridge-core/content/view/9AFE270D7099B787B8FD4F4CBADE0C6E/9781009397292AR.pdf/causal_factor_investing.pdf), and López de Prado, Lipton & Zoonekynd, "The Case for Causal Factor Investing" ([SSRN 4774522 copy](https://www.scribd.com/document/728736607/SSRN-id4774522); [JPM 2024 copy](https://www.scribd.com/document/859315589/Lopez-de-Prado-et-al-2024-CaseForCausalFactorInvesting)).
- Bootstrap: stationary block bootstrap, mean block 12 months, 5000 reps, seed 0, each period resampled separately.

## Deviations (recorded before results)

1. **No Jobson–Korkie–Memmel test.** JKM tests two Sharpe ratios measured over the same period. Pre- and post-publication samples cover disjoint periods, so I used an independent-samples z test on the SR difference with Newey–West HAC standard errors, plus a block-bootstrap CI. This limits nothing essential, but the test is not the named one.
2. **Live index returns are not public.** I could not obtain the index's return series (BGSUSEMF, identified from the sources above). So I used the SR and t-statistics the authors report and built iid CIs from them. Whether RVC_003's source paper ([doi:10.2139/ssrn.7216139](https://doi.org/10.2139/ssrn.7216139)) refers to this same index is **UNCHECKED**.
3. **Publication dates were entered from memory**, not checked against the papers (**UNCHECKED**). These are Banz 1981, Rosenberg-Reid-Lanstein 1985 (alt Fama-French 1992), Jegadeesh-Titman 1993, Novy-Marx 2013 (alt FF 2015), Titman-Wei-Xie 2004 (alt FF 2015), Jegadeesh / Lehmann 1990, and De Bondt-Thaler 1985. Alternative dates are reported where they plausibly matter.
4. The French library has more factors than the seven used here. The factor set is my choice.

## Results

Annualised Sharpe ratio before and after publication, with HAC standard errors. "Diff" is the post-minus-pre SR with a 95% block-bootstrap CI; z is the HAC z score; p is one-sided, for decay.

| factor | pub. date | SR pre | SR post | diff [boot 95% CI] | z | p |
|---|---|---|---|---|---|---|
| SMB | 1981-03 | 0.59 ± 0.30 | 0.04 ± 0.14 | −0.54 [−1.28, 0.11] | −1.65 | 0.049 |
| HML | 1985-04 | 0.69 ± 0.25 | 0.19 ± 0.19 | −0.51 [−1.11, 0.06] | −1.61 | 0.053 |
| HML (alt) | 1992-06 | 0.58 | 0.19 | −0.40 [−0.93, 0.15] | −1.29 | 0.098 |
| Mom | 1993-03 | 0.54 ± 0.11 | 0.29 ± 0.17 | −0.26 [−0.77, 0.18] | −1.26 | 0.104 |
| RMW | 2013-04 | 0.42 ± 0.17 | 0.22 ± 0.26 | −0.20 [−0.83, 0.45] | −0.64 | 0.261 |
| RMW (alt) | 2015-04 | 0.41 | 0.23 | −0.17 [−0.83, 0.55] | −0.51 | 0.304 |
| CMA | 2004-12 | 0.59 ± 0.18 | 0.04 ± 0.24 | −0.56 [−1.10, −0.03] | −1.85 | 0.032 |
| CMA (alt) | 2015-04 | 0.54 | −0.06 | −0.59 [−1.30, 0.06] | −1.64 | 0.051 |
| ST_Rev | 1990-07 | 0.92 | 0.13 | −0.79 [−1.19, −0.42] | −3.75 | <0.001 |
| LT_Rev | 1985-07 | 0.36 | 0.14 | −0.22 [−0.67, 0.20] | −0.88 | 0.189 |

The post-publication point estimate is lower for **7 of 7 factors**, under both primary and alternative dates. Taken one at a time, only ST_Rev and CMA (primary date) have bootstrap CIs that exclude 0. Ratio CIs are in `raw/results.json`.

**Live index.** These are the authors' reported figures. The CIs are iid, \(\mathrm{SE}\approx 1/\sqrt{\text{years}}\), which matches the SE implied by the reported t.

| source | window | SR | t | 95% CI |
|---|---|---|---|---|
| López de Prado 2023 (CUP) | 2007-05 → 2022-12 | 0.29 | 1.16 | [−0.22, 0.80] |
| LdP, Lipton, Zoonekynd (SSRN 4774522) | 2007-05 → 2023-12 | −0.08 | −0.33 | [−0.56, 0.40] |
| LdP, Lipton, Zoonekynd (JPM 2024) | 2007-05 → 2024-07 | 0.17 | 0.69 | [−0.31, 0.65] |

All three CIs include both 0 and 0.3.

**Source discrepancy (flagged, not resolved):** the windows nearly coincide, yet the reported SRs move from 0.29 to −0.08 to 0.17. The middle window adds about a year to the first. Getting from 0.29 to −0.08 would need a very large one-year loss, and then a recovery to 0.17 in seven months. The figures may use different index versions or definitions. I have not resolved this.

**Power at 17 years** (iid, two-sided α = 0.05):

- Significance threshold: SR ≈ 1.96/√17 ≈ 0.48, as the design said.
- 80%-power minimum detectable SR: 0.68.
- Power at SR = 0.3: 23%. At 0.17: 10%. At 0.5: 54%.
- About 87 years of data are needed for 80% power at SR = 0.3.

## Verdict vs pre-registered prediction

Prediction: "Decay present; live SR CI includes both 0 and 0.3."
Falsified if: "no decay for the majority of factors, or the live CI excludes 0.3."

**SUPPORTED**, with the caveats below.

- Decay is present in 7/7 point estimates. It is individually distinguishable from 0 for 2/7.
- All reported live CIs include 0 and 0.3.
- The live half of the result follows from the length of the sample alone: 17 years cannot separate 0 from 0.3. It would hold for nearly any reported SR between about −0.18 and 0.48.
- The H1 wording "consistent with a positive SR" is weak for the −0.08 figure. The CI still includes positive values.

## What this does and does not establish

- **Does:** with public French data and these dates, factor Sharpe ratios are lower after publication, consistent with McLean–Pontiff. The live index record the authors cite is too short to tell SR 0 from SR 0.3. 17 years gives about 23% power at SR 0.3.
- **Does not:**
  - Separate a publication effect from a time trend (for example, falling trading costs or crowding over time). Splitting at a single date confounds the two.
  - Validate the dates, which are UNCHECKED.
  - Test the live index on its own returns, which were not available.
  - Say anything about whether "causal factor discovery" would do better live, as the design itself states.
  - Confirm that the index is the one RVC_003 refers to (UNCHECKED).
