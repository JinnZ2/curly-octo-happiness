# Experiments — requisite variety and cybernetic regulation (`RVC`)

Status: PROPOSED · Date: 2026-11-24 · Read against
`hypotheses/requisite-variety-and-cybernetic-regulation.md` and
`hypotheses/RESEARCH_GAPS.md` at commit
`d469d9db381eabdbf8be22095dc712e79592ded7` (engine run 2026-11-23).

Nothing here is a result. **Checked (abstract)** = the source exists and its
abstract/landing page says what is quoted, as fetched 2026-11-24. Everything
else is **UNCHECKED**.

## 1. What the engine claims, and on what evidence

**The draft.** Node confidence 0.47; 4 surviving / 5 active / 0 refuted; 6
open gaps (all EMPIRICAL `UNDER_STUDY`). The two theory papers squarely on
Ashby's law in the topic ("A Formal Definition of Scale-dependent Complexity
and the Multi-scale Law of Requisite Variety"; "Requisite Variety,
Autopoiesis, and Self-organization") were routed to the unknown journal as
unfalsifiable, because their abstracts state no measurable condition. What
remains is a mix of conceptual frameworks and applied ML papers that matched
the query "good regulator theorem causal world model" on "world model".

**Sources checked (abstract level).**

| gap | source | what its abstract/landing page says |
|---|---|---|
| RVC_001 | [The Good Algorithmic Regulator Theorem](https://doi.org/10.20944/preprints202609.1967.v1) (Ruffini; preprint) and its journal version, [Entropy 28(11):1182](https://doi.org/10.3390/e28111182) | a theorem (GART): the reduction in prefix Kolmogorov complexity of the regulated output relative to the uncontrolled one is bounded by the information initially shared by world and regulator, plus a counterfactual residual and logarithmic coding overhead. Mathematical, not empirical |
| RVC_002 | [What-If World](http://arxiv.org/abs/2605.27589v1) (Cai et al.) | causal benchmark for video world models; across nine models none exceeds 52% on the paired score; open-source models near 28%; per-intervention scores 14.2%–40.4% |
| RVC_004 | [Auditing World-Model Explanations in Retail Forecasting](https://doi.org/10.2139/ssrn.7627720) (Iyer) | on **generated** store data, the world model passed several explanation checks but overstated true lift by 1.33–1.40× (LightGBM 1.26×); response to a lasting price change 4.7–6.5× the true response. The landing page's subtitle reads "…Faithfulness, Accuracy and Price Response"; the engine records "…Causal Validity". Which version is current is UNCHECKED |
| RVC_005 | [Requisite Variety For AI Security](https://doi.org/10.2139/ssrn.6255362) (Muhlert) | conceptual governance framework; a worked scenario about a fictional company; no empirical study |
| RVC_006 | [A Capacity-Based Theory of Complexity Control in Megaprojects](https://doi.org/10.31235/osf.io/3hdn5_v1) (Huemmer) | conceptual: complexity becomes critical when structural variety exceeds regulatory variety in a "4M" architecture; states no associated data |

RVC_003 ("From Causal Factor Investing to Causal Factor Discovery") is
**UNCHECKED** beyond its extracted sentence, which says a flagship live
multifactor index earned a Sharpe ratio statistically indistinguishable from
zero over seventeen years.

**What the evidence is.** Of the 5 checked sources, 1 is a theorem, 2 are
conceptual frameworks without data, and 2 are applied ML benchmarks that are
not about requisite variety. RVC_001's "corroboration" includes its own
journal version (`same_title` in `oracle_audit.py`). The topic's draft, then,
does not contain an empirical test of Ashby's law or the good-regulator
theorem; it contains pointers to one theorem and to places where the law is
invoked.

## 2. What science needs to be known

### 2a. Gaps the engine recorded

6 ids, all Protocol R. The engine names no separating condition.

### 2b. Gaps I identify

1. **Three kinds of claim are mixed, and each needs a different check.**
   - *Mathematical validity:* Ashby's law in the regulation game and GART are
     theorems. They are checked by reading the proof, not by experiment. An
     experiment can only check a **proxy** of them or their **application**.
   - *Structural/numerical checks:* computing both sides of a bound in a toy
     model where they are computable. `experiments/sketches/variety_sim.py`
     does this for H(E) ≥ H(D) − I(D;R) ≥ H(D) − H(R) in a Latin-square game;
     the bound holds on every run, as it must. That is numerical agreement
     with a theorem, not empirical support for an application.
   - *Empirical application:* "a regulator (SOC, project organisation) with a
     smaller variety margin fails more often". This is the claim RVC_005 and
     RVC_006 make, and it is untested in both (neither reports data).
2. **"Variety" is not operationalised in the applied claims.** Repertoire
   size log|R|, response entropy H(R), and the mutual information I(D;R)
   between disturbance and response give different answers. The sketch's
   noisy regulator has full H(R) = 4 bits but leaves 1.7 bits of outcome
   entropy, because only I(D;R) ≈ 2.3 bits is usable. A framework that
   counts capabilities (RVC_005's tiers, RVC_006's 4M) is measuring
   something like log|R|, which the law does not bound outcomes by.
3. **Kolmogorov complexity is uncomputable.** Any empirical use of GART needs
   a computable proxy (compression length, or entropy rate for stationary
   ergodic sources). A "violation" observed with a proxy is evidence against
   the proxy before it is evidence against the theorem.
4. **Scope leaks.** RVC_002 (video world-model benchmark), RVC_003 (factor
   investing), RVC_004 (retail forecasting explanations) are about world
   models or causal validity, not regulation by requisite variety. They have
   testable claims of their own and are designed below on those terms.
5. **Statistical power of "indistinguishable from zero".** For RVC_003's
   seventeen-year Sharpe claim: under an i.i.d. normal approximation the
   t-statistic of an annualised Sharpe ratio SR over Y years is about
   SR·√Y, so at Y = 17 the smallest SR detectable at two-sided 5% is
   1.96/√17 ≈ 0.48, and a true SR of 0.3 would be detected with roughly 24%
   power. This is arithmetic, not data. It says "indistinguishable from zero"
   at 17 years is weak evidence that the premium is zero.

## 3. Experiments

### EXP-RVC-01 — GART with computable proxies: does the bound hold when both sides are estimated?

**Gap:** RVC_001.

- **Two parts, kept separate.** (a) *Proof audit* (desk): two readers check
  the proof's steps and state the assumptions (e.g. what "initial shared
  information" is, and whether the bound is in expectation or pointwise).
  This is the only check of mathematical validity. (b) *Proxy experiment*
  (below), which checks whether the bound survives operationalisation.
- **H1 (proxy holds):** in simulated plants with stationary disturbances,
  using entropy-rate estimates as the proxy for per-symbol Kolmogorov
  complexity, the measured simplification h(uncontrolled) − h(regulated) is
  ≤ the estimated I(world; regulator) + residual + overhead, within the
  estimators' 95% CIs, on ≥ 95% of runs.
- **H0 (proxy fails):** the measured simplification exceeds the bound with CI
  excluding it on > 5% of runs. Pre-registered interpretation: a proxy
  failure is first attributed to the estimator (EXP-CSS-02 shows how
  block-entropy estimates can be biased), and only then to the theorem's
  application.
- **Design.** Discrete-state plants (finite-state disturbance processes with
  known h; Latin-square and non-Latin outcome tables); regulators with b ∈
  {0, 1, 2, 4} bits of the world's parameter built in, observation noise ε ∈
  {0, 0.1, 0.3}. Compression proxies (LZMA, PPM) alongside entropy-rate
  estimates; T ∈ {10⁴, 10⁵}; 50 seeds.
- **Tier:** laptop CPU.
- **Establishes / does not.** Whether GART's bound is usable with standard
  proxies. Does not prove or disprove GART (that is part (a)), and does not
  test "successful regulation requires a world model" as an empirical claim
  about organisms or organisations.

### EXP-RVC-02 — Does a measured variety margin predict regulation failure?

**Gaps:** RVC_005, RVC_006 (both conceptual; this is their Protocol M step
plus a first test).

- **Phase 0, operationalise (pre-registered before data).** Disturbance
  variety = entropy of the disturbance-class distribution H(D) over a fixed
  taxonomy; regulatory variety measured three ways: log|R| (capability
  count), H(R), and I(D;R) estimated from (disturbance, response) logs.
  Failure = a disturbance not returned to the target set within a deadline.
- **H1:** failure rate decreases with the margin I(D;R) − H(D), and I(D;R)
  predicts failure better than log|R| (difference in held-out log-loss > 0).
- **H0:** no association, or log|R| predicts as well as I(D;R).
- **Phase 1, simulation (laptop).** Extend `variety_sim.py` with response
  delay, non-injective outcome tables, and a capacity limit (responses per
  unit time). Expected: the margin predicts failure in the injective case
  (by construction) and loses predictive power as delay grows. This checks
  the measurement pipeline; it is not evidence about real systems.
- **Phase 2, observational (field/desk).** For RVC_005, a security-operations
  dataset with alert classes and analyst/agent responses (public candidates
  are thin; a partner SOC's de-identified logs would be the realistic
  source). For RVC_006, a public project-performance database (e.g. World
  Bank Independent Evaluation Group project ratings; suitability UNCHECKED),
  coding structural variety (components, interfaces, stakeholder classes)
  and regulatory capacity a priori from appraisal documents, blind to
  outcomes, two coders with κ reported.
- **Prediction.** H1 holds in simulation; in field data the sign holds but
  the effect is small after controlling for project size and sector.
  **Falsified if** the margin's coefficient CI includes 0 with power ≥ 0.8 for
  a pre-specified effect (odds ratio 1.5 per bit), or log|R| predicts as
  well as I(D;R).
- **Threats.** Reverse causation (troubled projects add capacity late; code
  capacity at appraisal only); outcome measurement in ratings data is itself
  a judgement.
- **Tier:** laptop (phase 1); field (phase 2).
- **Does not establish** that Ashby's law is true or false (it is a theorem
  in its own setting); establishes whether a particular operationalisation
  of it is predictive in a particular domain.

### EXP-RVC-03 — Retail world-model lift overstatement: replicate, then find the condition

**Gap:** RVC_004.

- **H1 (replication):** on the source's generator (code UNCHECKED), the world
  model's estimated promotional lift is 1.23–1.42× the true lift, as reported.
- **H2 (separating condition):** the overstatement is driven by promotion
  timing being correlated with latent demand (promotions scheduled on
  high-demand weeks), so it falls to ≈ 1.0× when promotions are randomised
  in the generator.
- **H0 for H2:** overstatement unchanged under randomised promotion timing.
- **Design.** (a) Source generator, stated conditions. (b) Same generator
  with promotion assignment independent of latent demand. (c) Semi-synthetic
  M5 (public) with injected promotions of known lift under both assignment
  rules. Models: the source's world model if available, LightGBM, and a
  regression with promotion randomisation as an instrument (oracle
  reference). 20 seeds.
- **Prediction.** H1 replicates; H2 holds. **Falsified if** (a) lift ratio CI
  excludes the reported range, or (b) randomisation leaves the ratio > 1.15.
- **Tier:** laptop CPU.
- **Establishes / does not.** Whether the explanation-audit result reflects
  a confounded promotion schedule (a hidden variable in the HVD sense).
  Does not bear on requisite variety.

### EXP-RVC-04 — What-If World: score reliability and seed variance

**Gap:** RVC_002.

- **H1:** the benchmark's paired score for a given model has seed-to-seed SD
  < 3 points and judge–human agreement κ ≥ 0.7, so the reported spread
  across models (28%–52%) reflects model differences.
- **H0:** SD ≥ 5 points or κ < 0.5 for at least one of two re-scored models.
- **Design.** Two open video models, 5 generation seeds each, the
  benchmark's evaluator plus 2 human raters on 200 paired items.
- **Tier:** single GPU to cluster (video generation).
- **Does not establish** whether video models "understand" causation.

### EXP-RVC-05 — Backtest-to-live decay of factor Sharpe ratios, with power stated

**Gap:** RVC_003.

- **H1:** post-publication (or post-index-launch) Sharpe ratios of published
  equity factors are lower than in-sample ones (McLean–Pontiff-style decay),
  and the live multifactor result cited in RVC_003 is consistent with a
  positive SR that 17 years cannot distinguish from zero.
- **H0:** no decay; and the live SR's CI excludes SR ≥ 0.3.
- **Design.** Kenneth French data library factor returns (public); split each
  factor at its publication date; HAC (Newey–West) or Lo (2002) standard
  errors for SR; a Jobson–Korkie–Memmel test for in-sample vs post-sample
  SR difference. Identify the "flagship live multifactor index" from the
  paper (UNCHECKED) and use its published returns if they are public.
- **Prediction.** Decay present; live SR CI includes both 0 and 0.3.
  **Falsified if** no decay for the majority of factors, or the live CI
  excludes 0.3.
- **Tier:** laptop CPU.
- **Does not establish** whether a "causal factor discovery" method (the
  paper's proposal) would do better live.

## 4. Gap → experiment map (all 6 RVC ids)

| gap | experiment / reason |
|---|---|
| RVC_001 | EXP-RVC-01 (proof audit + proxy experiment); the theorem itself is not empirically testable |
| RVC_002 | EXP-RVC-04 (scope leak: world-model benchmark, not requisite variety) |
| RVC_003 | EXP-RVC-05 (scope leak: factor investing; source UNCHECKED) |
| RVC_004 | EXP-RVC-03 (scope leak: forecasting explanations) |
| RVC_005 | EXP-RVC-02 (needs a definition first: Phase 0 operationalisation is part of the experiment) |
| RVC_006 | EXP-RVC-02 (needs a definition first, as RVC_005) |

All 6 also depend on EXP-ENG-01/02 for whether their recorded split means
anything.
