"""Falsifiable tests for grounding.core.dormancy.

The claims worth pinning: folding preserves ratios exactly and magnitude not at
all, the option to fold closes before the system dies, waiting costs viability
on a clock, over-compression is charged rather than rewarded, and a seed's
absence is reported as absent evidence rather than as proof of death.
"""

import pytest

from grounding.core.coupling import components, coupling_coherence, MSFWindow
from grounding.core.dormancy import (
    DEFAULT_FOLD_COST,
    erasure_cost,
    MAX_USEFUL_RESIDUAL,
    MIN_VIABLE_RESIDUAL,
    SEED_TERMS,
    SeedState,
    assess_dormancy,
    bet_monolayer,
    fold,
    fold_window,
    format_dormancy,
    unfold,
    viability,
)

HEALTHY = dict(resonance_energy=0.40, adaptability=0.30,
               diversity=0.55, coupling=0.70)


# --- the fold window --------------------------------------------------------

def test_window_is_open_while_energy_exceeds_the_fold_cost():
    assert fold_window(0.8).open


def test_window_closes_below_the_fold_cost():
    window = fold_window(DEFAULT_FOLD_COST / 2)
    assert not window.open
    assert "expired before the system did" in " ".join(window.warnings)


def test_closing_happens_before_the_system_reaches_zero():
    """The point of the window: the option is gone while energy remains."""
    assert not fold_window(0.05).open
    assert 0.05 > 0.0


def test_narrow_window_is_flagged_before_it_closes():
    window = fold_window(DEFAULT_FOLD_COST * 1.5)
    assert window.open
    assert "NARROW" in " ".join(window.warnings)


def test_invalid_cost_fraction_is_rejected():
    with pytest.raises(ValueError):
        fold_window(0.5, fold_cost_fraction=1.5)


# --- the fold cost, derived from what folding destroys ----------------------

def test_erasure_cost_is_never_zero():
    """Landauer's floor is what makes the window close before death."""
    assert erasure_cost(1e-9, 1) > 0
    assert erasure_cost(0.0, 4) > 0


def test_a_bigger_structure_costs_more_to_fold():
    assert erasure_cost(100.0, 4) > erasure_cost(10.0, 4) > erasure_cost(1.0, 4)


def test_an_older_structure_costs_more_to_fold():
    """History is erased too, so there is more to let go of."""
    assert erasure_cost(2.0, 4, history_steps=50) > erasure_cost(2.0, 4)


def test_more_terms_cost_more_phase_to_discard():
    assert erasure_cost(2.0, 12) > erasure_cost(2.0, 4)


def test_the_derived_cost_drives_the_window():
    """A structure can be alive and unable to afford folding, for a reason."""
    cheap = fold_window(0.25, magnitude=1.0, n_terms=4)
    dear = fold_window(0.25, magnitude=1000.0, n_terms=4, history_steps=20)
    assert cheap.open and not dear.open
    assert dear.cost > cheap.cost


def test_an_explicit_fraction_still_overrides_the_derivation():
    assert fold_window(0.5, fold_cost_fraction=0.9).open is False
    assert fold_window(0.5, fold_cost_fraction=0.1).open is True


# --- folding ----------------------------------------------------------------

def test_proportions_sum_to_one():
    assert sum(fold(**HEALTHY).proportions.values()) == pytest.approx(1.0, abs=1e-12)


def test_all_structural_terms_are_carried():
    assert set(fold(**HEALTHY).proportions) == set(SEED_TERMS)


def test_ratios_are_preserved_exactly():
    seed = fold(**HEALTHY)
    assert (seed.proportions["coupling"] / seed.proportions["adaptability"]
            == pytest.approx(HEALTHY["coupling"] / HEALTHY["adaptability"], abs=1e-12))


def test_magnitude_is_recorded_but_not_preserved_in_the_proportions():
    small = fold(**HEALTHY)
    big = fold(**{k: v * 100 for k, v in HEALTHY.items()})
    for term in SEED_TERMS:                      # same shape, different totals
        assert small.proportions[term] == pytest.approx(big.proportions[term], abs=1e-12)
    assert big.conserved_total == pytest.approx(small.conserved_total * 100, abs=1e-9)


def test_folding_states_what_it_destroys():
    joined = " ".join(fold(**HEALTHY).lost)
    assert "absolute magnitude" in joined
    assert "history" in joined


