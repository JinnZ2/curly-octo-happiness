"""Phase 1: the VSM channels, teachback claims, and the second-order guard."""

import pytest

from grounding.core.mentor import TeachbackMentor, overlap_score
from grounding.core.vsm import (
    AlgedonicSignal,
    SecondOrderGuard,
    Signal,
    ViableSystem,
)


def build_system(**kwargs):
    system = ViableSystem("test", **kwargs)
    system.register(1, "unit-a").register(2, "trust").register(5, "mentor")
    return system


# --- 1.1 / 1.2: the algedonic channel really bypasses ----------------------

def test_ordinary_signal_walks_the_hierarchy():
    system = build_system()
    system.mediator(2, lambda sig: True)
    system.mediator(3, lambda sig: True)
    delivered = []
    system.on_policy(delivered.append)

    signal = system.route(Signal(source="unit-a", message="routine"))
    assert signal.delivered
    assert signal.path == ["S1 unit-a", "S2 coordination", "S3 control", "S5 policy"]
    assert not signal.bypassed_mediation
    assert delivered == [signal]


def test_algedonic_signal_bypasses_mediation():
    system = build_system()
    # Mediators that would drop everything: the algedonic signal never meets them.
    seen_by_mediators = []
    system.mediator(2, lambda sig: seen_by_mediators.append(sig) or False)
    system.mediator(3, lambda sig: seen_by_mediators.append(sig) or False)
    delivered = []
    system.on_policy(delivered.append)

    pain = system.raise_algedonic(
        AlgedonicSignal(source="unit-a", message="thermal runaway"))
    assert pain.delivered and pain.bypassed_mediation
    assert pain.path == ["S1 unit-a", "S5 policy (algedonic)"]
    assert delivered == [pain]
    assert seen_by_mediators == []

    # ...while an ordinary signal is stopped dead by the same mediators.
    routine = system.route(Signal(source="unit-a", message="routine"))
    assert not routine.delivered
    assert routine.attenuated_by == ["S2 coordination"]


def test_algedonic_surfaces_through_recursion():
    """Every viable system contains viable systems; pain climbs all of them."""
    parent = ViableSystem("parent")
    child = ViableSystem("child")
    parent.contains(child)
    at_parent, at_child = [], []
    parent.on_policy(at_parent.append)
    child.on_policy(at_child.append)

    child.raise_algedonic(AlgedonicSignal(source="deep-unit", message="pain"))
    assert len(at_child) == 1 and len(at_parent) == 1
    assert at_parent[0] is at_child[0]
    assert len(parent.algedonic_log) == 1


def test_severity_must_be_pain_or_pleasure():
    with pytest.raises(ValueError):
        AlgedonicSignal(source="u", message="m", severity="mild")
    assert AlgedonicSignal(source="u", message="m", severity="pleasure").severity == "pleasure"


def test_saturation_is_itself_a_diagnosis():
    """An alarm channel that always fires has stopped being an alarm."""
    system = build_system(saturation_rate=0.25)
    system.mediator(2, lambda sig: True)
    system.mediator(3, lambda sig: True)

    for _ in range(8):
        system.route(Signal(source="unit-a", message="routine"))
    assert system.algedonic_load() == 0.0
    assert not system.saturated()

    for _ in range(6):
        system.raise_algedonic(AlgedonicSignal(source="unit-a", message="pain"))
    assert system.algedonic_load() > 0.25
    assert system.saturated()
    assert "SATURATED" in system.report()


def test_register_and_mediator_reject_bad_systems():
    system = ViableSystem("s")
    with pytest.raises(ValueError):
        system.register(6, "nope")
    with pytest.raises(ValueError):
        system.mediator(5, lambda sig: True)   # S5 decides, it does not mediate


# --- 1.3: teachback claims -------------------------------------------------

EXPLANATION = ("A regulator needs at least as many distinct responses as the "
               "environment has distinct disturbances")


def test_overlap_score_endpoints():
    assert overlap_score(EXPLANATION, EXPLANATION) == 1.0
    assert overlap_score(EXPLANATION, "unrelated words entirely") == 0.0
    assert overlap_score("", "anything") == 0.0


def test_teachback_needs_an_explanation_first():
    mentor = TeachbackMentor()
    message, claim = mentor.teachback("variety", "something")
    assert claim is None and "Nothing explained" in message


def test_reciting_the_explanation_back_fails_the_automatic_check():
    mentor = TeachbackMentor()
    mentor.explain("variety", EXPLANATION)
    message, claim = mentor.teachback("variety", EXPLANATION)
    assert "repeated back" in message
    assert claim.failed == 1 and claim.passed == 0


def test_low_overlap_abstains_rather_than_judging():
    """A lexical measure cannot separate 'missed it' from 'said it in synonyms'."""
    mentor = TeachbackMentor()
    mentor.explain("variety", EXPLANATION)
    message, claim = mentor.teachback(
        "variety", "you need enough different moves for whatever shows up")
    assert "too low for me to judge" in message
    assert (claim.passed, claim.failed) == (0, 0)   # nothing staked either way


