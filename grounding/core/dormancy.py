"""Dormancy: what a cut-off component does while it waits.

`coupling.py` reports that a network has partitioned and names who is on which
side. It says nothing about what the isolated side should *do*, and the default
— keep running as though the rest were still there — spends energy maintaining a
structure that has nothing to coordinate with.

Seeds solved this. A seed is not a small plant; it is a plant's *structure*
without its magnitude, held at a metabolic rate low enough that the structure
outlives the conditions that made it. Folding to a seed is not a loss of
information about what the organism is — it is the deliberate loss of
information about how big it currently is, which is the part that will have to
be rebuilt from local conditions anyway.

The mandala's reverse bloom is the same operation read from the other side: the
pattern collapses toward its centre, keeping every proportion and discarding
every dimension, and re-blooms at whatever scale the new ground supports.

What this module refuses to do
------------------------------
**Fold an empty structure.** Proportions of nothing are not a seed. A system
with no structure left reads as gone, and saying so is the honest answer.

**Reward over-compression.** Drying a seed further buys longer life only down to
a floor; past it the relationship inverts and ultra-dry storage damages what it
was meant to preserve (Ellis, Hong & Roberts). A compression metric that keeps
improving as you crush harder is measuring the crushing, not the survival.

**Treat an absent seed as a dead one.** No seed means no evidence either way. It
is not proof of death and it is not evidence of dormancy — the same rule this
repo applies to an untested claim, arrived at from the other direction.

The viability model
-------------------
Ellis & Roberts' improved viability equation (1980, *Annals of Botany* 45:13):

    v = K_i - p / sigma          log sigma = K_E - C_W log m - C_H t - C_Q t^2

Viability in probits falls linearly with storage period `p`; the time constant
`sigma` shrinks with moisture `m` and temperature `t`. Here moisture maps to the
residual activity a dormant component keeps, and temperature to the stress it
sits under. **This is an analogy, and the constants are not measurements of
anything in this repo** — every reading says so. What the analogy buys is a
shape that is not arbitrary: duration is purchased, the price is finite, and
there is a floor below which paying more buys nothing.

Stdlib only.
"""

from dataclasses import dataclass, field
from math import exp, inf, log10
from typing import Dict, List, Mapping, Optional, Sequence

__all__ = [
    "DEFAULT_FOLD_COST",
    "DormancyReading",
    "FoldWindow",
    "MAX_USEFUL_RESIDUAL",
    "MIN_VIABLE_RESIDUAL",
    "SEED_TERMS",
    "SeedState",
    "ViabilityReading",
    "assess_dormancy",
    "fold",
    "fold_window",
    "format_dormancy",
    "unfold",
    "viability",
]

# The canonical structural vocabulary. Any named terms may be folded; these are
# the ones the framework this came from uses, kept as the documented default.
SEED_TERMS = ("resonance_energy", "adaptability", "diversity", "coupling")

# Folding is not free — it costs energy to reorganise into a seed. The option
# therefore expires while the system is still alive, which is the whole point:
# a system that waits until it is dying has already lost the choice.
DEFAULT_FOLD_COST = 0.15

# Residual activity floor and ceiling, in the seed analogy's moisture units.
# Below the floor, further drying buys no duration and damages the structure;
# above the ceiling the seed is being stored wet and will not keep.
MIN_VIABLE_RESIDUAL = 0.02
MAX_USEFUL_RESIDUAL = 0.14

# Ellis & Roberts species constants. Illustrative, disclosed as such on every
# reading. K_i is the initial viability in probits.
_K_I = 2.0          # ~98% initial viability
_K_E = 5.0
_C_W = 3.0
_C_H = 0.03
_C_Q = 0.0004


@dataclass
class FoldWindow:
    """Whether there is still enough left to pay for folding."""

    open: bool
    energy: float
    cost: float
    margin: float
    warnings: List[str] = field(default_factory=list)


