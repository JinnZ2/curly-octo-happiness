"""Damage detection from prediction residuals: the body told the model it changed.

Lipson's result (Sci. Robotics 2022): a robot that keeps a model of its own
morphology notices damage as a *persistent mismatch* between what the model
predicted and what the body did, and recovers by relearning rather than by
being told what broke.

That is the same shape as hidden-node detection, pointed inward. In
`modules/hnd.py` the residual of a world model is scanned against exogenous
environmental series. Here the residual of the agent's own dynamics is scanned
against the agent's own *interoceptive* series — component health, temperature,
drift. The question changes from "what in the world am I not modelling?" to
"which part of me stopped behaving the way my model of me says it does?"

Two stages, deliberately separate:

**Detection** is a changepoint test on residual magnitude. Something changed;
this stage does not care what. Split the history at a candidate point and
compare the halves by effect size, so a noisy stream does not fire on drift.

**Localisation** asks which interoceptive signal explains the change, and reuses
the Phase 0 acceptance criterion rather than a fresh threshold: a signal counts
as the culprit only if conditioning the residual stream on it drops *both*
statistical complexity and entropy rate. Correlation is not attribution — a
signal that merely tracks the residual (every part ages at once) has to be
distinguishable from the one that explains it.

Localisation can fail while detection succeeds. That is a real state, not an
error: the model knows it is wrong and does not know why. It reports
`unattributed` rather than picking the best-correlated part, because naming an
innocent component is worse than admitting ignorance.

Stdlib only.
"""

from dataclasses import dataclass, field
from math import exp, inf, log
from statistics import mean, pstdev
from typing import Dict, List, Optional, Sequence, Tuple

from grounding.core.epsilon_machine import (
    equalized_history_length, reconstruct, symbolize)

__all__ = [
    "CusumAlarm",
    "DamageDetector",
    "DamageReport",
    "SequentialDamageDetector",
    "arl0_for",
    "decision_interval_for",
]


# ---------------------------------------------------------------------------
# Sequential monitoring: the right tool for looking repeatedly
# ---------------------------------------------------------------------------
#
# `DamageDetector.scan()` is a fixed-sample test. Run it once on a settled
# model it is sound; run it every step and false alarms accumulate, because
# repeated testing is not single testing and no per-test threshold fixes that.
#
# CUSUM (Page 1954) is built for exactly this. It accumulates evidence instead
# of re-testing, and Lorden's result makes it minimax optimal: among procedures
# meeting a false-alarm constraint, it minimises worst-case detection delay. The
# threshold is then calibrated to a *rate* rather than a per-look significance —
# which is what turns the choice from a convention into a quantity with units.

def arl0_for(decision_interval: float, reference: float = 0.5) -> float:
    """In-control average run length: observations per false alarm.

    Siegmund's approximation for a two-sided CUSUM. Reproduces the textbook
    pairing (reference 0.5, interval 5 -> ARL0 ~ 465) to within a percent.
    """
    b = decision_interval + 1.166
    drift = -reference
    one_sided = (exp(-2 * drift * b) + 2 * drift * b - 1) / (2 * drift * drift)
    return one_sided / 2.0


def decision_interval_for(arl0: float, reference: float = 0.5) -> float:
    """Invert `arl0_for`: what threshold buys this false-alarm rate?

    This is the parameter worth exposing. "One false alarm per 1000
    observations" is a statement an operator can hold an opinion about;
    "three sigma" is a statement about a distribution's tail that says nothing
    about how often the alarm will cry wolf on *their* stream.
    """
    if arl0 <= 1:
        raise ValueError("arl0 must exceed 1 observation")
    low, high = 0.01, 60.0
    for _ in range(200):
        middle = (low + high) / 2
        if arl0_for(middle, reference) < arl0:
            low = middle
        else:
            high = middle
    return (low + high) / 2


