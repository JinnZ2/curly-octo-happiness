"""Allostatic bands: setpoints that move *before* the regime does.

Homeostasis corrects after the fact — a value lands outside the bands, the
bands are recomputed, the encoder catches up. Allostasis moves the setpoint in
anticipation, so the regulator is already in the right range when the regime
arrives. That is strictly better when the prediction is good, and strictly
worse when it is not, which is why the cost has to be tracked.

Two numbers matter, and they pull in opposite directions:

    miscoverage      fraction of observations the current bands cannot resolve
                     (outside the range entirely, or all landing in one band).
                     This is what shifting is *for*.

    allostatic load  cumulative cost of the shifting itself, summed as the
                     normalised distance the thresholds have travelled. Every
                     shift discards the encoder's history: old bitstrings no
                     longer mean what new ones mean.

A regulator that predicts well pays a little load and buys a lot of coverage. A
regulator chasing noise pays load forever without ever fitting — `chronic()`
catches exactly that, and it needs history to see it, the same way the
second-order guard does.

Stdlib only. Band thresholds follow `graycode`'s convention: ascending, and a
value belongs to the highest band whose threshold it meets.
"""

from typing import Dict, List, Optional, Sequence

__all__ = ["AllostaticBands", "percentile_thresholds"]


def percentile_thresholds(samples: Sequence[float], n_bands: int = 8) -> List[float]:
    """The repo's `init_bands` convention: equal-occupancy ascending thresholds."""
    ordered = sorted(samples)
    if not ordered:
        return []
    thresholds = []
    for i in range(n_bands):
        position = (len(ordered) - 1) * (i / n_bands)
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        thresholds.append(ordered[low] + (ordered[high] - ordered[low]) * (position - low))
    return thresholds


class AllostaticBands:
    """Band thresholds that can be shifted reactively or predictively."""

    def __init__(self, thresholds: Sequence[float], name: str = "",
                 chronic_window: int = 4):
        """
        Args:
            thresholds: initial ascending band thresholds.
            chronic_window: how many shifts `chronic()` inspects for the
                pay-forever-fit-never pattern (minimum 3).
        """
        self.name = name
        self.thresholds = list(thresholds)
        self.chronic_window = max(3, chronic_window)
        self.observations: List[float] = []
        self.load = 0.0
        self.shifts: List[Dict[str, float]] = []

    # -- observation ----------------------------------------------------

    def observe(self, value: float) -> None:
        self.observations.append(float(value))

    def band_index(self, value: float) -> int:
        """Highest band whose threshold is <= value (graycode convention)."""
        index = 0
        for i, threshold in enumerate(self.thresholds):
            if value >= threshold:
                index = i
        return index

    def miscoverage(self, samples: Optional[Sequence[float]] = None) -> float:
        """How badly the current bands fail to resolve these samples, in [0, 1].

        Two failures, measured as one number because they cost the same thing —
        distinctions the regulator cannot make:

        * **under-range** — values below the lowest threshold are silently
          clamped into band 0 alongside legitimate band-0 values. (There is no
          matching over-range term: by the Gray-code convention the top band is
          open-ended, so a large value is in range by construction.)
        * **under-utilisation** — bands that no sample ever lands in. Eight
          bands with everything in one of them resolves no better than one band.

        The worse of the two governs, so fixing one failure cannot hide the
        other. This is the requisite-variety measure from `variety.py` applied
        to a single encoder's own repertoire.
        """
        values = list(self.observations if samples is None else samples)
        if not values or not self.thresholds:
            return 0.0
        under_range = sum(1 for v in values if v < self.thresholds[0]) / len(values)
        used = len({self.band_index(v) for v in values})
        under_used = 1.0 - used / len(self.thresholds)
        return max(under_range, under_used)

    # -- shifting -------------------------------------------------------

    def _apply(self, new_thresholds: Sequence[float], mode: str,
               note: str = "") -> Dict[str, float]:
        """Move the thresholds and charge the move to allostatic load."""
        new_thresholds = list(new_thresholds)
        if not new_thresholds:
            return {"mode": mode, "cost": 0.0, "note": "empty proposal ignored"}

        span = max(1e-9, abs(self.thresholds[-1] - self.thresholds[0])) if self.thresholds else 1.0
        pairs = zip(self.thresholds, new_thresholds)
        cost = sum(abs(new - old) for old, new in pairs) / (span * max(1, len(new_thresholds)))

        before = self.miscoverage()
        self.thresholds = new_thresholds
        after = self.miscoverage()
        self.load += cost

        record = {"mode": mode, "cost": round(cost, 6),
                  "miscoverage_before": round(before, 4),
                  "miscoverage_after": round(after, 4),
                  "load": round(self.load, 6), "note": note}
        self.shifts.append(record)
        return record

    def reactive_update(self, samples: Optional[Sequence[float]] = None,
                        n_bands: int = 8) -> Dict[str, float]:
        """Homeostatic catch-up: re-band on what has already been seen."""
        values = list(self.observations if samples is None else samples)
        return self._apply(percentile_thresholds(values, n_bands), "reactive")

    def anticipate(self, predicted: Sequence[float], n_bands: int = 8,
                   blend: float = 0.5) -> Dict[str, float]:
        """Allostatic shift: re-band on where the regime is *going*.

        `predicted` is a rollout — in this repo, the dream-recombination
        predictor. `blend` mixes the predicted bands with the observed ones:
        1.0 commits entirely to the forecast, 0.0 is a plain reactive update.
        Blending is not timidity; it is the honest weight to put on a predictor
        whose calibration is itself unknown.
        """
        if not predicted:
            return {"mode": "anticipatory", "cost": 0.0, "note": "no forecast"}
        forecast = percentile_thresholds(predicted, n_bands)
        observed = percentile_thresholds(self.observations, n_bands) or forecast
        if len(observed) != len(forecast):
            observed = forecast
        blended = [(1 - blend) * o + blend * f for o, f in zip(observed, forecast)]
        return self._apply(blended, "anticipatory",
                           note=f"blend={blend}, {len(predicted)} rollout samples")

    # -- pathology ------------------------------------------------------

    def chronic(self) -> bool:
        """Is the regulator paying load without buying coverage?

        True when the recent shifts have cost something real and miscoverage is
        no better at the end than it was at the start. That is allostatic load
        in its clinical sense: the standing cost of anticipation that never
        arrives at a fit.
        """
        window = self.shifts[-self.chronic_window:]
        if len(window) < self.chronic_window:
            return False
        paid = sum(s.get("cost", 0.0) for s in window)
        if paid <= 0.0:
            return False
        return window[-1]["miscoverage_after"] >= window[0]["miscoverage_before"]

    def report(self) -> str:
        label = f" [{self.name}]" if self.name else ""
        lines = [f"Allostatic bands{label}: {len(self.thresholds)} thresholds "
                 f"{self.thresholds[0]:.3g}..{self.thresholds[-1]:.3g}"
                 if self.thresholds else f"Allostatic bands{label}: unset"]
        lines.append(f"  observations {len(self.observations)}, "
                     f"miscoverage {self.miscoverage():.0%}, "
                     f"allostatic load {self.load:.3f} over {len(self.shifts)} shifts")
        for shift in self.shifts[-3:]:
            lines.append(f"  {shift['mode']:>13}: cost {shift['cost']:.3f}, "
                         f"miscoverage {shift['miscoverage_before']:.0%} -> "
                         f"{shift['miscoverage_after']:.0%}")
        if self.chronic():
            lines.append("  ⚠ chronic load: shifting keeps costing without "
                         "improving coverage — the predictor is chasing noise.")
        return "\n".join(lines)