def test_folding_cites_both_source_frameworks():
    joined = " ".join(fold(**HEALTHY).provenance)
    assert "Seed-physics" in joined
    assert "Mandala-Computing" in joined


def test_metric_signature_is_carried_verbatim():
    """A proportion means nothing without the convention that produced it."""
    seed = fold(**HEALTHY, metric_signature={"coupling_optimum": "phi"})
    assert seed.metric_signature["coupling_optimum"] == "phi"


def test_empty_structure_cannot_be_folded():
    with pytest.raises(ValueError) as excinfo:
        fold(resonance_energy=0.0, adaptability=0.0, diversity=0.0, coupling=0.0)
    assert "BLACK means what it says" in str(excinfo.value)


def test_closed_window_refuses_the_fold():
    with pytest.raises(ValueError):
        fold(resonance_energy=0.01, adaptability=0.3, diversity=0.5, coupling=0.7)


def test_term_already_at_zero_is_recorded_as_unrecoverable():
    seed = fold(resonance_energy=0.4, adaptability=0.0,
                diversity=0.55, coupling=0.7)
    assert seed.is_degenerate
    assert "re-expands to zero" in " ".join(seed.lost)


def test_seed_rejects_proportions_that_do_not_sum_to_one():
    with pytest.raises(ValueError):
        SeedState(proportions={"a": 0.3, "b": 0.3}, conserved_total=1.0)


def test_arbitrary_term_vocabularies_fold():
    """The four canonical terms are a default, not a requirement."""
    seed = fold({"claims": 12.0, "bands": 8.0, "repertoire": 4.0},
                energy=5.0)
    assert set(seed.proportions) == {"claims", "bands", "repertoire"}
    assert seed.proportions["claims"] == pytest.approx(0.5)


def test_an_unnamed_energy_budget_is_refused_not_guessed():
    """Picking whichever term came first makes the answer depend on dict order."""
    with pytest.raises(ValueError) as excinfo:
        fold({"claims": 12.0, "bands": 8.0})
    assert "would be a guess" in str(excinfo.value)
    # Naming it either way works.
    assert fold({"claims": 12.0, "bands": 8.0}, energy=5.0)
    assert fold({"claims": 12.0, "bands": 8.0}, energy_term="claims")


# --- viability decay: duration is bought, and the price is finite -----------

def test_viability_falls_monotonically_with_time():
    seed = fold(**HEALTHY, residual_activity=0.05)
    previous = 1.1
    for elapsed in (0, 100, 1000, 10000, 100000):
        current = viability(seed, float(elapsed), stress=10.0).viable_fraction
        assert current <= previous
        previous = current


def test_stress_shortens_the_time_constant():
    seed = fold(**HEALTHY)
    assert viability(seed, 0.0, stress=0.0).sigma > viability(seed, 0.0, stress=40.0).sigma


def test_lower_residual_activity_buys_duration():
    wet = fold(**HEALTHY, residual_activity=0.06)
    dry = fold(**HEALTHY, residual_activity=0.03)
    assert viability(dry, 0.0).sigma > viability(wet, 0.0).sigma


def test_a_stressed_seed_can_outlive_its_viability():
    assert viability(fold(**HEALTHY), 100000.0, stress=40.0).flag == "NONVIABLE"


def test_flags_progress_through_degrading_to_nonviable():
    seed = fold(**HEALTHY)
    flags = [viability(seed, float(p), stress=20.0).flag for p in (0, 300, 30000)]
    assert flags == ["VIABLE", "DEGRADING", "NONVIABLE"]


def test_seed_constants_are_disclosed_as_an_analogy():
    assert "analogy, not a measurement" in " ".join(
        viability(fold(**HEALTHY), 10.0).warnings)


def test_reading_cites_ellis_and_roberts():
    assert "Ellis & Roberts 1980" in viability(fold(**HEALTHY), 10.0).source


def test_negative_elapsed_is_rejected():
    with pytest.raises(ValueError):
        viability(fold(**HEALTHY), -1.0)


def test_a_very_long_wait_saturates_rather_than_overflowing():
    """Zero viability is a fact about the seed, not an arithmetic error."""
    assert viability(fold(**HEALTHY), 1e9, stress=40.0).viable_fraction == 0.0