@dataclass
class CusumAlarm:
    """A sequential detection, with the evidence that accumulated to it."""

    fired: bool
    direction: str = ""              # "up" | "down"
    statistic: float = 0.0
    threshold: float = 0.0
    observations: int = 0
    since_reset: int = 0
    baseline_mean: float = 0.0
    baseline_sd: float = 0.0
    arl0: float = 0.0

    def summary(self) -> str:
        if not self.fired:
            return (f"No sequential alarm: S={self.statistic:.2f} of "
                    f"h={self.threshold:.2f} after {self.since_reset} "
                    f"observations")
        return (f"CUSUM alarm ({self.direction}): S={self.statistic:.2f} "
                f"crossed h={self.threshold:.2f} after {self.since_reset} "
                f"observations, at a designed rate of one false alarm per "
                f"{self.arl0:g}")


class SequentialDamageDetector:
    """Online residual monitor calibrated by false-alarm rate, not by sigma.

    Learns a baseline from the first `calibration` observations — which assumes
    the model has settled, and says so rather than pretending otherwise — then
    accumulates standardised deviations in both directions. Damage that lowers
    the residual is caught as readily as damage that raises it, which the
    one-sided form would miss.
    """

    def __init__(self, arl0: float = 1000.0, reference: float = 0.5,
                 calibration: int = 100):
        """
        Args:
            arl0: target observations per false alarm, in control. The whole
                point of the class: pick how often you are willing to be
                interrupted for nothing.
            reference: slack in baseline standard deviations. 0.5 is the
                conventional pairing and is efficient for shifts near 1 sd.
            calibration: observations used to learn the in-control baseline.
        """
        self.arl0 = arl0
        self.reference = reference
        self.calibration = calibration
        self.threshold = decision_interval_for(arl0, reference)

        self.baseline: List[float] = []
        self.baseline_mean = 0.0
        self.baseline_sd = 0.0
        self.upper = 0.0
        self.lower = 0.0
        self.observations = 0
        self.since_reset = 0

    @property
    def calibrated(self) -> bool:
        return len(self.baseline) >= self.calibration

    def observe(self, residual: float) -> CusumAlarm:
        """Feed one residual. Returns the alarm state after this observation."""
        value = abs(float(residual))
        self.observations += 1

        if not self.calibrated:
            self.baseline.append(value)
            if self.calibrated:
                self.baseline_mean = mean(self.baseline)
                self.baseline_sd = pstdev(self.baseline) or 1e-9
            return CusumAlarm(fired=False, threshold=self.threshold,
                              observations=self.observations,
                              arl0=self.arl0)

        self.since_reset += 1
        z = (value - self.baseline_mean) / self.baseline_sd
        self.upper = max(0.0, self.upper + z - self.reference)
        self.lower = max(0.0, self.lower - z - self.reference)

        if self.upper > self.threshold or self.lower > self.threshold:
            up = self.upper >= self.lower
            alarm = CusumAlarm(
                fired=True, direction="up" if up else "down",
                statistic=self.upper if up else self.lower,
                threshold=self.threshold, observations=self.observations,
                since_reset=self.since_reset,
                baseline_mean=self.baseline_mean, baseline_sd=self.baseline_sd,
                arl0=self.arl0)
            self.reset_statistic()
            return alarm

        return CusumAlarm(fired=False, statistic=max(self.upper, self.lower),
                          threshold=self.threshold,
                          observations=self.observations,
                          since_reset=self.since_reset,
                          baseline_mean=self.baseline_mean,
                          baseline_sd=self.baseline_sd, arl0=self.arl0)

    def calibrate_from(self, in_control: Sequence[float],
                       tolerance: float = 0.15) -> Dict[str, float]:
        """Set the threshold from a real in-control stream, not from theory.

        Siegmund's ARL0 is exact for independent Gaussian observations. Measured
        on this repo's own settled residuals — lag-1 autocorrelation 0.74, still
        0.67 at lag 90, and folded to |residual| so not remotely normal — a
        *designed* ARL0 of 1000 delivers an empirical 7.8. Two orders of
        magnitude. AR(1) whitening recovers almost none of it (10.2), because
        the departure is not only serial correlation.

        So the threshold is measured instead: replay an in-control sample at
        candidate thresholds and take the one whose observed run length hits
        the target. The promise then holds on the stream it was made about,
        which is the only place a false-alarm rate means anything.

        Returns the calibration, including `theoretical_threshold` so the size
        of the gap stays visible rather than being quietly absorbed.

        Raises:
            ValueError: if no threshold in range achieves the target — an
                honest failure, because the alternative is a number that
                promises a rate the stream will not honour.
        """
        sample = [abs(float(v)) for v in in_control]
        # Estimating a run length of N needs enough runs to average over. Ten
        # expected alarms is the floor; below that the estimate jumps between
        # single-alarm values and the calibration is fitting noise.
        needed = int(self.calibration + 10 * self.arl0)
        if len(sample) < needed:
            raise ValueError(
                f"calibrating to one false alarm per {self.arl0:g} needs about "
                f"{needed} in-control observations (ten runs' worth plus the "
                f"baseline window); got {len(sample)}. A shorter sample cannot "
                "distinguish the target rate from several others.")

        theoretical = self.threshold
        # A geometric grid, not bisection: achieved ARL0 is a step function of
        # the threshold, so bisection lands on whichever step it happens to
        # bracket and can overshoot the target by an order of magnitude. Scan,
        # then take the threshold whose achieved rate is closest in log terms.
        # The range has to be generous — on an autocorrelated stream achieved
        # ARL0 grows roughly *linearly* with the threshold rather than
        # exponentially as normal theory has it.
        best = None
        candidate = max(0.5, theoretical * 0.5)
        while candidate <= 20000.0:
            achieved = self._replay(sample, candidate)
            distance = abs(log(achieved / self.arl0)) if achieved > 0 else inf
            if best is None or distance < best[2]:
                best = (candidate, achieved, distance)
            candidate *= 1.15

        if best is None or best[2] > log(4.0):
            raise ValueError(
                f"no threshold gets within a factor of 4 of one false alarm "
                f"per {self.arl0:g} on this stream. It is too far from "
                "in-control-and-independent for a rate promise to mean "
                "anything; monitor a whitened signal or thin the stream to its "
                "decorrelation length.")

        self.threshold, achieved = best[0], best[1]
        if abs(achieved - self.arl0) / self.arl0 > tolerance:
            achieved_note = f"achieved {achieved:g}, outside {tolerance:.0%}"
        else:
            achieved_note = f"achieved {achieved:g}"
        return {
            "threshold": self.threshold,
            "theoretical_threshold": theoretical,
            "inflation": self.threshold / theoretical if theoretical else inf,
            "target_arl0": self.arl0,
            "achieved_arl0": achieved,
            "note": achieved_note,
        }

    def _replay(self, sample: Sequence[float], threshold: float) -> float:
        """Observed run length at this threshold, on this sample."""
        warmup = sample[:self.calibration]
        centre, spread = mean(warmup), (pstdev(warmup) or 1e-9)
        upper = lower = 0.0
        runs, last = [], 0
        for index, value in enumerate(sample[self.calibration:]):
            z = (value - centre) / spread
            upper = max(0.0, upper + z - self.reference)
            lower = max(0.0, lower - z - self.reference)
            if upper > threshold or lower > threshold:
                runs.append(index - last)
                last = index
                upper = lower = 0.0
        if not runs:
            return float(len(sample) - self.calibration)
        return sum(runs) / len(runs)

    def reset_statistic(self) -> None:
        """Clear the accumulators, keeping the learned baseline."""
        self.upper = self.lower = 0.0
        self.since_reset = 0

    def rebaseline(self) -> None:
        """Forget the baseline too — after a relearn, the old normal is gone."""
        self.baseline.clear()
        self.baseline_mean = self.baseline_sd = 0.0
        self.reset_statistic()


