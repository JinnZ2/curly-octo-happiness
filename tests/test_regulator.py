"""Phase 2.1/2.2: causal-DAG grounding, good-regulator scoring, allostatic bands."""

import pytest

from grounding.core.allostasis import AllostaticBands, percentile_thresholds
from grounding.core.regulator import (
    CausalDAG,
    check_homomorphism,
    homomorphism_report,
    outcome_entropy,
    regulator_score,
)
from grounding.worlds.bumpy import BumpyWorld


# --- causal DAGs -----------------------------------------------------------

def test_dag_structure_and_roots():
    dag = CausalDAG("t").add_edges([("a", "b"), ("b", "c"), ("z", "c")])
    assert dag.nodes == {"a", "b", "c", "z"}
    assert dag.roots() == {"a", "z"}
    assert dag.parents("c") == {"b", "z"}
    assert dag.children("a") == {"b"}
    assert dag.ancestors("c") == {"a", "b", "z"}
    assert not dag.has_cycle()


def test_dag_detects_cycles():
    dag = CausalDAG().add_edges([("a", "b"), ("b", "c"), ("c", "a")])
    assert dag.has_cycle()
    assert "cycle" in dag.report()


def test_bumpy_world_states_its_causal_structure():
    dag = BumpyWorld.causal_dag()
    # Position causes slope causes next velocity causes next position.
    assert ("x_t", "slope_t") in dag.edges
    assert ("slope_t", "v_next") in dag.edges
    assert ("v_next", "x_next") in dag.edges
    # Time-indexed, so the physical feedback loop is not a graph cycle.
    assert not dag.has_cycle()
    assert "friction" in dag.roots()


# --- regulator scoring -----------------------------------------------------

def test_outcome_entropy_endpoints():
    assert outcome_entropy([]) == 0.0
    assert outcome_entropy(["held"] * 8) == 0.0
    assert outcome_entropy(["held", "refuted"]) == 1.0


def test_regulator_score_rewards_determined_outcomes():
    assert regulator_score(["held"] * 10) == 1.0          # fully regulated
    assert regulator_score(["held", "refuted"] * 10) == 0.0   # coin flips
    mixed = regulator_score(["held"] * 9 + ["refuted"])
    assert 0.0 < mixed < 1.0


# --- homomorphism ----------------------------------------------------------

WORLD = CausalDAG("world").add_edges([("rain", "soil"), ("soil", "yield"),
                                      ("sun", "yield")])


def test_exact_homomorphism_is_recognised():
    model = CausalDAG("model").add_edges([("Rain", "Soil"), ("Soil", "Yield"),
                                          ("Sun", "Yield")])
    result = check_homomorphism(WORLD, model,
                                {"rain": "Rain", "soil": "Soil",
                                 "sun": "Sun", "yield": "Yield"})
    assert result["is_homomorphism"]
    assert result["fidelity"] == 1.0
    assert result["broken"] == [] and result["hidden_node_candidates"] == []


def test_collapsing_two_variables_into_one_concept_is_legitimate():
    """Abstraction may merge detail — the edge lands inside a concept."""
    model = CausalDAG("model").add_edges([("Weather", "Yield")])
    result = check_homomorphism(WORLD, model,
                                {"rain": "Weather", "soil": "Weather",
                                 "sun": "Weather", "yield": "Yield"})
    assert result["is_homomorphism"]
    assert ("rain", "soil") not in result["broken"]


def test_unmapped_variables_become_hidden_node_candidates():
    model = CausalDAG("model").add_edges([("Soil", "Yield")])
    result = check_homomorphism(WORLD, model,
                                {"soil": "Soil", "yield": "Yield"})
    assert not result["is_homomorphism"]
    assert "rain" in result["unmapped"] and "sun" in result["unmapped"]
    # The world variables the model cannot see are exactly what HND should scan.
    assert set(result["hidden_node_candidates"]) >= {"rain", "sun"}
    assert result["missing_roots"] == ["rain", "sun"]
    assert "Hand to hidden-node detection" in homomorphism_report(
        WORLD, model, {"soil": "Soil", "yield": "Yield"})


def test_invented_roots_are_reported():
    """A model source with no world cause is the model inventing physics."""
    model = CausalDAG("model").add_edges([("Rain", "Soil"), ("Soil", "Yield"),
                                          ("Sun", "Yield"), ("Vibes", "Yield")])
    result = check_homomorphism(WORLD, model,
                                {"rain": "Rain", "soil": "Soil",
                                 "sun": "Sun", "yield": "Yield"})
    assert result["invented_roots"] == ["Vibes"]


