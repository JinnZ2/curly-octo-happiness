# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A toolkit for cross-domain analysis: a collection of experimental Python "playgrounds" exploring AI grounding, claim falsification, dependency mapping, and geometric system diagnostics. There is no build system, package manifest, linter, or test suite — every file is a standalone script or a design sketch. Several files are intentionally non-runnable pseudocode/snippets (see "Runnable vs. sketch files" below).

## Running things

There are no tests to run. Scripts are executed directly:

```bash
python garden.py                              # batch simulation, prints 100 steps
python unified_playground.py                  # interactive REPL (type 'exit' to quit)
python diagnostic/systems_diagnostic_suite.py # self-contained diagnostic demo
cd modules && python main.py                  # SDS pipeline (imports are CWD-relative)
```

Interactive playgrounds (`unified_playground*.py`, `weave*.py`, `relational_weave.py`) read from stdin in a loop. Batch scripts (`garden.py`, `garden_with_tree.py`, `self_modeling_explorer.py`, `initiation_loop.py`, `claim_falsification_garden.py`, `interplay.py`) run to completion.

Dependencies are undeclared. Stdlib-only: the root playgrounds and `shared.py`. Third-party: `modules/` needs `networkx`; `project/shape_board.py` needs `plotly` + `networkx`; `project/cognitive_playground.py` needs `torch`, `transformers`, `scikit-learn`, `numpy`; most of `plugins/` needs `numpy` (and `harmony_field_engine.py` imports `scipy`).

## Architecture

Three loosely-coupled strands coexist:

1. **Evolutionary playground line** (repo root). `claim_falsification_garden.py` → `garden.py` → `garden_with_tree.py` (physics/claims) and `relational_weave.py` → `weave.py` → `weave_with_memory.py` (conversation) merge into `unified_playground.py`, then `_v2`, `_v3`, `_v5`, `_v6` (there is no v4). Each version is a full copy-paste of the previous file plus one new subsystem (Dream/Journal → SkillLab → hardware encoder → chemical reactor). The core classes (`Claim`, `DependencyTree`, `BumpyWorld`, `WorldModel`, `EpisodicMemory`, `Mentor`) are duplicated in every file and drift slightly between copies — when fixing a bug in one, check all copies. `shared.py` is a parallel attempt at extracting those shared classes; only `playground4-8_*.py` and `meta_playground.py` import it (with different APIs than the unified line, e.g. `Claim.status` is a string attribute in `shared.py` but a method elsewhere).

2. **Plugin/encoder system**. `plugin_manager.py` (v1), `_v2`, `_v3` scan `plugins/` for modules exposing a `PLUGIN_META` dict. v1 expects `encoder_class` key + `from_geometry()/to_binary()/report()`; v2/v3 expect `class_name` and additionally support `process(geometry)` (v2) or `to_binary(state, prev_state, cross_signals)` (v3). Plugins encode physical sensor data into Gray-coded bitstrings using band thresholds. Some "plugins" (`harmony_field_engine`, `vector_pole_extension`, `geometric_inference_engine`, `unified_orchestrator`, `felt_service`, `trust_escrow`, `treaty_memory`) are actually services with constructor arguments and cannot be loaded by any of the managers as-is.

3. **Systems Diagnostic Suite (SDS)** — exists twice with incompatible APIs: `modules/` (GAE/HND/FDM split across files, networkx-based, `GeometricApplicabilityEngine.analyze(nodes, edges)`) and `diagnostic/systems_diagnostic_suite.py` (self-contained, `GAE(nodes, edges).analyze()`, plus a `TransitionSimulator`). `project/` connects the diagnostic-suite GAE to a plotly "Shape Board": `gae_shape_connector.py` extends `sys.path` to import from `diagnostic/`.

## Repository conventions and gotchas

- **Runnable vs. sketch files**: `unified_playground_v6.py` (elided `__init__`/methods), `plugin_manager_v3.py` (patch excerpt without `__init__`), and `project/Organize.md` are design sketches, not working code. Most `.md` files in `plugins/` are code snippets intended to be merged into an agent's `handle_mentor` method (`plugins/Light_bridge.md` documents the plugin that now lives in `plugins/light_bridge.py`).
- Versioned files (`unified_playground_v*`, `plugin_manager_v*`) are kept as history; the highest number is the newest but not necessarily the most complete (v5 is the last fully runnable unified playground).
- The canonical Gray-coding helper is the `gray_bits(value, bands)` pattern found in `unified_playground_v6.py` / `plugins/gravitational.py` (highest band whose threshold ≤ value).
- No packages/`__init__.py`: intra-directory imports (`modules/main.py`, `project/demo_connector.py`, `plugins/em_field.py`) assume the script's own directory is the CWD/`sys.path`.
- License is CC0 1.0 (public domain).
