# RESEARCH_GAPS.md

**This is an automated triage of a literature sample, not a set of findings.** Each claim is the first sentence of an abstract — often background rather than the paper's result, so read the source before running anything. “Corroborating” and “contradicting” mean another abstract's sentences on a shared subject lean for or against it — cross-reading, not replication. Every entry is a starting point someone with a lab, data, or a desk can pick up.

_Regenerated 2026-10-26 by `scripts/hypothesis_engine.py` (stage 8). Format: `RESEARCH_RENDER.md` §3. Ids are permanent: a gap that drops out keeps its id and moves to **Retired ids**; ids are never renumbered._

**Classes:** EMPIRICAL — a measurement nobody has made · METHODOLOGICAL — a procedure nobody has defined.  
**Knowledge states:** `UNDER_STUDY` sources disagree, value provisional · `UNDEFINED` no agreed falsifier · `UNMEASURED` no value.

**To pick one up:** choose a gap, open its source, run the protocol it names, and report the result against the gap id (an issue titled with the id is enough).

## Contents

- [calibration and falsifiability of LLM agents](#calibration-and-falsifiability-of-llm-agents) · `CFA` · 31 open gaps · 9 untested markers
- [hidden variable detection / causal discovery from residuals](#hidden-variable-detection-causal-discovery-from-residuals) · `HVD` · 8 open gaps · 2 untested markers
- [causal states and statistical complexity](#causal-states-and-statistical-complexity) · `CSS` · 1 open gap · 0 untested markers
- [requisite variety and cybernetic regulation](#requisite-variety-and-cybernetic-regulation) · `RVC` · 5 open gaps · 1 untested markers
- [Protocols](#protocols) · [Retired ids](#retired-ids)

## Protocols

Each gap names one. The steps are shared; what differs per gap is the claim, its sources and its record.

<a id="protocol-r"></a>

### Protocol R — Replication split (EMPIRICAL, `UNDER_STUDY`)

**Method:**
1. Read the source and every cross-read source in full, not the abstract.
2. Tabulate per source: data, scale, metric, setting, assumptions.
3. Find the condition that differs between corroborating and contradicting sources.
4. Replicate the source once under its own stated conditions.
5. Replicate again varying only the separating condition.

**Your own data:** rerun the stated method, data or benchmark under the source's own conditions  
**Someone's hands:** the authors of the source and of the cross-read sources  
**Expected deliverable:** A condition table across sources plus one replication under the stated conditions.  
**Falsifier:** The replication under stated conditions fails to reproduce the reported result (claim refuted as stated); or it reproduces and varying the separating condition changes nothing (the split came from the reading, not the world).  
**What it opens:** A separating condition is a hidden-variable candidate for the topic — stake it as a claim. A claim that holds becomes an anchor other claims can be tested against.

<a id="protocol-m"></a>

### Protocol M — Operationalise (METHODOLOGICAL, `UNDEFINED`)

**Method:**
1. List every operational term in the claim.
2. For each, find whether the field has an agreed measurement protocol.
3. Write the claim's falsifier in measured terms.
4. Test the rewritten claim once against existing data.

**Your own data:** operational definitions for each term the claim relies on  
**Someone's hands:** the source's authors; practitioners who measure its key terms  
**Expected deliverable:** An operational definition and a falsifiable restatement — or a documented finding that none exists yet.  
**Falsifier:** A measurable falsifier is written and existing data can evaluate it (gap closes). If no term can be operationalised, the claim stays a marker and that is the recorded result.  
**What it opens:** A falsifiable restatement re-enters the claim tree and is tested like any other claim.

<a id="protocol-h"></a>

### Protocol H — Driver check (EMPIRICAL, `UNMEASURED`)

**Method:**
1. Place the topic's claims and the candidate on one shared time grid.
2. Control for elapsed time.
3. Test on a held-out later window.
4. Look for a mechanism in the literature.

**Your own data:** the candidate series and the claims on one time grid  
**Someone's hands:** researchers who track the candidate quantity  
**Expected deliverable:** A held-out test with time controlled, and a mechanism search.  
**Falsifier:** The association vanishes on the held-out window or after controlling for time.  
**What it opens:** A surviving driver becomes a scoped claim; a vanished one is retracted — logged, never deleted.

<a id="calibration-and-falsifiability-of-llm-agents"></a>

## calibration and falsifiability of LLM agents (`CFA`)

### CFA_019 · EMPIRICAL · `UNDER_STUDY` — TapGuard: Temperature-Calibrated Execute–Confirm–Block Routing for LLM-Powered Mobile Agents

**Gap:** the sample splits on this claim — 4 corroborating / 2 contradicting readings, beta 0.62.

**Question:** does the result in “TapGuard: Temperature-Calibrated Execute–Confirm–Block Routing for LLM-Powered Mobile Agents” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Large language model-powered mobile agents can compose messages, manage files, operate financial applications, and act on content from other applications.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [TapGuard: Temperature-Calibrated Execute–Confirm–Block Routing for LLM-Powered Mobile Agents](https://www.semanticscholar.org/paper/455aff2b876a266a14e412f4d4ff3071da1bb7d3)
- cross-read: [Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare](http://arxiv.org/abs/2603.17419v1)
- cross-read: [Hallucination as output-boundary misclassification: a composite abstention architecture for language models](http://arxiv.org/abs/2604.06195v1)
- cross-read: [Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval](https://doi.org/10.69987/aimlr.2025.60401)
- cross-read: [Demystifying Multi-Agent Debate: The Role of Confidence and Diversity](https://www.semanticscholar.org/paper/73d2d6732aa4f9e6f7589ce17d07b77201eb340a)
- cross-read: [Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval](https://www.semanticscholar.org/paper/5fc6a54544f6b704a9fdcfabfae4ec5d2220c7f7)
- cross-read: [Mitigating Multimodal Hallucination via Phase-wise Self-reward](http://arxiv.org/abs/2604.17982v1)

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_020 · EMPIRICAL · `UNDER_STUDY` — From Calibrated Confidence to Calibrated Reliance: Human-Aware Confidence Communication for AI-Assisted Decisi

**Gap:** the sample splits on this claim — 3 corroborating / 2 contradicting readings, beta 0.57, reformulated 2×.

**Question:** does the result in “From Calibrated Confidence to Calibrated Reliance: Human-Aware Confidence Communication for AI-Assisted Decision Making” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** As AI systems increasingly support consequential human decisions, the confidence they display shapes whether users accept or override their recommendations.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [From Calibrated Confidence to Calibrated Reliance: Human-Aware Confidence Communication for AI-Assisted Decision Making](https://doi.org/10.1145/3843742)
- cross-read: [Learning From Failure: Integrating Negative Examples when Fine-tuning Large Language Models as Agents](http://arxiv.org/abs/2402.11651v2)
- cross-read: [Agents: An Open-source Framework for Autonomous Language Agents](http://arxiv.org/abs/2309.07870v3)
- cross-read: [Calibrating the Confidence of Large Language Models by Eliciting Fidelity](http://arxiv.org/abs/2404.02655v2)
- cross-read: [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1)
- cross-read: [Retrospex: Language Agent Meets Offline Reinforcement Learning Critic](http://arxiv.org/abs/2505.11807v2)
- cross-read: [Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets](https://doi.org/10.31224/7689)
- … 28 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_021 · EMPIRICAL · `UNDER_STUDY` — Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets

**Gap:** the sample splits on this claim — 3 corroborating / 2 contradicting readings, beta 0.57, reformulated 2×.

**Question:** does the result in “Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** A 3D Gaussian-splatting asset ships millions of primitives, each carrying a per-primitive confidence — a view count, an opacity — that downstream pruning, streaming, and level-of-detail decisions consume as if it meant something.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets](https://doi.org/10.31224/7689)
- cross-read: [Learning From Failure: Integrating Negative Examples when Fine-tuning Large Language Models as Agents](http://arxiv.org/abs/2402.11651v2)
- cross-read: [Agents: An Open-source Framework for Autonomous Language Agents](http://arxiv.org/abs/2309.07870v3)
- cross-read: [Calibrating the Confidence of Large Language Models by Eliciting Fidelity](http://arxiv.org/abs/2404.02655v2)
- cross-read: [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1)
- cross-read: [Retrospex: Language Agent Meets Offline Reinforcement Learning Critic](http://arxiv.org/abs/2505.11807v2)
- cross-read: [Establishing Shared Query Understanding in an Open Multi-Agent System](http://arxiv.org/abs/2305.09349v1)
- … 19 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_005 · EMPIRICAL · `UNDER_STUDY` — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

**Gap:** the sample splits on this claim — 2 corroborating / 2 contradicting readings, beta 0.50, reformulated 2×.

**Question:** does the result in “MameLoshnLM: Yiddish Language Model and Evaluation Benchmark” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** We present MameLoshnLM, the first open-source 8B-parameter language model built specifically for Yiddish.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [MameLoshnLM: Yiddish Language Model and Evaluation Benchmark](http://arxiv.org/abs/2608.05850v1)
- cross-read: [Learning From Failure: Integrating Negative Examples when Fine-tuning Large Language Models as Agents](http://arxiv.org/abs/2402.11651v2)
- cross-read: [How do language models learn facts? Dynamics, curricula and hallucinations](http://arxiv.org/abs/2503.21676v2)
- cross-read: [Agents: An Open-source Framework for Autonomous Language Agents](http://arxiv.org/abs/2309.07870v3)
- cross-read: [Calibrating the Confidence of Large Language Models by Eliciting Fidelity](http://arxiv.org/abs/2404.02655v2)
- cross-read: [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1)
- cross-read: [Retrospex: Language Agent Meets Offline Reinforcement Learning Critic](http://arxiv.org/abs/2505.11807v2)
- … 25 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_022 · EMPIRICAL · `UNDER_STUDY` — APEX-EM: Non-Parametric Online Learning for Autonomous Agents via Structured Procedural-Episodic Experience Re

**Gap:** the sample splits on this claim — 1 corroborating / 2 contradicting readings, beta 0.40, reformulated 2×.

**Question:** does the result in “APEX-EM: Non-Parametric Online Learning for Autonomous Agents via Structured Procedural-Episodic Experience Replay” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** LLM agents rerun full reasoning for every task, even one they solved moments earlier.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [APEX-EM: Non-Parametric Online Learning for Autonomous Agents via Structured Procedural-Episodic Experience Replay](https://www.semanticscholar.org/paper/16c110756c0f0395fe9cc9568434d9e5621cd464)
- cross-read: [Retrospex: Language Agent Meets Offline Reinforcement Learning Critic](http://arxiv.org/abs/2505.11807v2)
- cross-read: [Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets](https://doi.org/10.31224/7689)
- cross-read: [Semantic Validation Gates: A Computable, Statistically Calibrated Framework for Runtime Verification of Language-Model Outputs](https://doi.org/10.2139/ssrn.7157718)
- cross-read: [Agents of Context: A Methodological Critique and Counter-Evidence Analysis of Adversarial Red-Teaming Claims for Autonomous AI Agents](https://doi.org/10.65737/airjir2026369)
- cross-read: [Adversary-Controlled Abstention Adversary-Controlled Abstention: How Unevaluable Outcomes Inflate Reported Detection Rates](https://doi.org/10.2139/ssrn.7338498)
- cross-read: [A measurement substrate for agentic Kubernetes operations: Methodology and a case study in retrieval-compounding falsification](https://www.semanticscholar.org/paper/08649f99062f1d9624ec0c9017c4666b6ab3e5ad)
- … 10 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_023 · EMPIRICAL · `UNDER_STUDY` — A measurement substrate for agentic Kubernetes operations: Methodology and a case study in retrieval-compoundi

**Gap:** the sample splits on this claim — 1 corroborating / 1 contradicting readings, beta 0.50, reformulated 2×.

**Question:** does the result in “A measurement substrate for agentic Kubernetes operations: Methodology and a case study in retrieval-compounding falsification” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Empirical claims about autonomous Kubernetes operations agents are largely unfalsifiable.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [A measurement substrate for agentic Kubernetes operations: Methodology and a case study in retrieval-compounding falsification](https://www.semanticscholar.org/paper/08649f99062f1d9624ec0c9017c4666b6ab3e5ad)
- cross-read: [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1)
- cross-read: [Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets](https://doi.org/10.31224/7689)
- cross-read: [Semantic Validation Gates: A Computable, Statistically Calibrated Framework for Runtime Verification of Language-Model Outputs](https://doi.org/10.2139/ssrn.7157718)
- cross-read: [Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare](http://arxiv.org/abs/2603.17419v1)
- cross-read: [I-CALM: Incentivizing Confidence-Aware Abstention for LLM Hallucination Mitigation](http://arxiv.org/abs/2604.03904v1)
- cross-read: [Auditability Before Ontology: Operational Gates for Subjecthood Claims A Falsifiable Framework for Stakebearing Identity and Governance](https://doi.org/10.2139/ssrn.6181600)
- … 6 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_024 · EMPIRICAL · `UNDER_STUDY` — Large Language Model Evaluation Via Multi AI Agents: Preliminary results

**Gap:** the sample mostly contradicts this claim — 0 corroborating / 2 contradicting readings, beta 0.25, reformulated 2×.

**Question:** does the result in “Large Language Model Evaluation Via Multi AI Agents: Preliminary results” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** As Large Language Models (LLMs) have become integral to both research and daily operations, rigorous evaluation is crucial.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Large Language Model Evaluation Via Multi AI Agents: Preliminary results](http://arxiv.org/abs/2404.01023v1)
- cross-read: [Learning From Failure: Integrating Negative Examples when Fine-tuning Large Language Models as Agents](http://arxiv.org/abs/2402.11651v2)
- cross-read: [How do language models learn facts? Dynamics, curricula and hallucinations](http://arxiv.org/abs/2503.21676v2)
- cross-read: [Agents: An Open-source Framework for Autonomous Language Agents](http://arxiv.org/abs/2309.07870v3)
- cross-read: [Calibrating the Confidence of Large Language Models by Eliciting Fidelity](http://arxiv.org/abs/2404.02655v2)
- cross-read: [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1)
- cross-read: [Retrospex: Language Agent Meets Offline Reinforcement Learning Critic](http://arxiv.org/abs/2505.11807v2)
- … 24 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_025 · EMPIRICAL · `UNDER_STUDY` — From Sampling to Cognition: Modeling Internal Cognitive Confidence in Language Models for Robust Uncertainty C

**Gap:** the sample mostly contradicts this claim — 0 corroborating / 2 contradicting readings, beta 0.25, reformulated 2×.

**Question:** does the result in “From Sampling to Cognition: Modeling Internal Cognitive Confidence in Language Models for Robust Uncertainty Calibration” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Large Language Models (LLMs) have demonstrated remarkable performance across a wide range of tasks, yet they generally lack self-awareness, often displaying overconfidence when confronted with questions beyond their knowledge boundaries.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [From Sampling to Cognition: Modeling Internal Cognitive Confidence in Language Models for Robust Uncertainty Calibration](https://www.semanticscholar.org/paper/65ce1fc3a07d73774872ac573cc567435474a2d8)
- cross-read: [Calibrating the Confidence of Large Language Models by Eliciting Fidelity](http://arxiv.org/abs/2404.02655v2)
- cross-read: [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1)
- cross-read: [Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets](https://doi.org/10.31224/7689)
- cross-read: [Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare](http://arxiv.org/abs/2603.17419v1)
- cross-read: [Mitigating Multimodal Hallucination via Phase-wise Self-reward](http://arxiv.org/abs/2604.17982v1)
- cross-read: [An Explainable Agentic AI Framework for Uncertainty-Aware and Abstention-Enabled Acute Ischemic Stroke Imaging Decisions](http://arxiv.org/abs/2601.01008v1)
- … 21 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_026 · EMPIRICAL · `UNDER_STUDY` — The Calibration Gap: Model-Specific Confidence Thresholds for Reliable Customer Service LLMs

**Gap:** the sample mostly contradicts this claim — 0 corroborating / 2 contradicting readings, beta 0.25, reformulated 2×.

**Question:** does the result in “The Calibration Gap: Model-Specific Confidence Thresholds for Reliable Customer Service LLMs” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Every automated reply in customer service is a bet on a model's self-belief.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [The Calibration Gap: Model-Specific Confidence Thresholds for Reliable Customer Service LLMs](https://www.semanticscholar.org/paper/234b078f2646d8e90d5823b0c5aefb0c22d9c125)
- cross-read: [Calibrated Per-Carrier Confidence and Certified Pruning for Gaussian-Splat Assets](https://doi.org/10.31224/7689)
- cross-read: [Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare](http://arxiv.org/abs/2603.17419v1)
- cross-read: [Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval](https://doi.org/10.69987/aimlr.2025.60401)
- cross-read: [From Calibrated Confidence to Calibrated Reliance: Human-Aware Confidence Communication for AI-Assisted Decision Making](https://doi.org/10.1145/3843742)
- cross-read: [EviGraph: Evidence-Guided Autonomous Research Agents](https://www.semanticscholar.org/paper/84171611669441638d18bf3266065b796ed5cd5d)
- cross-read: [Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval](https://www.semanticscholar.org/paper/5fc6a54544f6b704a9fdcfabfae4ec5d2220c7f7)
- … 10 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_027 · EMPIRICAL · `UNDER_STUDY` — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

**Gap:** the sample mostly contradicts this claim — 0 corroborating / 2 contradicting readings, beta 0.25, reformulated 1×.

**Question:** does the result in “MameLoshnLM: Yiddish Language Model and Evaluation Benchmark” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** We present MameLoshnLM, the first open-source 8B-parameter language model built specifically for Yiddish.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [MameLoshnLM: Yiddish Language Model and Evaluation Benchmark](http://arxiv.org/abs/2608.05850v2)
- cross-read: [Agentic Confidence Calibration](http://arxiv.org/abs/2601.15778v1)
- cross-read: [Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare](http://arxiv.org/abs/2603.17419v1)
- cross-read: [Multi-agent Reinforcement Learning for Cooperative Lane Changing of Connected and Autonomous Vehicles in Mixed Traffic](http://arxiv.org/abs/2111.06318v2)
- cross-read: [Agents of Context: A Methodological Critique and Counter-Evidence Analysis of Adversarial Red-Teaming Claims for Autonomous AI Agents](https://doi.org/10.65737/airjir2026369)
- cross-read: [Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval](https://doi.org/10.69987/aimlr.2025.60401)
- cross-read: [MameLoshnLM: Yiddish Language Model and Evaluation Benchmark](http://arxiv.org/abs/2608.05850v1)
- … 7 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_028 · EMPIRICAL · `UNDER_STUDY` — Agent-ToM: Learning to Monitor Autonomous LLM Agents via Theory-of-Mind Reasoning

**Gap:** the sample mostly contradicts this claim — 0 corroborating / 2 contradicting readings, beta 0.25, reformulated 1×.

**Question:** does the result in “Agent-ToM: Learning to Monitor Autonomous LLM Agents via Theory-of-Mind Reasoning” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Monitoring autonomous large language model (LLM) agents for covert malicious behavior is challenging due to delayed, context-dependent, and long-horizon attack patterns.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Agent-ToM: Learning to Monitor Autonomous LLM Agents via Theory-of-Mind Reasoning](https://www.semanticscholar.org/paper/42d39b83a9f9f4ee96c62134afffe83cc28699e1)
- cross-read: [Retrospex: Language Agent Meets Offline Reinforcement Learning Critic](http://arxiv.org/abs/2505.11807v2)
- cross-read: [Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare](http://arxiv.org/abs/2603.17419v1)
- cross-read: [A Survey of Multi-Agent Deep Reinforcement Learning with Communication](http://arxiv.org/abs/2203.08975v2)
- cross-read: [Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval](https://doi.org/10.69987/aimlr.2025.60401)
- cross-read: [Do LLM Recommenders Know When They're Hallucinating? Auditing Confidence Calibration in Catalog Faithfulness](http://arxiv.org/abs/2608.10008v3)
- cross-read: [A measurement substrate for agentic Kubernetes operations: Methodology and a case study in retrieval-compounding falsification](https://www.semanticscholar.org/paper/08649f99062f1d9624ec0c9017c4666b6ab3e5ad)
- … 8 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### CFA_006 · METHODOLOGICAL · `UNDEFINED` — I-CALM: Incentivizing Confidence-Aware Abstention for LLM Hallucination Mitigation

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Large language models (LLMs) frequently produce confident but incorrect answers, partly because common binary scoring conventions reward answering over honestly expressing uncertainty.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [I-CALM: Incentivizing Confidence-Aware Abstention for LLM Hallucination Mitigation](http://arxiv.org/abs/2604.03904v1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_007 · METHODOLOGICAL · `UNDEFINED` — Deception and Communication in Autonomous Multi-Agent Systems: An Experimental Study with Among Us

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** As large language models are deployed as autonomous agents, their capacity for strategic deception raises core questions for coordination, reliability, and safety in multi-goal, multi-agent systems.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Deception and Communication in Autonomous Multi-Agent Systems: An Experimental Study with Among Us](http://arxiv.org/abs/2603.26635v1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_029 · METHODOLOGICAL · `UNDEFINED` — DiscoUQ: Structured Disagreement Analysis for Uncertainty Quantification in LLM Agent Ensembles

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Multi-agent LLM systems, where multiple prompted instances of a language model independently answer questions, are increasingly used for complex reasoning tasks.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [DiscoUQ: Structured Disagreement Analysis for Uncertainty Quantification in LLM Agent Ensembles](https://www.semanticscholar.org/paper/21e2855510b09e9f548010b7dfba81dd579e87d4)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_008 · METHODOLOGICAL · `UNDEFINED` — Agents of Context: A Methodological Critique and Counter-Evidence Analysis of Adversarial Red-Teaming Claims f

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** The recent paper Agents of Chaos (Shapira et al., 2026) reports an exploratory red-teaming study of six autonomous language-model-powered agents, documenting eleven vulnerability case studies including unauthorized compliance, sensitive data disclosure, identity spoofing, and multi-agent vulnerability propagation.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Agents of Context: A Methodological Critique and Counter-Evidence Analysis of Adversarial Red-Teaming Claims for Autonomous AI Agents](https://doi.org/10.65737/airjir2026369)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_009 · METHODOLOGICAL · `UNDEFINED` — Explicit Abstention Knobs for Predictable Reliability in Video Question Answering

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** High-stakes deployment of vision-language models (VLMs) requires selective prediction, where systems abstain when uncertain rather than risk costly errors.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Explicit Abstention Knobs for Predictable Reliability in Video Question Answering](http://arxiv.org/abs/2601.00138v2)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_030 · METHODOLOGICAL · `UNDEFINED` — Calibrating the Confidence of Large Language Models by Eliciting Fidelity

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Large language models optimized with techniques like RLHF have achieved good alignment in being helpful and harmless.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Calibrating the Confidence of Large Language Models by Eliciting Fidelity](http://arxiv.org/abs/2404.02655v2)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_031 · METHODOLOGICAL · `UNDEFINED` — SAVOR: Self-Aware Visual Grounding via Confidence-Calibrated Reinforcement Learning for Multimodal Hallucinati

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Multimodal large language models (MLLMs) have made strong progress on visual question answering and image captioning, yet they still produce fluent claims about objects, attributes, or relations that are not grounded in the image.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [SAVOR: Self-Aware Visual Grounding via Confidence-Calibrated Reinforcement Learning for Multimodal Hallucination Mitigation](https://www.semanticscholar.org/paper/304c3fc9ade77a8b94d4ef788f563648fa2577a1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_032 · METHODOLOGICAL · `UNDEFINED` — S-AI-ANTI HALLUCINATION: A BIO-INSPIRED AND CONFIDENCE-AWARE SPARSE AI FRAMEWORK FOR RELIABLE GENERATIVE SYSTE

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Large Language Models (LLMs) exhibit impressive generative capabilities but remain prone to hallucinations — plausible yet false statements produced with high confidence.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [S-AI-ANTI HALLUCINATION: A BIO-INSPIRED AND CONFIDENCE-AWARE SPARSE AI FRAMEWORK FOR RELIABLE GENERATIVE SYSTEMS](https://www.semanticscholar.org/paper/5f6f3a7c94113257fe8e6b0736e2918621dbf403)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_010 · METHODOLOGICAL · `UNDEFINED` — Mitigating Multimodal Hallucination via Phase-wise Self-reward

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Large Vision-Language Models (LVLMs) still struggle with vision hallucination, where generated responses are inconsistent with the visual input.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Mitigating Multimodal Hallucination via Phase-wise Self-reward](http://arxiv.org/abs/2604.17982v1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_033 · METHODOLOGICAL · `UNDEFINED` — Condence, Calibration, and Abstention in Small Open-Weight Language Models on Psychiatric Knowledge Questions:

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Abstract Small, locally deployable language models are increasingly proposed for psychiatric clinical decision support on privacy and compute grounds; two contemporaneous 2026 systems (ClinMPO; PKFAR) report accuracy or reasoning-quality gains from augmenting such models, and a 120-study taxonomy of LLMs in mental heal

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Condence, Calibration, and Abstention in Small Open-Weight Language Models on Psychiatric Knowledge Questions: A Cross-Domain Replication](https://doi.org/10.21203/rs.3.rs-11012222/v1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_011 · METHODOLOGICAL · `UNDEFINED` — Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Autonomous AI agents powered by large language models are being deployed in production with capabilities including shell execution, file system access, database queries, and multi-party communication.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare](http://arxiv.org/abs/2603.17419v1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_012 · METHODOLOGICAL · `UNDEFINED` — Semantic Validation Gates: A Computable, Statistically Calibrated Framework for Runtime Verification of Langua

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** As language models and autonomous agents produce long reasoning chains and consequential decisions, deployment requires a verification layer that converts qualitative judgments-wellformed, factual, consistent, safe, on-task-into calibrated, auditable measurements.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Semantic Validation Gates: A Computable, Statistically Calibrated Framework for Runtime Verification of Language-Model Outputs](https://doi.org/10.2139/ssrn.7157718)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_013 · METHODOLOGICAL · `UNDEFINED` — Hallucination as output-boundary misclassification: a composite abstention architecture for language models

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Large language models often produce unsupported claims.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Hallucination as output-boundary misclassification: a composite abstention architecture for language models](http://arxiv.org/abs/2604.06195v1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_034 · METHODOLOGICAL · `UNDEFINED` — FinPersona-Bench: A Benchmark for Longitudinal Psychometric Stability of Autonomous Financial Agents

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Large Language Models (LLMs) are increasingly deployed as autonomous financial agents initialized with explicit behavioral mandates such as"preserve capital"or"avoid speculative bets"that are meant to govern every decision throughout deployment.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [FinPersona-Bench: A Benchmark for Longitudinal Psychometric Stability of Autonomous Financial Agents](https://www.semanticscholar.org/paper/317d2659a28f8444d297f5020315bcdfc2509ab1)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_014 · METHODOLOGICAL · `UNDEFINED` — Demystifying Multi-Agent Debate: The Role of Confidence and Diversity

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Multi-agent debate (MAD) is widely used to improve large language model (LLM) performance through test-time scaling, yet recent work shows that vanilla MAD often underperforms simple majority vote despite higher computational cost.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Demystifying Multi-Agent Debate: The Role of Confidence and Diversity](https://www.semanticscholar.org/paper/73d2d6732aa4f9e6f7589ce17d07b77201eb340a)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_015 · METHODOLOGICAL · `UNDEFINED` — Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments 

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Large language models (LLMs) can generate fluent yet unsupported content (“hallucinations”), which undermines trust and complicates downstream decision making.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval](https://doi.org/10.69987/aimlr.2025.60401)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_016 · METHODOLOGICAL · `UNDEFINED` — Cryptographically verifiable authorization for autonomous AI agents: A falsifiable hypothesis and proof-of-con

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Autonomous AI agents increasingly execute actions, invoke tools, and operate on protected resources with limited human oversight.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Cryptographically verifiable authorization for autonomous AI agents: A falsifiable hypothesis and proof-of-concept](https://www.semanticscholar.org/paper/42bfa454a0008fa4d9181b287677f76421917c94)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_017 · METHODOLOGICAL · `UNDEFINED` — Digital Identity for Agentic Systems: Toward a Portable Authorization Standard for Autonomous Agents

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Enterprise AI is shifting from copilots to autonomous agents capable of executing workflows, negotiating outcomes, and making decisions with limited human oversight.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Digital Identity for Agentic Systems: Toward a Portable Authorization Standard for Autonomous Agents](https://www.semanticscholar.org/paper/5d53c3bc3d0b798bd09c2da38d15bd6c72ba261f)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_035 · METHODOLOGICAL · `UNDEFINED` — Herd Behavior: Investigating Peer Influence in LLM-based Multi-Agent Systems

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Recent advancements in Large Language Models (LLMs) have enabled the emergence of multi-agent systems where LLMs interact, collaborate, and make decisions in shared environments.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Herd Behavior: Investigating Peer Influence in LLM-based Multi-Agent Systems](https://www.semanticscholar.org/paper/1b645935ae20e2fb21aad6aac5dc0d95bb500a36)

**Run:** [Protocol M — Operationalise](#protocol-m)

### CFA_018 · METHODOLOGICAL · `UNDEFINED` — Calibrated Language Models and How to Find Them with Label Smoothing

**Gap:** failed, was reformulated, failed again until it left the tree — no fixed falsifier held. reformulated 3x without surviving a test

**Question:** what measurement would make this claim falsifiable — what result would count against it?

**Claim as extracted:** Recent advances in natural language processing (NLP) have opened up greater opportunities to enable fine-tuned large language models (LLMs) to behave as more powerful interactive agents through improved instruction-following ability.

**Disciplines:** machine learning, statistics (calibration, forecasting), philosophy of science

**Existing record:**
- source: [Calibrated Language Models and How to Find Them with Label Smoothing](https://www.semanticscholar.org/paper/4c04624c0a0c0c5c45a67a85829db08818ac03bb)

**Run:** [Protocol M — Operationalise](#protocol-m)

#### Markers — untested in this sample

No source in the sample spoke to these. That is a fact about the sample, not about the claim.

- Confidence Comes from Experience: Experiential Confidence Estimation from Reasoning to Agents — [source](https://www.semanticscholar.org/paper/a4eadda8b5fa6316b0b0ef5d60c40ea021835f59)
- Confidence Composition for Multiagent Language Model Systems — [source](https://www.semanticscholar.org/paper/35bcf942450e50382abea4f20844bf5c4adb2c2c)
- Cost-Calibrated Escalation: Learning Confidence-to-Tier Routing Policies for LLM-Assisted SOC Triage Under SLA Constraints — [source](https://www.semanticscholar.org/paper/e1442988917859798b9c8966dd7c08531ae7387e)
- Cryptographically verifiable authorization for autonomous AI agents: a falsifiable hypothesis and proof of concept — [source](http://arxiv.org/abs/2607.21325v3)
- Hallucination Detection and Confidence Calibration for Large Language Model Outputs: Reproducible Experiments on HaluEval — [source](https://www.semanticscholar.org/paper/5fc6a54544f6b704a9fdcfabfae4ec5d2220c7f7)
- Mathematical Analysis of Hallucination Dynamics in Large Language Models: Uncertainty Quantification, Advanced Decoding, and Principled Mitigation — [source](https://www.semanticscholar.org/paper/55fc275598aa95cff62e1c0246a7c3c0faaeb8a1)
- On Verbalized Confidence Scores for LLMs — [source](https://www.semanticscholar.org/paper/4fd8ded3fd8942fb9e8a557ac37722b9f7add8b8)
- Operationalizing Serendipity: Multi-Agent AI Workflows for Enhanced Materials Characterization with Theory-in-the-Loop — [source](https://www.semanticscholar.org/paper/5b014f349a093bc770a18858d8afbb21290bfce3)
- SearchJev: A Fast and Calibrated System-1 Model for Search Agents — [source](https://www.semanticscholar.org/paper/25c97215ea9ab363eec9d30543fa28b985f1b246)

<a id="hidden-variable-detection-causal-discovery-from-residuals"></a>

## hidden variable detection / causal discovery from residuals (`HVD`)

### HVD_001 · EMPIRICAL · `UNDER_STUDY` — Causal Discovery in High-Dimensional Time Series with Latent Confounders via Score-Based Diffusion Models

**Gap:** the sample splits on this claim — 4 corroborating / 2 contradicting readings, beta 0.62.

**Question:** does the result in “Causal Discovery in High-Dimensional Time Series with Latent Confounders via Score-Based Diffusion Models” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** The identification of causal relationships from observational time series data constitutes a fundamental challenge across scientific disciplines, ranging from climate science to econometrics and systems biology.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [Causal Discovery in High-Dimensional Time Series with Latent Confounders via Score-Based Diffusion Models](https://www.semanticscholar.org/paper/8be603b3e42d906489745267446de3078512bda4)
- cross-read: [Mitigating Hidden Confounding by Progressive Confounder Imputation via Large Language Models](http://arxiv.org/abs/2507.02928v1)
- cross-read: [Causal discovery of linear non-Gaussian acyclic models in the presence of latent confounders](http://arxiv.org/abs/2001.04197v4)
- cross-read: [Latent-Y: A Lab-Validated Autonomous Agent for De Novo Drug Design](http://arxiv.org/abs/2603.29727v2)
- cross-read: [Score matching through the roof: linear, nonlinear, and latent variables causal discovery](http://arxiv.org/abs/2407.18755v2)
- cross-read: [Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series](https://www.semanticscholar.org/paper/1c20be6817e06988735c30cb9eecaf05e0c21c9a)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)

**Run:** [Protocol R — Replication split](#protocol-r)

### HVD_002 · EMPIRICAL · `UNDER_STUDY` — Causal discovery from time-series discrete data in the presence of latent confounders.

**Gap:** the sample splits on this claim — 4 corroborating / 2 contradicting readings, beta 0.62.

**Question:** does the result in “Causal discovery from time-series discrete data in the presence of latent confounders.” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Learning causal structures from discrete time series data presents significant challenges, particularly in the presence of unobserved variables, or latent confounders, which are frequently encountered in real-world scenarios.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [Causal discovery from time-series discrete data in the presence of latent confounders.](https://www.semanticscholar.org/paper/c1cc59c9eae56b382d6b533dc76b6ec45c16ba20)
- cross-read: [Mitigating Hidden Confounding by Progressive Confounder Imputation via Large Language Models](http://arxiv.org/abs/2507.02928v1)
- cross-read: [Causal discovery of linear non-Gaussian acyclic models in the presence of latent confounders](http://arxiv.org/abs/2001.04197v4)
- cross-read: [Score matching through the roof: linear, nonlinear, and latent variables causal discovery](http://arxiv.org/abs/2407.18755v2)
- cross-read: [Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series](https://www.semanticscholar.org/paper/1c20be6817e06988735c30cb9eecaf05e0c21c9a)
- cross-read: [Use of prior knowledge to discover causal additive models with unobserved variables and its application to time series data](https://www.semanticscholar.org/paper/d426a88c16e45e1fe0c56056534b897b53f6dd31)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)

**Run:** [Protocol R — Replication split](#protocol-r)

### HVD_003 · EMPIRICAL · `UNDER_STUDY` — High-recall causal discovery for autocorrelated time series with latent confounders

**Gap:** the sample splits on this claim — 3 corroborating / 2 contradicting readings, beta 0.57.

**Question:** does the result in “High-recall causal discovery for autocorrelated time series with latent confounders” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** We present a new method for linear and nonlinear, lagged and contemporaneous constraint-based causal discovery from observational time series in the presence of latent confounders.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [High-recall causal discovery for autocorrelated time series with latent confounders](https://www.semanticscholar.org/paper/311c8cc775770257d43b6e4e26f6b6470d0cb02a)
- cross-read: [Mitigating Hidden Confounding by Progressive Confounder Imputation via Large Language Models](http://arxiv.org/abs/2507.02928v1)
- cross-read: [Causal discovery of linear non-Gaussian acyclic models in the presence of latent confounders](http://arxiv.org/abs/2001.04197v4)
- cross-read: [Score matching through the roof: linear, nonlinear, and latent variables causal discovery](http://arxiv.org/abs/2407.18755v2)
- cross-read: [Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series](https://www.semanticscholar.org/paper/1c20be6817e06988735c30cb9eecaf05e0c21c9a)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)

**Run:** [Protocol R — Replication split](#protocol-r)

### HVD_004 · EMPIRICAL · `UNDER_STUDY` — Causal Discovery for time series from multiple datasets with latent contexts

**Gap:** the sample splits on this claim — 2 corroborating / 2 contradicting readings, beta 0.50.

**Question:** does the result in “Causal Discovery for time series from multiple datasets with latent contexts” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Causal discovery from time series data is a typical problem setting across the sciences.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [Causal Discovery for time series from multiple datasets with latent contexts](https://www.semanticscholar.org/paper/a36cefa2643a9bfa3a40c4543a2ffee3cbfc117e)
- cross-read: [Use of prior knowledge to discover causal additive models with unobserved variables and its application to time series data](https://www.semanticscholar.org/paper/d426a88c16e45e1fe0c56056534b897b53f6dd31)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)
- cross-read: [Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series](https://www.semanticscholar.org/paper/1c20be6817e06988735c30cb9eecaf05e0c21c9a)
- cross-read: [Mitigating Hidden Confounding by Progressive Confounder Imputation via Large Language Models](http://arxiv.org/abs/2507.02928v1)

**Run:** [Protocol R — Replication split](#protocol-r)

### HVD_005 · EMPIRICAL · `UNDER_STUDY` — Causal discovery for time series with latent confounders

**Gap:** the sample splits on this claim — 2 corroborating / 1 contradicting readings, beta 0.60.

**Question:** does the result in “Causal discovery for time series with latent confounders” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Reconstructing the causal relationships behind the phenomena we observe is a fundamental challenge in all areas of science.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [Causal discovery for time series with latent confounders](https://www.semanticscholar.org/paper/b6d7bb52558a5ff924fdb995c7f849e5c7feb65b)
- cross-read: [Mitigating Hidden Confounding by Progressive Confounder Imputation via Large Language Models](http://arxiv.org/abs/2507.02928v1)
- cross-read: [Causal discovery of linear non-Gaussian acyclic models in the presence of latent confounders](http://arxiv.org/abs/2001.04197v4)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)

**Run:** [Protocol R — Replication split](#protocol-r)

### HVD_006 · EMPIRICAL · `UNDER_STUDY` — Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series

**Gap:** the sample splits on this claim — 2 corroborating / 1 contradicting readings, beta 0.60.

**Question:** does the result in “Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Increasingly large observational datasets from healthcare and social media may allow new types of causal inference.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series](https://www.semanticscholar.org/paper/1c20be6817e06988735c30cb9eecaf05e0c21c9a)
- cross-read: [Mitigating Hidden Confounding by Progressive Confounder Imputation via Large Language Models](http://arxiv.org/abs/2507.02928v1)
- cross-read: [Latent-Y: A Lab-Validated Autonomous Agent for De Novo Drug Design](http://arxiv.org/abs/2603.29727v2)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)

**Run:** [Protocol R — Replication split](#protocol-r)

### HVD_007 · EMPIRICAL · `UNDER_STUDY` — Addressing Information Asymmetry: Deep Temporal Causality Discovery for Mixed Time Series

**Gap:** the sample mostly contradicts this claim — 0 corroborating / 2 contradicting readings, beta 0.25.

**Question:** does the result in “Addressing Information Asymmetry: Deep Temporal Causality Discovery for Mixed Time Series” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** While existing causal discovery methods mostly focus on continuous time series, causal discovery for mixed time series encompassing both continuous variables (CVs) and discrete variables (DVs) is a fundamental yet underexplored problem.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [Addressing Information Asymmetry: Deep Temporal Causality Discovery for Mixed Time Series](https://www.semanticscholar.org/paper/8fc7bfbf9fb6b19ef772e6328959e253795ecce7)
- cross-read: [Use of prior knowledge to discover causal additive models with unobserved variables and its application to time series data](https://www.semanticscholar.org/paper/d426a88c16e45e1fe0c56056534b897b53f6dd31)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)

**Run:** [Protocol R — Replication split](#protocol-r)

### HVD_008 · EMPIRICAL · `UNDER_STUDY` — Causal Discovery with Inverted Self-attention for Multivariate Time Series

**Gap:** the sample mostly contradicts this claim — 0 corroborating / 2 contradicting readings, beta 0.25.

**Question:** does the result in “Causal Discovery with Inverted Self-attention for Multivariate Time Series” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Causal discovery in multivariate time series data is challenging due to complex interactions, high dimensionality, and nonlinear dependencies among variables.

**Disciplines:** causal inference, statistics, econometrics, climate and earth-system science

**Existing record:**
- source: [Causal Discovery with Inverted Self-attention for Multivariate Time Series](https://www.semanticscholar.org/paper/6f9d1f3c3fbf4751b3402e7a4ff4899b148570a2)
- cross-read: [Using Domain Knowledge to Overcome Latent Variables in Causal Inference from Time Series](https://www.semanticscholar.org/paper/1c20be6817e06988735c30cb9eecaf05e0c21c9a)
- cross-read: [Nonlinear Causal Discovery in Time Series](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)

**Run:** [Protocol R — Replication split](#protocol-r)

#### Markers — untested in this sample

No source in the sample spoke to these. That is a fact about the sample, not about the claim.

- Nonlinear Causal Discovery in Time Series — [source](https://www.semanticscholar.org/paper/53c4012d8f70b8cd28980d7e7ee96be911aeaaad)
- Use of prior knowledge to discover causal additive models with unobserved variables and its application to time series data — [source](https://www.semanticscholar.org/paper/d426a88c16e45e1fe0c56056534b897b53f6dd31)

<a id="causal-states-and-statistical-complexity"></a>

## causal states and statistical complexity (`CSS`)

### CSS_001 · EMPIRICAL · `UNDER_STUDY` — Entropy Rate Estimation for English via a Large Cognitive Experiment Using Mechanical Turk

**Gap:** the sample splits on this claim — 3 corroborating / 1 contradicting readings, beta 0.67.

**Question:** does the result in “Entropy Rate Estimation for English via a Large Cognitive Experiment Using Mechanical Turk” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** The entropy rate h of a natural language quantifies the complexity underlying the language.

**Disciplines:** computational mechanics, information theory, dynamical systems

**Existing record:**
- source: [Entropy Rate Estimation for English via a Large Cognitive Experiment Using Mechanical Turk](https://www.semanticscholar.org/paper/166b53765f33d7e5881e7dc73ae481c65fcf6bdc)
- cross-read: [Quantitative probing: Validating causal models using quantitative domain knowledge](http://arxiv.org/abs/2209.03013v1)
- cross-read: [Corrections to Bekenstein-Hawking entropy --- Quantum or not-so quantum?](http://arxiv.org/abs/1101.0030v1)
- cross-read: [A Decision Support System for Prediction of Paroxysmal Atrial Fibrillation based on Heart Rate Variability Metrics](https://www.semanticscholar.org/paper/3825f009d6a2f32ec89bf76f584414ed440f7836)
- cross-read: [Statistical Learning under Heterogeneous Distribution Shift](https://www.semanticscholar.org/paper/8ca566b647af7544080f0a942fc72f1716013787)

**Run:** [Protocol R — Replication split](#protocol-r)

<a id="requisite-variety-and-cybernetic-regulation"></a>

## requisite variety and cybernetic regulation (`RVC`)

### RVC_004 · EMPIRICAL · `UNDER_STUDY` — Auditing World-Model Explanations in Retail Forecasting: Faithfulness, Accuracy and Causal Validity

**Gap:** the sample splits on this claim — 2 corroborating / 2 contradicting readings, beta 0.50.

**Question:** does the result in “Auditing World-Model Explanations in Retail Forecasting: Faithfulness, Accuracy and Causal Validity” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Retail forecasting models that see the price and promotion plan can explain each forecast as a baseline, what would sell with nothing planned, plus the lift each part of the plan adds.

**Disciplines:** cybernetics, control theory, systems engineering

**Existing record:**
- source: [Auditing World-Model Explanations in Retail Forecasting: Faithfulness, Accuracy and Causal Validity](https://doi.org/10.2139/ssrn.7627720)
- cross-read: [What-If World: A Causal Benchmark for General World Models in Embodied Scenarios](http://arxiv.org/abs/2605.27589v1)
- cross-read: [From Causal Factor Investing to Causal Factor Discovery: Evolving a Neuro-symbolic World Model of the Market](https://doi.org/10.2139/ssrn.7216139)
- cross-read: [ForeTime-VLA: Causal Future-Token Distillation from a World Action Model for Conveyor-Belt Manipulation](http://arxiv.org/abs/2608.20735v1)
- cross-read: [ForeTime-VLA: Causal Future-Token Distillation from a World Action Model for Conveyor-Belt Manipulation](http://arxiv.org/abs/2608.20735v2)

**Run:** [Protocol R — Replication split](#protocol-r)

### RVC_001 · EMPIRICAL · `UNDER_STUDY` — The Good Algorithmic Regulator Theorem: Model It, Transmit It, or Leave It in the World

**Gap:** the sample splits on this claim — 3 corroborating / 1 contradicting readings, beta 0.67.

**Question:** does the result in “The Good Algorithmic Regulator Theorem: Model It, Transmit It, or Leave It in the World” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** The idea that successful regulation requires an internal world model helps motivate both the generative models of active inference and the modeling engine of Kolmogorov Theory's algorithmic agent.

**Disciplines:** cybernetics, control theory, systems engineering

**Existing record:**
- source: [The Good Algorithmic Regulator Theorem: Model It, Transmit It, or Leave It in the World](https://doi.org/10.20944/preprints202609.1967.v1)
- cross-read: [Data-Dependent Goal Modeling for ML-Enabled Law Enforcement Systems](http://arxiv.org/abs/2601.06237v1)
- cross-read: [Requisite Variety For Ai Security](https://doi.org/10.2139/ssrn.6255362)
- cross-read: [ForeTime-VLA: Causal Future-Token Distillation from a World Action Model for Conveyor-Belt Manipulation](http://arxiv.org/abs/2608.20735v1)
- cross-read: [ForeTime-VLA: Causal Future-Token Distillation from a World Action Model for Conveyor-Belt Manipulation](http://arxiv.org/abs/2608.20735v2)

**Run:** [Protocol R — Replication split](#protocol-r)

### RVC_002 · EMPIRICAL · `UNDER_STUDY` — What-If World: A Causal Benchmark for General World Models in Embodied Scenarios

**Gap:** the sample splits on this claim — 2 corroborating / 2 contradicting readings, beta 0.50, reformulated 1×.

**Question:** does the result in “What-If World: A Causal Benchmark for General World Models in Embodied Scenarios” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Video generation models are increasingly used as world simulators for tasks like driving and robotic manipulation.

**Disciplines:** cybernetics, control theory, systems engineering

**Existing record:**
- source: [What-If World: A Causal Benchmark for General World Models in Embodied Scenarios](http://arxiv.org/abs/2605.27589v1)
- cross-read: [Data-Dependent Goal Modeling for ML-Enabled Law Enforcement Systems](http://arxiv.org/abs/2601.06237v1)
- cross-read: [D'Zilva's Addition to Ashby's Law of Requisite Variety](https://doi.org/10.2139/ssrn.6452601)
- cross-read: [Requisite Variety For Ai Security](https://doi.org/10.2139/ssrn.6255362)
- cross-read: [WorldGym: World Model as An Environment for Policy Evaluation](http://arxiv.org/abs/2506.00613v3)
- cross-read: [Multi-Domain Causal Discovery in Bijective Causal Models](http://arxiv.org/abs/2504.21261v1)
- cross-read: [From Causal Factor Investing to Causal Factor Discovery: Evolving a Neuro-symbolic World Model of the Market](https://doi.org/10.2139/ssrn.7216139)
- … 4 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### RVC_003 · EMPIRICAL · `UNDER_STUDY` — From Causal Factor Investing to Causal Factor Discovery: Evolving a Neuro-symbolic World Model of the Market

**Gap:** the sample splits on this claim — 2 corroborating / 2 contradicting readings, beta 0.50, reformulated 1×.

**Question:** does the result in “From Causal Factor Investing to Causal Factor Discovery: Evolving a Neuro-symbolic World Model of the Market” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Quantitative factor strategies routinely excel in backtests and disappoint in production: the flagship live multifactor index earned a Sharpe ratio statistically indistinguishable from zero over seventeen years.

**Disciplines:** cybernetics, control theory, systems engineering

**Existing record:**
- source: [From Causal Factor Investing to Causal Factor Discovery: Evolving a Neuro-symbolic World Model of the Market](https://doi.org/10.2139/ssrn.7216139)
- cross-read: [Data-Dependent Goal Modeling for ML-Enabled Law Enforcement Systems](http://arxiv.org/abs/2601.06237v1)
- cross-read: [D'Zilva's Addition to Ashby's Law of Requisite Variety](https://doi.org/10.2139/ssrn.6452601)
- cross-read: [Requisite Variety For Ai Security](https://doi.org/10.2139/ssrn.6255362)
- cross-read: [What-If World: A Causal Benchmark for General World Models in Embodied Scenarios](http://arxiv.org/abs/2605.27589v1)
- cross-read: [WorldGym: World Model as An Environment for Policy Evaluation](http://arxiv.org/abs/2506.00613v3)
- cross-read: [Multi-Domain Causal Discovery in Bijective Causal Models](http://arxiv.org/abs/2504.21261v1)
- … 4 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

### RVC_005 · EMPIRICAL · `UNDER_STUDY` — Requisite Variety For Ai Security

**Gap:** the sample splits on this claim — 2 corroborating / 1 contradicting readings, beta 0.60, reformulated 1×.

**Question:** does the result in “Requisite Variety For Ai Security” hold under its stated conditions, and which condition separates the sources that disagree?

**Claim as extracted:** Enterprises are deploying large language models and autonomous AI agents into operational control loops-security operations, quality assurance, procurement, infrastructure management-where these systems make thousands of consequential decisions with tool access, external data ingestion, and limited human oversight.

**Disciplines:** cybernetics, control theory, systems engineering

**Existing record:**
- source: [Requisite Variety For Ai Security](https://doi.org/10.2139/ssrn.6255362)
- cross-read: [Incorporating AI incident reporting into telecommunications law and policy: Insights from India](http://arxiv.org/abs/2509.09508v2)
- cross-read: [Data-Dependent Goal Modeling for ML-Enabled Law Enforcement Systems](http://arxiv.org/abs/2601.06237v1)
- cross-read: [D'Zilva's Addition to Ashby's Law of Requisite Variety](https://doi.org/10.2139/ssrn.6452601)
- cross-read: [What-If World: A Causal Benchmark for General World Models in Embodied Scenarios](http://arxiv.org/abs/2605.27589v1)
- cross-read: [WorldGym: World Model as An Environment for Policy Evaluation](http://arxiv.org/abs/2506.00613v3)
- cross-read: [Multi-Domain Causal Discovery in Bijective Causal Models](http://arxiv.org/abs/2504.21261v1)
- … 5 more in `data/findings_log.jsonl`

**Run:** [Protocol R — Replication split](#protocol-r)

#### Markers — untested in this sample

No source in the sample spoke to these. That is a fact about the sample, not about the claim.

- ForeTime-VLA: Causal Future-Token Distillation from a World Action Model for Conveyor-Belt Manipulation — [source](http://arxiv.org/abs/2608.20735v2)

<a id="retired-ids"></a>

## Retired ids

Ids that no longer qualify as open (claim resolved, retired off-scope, or re-staked). Kept so a citation never points at a reused id.

- `CFA_001` · contested · last seen 2026-10-08 · On Verbalized Confidence Scores for LLMs
- `CFA_002` · contested · last seen 2026-10-08 · DiscoUQ: Structured Disagreement Analysis for Uncertainty Quantification in LLM Agent Ensembles
- `CFA_003` · contested · last seen 2026-10-08 · Calibrating the Confidence of Large Language Models by Eliciting Fidelity
- `CFA_004` · contested · last seen 2026-10-08 · Herd Behavior: Investigating Peer Influence in LLM-based Multi-Agent Systems