def test_agent_model_is_checked_against_the_world():
    from unified_playground import UnifiedAgent
    ari = UnifiedAgent()
    for _ in range(12):
        ari.run_experiment()
    result = ari.regulator_check()
    assert 0.0 <= result["fidelity"] <= 1.0
    assert result["n_resolutions"] > 0
    assert 0.0 <= result["regulator_score"] <= 1.0
    # Unmodelled world variables are journalled, not silently dropped.
    assert result["hidden_node_candidates"]
    assert "no concept in my model" in ari.journal.list_unknowns()


# --- allostatic bands ------------------------------------------------------

def test_percentile_thresholds_are_ascending():
    thresholds = percentile_thresholds([5, 1, 3, 2, 4], n_bands=4)
    assert thresholds == sorted(thresholds) and len(thresholds) == 4
    assert percentile_thresholds([], 4) == []


def test_band_index_follows_the_graycode_convention():
    bands = AllostaticBands([0.0, 0.5, 1.0])
    assert bands.band_index(-1) == 0
    assert bands.band_index(0.4) == 0
    assert bands.band_index(0.5) == 1
    assert bands.band_index(9.9) == 2


def test_miscoverage_counts_both_failures():
    # Every band exercised, nothing under range: fully resolved.
    resolved = AllostaticBands([0.0, 0.5, 1.0])
    for value in (2.0, 3.0, 0.2, 0.7):
        resolved.observe(value)
    assert resolved.miscoverage() == 0.0

    # In range, but every value lands in one band: two of three bands wasted.
    collapsed = AllostaticBands([0.0, 100.0, 200.0])
    for value in (1.0, 2.0, 3.0):
        collapsed.observe(value)
    assert collapsed.miscoverage() == pytest.approx(2 / 3)

    # Under range: silently clamped into band 0 alongside real band-0 values.
    under = AllostaticBands([10.0, 20.0])
    for value in (1.0, 2.0, 15.0, 25.0):
        under.observe(value)
    assert under.miscoverage() == pytest.approx(0.5)


def test_shifting_buys_coverage_and_costs_load():
    bands = AllostaticBands([0.0, 0.1, 0.2, 0.3], name="err")
    for value in (5.0, 6.0, 7.0, 8.0, 9.0):
        bands.observe(value)
    assert bands.miscoverage() > 0
    record = bands.reactive_update(n_bands=4)
    assert record["cost"] > 0
    assert bands.load == pytest.approx(record["cost"])
    assert record["miscoverage_after"] < record["miscoverage_before"]


def test_anticipation_moves_toward_the_forecast():
    observed = [1.0, 1.1, 1.2, 1.3]
    forecast = [9.0, 9.1, 9.2, 9.3]
    bands = AllostaticBands(percentile_thresholds(observed, 4))
    for value in observed:
        bands.observe(value)
    bands.anticipate(forecast, n_bands=4, blend=1.0)
    assert bands.thresholds[0] >= 9.0          # committed to the forecast
    assert "anticipatory" in bands.shifts[-1]["mode"]

    # blend=0 is a plain reactive update; no forecast at all is a no-op.
    reactive = AllostaticBands(percentile_thresholds(observed, 4))
    for value in observed:
        reactive.observe(value)
    reactive.anticipate(forecast, n_bands=4, blend=0.0)
    assert reactive.thresholds[0] < 2.0
    assert reactive.anticipate([], n_bands=4)["cost"] == 0.0


def test_chronic_load_flags_a_predictor_chasing_noise():
    """Paying to shift, over and over, without ever covering better."""
    bands = AllostaticBands([0.0, 100.0, 200.0, 300.0], chronic_window=3)
    for value in (1.0, 2.0, 3.0):
        bands.observe(value)      # miscoverage 1.0: all collapse into one band
    for offset in (400.0, 800.0, 1200.0):
        bands.anticipate([offset, offset + 1, offset + 2, offset + 3], n_bands=4)
    assert bands.load > 0
    assert bands.chronic()
    assert "chronic load" in bands.report()


def test_a_settled_regulator_is_not_chronic():
    bands = AllostaticBands([0.0, 0.25, 0.5, 0.75], chronic_window=3)
    for value in (0.1, 0.3, 0.5, 0.7):
        bands.observe(value)
    for _ in range(3):
        bands.anticipate([0.1, 0.3, 0.5, 0.7], n_bands=4)
    assert not bands.chronic()
