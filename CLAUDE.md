# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A toolkit for cross-domain analysis: experimental Python "playgrounds" exploring AI grounding, claim falsification, dependency mapping, and geometric system diagnostics. Shared infrastructure lives in the `grounding` package; everything else is a runnable script or a design sketch.

## Running things

```bash
python garden.py                              # batch simulation, prints 100 steps
python unified_playground.py                  # interactive REPL (type 'exit' to quit)
python meta_playground.py                     # one "day" across all playgrounds
python diagnostic/systems_diagnostic_suite.py # SDS demo (needs networkx)
cd modules && python main.py                  # SDS pipeline (imports are CWD-relative)

python -m pytest tests/                       # test suite (needs pytest; networkx/numpy
                                              # for the SDS/plugin tests, else skipped)
```

Run root scripts **from the repository root** — they import the `grounding` package by relative path (or `pip install -e .` to make it importable anywhere). Interactive playgrounds (`unified_playground.py`, `weave*.py`, `relational_weave.py`) read from stdin in a loop; a single test is `python -m pytest tests/test_sds.py::test_fdm_max_depth_not_zero`.

Dependencies: the `grounding` package and root playgrounds are stdlib-only. Extras (see `pyproject.toml` optional-dependencies / `requirements.txt`): `modules/` and `diagnostic/` need `networkx`; most of `plugins/` needs `numpy`; `project/shape_board.py` needs `plotly` + `networkx`; `project/cognitive_playground.py` needs `torch`, `transformers`, `scikit-learn`, `numpy`.

## Architecture

- **`grounding/`** — the one canonical home of the previously copy-pasted core classes: `core/epsilon_machine.py`, `core/variety.py` (see the complexity/cybernetics layer below), `core/claims.py` (`Claim`, `DependencyTree` — with historical aliases `get_or_create`/`add_node`, `recalibrate`, `summary`), `core/graycode.py` (`gray_bits`/`gray_to_index`, the band-encoding convention every plugin uses), `core/memory.py` (`EpisodicMemory`, `MemoryStream`, `SharedMemory`), `core/mentor.py`, `worlds/bumpy.py` (`BumpyWorld`, `WorldModel`). `shared.py` is a re-export shim kept for `playground4-8_*.py`/`meta_playground.py`. Note: `Claim.status` is a **property** (string), not a method.

