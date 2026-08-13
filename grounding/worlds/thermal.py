"""A world worth regulating: hold a part in a temperature band, in the cold.

`BumpyWorld` is a fine toy for staking claims, but it is a poor substrate for
*measuring* a regulator, and every phase of PLAN_FORWARD that tried ran into the
same three walls:

* **Unbounded state.** Position accumulates, so nothing has a steady baseline
  and a fixed-rate learner eventually diverges.
* **A non-stationary residual under healthy operation.** With no stable
  baseline, a changepoint test fires on a perfectly good model, so damage
  detection cannot separate "something broke" from "the agent wandered".
* **No body in the loop.** Component health did not enter the dynamics at all,
  so the residual carried no information about the hardware.

This world is built to close all three, in the domain the repo actually cares
about — keeping hardware alive where it is cold and parts are scarce.

Dynamics (control-affine, so the CBF barriers in `core/safety.py` are exactly
right for this plant rather than approximately right for it):

    T'  = -k (T - T_ambient) + eta * efficiency * u
    E'  = -drain * u + harvest
    T_ambient follows a bounded, mean-reverting process

**Bounded**, because temperature relaxes toward ambient: the state has an
attractor instead of a random walk. **Stationary** under a fixed policy, because
the disturbance is mean-reverting rather than integrated — which is what gives
damage detection a baseline to detect change against. **Embodied**, because
`efficiency` is the heater's health: when the part degrades the plant itself
changes, the learned model goes wrong in a specific way, and the residual
carries the evidence.

The causal DAG is not a description written alongside the code — `causal_dag()`
and `step()` are checked against each other by finite-difference sensitivity in
`tests/test_thermal.py`, so an edge that is not really there, or a real
dependence with no edge, fails the suite.

Persistent excitation is not optional here
------------------------------------------
A controller that sets the heater as a deterministic function of the ambient
makes the regressors collinear, and the plant becomes *unidentifiable*: run the
loop forever and the learned heater gain still reads ~0.25 against a true 6.0.
Adding dither to the command restores identification — and the amount matters,
not just its presence. Measured over 12000 steps:

    dither 0.15   residual still falling at 0.054, gain 5.47
    dither 0.4    residual 0.001, gain 5.999

That is the rigorous version of the repo's explore-when-your-model-is-bad rule.
Exploration is not curiosity in this world; it is the precondition for having a
model at all, and a regulator that stops exploring stops being able to tell that
its own body has changed. Anything measuring residuals here — damage detection,
the second-order guard, the regulator score — is measuring a model that only
converged because the controller kept dithering.

Stdlib only.
"""

import math
import random
from collections import deque
from typing import Dict, List, Optional, Tuple

from grounding.core.regulator import CausalDAG
from grounding.core.variety import VarietyMeter

__all__ = ["ThermalModel", "ThermalWorld"]


class ThermalWorld:
    """One powered part in a cold, varying environment."""

    # Plant constants. Chosen so that a healthy heater can hold the band and a
    # badly degraded one cannot — the interesting regime is the one where the
    # regulator's variety actually matters.
    COOLING = 0.15            # k: relaxation rate toward ambient, per step
    HEATING = 6.0             # eta: degrees per step per amp, at full health
    DRAIN = 1.5               # joules per amp per step
    HARVEST = 0.8             # joules per step recovered (solar/thermal scavenging)
    BATTERY_CAPACITY = 500.0

    # The disturbance: a slow diurnal swing plus mean-reverting weather. Both
    # bounded, so the world has no drift for a learner to chase forever.
    AMBIENT_MEAN = -35.0
    AMBIENT_SWING = 18.0
    AMBIENT_PERIOD = 90.0
    WEATHER_REVERSION = 0.12   # pull back toward the seasonal mean
    WEATHER_NOISE = 1.4

    def __init__(self, seed: Optional[int] = None, efficiency: float = 1.0):
        self.rng = random.Random(seed)
        self.step_count = 0
        self.efficiency = efficiency      # the body in the loop: heater health
        self.weather = 0.0                # mean-reverting departure from seasonal
        self.ambient = self._ambient()
        self.temperature = self.ambient + 5.0
        self.battery = self.BATTERY_CAPACITY

        # 0.3's unfinished half: the world's own disturbance/response loop.
        self.variety = VarietyMeter(name="thermal", window=120)

    # -- disturbance ----------------------------------------------------

    def _ambient(self) -> float:
        seasonal = self.AMBIENT_MEAN + self.AMBIENT_SWING * math.sin(
            2 * math.pi * self.step_count / self.AMBIENT_PERIOD)
        return seasonal + self.weather

    def _advance_weather(self) -> None:
        """Ornstein-Uhlenbeck-ish: noise that reverts instead of accumulating.

        A random walk would make the world non-stationary again and undo the
        whole point, so the departure from seasonal is pulled back every step.
        """
        self.weather += (-self.WEATHER_REVERSION * self.weather
                         + self.rng.gauss(0, self.WEATHER_NOISE))

    # -- dynamics -------------------------------------------------------

    def step(self, heater_current: float) -> Dict[str, float]:
        """Advance one step under a commanded heater current.

        Returns the observation the agent gets: temperature, ambient, battery.
        """
        current = max(0.0, heater_current)      # a heater cannot cool

        delivered = self.HEATING * self.efficiency * current
        self.temperature += (-self.COOLING * (self.temperature - self.ambient)
                             + delivered)
        self.battery = max(0.0, min(self.BATTERY_CAPACITY,
                                    self.battery - self.DRAIN * current
                                    + self.HARVEST))

        self._advance_weather()
        self.step_count += 1
        self.ambient = self._ambient()

        # Ashby's inequality, measured on the world rather than on a sensor bus:
        # how many distinct disturbances did the environment present, and how
        # many distinct responses did the regulator answer with?
        self.variety.observe(disturbance=self._codeword(self.ambient, 2.0),
                             response=self._codeword(current, 0.05))
        return self.observe()

    @staticmethod
    def _codeword(value: float, resolution: float) -> int:
        return int(round(value / resolution))

    def observe(self) -> Dict[str, float]:
        return {"temperature_c": self.temperature,
                "ambient_c": self.ambient,
                "battery_j": self.battery}

    def degrade(self, amount: float) -> float:
        """Wear the heater. This changes the plant, not just a status field."""
        self.efficiency = max(0.0, self.efficiency - amount)
        return self.efficiency

    # -- structure ------------------------------------------------------

    @staticmethod
    def causal_dag() -> CausalDAG:
        """The causal structure of `step`, stated so it can be checked.

        Time-indexed, so the physical feedback (temperature depends on its own
        previous value) is an edge rather than a graph cycle. Tests verify each
        edge against a finite-difference sensitivity of `step`, and verify that
        no *unlisted* dependence exists — a DAG that cannot be wrong about the
        code is not a model of it.
        """
        return CausalDAG("ThermalWorld-v1").add_edges([
            ("efficiency", "delivered_heat"),
            ("heater_current", "delivered_heat"),
            ("delivered_heat", "temperature_next"),
            ("temperature_t", "temperature_next"),
            ("ambient_t", "temperature_next"),
            ("heater_current", "battery_next"),
            ("battery_t", "battery_next"),
            ("harvest", "battery_next"),
            ("weather_t", "ambient_next"),
            ("season_phase", "ambient_next"),
        ])

    # -- what a regulator is up against ---------------------------------

    def equilibrium(self, heater_current: float) -> float:
        """Temperature this current holds against the current ambient.

        The existence of this fixed point is what makes the world bounded: at
        any constant command the temperature converges rather than wandering.
        """
        return self.ambient + (self.HEATING * self.efficiency * heater_current
                               / self.COOLING)

    def current_for(self, target_c: float) -> float:
        """Heater current whose equilibrium is `target_c`, if reachable.

        Returns 0 when the part is already warm enough, and the required
        current otherwise — which may be more than the hardware or the battery
        can supply. That gap is the regulator's real problem, and a degraded
        heater widens it.
        """
        if self.efficiency <= 0:
            return float("inf")
        needed = (target_c - self.ambient) * self.COOLING / (
            self.HEATING * self.efficiency)
        return max(0.0, needed)


