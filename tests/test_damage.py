"""Phase 3.5: damage detection from prediction residuals, and its limits."""

import random

import pytest

from grounding.core.damage import DamageDetector
from grounding.worlds.bumpy import WorldModel


def stream(residual_fn, health_fn, n=200, seed=4):
    rng = random.Random(seed)
    detector = DamageDetector()
    for i in range(n):
        detector.observe(residual_fn(rng, i),
                         {"D1_health": health_fn(i), "R1_health": 1.0})
    return detector


# --- stage 1: detection -----------------------------------------------------

def test_stable_residuals_report_no_damage():
    detector = stream(lambda rng, i: rng.gauss(0, 0.05), lambda i: 1.0)
    report = detector.scan()
    assert not report.detected
    assert "No damage signature" in report.summary()


def test_step_change_is_located_at_the_step():
    detector = stream(lambda rng, i: rng.gauss(0, 0.05) + (0.5 if i >= 120 else 0.0),
                      lambda i: 1.0 if i < 120 else 0.2)
    report = detector.scan()
    assert report.detected
    assert abs(report.changepoint - 120) <= 2
    assert report.effect_size > detector.EFFECT_THRESHOLD


def test_damage_that_quiets_the_residual_is_still_damage():
    """A weakened actuator moves less, so its errors shrink. Signed tests miss it."""
    detector = stream(
        lambda rng, i: rng.gauss(0, 0.05) * (0.2 if i >= 120 else 1.0),
        lambda i: 1.0 if i < 120 else 0.2)
    report = detector.scan()
    assert report.detected
    assert report.after < report.before      # the residual went *down*


def test_short_history_reports_nothing_rather_than_guessing():
    detector = DamageDetector()
    for _ in range(6):
        detector.observe(0.1)
    report = detector.scan()
    assert not report.detected and "not enough history" in report.reason


def test_the_search_cannot_reach_back_to_the_learning_transient():
    """A model that started badly and settled must not read as damaged."""
    detector = DamageDetector()
    rng = random.Random(0)
    for i in range(300):
        # Big errors for the first 40 samples, then a long stable regime.
        scale = 5.0 if i < 40 else 0.05
        detector.observe(rng.gauss(0, scale), {"D1_health": 1.0})
    assert not detector.scan().detected


# --- stage 2: attribution ---------------------------------------------------

def test_a_varying_signal_that_explains_the_residual_is_named():
    detector = stream(
        lambda rng, i: rng.gauss(0, 0.05) + max(0, i - 120) * 0.008,
        lambda i: 1.0 if i < 120 else max(0.0, 1 - (i - 120) * 0.01))
    report = detector.scan()
    assert report.detected
    assert report.culprit == "D1_health"
    assert not report.unattributed
    assert report.candidates["R1_health"]["acceptance"] == "rejected"
    assert "attributed to" in report.summary()


def test_detection_without_attribution_is_a_real_state():
    """Knowing the model is wrong is not the same as knowing why."""
    detector = stream(lambda rng, i: rng.gauss(0, 0.05) + (0.5 if i >= 120 else 0.0),
                      lambda i: 1.0)          # no signal moves at all
    report = detector.scan()
    assert report.detected and report.unattributed and report.culprit is None
    assert "UNATTRIBUTED" in report.summary()


def test_attribution_abstains_below_the_data_floor():
    detector = DamageDetector()
    for i in range(40):
        detector.observe(0.1 * (i % 5), {"D1_health": 1.0 - i * 0.01})
    accepted, diagnostics = detector.attribute("D1_health")
    assert not accepted and diagnostics["acceptance"] == "skipped"


def test_attribution_of_an_unknown_signal_is_skipped():
    detector = stream(lambda rng, i: rng.gauss(0, 0.05), lambda i: 1.0)
    accepted, diagnostics = detector.attribute("ghost")
    assert not accepted and diagnostics["acceptance"] == "skipped"


def test_signals_stay_aligned_with_the_residual_stream():
    """A signal that starts reporting late must still line up."""
    detector = DamageDetector()
    for i in range(5):
        detector.observe(0.1)
    for i in range(5):
        detector.observe(0.1, {"late": 1.0})
    assert len(detector.signals["late"]) == len(detector.residuals) == 10


def test_capacity_bounds_the_buffers_together():
    detector = DamageDetector(capacity=50)
    for i in range(200):
        detector.observe(0.1, {"a": float(i)})
    assert len(detector.residuals) == 50
    assert len(detector.signals["a"]) == 50


def test_reset_clears_history():
    detector = stream(lambda rng, i: rng.gauss(0, 0.05), lambda i: 1.0)
    detector.reset()
    assert not detector.residuals and not detector.signals


# --- the world model this all rests on --------------------------------------

def test_world_model_stays_stable_as_position_grows():
    """Plain LMS diverges here; the normalised update must not.

    BumpyWorld's position accumulates without bound, and a fixed-rate LMS step
    is only stable relative to input power — a long run used to blow the weights
    up to ~1e190, silently corrupting every statistic downstream.
    """
    model = WorldModel()
    x = 0.0
    for step in range(2000):
        x += 0.5                       # position marches off to 1000
        action = (step % 7) / 7.0 - 0.5
        model.update(x, action, x + 0.4 * action)
    assert all(abs(w) < 100 for w in model.w)
    assert abs(model.b) < 100
    assert model.avg_error() < 1.0


def test_world_model_learns_the_right_coefficient():
    model = WorldModel()
    rng = random.Random(3)
    for _ in range(4000):
        x = rng.uniform(-5, 5)
        action = rng.uniform(-1, 1)
        model.update(x, action, 1.0 * x + 0.4 * action)
    assert model.w[0] == pytest.approx(1.0, abs=0.1)


# --- the agent's wiring -----------------------------------------------------

def test_agent_feeds_residuals_and_body_state_to_the_detector():
    from unified_playground import UnifiedAgent
    ari = UnifiedAgent()
    for _ in range(20):
        ari.run_experiment()
    assert len(ari.damage.residuals) == 20
    assert {f"{c.name}_health" for c in ari.components} <= set(ari.damage.signals)


def test_a_worn_actuator_actually_changes_the_dynamics():
    """Without a body in the loop the residual carries no information about it."""
    from unified_playground import UnifiedAgent
    ari = UnifiedAgent()
    assert ari.actuator_efficiency() == pytest.approx(1.0)
    for component in ari.components:
        if component.name == ari.ACTUATOR:
            component.health = 0.0
    assert ari.actuator_efficiency() < 0.5


def test_unattributed_detections_do_not_trigger_relearning():
    """The attribution gate is what makes a noisy detector safe to wire up.

    BumpyWorld's residual is non-stationary even with healthy hardware — the
    position wanders, so error magnitude drifts and the changepoint test fires.
    Requiring an attributed culprit before relearning is what keeps that false
    positive from resetting a perfectly good model.
    """
    from unified_playground import UnifiedAgent
    ari = UnifiedAgent()
    for _ in range(120):
        ari.run_experiment()
    report = ari.damage_scan()
    if report.detected and report.unattributed:
        assert ari.relearns == 0
    assert ari.relearns == 0 or report.culprit is not None