def fold_window(energy: float, fold_cost_fraction: float = DEFAULT_FOLD_COST
                ) -> FoldWindow:
    """Can this system still afford to fold?

    Reorganising into a seed costs energy, so the option closes *before* the
    system reaches zero. A component that spends its last reserves staying
    expanded has not chosen to die — it has lost the ability to choose.
    """
    if not 0.0 < fold_cost_fraction < 1.0:
        raise ValueError("fold_cost_fraction must be in (0, 1)")

    cost = fold_cost_fraction
    margin = energy - cost
    warnings: List[str] = []

    if margin < 0:
        warnings.append(
            f"fold window expired before the system did: {energy:.3f} energy "
            f"left against a fold cost of {cost:.3f}. The structure can no "
            "longer afford to become a seed.")
    elif margin < cost:
        warnings.append(
            f"fold window NARROW: {margin:.3f} above the {cost:.3f} fold cost. "
            "The choice is still available and will not be for long.")

    return FoldWindow(open=margin >= 0, energy=energy, cost=cost,
                      margin=margin, warnings=warnings)


@dataclass
class SeedState:
    """A structure without its magnitude.

    `proportions` sum to 1 and carry every ratio exactly. `conserved_total`
    records the magnitude that was discarded, so a round trip at the original
    scale is exact — but nothing about the seed depends on it.
    """

    proportions: Dict[str, float]
    conserved_total: float
    residual_activity: float = 0.05
    metric_signature: Dict[str, object] = field(default_factory=dict)
    lost: List[str] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        total = sum(self.proportions.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"seed proportions must sum to 1, got {total}. A seed that does "
                "not sum to one has lost the ratios it exists to carry.")

    @property
    def is_degenerate(self) -> bool:
        """Does some term sit at exactly zero, and so re-expand to zero?"""
        return any(value == 0.0 for value in self.proportions.values())


def fold(terms: Optional[Mapping[str, float]] = None,
         residual_activity: float = 0.05,
         metric_signature: Optional[Mapping[str, object]] = None,
         fold_cost_fraction: float = DEFAULT_FOLD_COST,
         **named_terms: float) -> SeedState:
    """Collapse a structure to its proportions — the reverse bloom.

    Args:
        terms: named structural quantities. May also be passed as keywords.
        residual_activity: metabolic rate kept while dormant, in the seed
            analogy's moisture units. Lower buys duration, down to a floor.
        metric_signature: whatever the caller needs carried verbatim — the seed
            keeps it untouched, because a proportion means nothing without the
            convention that produced it.
        fold_cost_fraction: energy fraction folding costs. The first term is
            treated as the energy budget the cost is charged against.

    Raises:
        ValueError: on an empty structure (there is nothing to fold and saying
            so is the honest answer), or when the fold window has closed.
    """
    values = dict(terms or {})
    values.update(named_terms)
    if not values:
        raise ValueError("nothing to fold: no structural terms given")

    for name, value in values.items():
        if value < 0:
            raise ValueError(f"structural term '{name}' is negative: {value}")

    total = sum(values.values())
    if total <= 0:
        raise ValueError(
            "cannot fold an empty structure: every term is zero, so there are "
            "no proportions to carry. This is the case where a dead reading "
            "means what it says — BLACK means what it says.")

    # The fold has to be affordable, and affordability is judged on the energy
    # term when one is present rather than on the total.
    energy = values.get("resonance_energy", values[next(iter(values))])
    window = fold_window(energy, fold_cost_fraction)
    if not window.open:
        raise ValueError(
            "fold window has closed: " + " ".join(window.warnings))

    proportions = {name: value / total for name, value in values.items()}

    lost = [
        "absolute magnitude — the seed knows every ratio and no size",
        "history — how the structure arrived at these proportions is not carried",
        "phase — where in any cycle the system was when it folded",
    ]
    degenerate = [name for name, value in proportions.items() if value == 0.0]
    if degenerate:
        lost.append(
            f"{', '.join(sorted(degenerate))}: already zero at fold time, so "
            "re-expands to zero at any scale. A seed cannot restore a term the "
            "structure had already lost.")

    provenance = [
        "Seed-physics: structure preserved, magnitude discarded, metabolism "
        "reduced to a rate the structure outlives",
        "Mandala-Computing: the reverse bloom — collapse toward the centre "
        "keeping every proportion, re-bloom at whatever scale the ground gives",
    ]
    if residual_activity < MIN_VIABLE_RESIDUAL:
        provenance.append(
            f"residual activity {residual_activity:.4f} is below the "
            f"{MIN_VIABLE_RESIDUAL} floor; further compression buys no "
            "duration and is charged as damage")
    if window.warnings:
        provenance.extend(window.warnings)

    return SeedState(proportions=proportions, conserved_total=total,
                     residual_activity=residual_activity,
                     metric_signature=dict(metric_signature or {}),
                     lost=lost, provenance=provenance)