def test_reconstruction_in_own_words_is_learned_after_confirmation():
    mentor = TeachbackMentor()
    mentor.explain("variety", EXPLANATION)
    mentor.teachback("variety",
                     "a regulator with fewer responses than the environment has "
                     "disturbances cannot hold anything steady")
    assert not mentor.learned("variety")     # one automatic pass is not learning
    mentor.confirm("variety")
    mentor.confirm("variety")
    assert mentor.learned("variety")
    assert "learned" in mentor.status()


def test_correction_is_evidence_against_and_replaces_the_explanation():
    mentor = TeachbackMentor()
    mentor.explain("variety", EXPLANATION)
    mentor.teachback("variety", "the regulator has responses and the environment "
                                "has disturbances of some distinct kind")
    before = mentor.claims["variety"].failed
    mentor.correct("variety", "Variety is counted in bits, not in moves")
    assert mentor.claims["variety"].failed == before + 1
    assert mentor.explanations["variety"] == "Variety is counted in bits, not in moves"
    assert not mentor.learned("variety")


def test_serial_rewording_is_a_counted_escape_hatch():
    """Retrying the wording until something sticks must not read as learning."""
    mentor = TeachbackMentor()
    mentor.explain("x", "the alarm bypasses the coordination layer entirely")
    for wording in ("alarms skip something", "the alarm skips a layer",
                    "an alarm goes past coordination", "the alarm bypasses coordination"):
        mentor.teachback("x", wording)
    claim = mentor.claims["x"]
    assert claim.reformulation_count == 3
    assert claim.escape_hatch_suspected
    for _ in range(3):
        mentor.confirm("x")
    # The claim survives on its fourth wording; the concept is still not learned.
    assert claim.status == "survived"
    assert not mentor.learned("x")
    assert "escape hatch" in mentor.status()


def test_confirm_and_correct_without_teachback():
    mentor = TeachbackMentor()
    assert "No teachback" in mentor.confirm("ghost")
    assert "No teachback" in mentor.correct("ghost", "text")
    assert mentor.status() == "No concepts under discussion."


# --- 1.4: second-order guard ----------------------------------------------

def test_guard_is_quiet_when_self_model_matches_diagnostics():
    guard = SecondOrderGuard()
    for _ in range(5):
        assert guard.check(self_confidence=0.7, independent_error=0.3) == []
    assert "consistent" in guard.report()


def test_guard_flags_confidence_the_diagnostics_do_not_support():
    guard = SecondOrderGuard(tolerance=0.3)
    flags = guard.check(self_confidence=0.95, independent_error=0.8)
    assert any("overconfident" in f for f in flags)


def test_guard_flags_eigenvalue_drift():
    """Confidence climbing while independent error refuses to fall."""
    guard = SecondOrderGuard(tolerance=0.9, history=4)   # tolerance off, drift only
    flags = []
    for confidence in (0.50, 0.60, 0.70, 0.80):
        flags = guard.check(self_confidence=confidence, independent_error=0.5)
    assert any("eigenvalue drift" in f for f in flags)
    assert "⚠" in guard.report()


def test_guard_does_not_call_honest_improvement_drift():
    guard = SecondOrderGuard(tolerance=0.9, history=4)
    flags = []
    for confidence, error in ((0.50, 0.50), (0.60, 0.40), (0.70, 0.30), (0.80, 0.20)):
        flags = guard.check(self_confidence=confidence, independent_error=error)
    assert flags == []   # confidence rose because the error actually fell


def test_guard_reports_nothing_before_it_observes():
    guard = SecondOrderGuard()
    assert guard.check() == []
    assert "nothing observed" in guard.report()


# --- the agent's wiring ----------------------------------------------------

def agent():
    from unified_playground import UnifiedAgent
    return UnifiedAgent()


def test_agent_maps_its_parts_onto_the_five_systems():
    system = agent().vsm
    assert any("component:" in u for u in system.units[1])
    assert system.units[2] and system.units[3] and system.units[4] and system.units[5]
    assert "S3*" in " ".join(system.units[3])   # the audit channel is named
    assert "S5 policy" in system.report()


def test_healthy_hardware_reports_routinely_and_is_damped_at_s2():
    ari = agent()
    assert ari.hardware_scan() == []            # nothing in pain
    assert ari.pain == []
    routine = ari.vsm.log
    assert routine and all(s.attenuated_by == ["S2 coordination"] for s in routine)
    assert ari.vsm.algedonic_load() == 0.0


def test_failing_hardware_reaches_policy_by_itself():
    """1.2: the quarantine override no longer waits for someone to run `check`."""
    ari = agent()
    for _ in range(60):
        ari.degrade_hardware(0.3)
    raised = ari.hardware_scan()

    assert raised, "flatlined components should raise pain"
    assert all(s.bypassed_mediation for s in raised)
    assert ari.pain == raised
    assert "Algedonic" in ari.journal.list_unknowns()
    assert "bypassed mediation: True" in ari.handle_mentor("pain")


def test_self_model_check_waits_for_independent_evidence():
    ari = agent()
    assert ari.self_model_check() == []          # no world-model history yet
    for _ in range(6):
        ari.run_experiment()
    ari.self_model_check()
    assert ari.guard.observations                # now it has something to compare
