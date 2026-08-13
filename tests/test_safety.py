"""Phase 3.1/3.2: control-barrier safety filter and the fallback catalog."""

import pytest

from grounding.core.safety import (
    Barrier,
    Fallback,
    FallbackCatalog,
    SafetyFilter,
    battery_barrier,
    project_onto_halfspace,
    safety_claim,
    solve_min_norm,
    thermal_barriers,
)

WARM = {"temperature_c": 80.0, "ambient_c": 25.0, "battery_j": 500.0}


def standard_filter(t_max=85.0, t_min=-40.0, cooling=0.05, heating=8.0,
                    e_min=100.0, drain=2.0):
    return SafetyFilter(thermal_barriers(t_max, t_min, cooling, heating)
                        + [battery_barrier(e_min, drain)])


# --- the projection ---------------------------------------------------------

def test_projection_leaves_satisfied_points_alone():
    assert project_onto_halfspace([1.0, 2.0], [1.0, 0.0], 0.5) == [1.0, 2.0]


def test_projection_moves_the_shortest_distance():
    # a . u >= b with a = (1, 0), b = 3: only the first coordinate must move.
    assert project_onto_halfspace([1.0, 2.0], [1.0, 0.0], 3.0) == pytest.approx([3.0, 2.0])


def test_projection_handles_a_control_with_no_leverage():
    assert project_onto_halfspace([1.0], [0.0], 5.0) == [1.0]


def test_min_norm_with_no_constraints_is_the_nominal():
    u, converged = solve_min_norm([0.7], [])
    assert u == [0.7] and converged


def test_min_norm_satisfies_compatible_constraints():
    # u >= 1 and -u >= -3  (i.e. 1 <= u <= 3), nominal 0 -> nearest is 1.
    u, converged = solve_min_norm([0.0], [([1.0], 1.0), ([-1.0], -3.0)])
    assert converged and u[0] == pytest.approx(1.0, abs=1e-6)


# --- the filter -------------------------------------------------------------

def test_minimal_intervention_passes_safe_commands_through():
    decision = standard_filter().filter(WARM, [0.0])
    assert not decision.intervened
    assert decision.u == [0.0]
    assert decision.feasible and not decision.violated


def test_filter_clips_a_command_that_would_breach_the_ceiling():
    decision = standard_filter().filter(WARM, [1.0])
    assert decision.intervened
    assert decision.u[0] < 1.0
    assert "thermal_ceiling" in decision.active
    assert "overrode" in decision.report()


def test_cold_ambient_makes_the_floor_demand_current():
    """The plan's cold-environment case: the floor pushes where the ceiling pulls."""
    freezing = {"temperature_c": -39.5, "ambient_c": -70.0, "battery_j": 500.0}
    decision = standard_filter().filter(freezing, [0.0])
    assert decision.intervened
    assert decision.u[0] > 0          # heat, do not coast
    assert "thermal_floor" in decision.active


def test_a_comfortable_margin_permits_coasting():
    """A barrier is not a setpoint: it constrains the *rate*, not the state.

    Two degrees above the floor while cooling slowly, the CBF condition allows h
    to decay toward zero without crossing it, so the filter does not intervene.
    Demanding current here would be a thermostat, not a barrier.
    """
    cool = {"temperature_c": -38.0, "ambient_c": -70.0, "battery_j": 500.0}
    decision = standard_filter().filter(cool, [0.0])
    assert not decision.intervened
    assert decision.margins["thermal_floor"] > 0


def test_violated_barriers_are_reported_not_hidden():
    breached = {"temperature_c": -50.0, "ambient_c": -70.0, "battery_j": 500.0}
    filt = standard_filter()
    assert not filt.safe(breached)
    decision = filt.filter(breached, [0.0])
    assert "thermal_floor" in decision.violated
    assert "VIOLATED" in decision.report()


def test_incompatible_barriers_report_infeasible_rather_than_guessing():
    """Freezing, with no battery to spare: there is no safe control at all."""
    squeeze = {"temperature_c": -39.5, "ambient_c": -80.0, "battery_j": 100.2}
    decision = standard_filter(t_max=-20.0, t_min=-40.0, cooling=0.5,
                               heating=1.0, drain=5.0).filter(squeeze, [0.0])
    assert not decision.feasible
    assert "cannot be satisfied together" in decision.report()


def test_alpha_controls_how_close_to_the_boundary_the_filter_allows():
    near = {"temperature_c": 84.0, "ambient_c": 25.0, "battery_j": 500.0}
    cautious = SafetyFilter(thermal_barriers(85.0, -40.0, 0.05, 8.0, alpha=0.1))
    permissive = SafetyFilter(thermal_barriers(85.0, -40.0, 0.05, 8.0, alpha=5.0))
    assert (cautious.filter(near, [1.0]).u[0]
            < permissive.filter(near, [1.0]).u[0])