@dataclass
class ViabilityReading:
    """How much of the seed is still able to germinate."""

    viable_fraction: float
    sigma: float
    flag: str                       # VIABLE | DEGRADING | NONVIABLE
    periods_elapsed: float
    stress: float
    source: str = ""
    warnings: List[str] = field(default_factory=list)


def _probit_to_fraction(probit: float) -> float:
    """Logistic stand-in for the normal CDF — stdlib, and monotone, which is
    all the shape needs to be for a disclosed analogy.

    Saturated rather than allowed to overflow: a seed that has been waiting for
    a very long time is at zero viability, and that is a fact about the seed,
    not an arithmetic error to propagate.
    """
    scaled = 1.7 * probit
    if scaled < -60:
        return 0.0
    if scaled > 60:
        return 1.0
    return 1.0 / (1.0 + exp(-scaled))


def viability(seed: SeedState, periods_elapsed: float,
              stress: float = 20.0) -> ViabilityReading:
    """Ellis & Roberts viability after a wait under stress.

    Duration is bought and the price is finite: lowering residual activity or
    stress raises `sigma`, the time constant of decay, but only down to the
    floor. Below it, the reading is charged rather than improved — a seed dried
    past what it can survive is not better preserved.
    """
    if periods_elapsed < 0:
        raise ValueError("elapsed periods cannot be negative")

    warnings = [
        "the seed constants here are an analogy, not a measurement of anything "
        "in this system; the shape is meaningful, the numbers are not",
    ]

    moisture = seed.residual_activity
    if moisture < MIN_VIABLE_RESIDUAL:
        warnings.append(
            f"over-compression: residual activity {moisture:.4f} is below the "
            f"{MIN_VIABLE_RESIDUAL} floor. Further drying buys no duration, so "
            "the floor is used for sigma and the excess is charged as damage.")
        effective_moisture = MIN_VIABLE_RESIDUAL
    else:
        effective_moisture = moisture
    if moisture > MAX_USEFUL_RESIDUAL:
        warnings.append(
            f"storing wetter than {MAX_USEFUL_RESIDUAL}: metabolism is high "
            "enough that the structure is consuming itself while it waits")

    # log sigma = K_E - C_W log m - C_H t - C_Q t^2, moisture in percent.
    log_sigma = (_K_E
                 - _C_W * log10(effective_moisture * 100.0)
                 - _C_H * stress
                 - _C_Q * stress * stress)
    sigma = pow(10.0, log_sigma)

    probit = _K_I - periods_elapsed / sigma
    fraction = _probit_to_fraction(probit)

    # Over-compression is charged here rather than being allowed to look like
    # better preservation: the structure is damaged even though sigma is not.
    if moisture < MIN_VIABLE_RESIDUAL:
        shortfall = (MIN_VIABLE_RESIDUAL - moisture) / MIN_VIABLE_RESIDUAL
        fraction *= max(0.0, 1.0 - shortfall)

    if fraction >= 0.85:
        flag = "VIABLE"
    elif fraction >= 0.05:
        flag = "DEGRADING"
    else:
        flag = "NONVIABLE"

    return ViabilityReading(
        viable_fraction=fraction, sigma=sigma, flag=flag,
        periods_elapsed=periods_elapsed, stress=stress,
        source="Ellis & Roberts 1980, Annals of Botany 45:13 (improved "
               "viability equation); floor from Ellis, Hong & Roberts",
        warnings=warnings)