- **Epistemics layer** (`grounding/core/epistemics.py` + optional `Claim` fields). Claims can carry a machine-checkable `logical_form` ({"op": "abs_diff_lt", "args": [...]}) evaluated via `claim.evaluate(bindings)` — the single source of truth for the falsification condition — plus `scope`, `reference_class`, an executable `refutation_test`, and an escape-hatch counter (`reformulate()`); `beta_confidence` is the calibrated Beta-posterior alternative to the step-heuristic `confidence`. `classify_falsifiability` routes unfalsifiable claims to the `UnknownJournal` (see the agent's `claim <text> :: <falsification>` command). `check_geometry_units` validates the `_v`/`_K`/`_pa`-style key-suffix unit convention (opt-in via `PluginManager(unit_checks=True)`); `check_with_z3` cross-checks logical forms when `z3-solver` is installed. FDM knowledge bases live in `data/*.json` (`FractalDependencyMapper.from_json`).

- **Playground line** (repo root). `claim_falsification_garden.py` → `garden.py` → `garden_with_tree.py` (physics/claims) and `relational_weave.py` → `weave.py` → `weave_with_memory.py` (conversation) merge into `unified_playground.py` — the current agent (Ari: experiments, chat, dreams, skill lab, hardware encoder). `playground4-8_*.py` are standalone sketches of individual subsystems; `meta_playground.py` runs one cycle of everything. Historical versions live in `design/archive/` (v1–v6; there was never a v4) — read-only, do not extend them.

- **Plugin/encoder system**. `plugin_manager.py` (single, consolidated) scans `plugins/` for modules exposing `PLUGIN_META` (`name`, `description`, `class_name`; legacy `encoder_class` accepted). Read paths, in priority order: extended `to_binary(state, prev_state, cross_signals)`, `process(geometry)`, then `from_geometry()/to_binary()`. Classes needing constructor args (`harmony_field_engine`, `vector_pole_extension`, …) register as **services**; get them via `pm.get_service(name, *args)`. Plugins encode sensor data into Gray-coded bitstrings using band thresholds (`grounding.core.graycode` convention: highest band whose threshold ≤ value).

- **Good-regulator / allostasis layer** (Phase 2.1–2.3 of `PLAN_FORWARD.md`). `grounding/core/regulator.py` — `CausalDAG` (worlds state their causal structure; `BumpyWorld.causal_dag()`), `check_homomorphism` (does the claims tree preserve the world's causal edges? collapsing variables is legitimate abstraction, losing a primitive root is not; unmapped variables are handed to HND), `regulator_score` = 1 − H(outcomes)/H_max over **tested** claims. `grounding/core/allostasis.py::AllostaticBands` — reactive vs anticipatory band shifts, each charged to a cumulative `load`, with `chronic()` for pay-forever-fit-never and `miscoverage` measured as band utilisation. Both behind the agent's `regulator` and `bands` commands. `modules/transition.py` measures antifragility properly: mean-preserving spread with common random numbers, viability test (convexity while ruined is the floor at zero, not resilience), and Taleb's fragile/robust/antifragile triad. Note the measured result contradicts the plan's prediction — TORUS is robust, not antifragile — and `tests/test_sds.py` pins that.

- **Cybernetic architecture** (Phase 1 of `PLAN_FORWARD.md`). `grounding/core/vsm.py` — Beer's five systems as real routing: `ViableSystem.route()` walks S1→S2→S3→S5 and can be attenuated at any hop, `raise_algedonic()` goes S1→S5 consulting no mediator, and every `Signal` carries the `path` it travelled so `bypassed_mediation` is checkable per message. Also `saturated()` (an alarm channel that always fires is not an alarm) and `SecondOrderGuard` (von Foerster eigenvalue drift: self-confidence rising while independent error does not fall). `grounding/core/mentor.py::TeachbackMentor` — Pask teachback as staked claims; the automatic overlap check abstains at low overlap, rewordings go through `claim.reformulate()`, and an escape-hatched concept is never `learned()`. Wired into `unified_playground.py` (`UnifiedAgent._build_vsm`, `hardware_scan`, `self_model_check`) behind the commands `vsm`, `pain`, `self-check`, `explain … :: …`, `teachback … :: …`, `confirm`, `correct … :: …`, `learned`. Note `explain <concept>` (asks the tree) and `explain <concept> :: <text>` (mentor teaching) are different commands, disambiguated by the `::`.

- **Complexity/cybernetics layer** (Phase 0 of `PLAN_FORWARD.md`). `grounding/core/epsilon_machine.py` — CSSR-style causal-state reconstruction (`reconstruct`, `symbolize`, `equalized_history_length`) yielding statistical complexity `C_mu` and entropy rate `h_mu`; phases I–II only, so read it comparatively, not as an absolute. It backs `HiddenNodeDetector.scan(..., acceptance="epsilon_machine")`, which keeps a correlated candidate only if conditioning on it drops **both** `C_mu` and `h_mu`. `grounding/core/variety.py` — `VarietyMeter`, Ashby's `V(Z) >= V(D) - V(R)` as an alarm; wired into `plugins/physics_discovery.py` (`variety_status()`, `run_full_discovery(trigger="novelty"|"variety"|"either")`) so band expansion fires when the encoders run out of distinctions, not only on out-of-range data.

- **Systems Diagnostic Suite (SDS)**. Canonical implementation in `modules/`: `gae.py` (`GeometricApplicabilityEngine.analyze(nodes, edges)`, plus constructor-style `GAE(nodes, edges).analyze()` wrapper; always reports Sinha–de Weck structural complexity, graph energy, hub concentration and attack tolerance, and with `complexity_scoring=True` lets hub fragility boost TORUS/ICOSAHEDRON), `hnd.py`, `fdm.py`, `transition.py`, `main.py::diagnose_system()`. `diagnostic/systems_diagnostic_suite.py` is a compatibility shim (short names `GAE`/`HND`/`FDM`) + runnable demo. `project/` connects GAE to a plotly "Shape Board" (`shape_board.py` has all five shape generators; `gae_shape_connector.py` reaches `diagnostic/` via `sys.path`).

## Repository conventions and gotchas

- **Hypothesis engine**: `scripts/hypothesis_engine.py` — a stdlib-only, deterministic weekly research pipeline (explore free scholarly APIs → log → stake `Claim`s → cross-source test → reformulate/escape-hatch → hidden-variable scan → hypothesis drafts). It stakes into the repo's own `grounding.core.claims` machinery rather than reimplementing it; `he.DependencyTree` is an id-keyed claim registry wrapping the repo tree. Config in `config/topics.json`, design doc at `design/hypothesis_engine.md`, offline tests in `tests/test_hypothesis_engine.py` (`--dry-run` uses `scripts/sample_findings.json`, no network). Outputs (`data/*.jsonl`, `data/claim_tree.json`, `hypotheses/*.md`) are generated and committed by `.github/workflows/hypothesis-engine.yml`.

- **Sketches vs. code**: `design/archive/`, `design/notes/` (research notes, index at `00_INDEX.md`), root `PLAN_FORWARD.md` (phased roadmap those notes feed), `design/hypothesis_engine.md`, and `project/Organize.md` are non-runnable history/notes/plans. The `.md` files in `plugins/` are wiring snippets for `UnifiedAgent.handle_mentor` (each states its target at the top); `plugins/Light_bridge.md` documents `plugins/light_bridge.py`.
- No packages outside `grounding/`: `modules/`, `plugins/`, `diagnostic/`, `project/` rely on their own directory being on `sys.path` (scripts there assume CWD or add paths themselves; `tests/conftest.py` handles it for tests).
- When adding an encoder plugin, use `grounding.core.graycode.gray_bits` semantics for banding and declare `class_name` in `PLUGIN_META`; adaptive banding goes in an `init_bands(samples)` method.
- License is CC0 1.0 (public domain).
