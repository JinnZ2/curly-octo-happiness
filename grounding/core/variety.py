"""Ashby's Law of Requisite Variety as a running meter.

    V(Z) >= V(D) - V(R)

The variety left uncontrolled in the outcome Z is at least the disturbance
variety V(D) minus the regulator's response variety V(R). "Only variety can
absorb variety": a regulator that can express fewer distinct responses than the
environment can present distinct disturbances *cannot* hold the outcome steady,
no matter how well tuned it is. The gap is a structural limit, not a bug to be
fixed by better parameters.

The practical use here is as an alarm. Give the meter a stream of disturbance
codewords and a stream of response codewords; when the margin V(R) - V(D)
approaches zero, the regulator is running out of distinctions and needs its
repertoire widened -- which for this repo means wider or finer bands.

Two readings of "variety" are supported, both in bits:

    count   V = log2(number of distinct codewords)   -- Ashby's original
    entropy V = -sum p log2 p                        -- Shannon refinement,
                which discounts codewords that are technically available but
                almost never used

Entropy is the default: a repertoire you never exercise is not requisite
variety, it is inventory.

Stdlib only.
"""

from collections import Counter, deque
from math import log2
from typing import Deque, Hashable, Optional

__all__ = ["VarietyMeter"]


class VarietyMeter:
    """Track disturbance vs. response variety and alarm when the margin closes."""

    def __init__(self, name: str = "", window: Optional[int] = None,
                 mode: str = "entropy"):
        """
        Args:
            name: label for reports.
            window: keep only the most recent N observations of each stream
                (None = keep all). A window makes the meter track regime
                changes instead of averaging over the system's whole history.
            mode: "entropy" (default) or "count", per the module docstring.
        """
        if mode not in ("entropy", "count"):
            raise ValueError(f"unknown variety mode: {mode!r}")
        self.name = name
        self.mode = mode
        self.window = window
        self.disturbances: Deque[Hashable] = deque(maxlen=window)
        self.responses: Deque[Hashable] = deque(maxlen=window)

    # ------------------------------------------------------------------
    # observation
    # ------------------------------------------------------------------

    def observe_disturbance(self, codeword: Hashable) -> None:
        """Record one distinguishable state the environment presented."""
        self.disturbances.append(codeword)

    def observe_response(self, codeword: Hashable) -> None:
        """Record one distinguishable state the regulator answered with."""
        self.responses.append(codeword)

    def observe(self, disturbance: Hashable, response: Hashable) -> None:
        """Record a matched (disturbance, response) pair."""
        self.observe_disturbance(disturbance)
        self.observe_response(response)

    def reset(self) -> None:
        self.disturbances.clear()
        self.responses.clear()

    # ------------------------------------------------------------------
    # measurement
    # ------------------------------------------------------------------

    def _variety(self, samples) -> float:
        counts = Counter(samples)
        if not counts:
            return 0.0
        if self.mode == "count":
            return log2(len(counts))
        total = sum(counts.values())
        return -sum((c / total) * log2(c / total) for c in counts.values() if c)

    @property
    def disturbance_variety(self) -> float:
        """V(D), in bits."""
        return self._variety(self.disturbances)

    @property
    def response_variety(self) -> float:
        """V(R), in bits."""
        return self._variety(self.responses)

    @property
    def margin(self) -> float:
        """V(R) - V(D). Negative means the regulator is already outmatched."""
        return self.response_variety - self.disturbance_variety

    @property
    def uncontrolled_variety(self) -> float:
        """The V(Z) lower bound: max(0, V(D) - V(R)) bits Ashby says leak through."""
        return max(0.0, -self.margin)

    def alarm(self, threshold: float = 0.5) -> bool:
        """True when the margin has closed to within `threshold` bits.

        Fires *before* the regulator is fully outmatched -- the point is to
        widen the repertoire while there is still slack, not to report the
        failure afterwards. Needs observations on both sides to mean anything.
        """
        if not self.disturbances or not self.responses:
            return False
        return self.margin <= threshold

    def status(self, threshold: float = 0.5) -> dict:
        """Machine-readable snapshot, suitable for logging or a claim."""
        return {
            "name": self.name,
            "mode": self.mode,
            "disturbance_variety": round(self.disturbance_variety, 4),
            "response_variety": round(self.response_variety, 4),
            "margin": round(self.margin, 4),
            "uncontrolled_variety": round(self.uncontrolled_variety, 4),
            "n_disturbances": len(self.disturbances),
            "n_responses": len(self.responses),
            "distinct_disturbances": len(set(self.disturbances)),
            "distinct_responses": len(set(self.responses)),
            "alarm": self.alarm(threshold),
            "threshold": threshold,
        }

    def report(self, threshold: float = 0.5) -> str:
        s = self.status(threshold)
        label = f" [{self.name}]" if self.name else ""
        verdict = ("ALARM: repertoire too narrow, widen the bands"
                   if s["alarm"] else "margin OK")
        return (f"Requisite variety{label} ({self.mode}): "
                f"V(D)={s['disturbance_variety']:.2f} bits over "
                f"{s['distinct_disturbances']} codewords, "
                f"V(R)={s['response_variety']:.2f} bits over "
                f"{s['distinct_responses']} codewords, "
                f"margin={s['margin']:+.2f} -> {verdict}")
