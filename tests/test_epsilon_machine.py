"""Causal-state reconstruction and the HND acceptance criterion it powers."""

import random

from grounding.core.epsilon_machine import (
    entropy,
    equalized_history_length,
    percentile_bands,
    reconstruct,
    symbolize,
)


def _fair_coin(n=600, seed=0):
    rng = random.Random(seed)
    return [rng.randint(0, 1) for _ in range(n)]


def test_entropy_endpoints():
    assert entropy({}) == 0.0
    assert entropy({"a": 5}) == 0.0                       # certainty
    assert entropy({"a": 1, "b": 1}) == 1.0               # fair coin
    assert abs(entropy({"a": 1, "b": 1, "c": 1, "d": 1}) - 2.0) < 1e-12


def test_symbolize_follows_the_band_convention():
    # Equal-occupancy bands: eight ascending values into four bands, two each.
    assert symbolize([0, 1, 2, 3, 4, 5, 6, 7], n_bands=4) == [0, 0, 1, 1, 2, 2, 3, 3]
    # Explicit thresholds use "highest band whose threshold <= value".
    assert symbolize([0.0, 0.4, 0.6, 9.9], bands=[0.0, 0.5]) == [0, 0, 1, 1]
    # A constant series is one symbol, not a crash.
    assert len(set(symbolize([2.0] * 5, n_bands=4))) == 1


def test_percentile_bands_are_ascending():
    bands = percentile_bands([5, 1, 3, 2, 4], n_bands=4)
    assert bands == sorted(bands)
    assert len(bands) == 4


def test_iid_stream_has_no_memory_and_maximal_surprise():
    machine = reconstruct(_fair_coin(), max_history=2)
    # Nothing in the past helps, so every history collapses to one causal state.
    assert machine.n_states == 1
    assert machine.statistical_complexity < 0.05      # C_mu ~ 0 bits of memory
    assert machine.entropy_rate > 0.95                # h_mu ~ 1 bit of surprise