# --- over-compression is loss, not better compression -----------------------

def test_below_the_floor_is_charged_not_rewarded():
    at_floor = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL)
    crushed = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL / 4)
    assert (viability(at_floor, 1000.0).viable_fraction
            > viability(crushed, 1000.0).viable_fraction)


def test_drying_below_the_floor_does_not_extend_sigma():
    at_floor = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL)
    crushed = fold(**HEALTHY, residual_activity=MIN_VIABLE_RESIDUAL / 10)
    assert viability(at_floor, 0.0).sigma == pytest.approx(
        viability(crushed, 0.0).sigma, abs=1e-9)


def test_over_compression_is_named_in_the_warnings():
    crushed = fold(**HEALTHY, residual_activity=0.001)
    assert "over-compression" in " ".join(viability(crushed, 10.0).warnings).lower()


def test_storing_too_wet_is_flagged():
    wet = fold(**HEALTHY, residual_activity=MAX_USEFUL_RESIDUAL * 2)
    assert "storing wetter" in " ".join(viability(wet, 10.0).warnings)


def test_fold_notes_the_floor_when_crossed():
    assert "floor" in " ".join(fold(**HEALTHY, residual_activity=0.005).provenance)


# --- the reverse bloom ------------------------------------------------------

def test_round_trip_at_the_original_total_recovers_the_inputs():
    seed = fold(**HEALTHY)
    revived = unfold(seed, available_energy=seed.conserved_total)
    for term, original in HEALTHY.items():
        assert revived[term] == pytest.approx(original, abs=1e-12)


def test_re_expansion_scales_to_what_is_available():
    seed = fold(**HEALTHY)
    small = unfold(seed, available_energy=seed.conserved_total / 4)
    assert sum(small.values()) == pytest.approx(seed.conserved_total / 4, abs=1e-12)


def test_proportions_survive_a_change_of_scale():
    seed = fold(**HEALTHY)
    revived = unfold(seed, available_energy=0.2)
    assert (revived["coupling"] / revived["adaptability"]
            == pytest.approx(HEALTHY["coupling"] / HEALTHY["adaptability"], abs=1e-12))


def test_partial_viability_re_expands_smaller_not_distorted():
    """Losing viability costs size, never shape — ratios are what a seed protects."""
    seed = fold(**HEALTHY)
    reading = viability(seed, 300.0, stress=20.0)
    assert reading.flag == "DEGRADING"
    revived = unfold(seed, available_energy=1.0, viability_reading=reading)
    assert sum(revived.values()) < 1.0
    assert (revived["diversity"] / revived["coupling"]
            == pytest.approx(HEALTHY["diversity"] / HEALTHY["coupling"], abs=1e-12))


def test_nonviable_seed_cannot_be_re_expanded():
    seed = fold(**HEALTHY)
    dead = viability(seed, 1000000.0, stress=40.0)
    with pytest.raises(ValueError) as excinfo:
        unfold(seed, available_energy=1.0, viability_reading=dead)
    assert "inventing a pattern rather than restoring one" in str(excinfo.value)


def test_zero_energy_budget_is_rejected():
    with pytest.raises(ValueError):
        unfold(fold(**HEALTHY), available_energy=0.0)


def test_degenerate_term_re_expands_to_zero():
    seed = fold(resonance_energy=0.4, adaptability=0.0,
                diversity=0.55, coupling=0.7)
    assert unfold(seed, available_energy=10.0)["adaptability"] == 0.0


# --- the structural channel beside a flatlined activity reading -------------

def test_fresh_seed_reads_dormant_not_dead():
    assert assess_dormancy(fold(**HEALTHY), periods_elapsed=10.0).state == "DORMANT"


def test_dormant_reading_names_the_false_positive_it_corrects():
    reading = assess_dormancy(fold(**HEALTHY), periods_elapsed=10.0)
    assert "no flux, not because there is no structure" in " ".join(reading.warnings) \
        or "not because there is no structure" in " ".join(reading.warnings)


def test_expired_seed_reads_lost_and_concedes_the_dead_reading():
    reading = assess_dormancy(fold(**HEALTHY), periods_elapsed=1000000.0, stress=40.0)
    assert reading.state == "SEED_LOST"
    assert "BLACK is now the correct reading" in " ".join(reading.warnings)