# --- safe sets as claims ----------------------------------------------------

def test_safety_claim_is_machine_checkable_and_refuted_by_observation():
    barrier = thermal_barriers(85.0, -40.0, 0.05, 8.0)[0]
    claim = safety_claim(barrier, scope={"component": "D1"})
    assert claim.falsifiability == "machine-checkable"

    claim.evaluate({"h": barrier.margin(WARM)})      # inside the safe set
    assert claim.passed == 1 and claim.failed == 0

    hot = {"temperature_c": 99.0, "ambient_c": 25.0, "battery_j": 500.0}
    for _ in range(3):
        claim.evaluate({"h": barrier.margin(hot)})
    assert claim.status == "falsified"


# --- the fallback catalog ---------------------------------------------------

def make_catalog():
    catalog = FallbackCatalog()
    catalog.register("diode", Fallback(
        failure_mode="short_circuit",
        capability="conductor",
        effectiveness=9.0,
        envelope={"temperature_c_max": 45.0, "battery_j_min": 100.0},
        barriers=lambda: thermal_barriers(45.0, -40.0, 0.02, 8.0)
                         + [battery_barrier(100.0, 4.0)],
    ))
    catalog.register("default", Fallback(
        failure_mode="drift", capability="sensor", effectiveness=5.5,
        envelope={}, barriers=lambda: [],
    ))
    return catalog


def test_unknown_failure_modes_are_refused_not_guessed():
    result = make_catalog().select("diode", "vaporised", WARM)
    assert not result["available"]
    assert result["reason"] == "no catalogued fallback"


def test_component_types_fall_back_to_the_default_entry():
    result = make_catalog().select("resistor", "drift", WARM)
    assert result["available"] and result["capability"] == "sensor"


def test_the_same_fallback_is_offered_or_refused_by_state():
    """Provably safe repurposing: the envelope is recomputed, not inherited."""
    catalog = make_catalog()
    cool = {"temperature_c": 20.0, "ambient_c": 20.0, "battery_j": 500.0}
    hot = {"temperature_c": 60.0, "ambient_c": 55.0, "battery_j": 500.0}

    offered = catalog.select("diode", "short_circuit", cool)
    assert offered["available"] and offered["capability"] == "conductor"

    refused = catalog.select("diode", "short_circuit", hot)
    assert not refused["available"]
    assert refused["reason"] == "outside recomputed envelope"
    assert refused["breaches"] == ["temperature_c=60.00 > 45.00"]


def test_a_flat_battery_refuses_the_fallback_whatever_the_temperature():
    flat = {"temperature_c": 20.0, "ambient_c": 20.0, "battery_j": 50.0}
    result = make_catalog().select("diode", "short_circuit", flat)
    assert not result["available"]
    assert "battery_j=50.00 < 100.00" in result["breaches"]


def test_catalog_report_renders_envelopes():
    text = make_catalog().report(WARM)
    assert "conductor" in text and "envelope" in text


# --- the agent's wiring -----------------------------------------------------

def agent():
    from unified_playground import UnifiedAgent
    return UnifiedAgent()


def test_degraded_parts_get_a_smaller_safe_set():
    ari = agent()
    healthy = ari.degraded_plant(1.0)
    worn = ari.degraded_plant(0.2)
    assert worn["t_max"] < healthy["t_max"]        # less thermal headroom
    assert worn["cooling"] < healthy["cooling"]    # sheds heat worse
    assert worn["drain"] > healthy["drain"]        # wastes more power


def test_safety_check_stakes_and_evaluates_a_claim_per_barrier():
    ari = agent()
    component, state, decision = ari.safety_check("D1")
    assert component is not None and decision.feasible
    assert {name for _, name in ari.safety_claims} == {
        "thermal_ceiling", "thermal_floor", "battery_reserve"}
    for claim in ari.safety_claims.values():
        assert claim.passed + claim.failed == 1


def test_repeated_safety_breaches_raise_pain_to_policy():
    """A falsified safety claim is exactly what the algedonic channel is for."""
    ari = agent()
    ari.ambient_c = -80.0
    ari.degrade_hardware(0.1)
    for _ in range(3):
        ari.safety_check("D1")
    assert any("safe set" in signal.message for signal in ari.pain)
    assert all(signal.bypassed_mediation for signal in ari.pain)


def test_cold_ambient_actually_cools_the_component():
    """Otherwise the thermal floor could never bind and the barrier is theatre."""
    ari = agent()
    ari.ambient_c = -60.0
    ari.degrade_hardware(0.01)
    assert ari.components[0].temp < 0


def test_unknown_component_is_reported():
    ari = agent()
    assert ari.safety_check("nope") == (None, None, None)
    assert ari.fallback_for("nope") is None
