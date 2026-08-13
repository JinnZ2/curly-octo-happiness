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
from statistics import mean, pstdev
from typing import Dict, List, Optional, Sequence, Tuple

from grounding.core.epsilon_machine import (
    equalized_history_length, reconstruct, symbolize)

__all__ = ["DamageDetector", "DamageReport"]


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
