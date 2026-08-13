"""ThermalWorld: a world built to be measurable, and the proof that it is."""

import random
import statistics as st

import pytest

from grounding.core.damage import DamageDetector
from grounding.core.regulator import check_homomorphism
from grounding.core.safety import SafetyFilter, battery_barrier, thermal_barriers
from grounding.worlds.thermal import ThermalModel, ThermalWorld


def drive(world, model=None, steps=500, target=-20.0, dither=0.4, seed=0,
          detector=None, observe_from=0):
    """Run a closed loop with dither. Returns the residuals it produced."""
    rng = random.Random(seed)
    residuals = []
    for step in range(steps):
        current = max(0.0, min(1.2, world.current_for(target)
                               + rng.uniform(-dither, dither)))
        temperature, ambient = world.temperature, world.ambient
        world.step(current)
        if model is not None:
            error = model.update(temperature, ambient, current, world.temperature)
            residuals.append(error)
            if detector is not None and step >= observe_from:
                detector.observe(error, {"heater_efficiency": world.efficiency,
                                         "battery": world.battery})
    return residuals


# --- the three walls BumpyWorld could not clear -----------------------------

def test_state_is_bounded():
    """An attractor, not a random walk: temperature relaxes toward ambient."""
    world = ThermalWorld(seed=1)
    temperatures = []
    for _ in range(3000):
        world.step(0.5)
        temperatures.append(world.temperature)
    assert min(temperatures) > -80 and max(temperatures) < 40
    assert 0 <= world.battery <= world.BATTERY_CAPACITY


def test_the_disturbance_reverts_instead_of_accumulating():
    world = ThermalWorld(seed=2)
    ambients = []
    for _ in range(4000):
        world.step(0.3)
        ambients.append(world.ambient)
    first, last = ambients[:800], ambients[-800:]
    # Mean-reverting weather: the same distribution at the start and the end.
    assert st.mean(first) == pytest.approx(st.mean(last), abs=6.0)
    assert st.pstdev(first) == pytest.approx(st.pstdev(last), rel=0.5)


def test_a_healthy_settled_model_has_a_stationary_residual():
    """This is what damage detection needs and BumpyWorld never provided."""
    world, model = ThermalWorld(seed=3), ThermalModel()
    drive(world, model, steps=8000)                    # settle (see excitation note)
    residuals = [abs(e) for e in drive(world, model, steps=800, seed=7)]
    first, last = residuals[:300], residuals[-300:]
    assert st.mean(first) == pytest.approx(st.mean(last), abs=0.02)
    assert st.mean(last) < 0.05


def test_the_body_is_in_the_loop():
    """Efficiency is a plant parameter, not a status field."""
    healthy, worn = ThermalWorld(seed=4), ThermalWorld(seed=4, efficiency=0.3)
    for _ in range(60):
        healthy.step(1.0)
        worn.step(1.0)
    assert healthy.temperature > worn.temperature
    assert worn.current_for(-20.0) > healthy.current_for(-20.0)


# --- the model has a known right answer -------------------------------------

def test_model_converges_to_the_true_plant():
    world, model = ThermalWorld(seed=5), ThermalModel()
    rng = random.Random(0)
    for _ in range(6000):
        current = rng.uniform(0, 1.2)
        temperature, ambient = world.temperature, world.ambient
        world.step(current)
        model.update(temperature, ambient, current, world.temperature)
    assert model.w[0] == pytest.approx(-world.COOLING, abs=0.02)
    assert model.w[1] == pytest.approx(world.COOLING, abs=0.02)
    assert model.w[2] == pytest.approx(world.HEATING, abs=0.1)
    assert model.avg_error() < 0.1


@pytest.mark.parametrize("efficiency", [1.0, 0.5, 0.2])
def test_learned_gain_tracks_the_damaged_heater(efficiency):
    """The damage-sensitive parameter is identifiable, so attribution can work."""
    world = ThermalWorld(seed=6, efficiency=efficiency)
    model = ThermalModel()
    rng = random.Random(0)
    for _ in range(6000):
        current = rng.uniform(0, 1.2)
        temperature, ambient = world.temperature, world.ambient
        world.step(current)
        model.update(temperature, ambient, current, world.temperature)
    assert model.learned_gain() == pytest.approx(
        world.HEATING * efficiency, abs=0.1)


