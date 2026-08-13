# curly-octo-happiness — AI Grounding & Claim-Falsification Playgrounds

A Python toolkit for **cross-domain systems analysis** and **AI epistemic grounding**:
agents that make explicit, falsifiable claims, track confidence through dependency
trees, detect hidden variables from model residuals, and encode multi-physics sensor
data (EM, magnetic, gravitational-wave, chemical, affective) into Gray-coded
bitstreams via a plugin system.

**Core ideas:** claim falsification · dependency mapping · hidden-node detection ·
geometric system diagnostics (GAE/HND/FDM) · curiosity-driven world models ·
sensor-fusion encoders.

## Quick start

```bash
git clone https://github.com/JinnZ2/curly-octo-happiness && cd curly-octo-happiness
python garden.py                              # watch an agent make & falsify 100 claims
python unified_playground.py                  # chat with Ari ('experiment 5', 'vsm', 'pain', 'exit')
python diagnostic/systems_diagnostic_suite.py # geometry diagnostics + hidden-node demo
python scripts/hypothesis_engine.py --dry-run # research pipeline, offline sample corpus
```

**The core is stdlib-only on purpose.** `grounding/` and the root playgrounds run on a
bare Python install with nothing to fetch — the hardware-stewardship line is about working
where parts and bandwidth are scarce, and a core that needs wheels does not. Heavier
capability lives behind extras and must *add* to that path rather than replace it
(`modules/gae.py` computes graph energy with numpy when present and a stdlib Jacobi solver
when not, with a test asserting they agree). Extras: `modules/` → `networkx`;
`plugins/` → `numpy`; `project/shape_board.py` → `plotly networkx`;
`project/cognitive_playground.py` → `torch transformers scikit-learn`.

```bash
pip install -e ".[test]"     # optional: installable package + test deps
python -m pytest tests/     # 272 tests (2 skipped: plotly, and a numpy-only guard)
```

## What's in here

| Area | Files | What it does |
|---|---|---|
| Claim & falsification playgrounds | `garden*.py`, `claim_falsification_garden.py` | Agents that stake falsifiable claims about a physics world and test them |
| Relational playgrounds | `weave*.py`, `relational_weave.py` | Conversation agents with episodic memory and reflection |
| Unified agent line | `unified_playground*.py` | The above merged, growing per version (dreams, skills, hardware, chemistry) |
| Plugin encoders | `plugin_manager*.py`, `plugins/` | Physical sensor data → Gray-coded bitstreams (EM, magnetic, GW, light, affect) |
| Systems Diagnostic Suite | `modules/`, `diagnostic/` | GAE (geometry fit + structural complexity/attack tolerance), HND (hidden variables from residuals, ε-machine acceptance), FDM (root tracing) |
| Complexity & cybernetics | `grounding/core/epsilon_machine.py`, `variety.py`, `vsm.py`, `regulator.py`, `allostasis.py` | Causal-state reconstruction (C_mu, h_mu), Ashby's requisite-variety alarm, Beer's five systems with a bypassing algedonic channel, good-regulator homomorphism checks, allostatic bands |
| Safety & repurposing | `grounding/core/safety.py` | Control-barrier safety filter (no QP dependency) and a runtime-assurance fallback catalog that recomputes each envelope on degraded dynamics |
| Damage & self-model | `grounding/core/damage.py` | Changepoint detection on prediction residuals, with attribution to the interoceptive signal that explains it |
| Dormancy & reverse bloom | `grounding/core/dormancy.py` | Fold a cut-off component to a scale-free seed, measure how long it keeps (Ellis & Roberts), re-bloom at whatever scale returns |
| Coupling & synchronizability | `grounding/core/coupling.py`, `linalg.py` | Master Stability Function: when a network of units can hold together, when a partition is structural, and when no coupling strength can help |
| Worlds | `grounding/worlds/` | `BumpyWorld` (1-D physics toy) and `ThermalWorld` — bounded, stationary, body-in-the-loop, with a causal DAG checked against the code |
| Event encoding | `grounding/core/events.py` | DVS-style Δ-threshold + refractory encoding over the Gray-code bands, with the compression staked as a testable claim |
| Shape Board | `project/` | GAE recommendations rendered as interactive 3D task shapes (plotly) |
| Hypothesis engine | `scripts/hypothesis_engine.py`, `config/topics.json` | Weekly autonomous research pipeline: explore scholarly APIs → stake claims → cross-source test → consolidate hypothesis drafts |

See `Playgrounds.md` for design write-ups and `REVIEW.md` for a full code review.

## Research notes & roadmap

`design/notes/` holds consolidated notes pairing the repo's own equations and design
rules with the 2024–2026 literature on the same themes (epistemics & falsification,
training/calibration, transformer design, diagnostics & neural architecture, learning
simulation, and complexity engineering / cybernetics / robotics). Start at
[`design/notes/00_INDEX.md`](design/notes/00_INDEX.md).

[`PLAN_FORWARD.md`](PLAN_FORWARD.md) is the roadmap those notes feed: a phased plan for
grounding the existing heuristics (HND thresholds, GAE scores, adaptive bands) in
validated theory, then layering a cybernetic architecture, a good-regulator world model,
and a robotics embodiment layer on top. **Phases 0, 1, most of 2, and the safety half of 3
are implemented** — ε-machine acceptance in HND, structural complexity and attack tolerance
in GAE, the requisite-variety alarm on the physics-discovery loop, Beer's VSM with a genuinely
bypassing algedonic channel, Pask teachback claims, a second-order guard against
self-confirming self-description, good-regulator homomorphism checks against each world's
causal DAG, allostatic bands with a load counter, antifragility measured as a falsifiable
claim (which came back refuted — see the roadmap), and a control-barrier safety filter whose
fallback catalog recomputes each envelope on degraded dynamics, damage detection that traces
a change in the dynamics back to the part responsible, and event-driven encoding that sends
band changes instead of samples; Phase 2.4, Phases 3.3/3.4 and Phase 4 are still plan — and
3.3/3.4 are the only items that genuinely need a dependency.

## Why this matters

Large models assert; they rarely *stake* claims. This project prototypes the
missing discipline: every claim an agent makes carries an explicit falsification
condition, gets tested against a world, and propagates calibrated confidence
through the concepts that depend on it. The same machinery — hidden-node
detection, dependency root-tracing, geometry diagnostics — applies to real
systems analysis (food systems, infrastructure, regenerative agriculture),
where unmodeled variables and unfalsifiable assumptions are exactly what
cause plans to fail.

## License

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](https://creativecommons.org/publicdomain/zero/1.0/)
Released under **CC0 1.0** (public domain dedication) — use it for anything, no attribution required.
