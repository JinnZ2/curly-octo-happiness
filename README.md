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
python unified_playground.py                  # chat with Ari ('experiment 5', 'why right', 'exit')
python diagnostic/systems_diagnostic_suite.py # geometry diagnostics + hidden-node demo
```

The root playgrounds are stdlib-only (run them from the repo root — they use the
`grounding` package). Some subsystems need extras: `modules/` → `networkx`;
`plugins/` → `numpy`; `project/shape_board.py` → `plotly networkx`;
`project/cognitive_playground.py` → `torch transformers scikit-learn`.

```bash
pip install -e ".[test]"     # optional: installable package + test deps
python -m pytest tests/     # 34 tests
```

## What's in here

| Area | Files | What it does |
|---|---|---|
| Claim & falsification playgrounds | `garden*.py`, `claim_falsification_garden.py` | Agents that stake falsifiable claims about a physics world and test them |
| Relational playgrounds | `weave*.py`, `relational_weave.py` | Conversation agents with episodic memory and reflection |
| Unified agent line | `unified_playground*.py` | The above merged, growing per version (dreams, skills, hardware, chemistry) |
| Plugin encoders | `plugin_manager*.py`, `plugins/` | Physical sensor data → Gray-coded bitstreams (EM, magnetic, GW, light, affect) |
| Systems Diagnostic Suite | `modules/`, `diagnostic/` | GAE (geometry fit), HND (hidden variables from residuals), FDM (root tracing) |
| Shape Board | `project/` | GAE recommendations rendered as interactive 3D task shapes (plotly) |

See `Playgrounds.md` for design write-ups and `REVIEW.md` for a full code review.

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