def test_cold_start_does_not_blow_up_the_model():
    """Ambient^2 is ~1200 while the power estimates start at 1."""
    world, model = ThermalWorld(seed=7), ThermalModel()
    drive(world, model, steps=50)
    assert all(abs(w) < 100 for w in model.w)


# --- the causal DAG is checked against the code, not asserted beside it ------

def test_declared_causal_edges_are_real_dependencies():
    """Finite-difference sensitivity: perturb a cause, see the effect move.

    A DAG that cannot be wrong about the code is not a model of it, so every
    declared edge into `temperature_next` and `battery_next` has to show up as
    an actual dependence of `step`.
    """
    def next_state(temperature, ambient, current, efficiency=1.0, battery=400.0):
        world = ThermalWorld(seed=0, efficiency=efficiency)
        world.temperature, world.weather, world.battery = temperature, 0.0, battery
        world.ambient = ambient
        world.step(current)
        return world.temperature, world.battery

    base_t, base_e = next_state(-20.0, -40.0, 0.5)

    # temperature_t -> temperature_next
    assert next_state(-10.0, -40.0, 0.5)[0] != base_t
    # ambient_t -> temperature_next
    assert next_state(-20.0, -50.0, 0.5)[0] != base_t
    # heater_current -> temperature_next and -> battery_next
    warmer_t, drained_e = next_state(-20.0, -40.0, 1.0)
    assert warmer_t > base_t and drained_e < base_e
    # efficiency -> delivered_heat -> temperature_next
    assert next_state(-20.0, -40.0, 0.5, efficiency=0.2)[0] < base_t
    # battery_t -> battery_next
    assert next_state(-20.0, -40.0, 0.5, battery=200.0)[1] != base_e


def test_no_undeclared_dependence_of_temperature_on_battery():
    """The other half: a dependence with no edge would also be a wrong DAG."""
    def temperature_after(battery):
        world = ThermalWorld(seed=0)
        world.temperature, world.weather, world.battery = -20.0, 0.0, battery
        world.ambient = -40.0
        world.step(0.5)
        return world.temperature

    assert temperature_after(500.0) == temperature_after(100.0)
    dag = ThermalWorld.causal_dag()
    assert ("battery_t", "temperature_next") not in dag.edges


def test_causal_dag_is_acyclic_and_names_its_roots():
    dag = ThermalWorld.causal_dag()
    assert not dag.has_cycle()
    assert {"efficiency", "heater_current", "harvest"} <= dag.roots()


def test_a_model_that_maps_the_world_is_a_homomorphism():
    """The good-regulator check has something real to measure here."""
    world = ThermalWorld.causal_dag()
    from grounding.core.regulator import CausalDAG
    model = CausalDAG("thermal model").add_edges([
        ("heat", "temp_next"), ("temp", "temp_next"), ("ambient", "temp_next"),
        ("heater", "heat"), ("efficiency", "heat"),
        ("heater", "battery_next"), ("battery", "battery_next"),
        ("harvest", "battery_next"),
        ("weather", "ambient_next"), ("phase", "ambient_next"),
    ])
    mapping = {
        "efficiency": "efficiency", "heater_current": "heater",
        "delivered_heat": "heat", "temperature_t": "temp",
        "ambient_t": "ambient", "temperature_next": "temp_next",
        "battery_t": "battery", "battery_next": "battery_next",
        "harvest": "harvest", "weather_t": "weather",
        "season_phase": "phase", "ambient_next": "ambient_next",
    }
    result = check_homomorphism(world, model, mapping)
    assert result["is_homomorphism"]
    assert result["fidelity"] == 1.0


# --- what the world unlocks -------------------------------------------------

