"""Ashby's requisite-variety meter."""

import pytest

from grounding.core.variety import VarietyMeter


def test_counting_variety_is_log2_of_the_repertoire():
    meter = VarietyMeter(mode="count")
    for codeword in ("a", "b", "c", "d"):
        meter.observe_disturbance(codeword)
    for codeword in ("x", "y"):
        meter.observe_response(codeword)
    assert meter.disturbance_variety == 2.0     # log2(4)
    assert meter.response_variety == 1.0        # log2(2)
    assert meter.margin == -1.0
    assert meter.uncontrolled_variety == 1.0    # a bit leaks through, per V(Z) >= V(D)-V(R)


def test_entropy_variety_discounts_unused_repertoire():
    """Two regulators with the same repertoire size but different usage."""
    even = VarietyMeter()
    lopsided = VarietyMeter()
    for _ in range(50):
        even.observe_response("a")
        even.observe_response("b")
    for _ in range(99):
        lopsided.observe_response("a")
    lopsided.observe_response("b")

    assert even.response_variety == pytest.approx(1.0)
    assert lopsided.response_variety < 0.1      # "b" is inventory, not variety
    # Counting variety cannot tell them apart; that is why entropy is default.
    assert VarietyMeter(mode="count")._variety(["a", "b"]) == 1.0


def test_alarm_fires_only_when_the_margin_closes():
    meter = VarietyMeter(name="sensor")
    # Regulator out-varies the environment: plenty of slack.
    for i in range(64):
        meter.observe(disturbance=i % 2, response=i % 16)
    assert meter.margin > 0.5
    assert not meter.alarm(threshold=0.5)

    # Environment out-varies the regulator: alarm.
    starved = VarietyMeter(name="sensor")
    for i in range(64):
        starved.observe(disturbance=i % 16, response=i % 2)
    assert starved.margin < 0
    assert starved.alarm(threshold=0.5)
    assert "ALARM" in starved.report()


def test_alarm_needs_both_sides_observed():
    meter = VarietyMeter()
    for i in range(10):
        meter.observe_disturbance(i)
    # No responses recorded at all: silence is not evidence of a deficit.
    assert not meter.alarm()


def test_window_tracks_regime_change():
    meter = VarietyMeter(window=10)
    for i in range(100):
        meter.observe_response(i)          # wide-ranging history
    for _ in range(10):
        meter.observe_response("stuck")    # recent regime is a single codeword
    assert meter.response_variety == 0.0


def test_status_snapshot_and_bad_mode():
    meter = VarietyMeter(name="s")
    meter.observe(disturbance=1, response=2)
    status = meter.status()
    assert status["name"] == "s"
    assert status["n_disturbances"] == status["n_responses"] == 1
    assert status["distinct_responses"] == 1
    meter.reset()
    assert not meter.disturbances and not meter.responses

    with pytest.raises(ValueError):
        VarietyMeter(mode="vibes")