def test_periodic_stream_is_memory_not_surprise():
    period_six = [(i // 3) % 2 for i in range(600)]   # 000111 repeating
    machine = reconstruct(period_six, max_history=3)
    assert machine.statistical_complexity > 0.5       # it takes memory to track phase
    assert machine.entropy_rate < 1e-9                # but the next symbol is certain


def test_equalized_history_length_matches_search_spaces():
    # 4-symbol alphabet at L=2 searches 16 histories; a 16-symbol augmented
    # alphabet reaches the same 16 at L=1.
    assert equalized_history_length(4, 16, 2) == 1
    assert equalized_history_length(4, 4, 2) == 2
    # Never returns 0, however lopsided the alphabets are.
    assert equalized_history_length(2, 256, 1) == 1
    assert equalized_history_length(4, 1, 3) == 3


def test_conditioning_on_the_driver_simplifies_the_stream():
    """A real hidden driver drops both C_mu and h_mu; noise does not drop both."""
    rng = random.Random(1)
    n = 400
    driver = [float((i // 7) % 3) for i in range(n)]
    residual = [0.4 * d + rng.gauss(0, 0.05) for d in driver]

    residual_symbols = symbolize(residual, n_bands=4)
    driver_symbols = symbolize(driver, n_bands=4)
    noise_symbols = symbolize([rng.gauss(0, 1) for _ in range(n)], n_bands=4)

    def augment(candidate_symbols):
        pairs = list(zip(residual_symbols, candidate_symbols))
        length = equalized_history_length(
            len(set(residual_symbols)), len(set(pairs)), 2)
        return reconstruct(residual_symbols, pairs, max_history=length)

    base = reconstruct(residual_symbols, max_history=2)
    with_driver = augment(driver_symbols)
    with_noise = augment(noise_symbols)

    assert with_driver.statistical_complexity < base.statistical_complexity
    assert with_driver.entropy_rate < base.entropy_rate

    # Noise must not pass the criterion: requiring both C_mu and h_mu to drop
    # is what makes it a test rather than a ratchet. (Until 2026-11-27 this
    # asserted that noise raises C_mu. That held for the old total-variation
    # merge rule, which shattered noisy histories into spurious states; with
    # CSSR's chi-squared test and Phase III, noise lowers C_mu here but raises
    # h_mu, and is still rejected. See experiments/results/EXP-CSS-02/
    # rerun-2026-11-27.)
    assert not (with_noise.statistical_complexity < base.statistical_complexity
                and with_noise.entropy_rate < base.entropy_rate)


def test_reconstruct_rejects_mismatched_streams():
    try:
        reconstruct([0, 1, 0], [0, 1])
    except ValueError:
        return
    raise AssertionError("expected ValueError on length mismatch")


def test_degenerate_streams_do_not_crash():
    for stream in ([], [1], [3, 3, 3, 3]):
        machine = reconstruct(stream)
        assert machine.statistical_complexity == 0.0
        assert machine.entropy_rate == 0.0
        assert "eps-machine" in machine.summary()


# --- Regression cases from EXP-CSS-02 (added 2026-11-27) --------------------
# Pre-registered processes with analytic C_mu and h_mu. Before CSSR Phase III
# was added, period-3 came out at 2 states / C_mu = 0.918 at every T and L.

LOG2_3 = 1.584962500721156


def _period3(n=3000, phase=1):
    return [1 if (i + phase) % 3 == 2 else 0 for i in range(n)]


def _golden_mean(n=20000, seed=7):
    rng, state, out = random.Random(seed), "A", []
    for _ in range(n + 100):
        if state == "A":
            b = rng.randint(0, 1)
            state = "B" if b else "A"
        else:
            b, state = 0, "A"
        out.append(b)
    return out[100:]


def test_period_three_recovers_three_states():
    for length in (2, 3, 5, 10):
        machine = reconstruct(_period3(), max_history=length)
        assert machine.n_states == 3, length
        assert abs(machine.statistical_complexity - LOG2_3) < 1e-6
        assert machine.entropy_rate < 1e-9


def test_period_three_machine_is_unifilar():
    # Each state's histories must send every symbol to a single state.
    seq = _period3()
    machine = reconstruct(seq, max_history=3)
    label = {h: k for k, st in enumerate(machine.states) for h in st.histories}
    for st in machine.states:
        for sym in (0, 1):
            targets = {label.get(h[1:] + (sym,)) for h in st.histories} - {None}
            assert len(targets) <= 1


def test_golden_mean_two_states():
    for length in (2, 3, 5):
        machine = reconstruct(_golden_mean(), max_history=length)
        assert machine.n_states == 2
        assert abs(machine.statistical_complexity - 0.9183) < 0.03
        assert abs(machine.entropy_rate - 2 / 3) < 0.02


def test_biased_coin_one_state():
    rng = random.Random(3)
    seq = [1 if rng.random() < 0.3 else 0 for _ in range(10000)]
    for length in (2, 3, 5):
        machine = reconstruct(seq, max_history=length)
        assert machine.n_states == 1
        assert machine.statistical_complexity == 0.0
        assert abs(machine.entropy_rate - 0.8813) < 0.02


def test_simple_nonunifilar_source_is_undercounted():
    # The SNS has infinitely many causal states (C_mu ~ 2.71 bits); any
    # finite-L reconstruction undercounts. Documented, not hidden.
    rng, state, out = random.Random(11), "A", []
    for _ in range(20100):
        if state == "A":
            b, state = 1, ("A" if rng.random() < 0.5 else "B")
        elif rng.random() < 0.5:
            b, state = 1, "B"
        else:
            b, state = 0, "A"
        out.append(b)
    machine = reconstruct(out[100:], max_history=5)
    assert machine.statistical_complexity < 2.71


def test_tv_option_and_bad_test_name():
    machine = reconstruct(_period3(), max_history=2, test="tv")
    assert machine.n_states == 3
    try:
        reconstruct(_period3(), test="ks")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown test")
