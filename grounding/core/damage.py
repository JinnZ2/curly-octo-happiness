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

    def __init__(self, capacity: int = 400):
        self.capacity = capacity
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

    def attribute(self, signal_name: str, n_bands: int = 4,
                  max_history: int = 2, margin: float = 0.02
                  ) -> Tuple[bool, Dict[str, float]]:
        """Does conditioning on this interoceptive signal explain the residual?

        Identical criterion to `HiddenNodeDetector.accept_by_epsilon_machine`:
        both statistical complexity and entropy rate must fall. Reusing it is
        the point — the same standard of evidence should apply whether the
        unmodelled variable is out in the world or inside the robot.
        """
        series = self.signals.get(signal_name)
        if not series or len(series) != len(self.residuals):
            return False, {"acceptance": "skipped", "why": "signal unusable"}

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
            "delta_c_mu": round(delta_c, 4),
            "delta_h_mu": round(delta_h, 4),
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

        candidates: Dict[str, Dict[str, float]] = {}
        best_name, best_delta = None, 0.0
        for name in sorted(self.signals):
            accepted, diagnostics = self.attribute(name)
            candidates[name] = diagnostics
            if accepted:
                combined = diagnostics["delta_c_mu"] + diagnostics["delta_h_mu"]
                if combined > best_delta:
                    best_name, best_delta = name, combined

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