@dataclass
class DamageReport:
    """What the residual says, and how confident the attribution is."""

    detected: bool
    culprit: Optional[str] = None
    effect_size: float = 0.0
    before: float = 0.0
    after: float = 0.0
    changepoint: Optional[int] = None
    unattributed: bool = False
    candidates: Dict[str, Dict[str, float]] = field(default_factory=dict)
    reason: str = ""

    def summary(self) -> str:
        if not self.detected:
            return f"No damage signature: {self.reason or 'residual stable'}"
        head = (f"Damage signature at sample {self.changepoint}: mean |residual| "
                f"{self.before:.3f} -> {self.after:.3f} (Welch t={self.effect_size:.2f})")
        if self.culprit:
            diagnostics = self.candidates.get(self.culprit, {})
            return (f"{head}\n  attributed to '{self.culprit}' "
                    f"(C_mu -{diagnostics.get('delta_c_mu', 0):.2f}, "
                    f"h_mu -{diagnostics.get('delta_h_mu', 0):.2f})")
        return (f"{head}\n  UNATTRIBUTED — the model knows it is wrong and not "
                f"why; no interoceptive signal explains the change")


class DamageDetector:
    """Watch a residual stream against the agent's own interoceptive signals."""

    # Below this many samples on each side of a split there is nothing to test.
    MIN_WINDOW = 8
    # Welch t above which the two windows are taken to have different means.
    # This is a t, not a Cohen's d: the question is whether the *mean* residual
    # moved, and a per-sample effect size answers a different question. A real
    # actuator failure in a noisy world separates the per-sample distributions
    # by well under 1 sigma while shifting the mean unmistakably — thresholding
    # the per-sample separation would miss every such failure.
    EFFECT_THRESHOLD = 3.0
    # Samples per history cell needed before attribution is worth believing —
    # the same data-density floor the HND acceptance criterion applies.
    MIN_SAMPLES_PER_HISTORY = 12
    # How far back the changepoint search looks, in windows. Bounded on purpose:
    # far enough that a change is not missed the moment it ages out of the
    # trailing comparison, near enough that the search cannot reach the model's
    # own learning transient and call it damage. The search does take the best
    # of many splits, so the reported t is optimistic by the usual
    # multiple-comparisons margin — read it as a detection statistic, not a
    # p-value.
    RECENT_SPAN = 3

    def __init__(self, capacity: int = 400, min_shift: float = 0.0):
        """
        Args:
            capacity: samples retained. The buffer must span the change for
                attribution to work — evict the pre-change samples and the
                culprit signal looks constant.
            min_shift: smallest change in mean |residual| worth reporting, in
                the residual's own units. Statistical significance alone is not
                enough on a well-converged model: once the residual is tiny and
                steady, a practically meaningless wobble is many standard errors
                wide and the Welch t fires on it. Only the caller knows what
                counts as a real change for their signal, so the floor is theirs
                to set; 0.0 keeps the pure statistical behaviour.
        """
        self.capacity = capacity
        self.min_shift = min_shift
        self.residuals: List[float] = []
        self.signals: Dict[str, List[float]] = {}

    def observe(self, residual: float, signals: Optional[Dict[str, float]] = None) -> None:
        """Record one prediction residual and the body state that produced it."""
        self.residuals.append(abs(float(residual)))
        for name, value in (signals or {}).items():
            series = self.signals.setdefault(name, [0.0] * (len(self.residuals) - 1))
            series.append(float(value))
        # Keep every series the same length as the residual stream, so a signal
        # that starts reporting late still lines up with the right samples.
        for series in self.signals.values():
            while len(series) < len(self.residuals):
                series.append(series[-1] if series else 0.0)
        if len(self.residuals) > self.capacity:
            drop = len(self.residuals) - self.capacity
            self.residuals = self.residuals[drop:]
            for name in self.signals:
                self.signals[name] = self.signals[name][drop:]

    # -- stage 1: did anything change? ----------------------------------

    def changepoint(self, window: Optional[int] = None
                    ) -> Tuple[Optional[int], float, float, float]:
        """Compare the most recent window against the one just before it.

        Returns (split index, Welch t, mean before, mean after). The statistic
        is the absolute Welch t between the two windows — the difference in
        means over the standard error of that difference — so a noisy stream
        does not register a change and a small shift in a quiet stream does,
        and more evidence counts for more.

        Two decisions worth stating, because the obvious alternatives are wrong:

        **Trailing, not global.** Searching every split for the largest shift
        finds the model's own learning transient — early on it was untrained, so
        the biggest regime change in any history is usually the moment it
        started working. That is learning, not damage. Comparing recent against
        just-before asks the question actually wanted: has something changed
        *lately*?

        **Absolute, not signed.** Damage need not raise the residual. A weakened
        actuator moves the body less, so its prediction errors get *smaller*
        while the model is just as wrong about the dynamics. Anything that
        detects only deterioration would miss it entirely.
        """
        n = len(self.residuals)
        if n < 2 * self.MIN_WINDOW:
            return None, 0.0, 0.0, 0.0
        if window is None:
            window = max(self.MIN_WINDOW, min(n // 2, 40))

        # Candidate splits are restricted to the recent past. A purely trailing
        # comparison misses a change as soon as it ages out of the window, and
        # an unrestricted search finds the learning transient instead, so the
        # search spans the last few windows and no further.
        earliest = max(self.MIN_WINDOW, n - self.RECENT_SPAN * window)
        best = (None, 0.0, 0.0, 0.0)
        for split in range(earliest, n - self.MIN_WINDOW + 1):
            before = self.residuals[max(0, split - window):split]
            after = self.residuals[split:split + window]
            difference = abs(mean(after) - mean(before))
            standard_error = ((pstdev(before) ** 2) / len(before)
                              + (pstdev(after) ** 2) / len(after)) ** 0.5
            t = difference / standard_error if standard_error > 1e-12 else (
                float("inf") if difference > 1e-12 else 0.0)
            if t > best[1]:
                best = (split, t, mean(before), mean(after))
        return best

    # -- stage 2: which part of me? -------------------------------------

    # A signal taking at most this many distinct values is a *level* signal —
    # "healthy then broken" — and gets a two-sample test instead of the
    # causal-state one. The two tests answer the same question for different
    # kinds of evidence, and using the wrong one is how a real culprit escapes.
    MAX_LEVELS_FOR_TWO_SAMPLE = 4

    def attribute(self, signal_name: str, n_bands: int = 4,
                  max_history: int = 2, margin: float = 0.02
                  ) -> Tuple[bool, Dict[str, float]]:
        """Does conditioning on this interoceptive signal explain the residual?

        Two tests, picked by what the signal actually looks like:

        **Few distinct levels** — component health that stepped from healthy to
        broken. Group the residuals by level and compare them; if the residual
        distribution differs across the signal's values, the signal explains it.
        The causal-state criterion is nearly blind here, because a signal that
        is constant within each regime adds no *predictive* structure the
        residual's own history did not already have — it would clear a genuine
        culprit for lack of dynamics.

        **Many levels** — a continuously varying signal, where the question is
        whether conditioning on it simplifies the process. That is
        `HiddenNodeDetector.accept_by_epsilon_machine`'s criterion exactly: both
        statistical complexity and entropy rate must fall. Reusing it is the
        point — the same standard of evidence whether the unmodelled variable is
        out in the world or inside the robot.
        """
        series = self.signals.get(signal_name)
        if not series or len(series) != len(self.residuals):
            return False, {"acceptance": "skipped", "why": "signal unusable"}

        levels = sorted(set(series))
        if 2 <= len(levels) <= self.MAX_LEVELS_FOR_TWO_SAMPLE:
            return self._attribute_by_level(series, levels)
        if len(levels) < 2:
            return False, {"acceptance": "skipped", "why": "signal never varies",
                           "test": "two-sample"}

        residual_symbols = symbolize(self.residuals, n_bands=n_bands)
        needed = self.MIN_SAMPLES_PER_HISTORY * len(set(residual_symbols)) ** max_history
        if len(self.residuals) < needed:
            return False, {"acceptance": "skipped",
                           "why": f"{len(self.residuals)} samples, need ~{needed}"}

        signal_symbols = symbolize(series, n_bands=n_bands)
        augmented = list(zip(residual_symbols, signal_symbols))
        history = equalized_history_length(
            len(set(residual_symbols)), len(set(augmented)), max_history)

        before = reconstruct(residual_symbols, max_history=max_history)
        after = reconstruct(residual_symbols, augmented, max_history=history)
        delta_c = before.statistical_complexity - after.statistical_complexity
        delta_h = before.entropy_rate - after.entropy_rate

        accepted = delta_c >= margin and delta_h >= margin
        return accepted, {
            "acceptance": "accepted" if accepted else "rejected",
            "test": "epsilon-machine",
            "delta_c_mu": round(delta_c, 4),
            "delta_h_mu": round(delta_h, 4),
        }

    def _attribute_by_level(self, series: Sequence[float], levels: Sequence[float]
                            ) -> Tuple[bool, Dict[str, float]]:
        """Do the residuals differ across this signal's levels? (Welch t)"""
        groups = []
        for level in levels:
            values = [r for r, s in zip(self.residuals, series) if s == level]
            if len(values) >= self.MIN_WINDOW:
                groups.append((level, values))
        if len(groups) < 2:
            return False, {"acceptance": "skipped", "test": "two-sample",
                           "why": "no two levels with enough samples"}

        # Compare the most and least extreme groups by mean residual.
        groups.sort(key=lambda pair: mean(pair[1]))
        (low_level, low), (high_level, high) = groups[0], groups[-1]
        difference = abs(mean(high) - mean(low))
        standard_error = ((pstdev(low) ** 2) / len(low)
                          + (pstdev(high) ** 2) / len(high)) ** 0.5
        t = difference / standard_error if standard_error > 1e-12 else (
            float("inf") if difference > 1e-12 else 0.0)

        accepted = t >= self.EFFECT_THRESHOLD
        return accepted, {
            "acceptance": "accepted" if accepted else "rejected",
            "test": "two-sample",
            "t": round(t, 4),
            "levels": [low_level, high_level],
            "mean_residual": [round(mean(low), 4), round(mean(high), 4)],
        }

    def scan(self) -> DamageReport:
        """Detect a regime change, then try to name the part responsible."""
        split, effect, before, after = self.changepoint()
        if split is None:
            return DamageReport(False, reason="not enough history")
        if effect < self.EFFECT_THRESHOLD:
            return DamageReport(False, effect_size=effect, before=before,
                                after=after, changepoint=split,
                                reason=f"recent shift is t={effect:.2f}, "
                                       f"below {self.EFFECT_THRESHOLD}")
        if abs(after - before) < self.min_shift:
            return DamageReport(False, effect_size=effect, before=before,
                                after=after, changepoint=split,
                                reason=(f"shift of {abs(after - before):.4f} is "
                                        f"statistically clear (t={effect:.2f}) but "
                                        f"below the {self.min_shift:g} floor that "
                                        f"counts as a real change here"))

        candidates: Dict[str, Dict[str, float]] = {}
        best_name, best_score = None, 0.0
        for name in sorted(self.signals):
            accepted, diagnostics = self.attribute(name)
            candidates[name] = diagnostics
            if not accepted:
                continue
            # Rank within a test, never across one: a Welch t and a pair of
            # bit-drops are not on the same scale, and comparing them would
            # pick the culprit by which test it happened to qualify under.
            score = (diagnostics["t"] if diagnostics.get("test") == "two-sample"
                     else diagnostics["delta_c_mu"] + diagnostics["delta_h_mu"])
            if best_name is None or score > best_score:
                best_name, best_score = name, score

        return DamageReport(
            detected=True,
            culprit=best_name,
            effect_size=effect,
            before=before,
            after=after,
            changepoint=split,
            unattributed=best_name is None,
            candidates=candidates,
            reason="residual regime change",
        )

    def reset(self) -> None:
        """Forget the history — call after relearning, so the *next* change is
        measured against the new dynamics rather than the ones that broke."""
        self.residuals.clear()
        self.signals.clear()