def test_persistent_excitation_is_required_to_identify_the_plant():
    """A controller that is a deterministic function of the state hides the plant.

    Without dither the current is an exact function of ambient, the regressors
    are collinear, and the heater gain is unidentifiable however long the agent
    runs. This is the rigorous version of the repo's explore-when-uncertain
    rule: exploration is not curiosity here, it is the precondition for having
    a model at all.
    """
    def learned_gain(dither):
        world, model = ThermalWorld(seed=8), ThermalModel()
        drive(world, model, steps=6000, dither=dither, seed=1)
        return model.learned_gain()

    assert learned_gain(0.0) < 2.0                       # nowhere near 6.0
    assert learned_gain(0.4) == pytest.approx(6.0, abs=0.5)
    # More excitation is not just faster, it is the difference between
    # identifying the plant and never identifying it.
    assert learned_gain(0.4) > learned_gain(0.1)


def test_damage_is_detectable_against_a_stationary_baseline():
    """One scan on a settled model, with the buffer spanning the change."""
    world, model = ThermalWorld(seed=9), ThermalModel()
    drive(world, model, steps=8000, seed=2)              # settle
    # A converged model here sits at |residual| ~0.009 and damage takes it to
    # ~0.25, so anything past 0.05 is a real change rather than a wobble.
    detector = DamageDetector(min_shift=0.05)
    drive(world, model, steps=150, seed=3, detector=detector)
    world.efficiency = 0.3                               # heater fails
    drive(world, model, steps=150, seed=4, detector=detector)
    report = detector.scan()
    assert report.detected
    # And named: the level-based test separates the residual across the two
    # efficiency regimes cleanly, which is what the relearn gate needs.
    assert report.culprit == "heater_efficiency"
    assert report.candidates["heater_efficiency"]["test"] == "two-sample"
    low, high = report.candidates["heater_efficiency"]["mean_residual"]
    assert high > low * 5


def test_a_healthy_world_does_not_look_damaged():
    world, model = ThermalWorld(seed=10), ThermalModel()
    drive(world, model, steps=8000, seed=2)
    detector = DamageDetector(min_shift=0.05)
    drive(world, model, steps=300, seed=5, detector=detector)
    assert not detector.scan().detected


def test_significance_without_effect_size_is_not_a_change():
    """A converged model makes meaningless wobbles statistically overwhelming."""
    world, model = ThermalWorld(seed=10), ThermalModel()
    drive(world, model, steps=8000, seed=2)
    naive, guarded = DamageDetector(), DamageDetector(min_shift=0.05)
    for detector in (naive, guarded):
        drive(ThermalWorld(seed=10), model, steps=300, seed=5, detector=detector)
    assert naive.scan().effect_size > naive.EFFECT_THRESHOLD   # significant...
    assert not guarded.scan().detected                          # ...and trivial
    assert "below the" in guarded.scan().reason


def test_the_safety_filter_is_exactly_right_for_this_plant():
    """The barriers' Lie derivatives match these dynamics rather than approximating."""
    world = ThermalWorld(seed=11)
    filt = SafetyFilter(
        thermal_barriers(t_max=10.0, t_min=-30.0,
                         cooling=world.COOLING, heating=world.HEATING)
        + [battery_barrier(100.0, world.DRAIN)])
    state = {"temperature_c": -29.0, "ambient_c": -60.0,
             "battery_j": world.BATTERY_CAPACITY}
    decision = filt.filter(state, [0.0])
    assert decision.intervened and decision.u[0] > 0     # freezing: heat
    assert decision.feasible


def test_the_world_measures_its_own_requisite_variety():
    """0.3's unfinished half: the disturbance/response loop of a world."""
    world = ThermalWorld(seed=12)
    rng = random.Random(0)
    for _ in range(300):
        world.step(max(0.0, world.current_for(-20.0) + rng.uniform(-0.1, 0.1)))
    status = world.variety.status()
    # The meter keeps a window, so it reports the recent regime, not all history.
    assert status["n_disturbances"] == status["n_responses"] == world.variety.window
    assert status["disturbance_variety"] > 0
    assert status["response_variety"] > 0