def test_partly_degraded_seed_reads_revivable():
    reading = assess_dormancy(fold(**HEALTHY), periods_elapsed=300.0, stress=20.0)
    assert reading.state == "REVIVABLE"


def test_no_seed_is_absent_evidence_not_proof_of_death():
    reading = assess_dormancy(None)
    assert reading.state == "NEVER_FOLDED"
    joined = " ".join(reading.warnings)
    assert "not proof of death" in joined
    assert "not evidence of dormancy either" in joined


def test_format_includes_proportions_losses_and_the_disclaimer():
    text = format_dormancy(assess_dormancy(fold(**HEALTHY), 10.0))
    assert "preserved proportions" in text
    assert "NOT PRESERVED BY FOLDING" in text
    assert "Whether waiting is worth it is not a measurement" in text


def test_format_handles_the_never_folded_case():
    assert "NEVER_FOLDED" in format_dormancy(assess_dormancy(None))


# --- what it is for: a partitioned component ---------------------------------

SPLIT = [[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]
CLASS_III = MSFWindow(nu_lower=0.2, nu_upper=4.0)


def test_a_partitioned_component_can_fold_and_later_re_bloom():
    """The half coupling.py could not answer: what the cut-off side does.

    The partition is structural — no coupling strength repairs it — so the
    isolated component folds rather than spending its reserves coordinating
    with units it cannot reach, and re-blooms at whatever the reconnected
    network supports.
    """
    reading = coupling_coherence(1.0, SPLIT, CLASS_III)
    assert reading.regime == "FRAGMENTED_STRUCTURALLY"
    assert components(SPLIT) == [[0, 1], [2, 3]]

    # The isolated side folds what it still has.
    seed = fold({"claims": 6.0, "bands": 8.0, "variety": 2.0},
                residual_activity=0.03, energy=2.0,
                metric_signature={"partition": [0, 1]})
    assert assess_dormancy(seed, periods_elapsed=50.0).state == "DORMANT"

    # Reconnected later, into a smaller share of the network than it left.
    revived = unfold(seed, available_energy=4.0,
                     viability_reading=viability(seed, 50.0))
    assert sum(revived.values()) < 4.0                     # smaller
    assert (revived["bands"] / revived["claims"]
            == pytest.approx(8.0 / 6.0, abs=1e-12))        # same shape
    assert seed.metric_signature["partition"] == [0, 1]


# --- the residual floor, derived from a sorption isotherm -------------------

def bet_isotherm(monolayer, c_constant, activities):
    """Synthesise a BET isotherm with known parameters."""
    return [(a, monolayer * c_constant * a
             / ((1 - a) * (1 + (c_constant - 1) * a))) for a in activities]


ACTIVITIES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.60, 0.80]


@pytest.mark.parametrize("monolayer,c_constant", [
    (0.055, 20.0),      # ~maize embryo storage optimum
    (0.020, 15.0),      # ~safflower
    (0.045, 30.0),      # ~elm
])
def test_bet_recovers_a_known_monolayer(monolayer, c_constant):
    """The floor is measurable, not chosen — and species-specific."""
    fitted = bet_monolayer(bet_isotherm(monolayer, c_constant, ACTIVITIES))
    assert fitted["monolayer"] == pytest.approx(monolayer, rel=1e-6)
    assert fitted["c_constant"] == pytest.approx(c_constant, rel=1e-6)


def test_bet_excludes_the_multilayer_region():
    """A fit through high activity returns something that is not a monolayer."""
    fitted = bet_monolayer(bet_isotherm(0.055, 20.0, ACTIVITIES))
    assert fitted["n_points"] == 9          # the 0.60 and 0.80 points dropped


def test_bet_refuses_a_fit_it_cannot_support():
    with pytest.raises(ValueError) as excinfo:
        bet_monolayer([(0.6, 0.1), (0.8, 0.2)])
    assert "monolayer region" in str(excinfo.value)
    with pytest.raises(ValueError):
        bet_monolayer([(0.2, 0.05), (0.2, 0.05), (0.2, 0.05)])   # no spread


def test_the_default_floor_sits_in_the_measured_species_range():
    """0.02 is safflower's optimum, not a universal constant — and is documented
    as a default to be replaced by a measurement."""
    assert 0.015 <= MIN_VIABLE_RESIDUAL <= 0.06