def unfold(seed: SeedState, available_energy: float,
           viability_reading: Optional[ViabilityReading] = None
           ) -> Dict[str, float]:
    """Re-bloom the seed at whatever scale the ground supports.

    The proportions are restored exactly; the magnitude comes from what is
    available now, not from what was folded. A partly-degraded seed re-expands
    *smaller*, never distorted — losing viability costs the system size, not
    shape, because the ratios are the part the seed exists to protect.
    """
    if available_energy <= 0:
        raise ValueError("cannot re-expand into a zero energy budget")

    scale = available_energy
    if viability_reading is not None:
        if viability_reading.flag == "NONVIABLE":
            raise ValueError(
                f"seed is NONVIABLE after {viability_reading.periods_elapsed:g} "
                f"periods at stress {viability_reading.stress:g}: the structure "
                "did not outlast the wait, and re-expanding it would be "
                "inventing a pattern rather than restoring one")
        scale *= viability_reading.viable_fraction

    return {name: proportion * scale
            for name, proportion in seed.proportions.items()}


@dataclass
class DormancyReading:
    """Is this quiet a seed, a corpse, or an absence of evidence?"""

    state: str                    # DORMANT | REVIVABLE | SEED_LOST | NEVER_FOLDED
    seed: Optional[SeedState] = None
    viability_reading: Optional[ViabilityReading] = None
    warnings: List[str] = field(default_factory=list)


def assess_dormancy(seed: Optional[SeedState], periods_elapsed: float = 0.0,
                    stress: float = 20.0) -> DormancyReading:
    """The structural channel that stands alongside a flatlined activity reading.

    A dormant system and a dead one look identical to any measure of flux. The
    difference is not in the activity — there is none either way — but in
    whether a structure is still there to re-expand. This reports that channel
    separately so a quiet reading is not automatically read as an ending.
    """
    if seed is None:
        return DormancyReading(
            state="NEVER_FOLDED",
            warnings=[
                "no seed was recorded. This is absent evidence: it is not proof "
                "of death, and it is not evidence of dormancy either. The "
                "system may have folded without recording it, or may never have "
                "folded at all.",
            ])

    reading = viability(seed, periods_elapsed, stress)
    warnings = list(reading.warnings)

    if reading.flag == "VIABLE":
        state = "DORMANT"
        warnings.append(
            "activity is near zero because the structure is folded, not because "
            "there is no structure. A flux measurement alone would read this as "
            "dead — that is the false positive this channel corrects.")
    elif reading.flag == "DEGRADING":
        state = "REVIVABLE"
        warnings.append(
            f"{reading.viable_fraction:.0%} of the structure would survive "
            "re-expansion; it will re-bloom smaller, with its proportions "
            "intact.")
    else:
        state = "SEED_LOST"
        warnings.append(
            "the seed did not outlast the wait. There is no structure left to "
            "re-expand, so a dead reading is now the correct one — BLACK is now "
            "the correct reading, having not been before.")

    return DormancyReading(state=state, seed=seed, viability_reading=reading,
                           warnings=warnings)


def format_dormancy(reading: DormancyReading) -> str:
    """Human-readable rendering, including what folding destroyed."""
    lines = ["=" * 70, f"DORMANCY: {reading.state}", "=" * 70]

    if reading.seed is not None:
        lines.append("  preserved proportions:")
        for name, value in sorted(reading.seed.proportions.items()):
            lines.append(f"    {name:22} {value:.4f}")
        lines.append(f"  conserved total: {reading.seed.conserved_total:.4f}")
        if reading.viability_reading is not None:
            v = reading.viability_reading
            lines.append(f"  viability: {v.viable_fraction:.1%} after "
                         f"{v.periods_elapsed:g} periods at stress {v.stress:g} "
                         f"(sigma = {v.sigma:.1f})")
        lines.extend(["", "  NOT PRESERVED BY FOLDING:"])
        lines.extend(f"    - {item}" for item in reading.seed.lost)
        if reading.seed.provenance:
            lines.extend(["", "  provenance:"])
            lines.extend(f"    - {item}" for item in reading.seed.provenance)

    if reading.warnings:
        lines.extend(["", "  NOTES:"])
        lines.extend(f"    - {item}" for item in reading.warnings)

    lines.extend([
        "",
        "Whether waiting is worth it is not a measurement.",
        "=" * 70,
    ])
    return "\n".join(lines)