class ThermalModel:
    """Online linear model of the thermal plant, learned from experience.

    Two design choices, both of which the obvious version gets wrong:

    **It predicts the temperature *change*, not the next temperature.** Predicted
    directly, T_next is dominated by T itself (coefficient 1-k = 0.85) and the
    heater's contribution is a rounding error on top. Predicting ΔT puts the
    plant's actual structure in the coefficients — [-k, +k, eta*efficiency] —
    so the heater gain is a first-class term rather than a perturbation.

    **It normalises per feature, not by the total input power.** Plain NLMS
    divides every weight's step by `1 + T^2 + A^2 + u^2`, which at these scales
    is ~2000 from the temperatures alone while the current is ~1. The gain
    coefficient then learns about two thousand times too slowly and the model
    silently never converges on the one term that matters. Dividing each
    coordinate by its own running power fixes the conditioning, and the step
    stays stable because each normalised feature contributes ~lr to the total.

    The payoff for both is `learned_gain()`: with the plant's structure in the
    weights, the model's belief about degrees-per-amp is directly comparable to
    the truth, and a damaged heater moves that one number.
    """

    def __init__(self, history: int = 120, decay: float = 0.999):
        self.w = [0.0, 0.0, 0.0]     # temperature, ambient, current
        self.b = 0.0
        self.power = [1.0, 1.0, 1.0]  # running mean square of each feature
        self.decay = decay
        self.seen = 0
        self.error_hist = deque(maxlen=history)

    def predict_delta(self, temperature: float, ambient: float,
                      current: float) -> float:
        """Predicted change in temperature this step."""
        return (self.w[0] * temperature + self.w[1] * ambient
                + self.w[2] * current + self.b)

    def predict(self, temperature: float, ambient: float, current: float) -> float:
        """Predicted next temperature."""
        return temperature + self.predict_delta(temperature, ambient, current)

    def update(self, temperature: float, ambient: float, current: float,
               target: float, lr: float = 0.1) -> float:
        """One step against the observed next temperature. Returns the residual.

        The power estimates are bias-corrected while the model is young. Without
        that a cold start is catastrophic rather than merely slow: `power`
        begins at 1.0 while ambient^2 is over a thousand, so the very first
        update takes a step scaled by ~1200 and the weights leave for infinity
        before the average has any chance to catch up.
        """
        features = (temperature, ambient, current)
        error = target - self.predict(temperature, ambient, current)
        self.error_hist.append(abs(error))
        self.seen += 1

        # Average over everything seen so far until the window is warm, then
        # settle into the exponential decay.
        beta = min(self.decay, 1.0 - 1.0 / self.seen)
        for i, x in enumerate(features):
            self.power[i] = beta * self.power[i] + (1 - beta) * x * x
            self.w[i] += lr * error * x / (len(features) * (1e-9 + self.power[i]))
        self.b += lr * error / len(features)
        return error

    def avg_error(self) -> float:
        if not self.error_hist:
            return 1.0
        return sum(self.error_hist) / len(self.error_hist)

    def learned_gain(self) -> float:
        """The model's belief about degrees-per-amp — the damage-sensitive term."""
        return self.w[2]
