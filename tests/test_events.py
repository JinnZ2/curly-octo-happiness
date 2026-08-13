"""Phase 3.6: event-driven encoding — Δ-threshold, refractory, and its cost."""

import math
import random

import pytest

from grounding.core.allostasis import percentile_thresholds
from grounding.core.events import EventEncoder, fidelity_claim, reconstruct

BANDS = [0.0, 1.0, 2.0, 3.0]


def encode(values, times=None, **kwargs):
    encoder = EventEncoder(kwargs.pop("bands", BANDS), **kwargs)
    schedule = times if times is not None else range(len(values))
    for t, value in zip(schedule, values):
        encoder.observe(t, value)
    return encoder


def test_construction_rejects_nonsense():
    with pytest.raises(ValueError):
        EventEncoder([])
    with pytest.raises(ValueError):
        EventEncoder(BANDS, threshold=-1.0)


def test_first_sample_always_reports():
    encoder = encode([1.5])
    assert len(encoder.events) == 1
    assert encoder.events[0].polarity == 0     # a level, not a direction


def test_silence_while_the_band_holds():
    """Re-sending an unchanged codeword is the waste this exists to remove."""
    encoder = encode([1.1, 1.2, 1.3, 1.9, 1.05])
    assert len(encoder.events) == 1            # all inside band 1
    assert encoder.compression == pytest.approx(0.8)


def test_band_changes_fire_with_polarity():
    encoder = encode([0.5, 1.5, 2.5, 0.5])
    assert [e.polarity for e in encoder.events] == [0, 1, 1, -1]
    assert [e.band for e in encoder.events] == [0, 1, 2, 0]


def test_events_carry_gray_coded_bands():
    encoder = encode([0.5, 1.5, 2.5])
    assert [e.bits for e in encoder.events] == ["000", "001", "011"]


def test_hysteresis_suppresses_dithering_at_a_band_edge():
    """The reference is the last *event*, not the last sample, or it chatters."""
    dither = [0.99, 1.01, 0.99, 1.01, 0.99, 1.01]
    chatty = encode(dither)
    steady = encode(dither, threshold=0.5)
    assert len(chatty.events) > len(steady.events)
    assert len(steady.events) == 1


def test_refractory_bounds_the_event_rate_and_says_what_it_cost():
    fast = [0.5, 1.5, 2.5, 0.5, 1.5, 2.5, 0.5, 1.5]
    encoder = encode(fast, refractory=3.0)
    assert encoder.suppressed > 0
    assert encoder.event_rate < encode(fast).event_rate
    assert "suppressed" in encoder.report()


def test_reconstruction_holds_the_last_level():
    encoder = encode([0.5, 0.6, 2.5, 2.6, 0.5])
    replayed = reconstruct(encoder.events, 5)
    assert replayed == [0, 0, 2, 2, 0]
    assert reconstruct([], 0) == []
    assert reconstruct([], 3) == [0, 0, 0]


# --- the compression claim --------------------------------------------------

def slow_signal(n=400, seed=2):
    rng = random.Random(seed)
    return [math.sin(i / 40) * 5 + rng.gauss(0, 0.15) for i in range(n)]


def test_reporting_every_band_change_is_lossless():
    values = slow_signal()
    encoder = encode(values, bands=percentile_thresholds(values, 8))
    claim, measurement = fidelity_claim(encoder, values)
    assert measurement["band_error"] == 0.0
    assert claim.passed == 1 and claim.failed == 0
    # ...and still saves most of the traffic on a slowly-varying signal.
    assert measurement["compression"] > 0.5


def test_too_much_hysteresis_refutes_the_claim():
    """Bandwidth bought by dropping the signal is measured, not assumed."""
    values = slow_signal()
    bands = percentile_thresholds(values, 8)
    greedy = encode(values, bands=bands, threshold=2.0)
    claim, measurement = fidelity_claim(greedy, values)
    assert measurement["compression"] > 0.9      # very cheap
    assert measurement["band_error"] > 0.05      # and very wrong
    assert claim.failed == 1
    assert claim.falsifiability == "machine-checkable"


def test_a_fast_noisy_signal_compresses_badly_and_says_so():
    rng = random.Random(1)
    values = [rng.uniform(0, 3) for _ in range(200)]
    encoder = encode(values)
    claim, measurement = fidelity_claim(encoder, values)
    assert measurement["band_error"] == 0.0      # still lossless
    assert measurement["compression"] < 0.4      # but hardly worth the trouble


# --- the retune control loop ------------------------------------------------

def test_retune_moves_the_threshold_toward_the_target_rate():
    values = slow_signal()
    bands = percentile_thresholds(values, 8)
    encoder = encode(values, bands=bands)
    start_rate = encoder.event_rate

    for _ in range(5):
        encoder.retune(0.05)
        encoder = encode(values, bands=bands, threshold=encoder.threshold)
    assert encoder.event_rate < start_rate
    assert encoder.threshold > 0


def test_retune_relaxes_when_under_target():
    values = slow_signal()
    encoder = encode(values, bands=percentile_thresholds(values, 8), threshold=3.0)
    before = encoder.threshold
    encoder.retune(0.9)
    assert encoder.threshold < before


def test_retune_validates_its_target_and_handles_no_data():
    encoder = EventEncoder(BANDS)
    with pytest.raises(ValueError):
        encoder.retune(0.0)
    with pytest.raises(ValueError):
        encoder.retune(1.5)
    assert encoder.retune(0.1)["note"] == "no data"


# --- the agent's wiring -----------------------------------------------------

def test_agent_event_encodes_its_own_error_stream():
    from unified_playground import UnifiedAgent
    ari = UnifiedAgent()
    assert ari.event_encode() == (None, None, None)     # no history yet
    for _ in range(40):
        ari.run_experiment()
    encoder, claim, measurement = ari.event_encode()
    assert encoder.samples == len(ari.wm.error_hist)
    assert measurement["band_error"] == 0.0
    assert claim.passed == 1
