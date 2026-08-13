# transition.py
"""
Transition Simulator v1.0

Simulates the Line → Torus transition over time (industrial vs.
regenerative farm), producing per-year FarmState snapshots and a
comparison report. Moved here from diagnostic/systems_diagnostic_suite.py
when the two SDS copies were merged.
"""

import os
import random
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# Claims live in the shared core package; modules/ is normally run with its own
# directory as CWD, so reach the repository root first (as hnd.py does).
try:
    from grounding.core.claims import Claim
except ImportError:  # pragma: no cover - depends on how the script was launched
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from grounding.core.claims import Claim


@dataclass
class FarmState:
    year: int
    soil_organic_matter: float
    water_retention: float
    yield_per_acre: float
    biodiversity_index: float
    fertilizer_use: float
    resilience_score: float


class TransitionSimulator:
    """Simulates Line → Torus transition over time."""

    def __init__(self):
        self.history = []

    def run_linear(self, years: int = 20) -> List[FarmState]:
        """Simulate linear (industrial) farm."""
        states = []
        state = FarmState(0, 2.0, 0.35, 3.5, 0.2, 0.5, 0.3)

        for year in range(years + 1):
            state.year = year
            # Linear: soil degrades, fertilizer increases, yield plateaus then declines
            state.soil_organic_matter = max(0.5, 2.0 - year * 0.08)
            state.water_retention = max(0.15, 0.35 - year * 0.01)
            state.fertilizer_use = min(1.2, 0.5 + year * 0.04)
            state.yield_per_acre = max(0.5, 3.5 + 0.1 * year - 0.005 * year ** 2)
            state.biodiversity_index = max(0.05, 0.2 - year * 0.008)
            state.resilience_score = max(0.05, 0.3 - year * 0.015)

            # Random drought shock (10% chance)
            if random.random() < 0.1:
                state.yield_per_acre *= 0.7
                state.resilience_score *= 0.8

            states.append(FarmState(**state.__dict__))

        return states

    def run_torus(self, years: int = 20) -> List[FarmState]:
        """Simulate torus (regenerative) farm."""
        states = []
        state = FarmState(0, 2.0, 0.35, 3.0, 0.2, 0.0, 0.3)

        # Transition phases: Year 1-5 build soil, water, yield
        phases = {
            1: (0.2, 0.05, 0.1, 0.05),
            2: (0.3, 0.08, 0.15, 0.08),
            3: (0.4, 0.1, 0.2, 0.1),
            4: (0.5, 0.12, 0.25, 0.12),
            5: (0.6, 0.15, 0.3, 0.15),
        }

        for year in range(years + 1):
            state.year = year
            if year <= 5 and year in phases:
                s, w, y, b = phases[year]
                state.soil_organic_matter += s
                state.water_retention += w
                state.yield_per_acre += y
                state.biodiversity_index += b
            elif year > 5:
                state.soil_organic_matter += 0.05
                state.water_retention += 0.02
                state.yield_per_acre += 0.03
                state.biodiversity_index += 0.01

            # Cap values
            state.soil_organic_matter = min(8.0, state.soil_organic_matter)
            state.water_retention = min(0.95, state.water_retention)
            state.yield_per_acre = min(6.0, state.yield_per_acre)
            state.biodiversity_index = min(1.0, state.biodiversity_index)
            state.fertilizer_use = max(0.0, state.fertilizer_use - 0.02)

            state.resilience_score = (
                0.3 * state.water_retention +
                0.3 * state.biodiversity_index +
                0.4 * (state.soil_organic_matter / 8.0)
            )

            # Random drought shock (10% chance) - less impact than linear
            if random.random() < 0.1:
                state.yield_per_acre *= 0.85
                state.water_retention *= 0.95

            states.append(FarmState(**state.__dict__))

        return states

    def compare(self, years: int = 20) -> Dict:
        """Compare linear vs torus scenarios."""
        linear = self.run_linear(years)
        torus = self.run_torus(years)

        return {
            "linear_final": linear[-1].__dict__,
            "torus_final": torus[-1].__dict__,
            "comparison": {
                "soil_advantage": torus[-1].soil_organic_matter - linear[-1].soil_organic_matter,
                "yield_advantage": torus[-1].yield_per_acre - linear[-1].yield_per_acre,
                "resilience_advantage": torus[-1].resilience_score - linear[-1].resilience_score,
                "water_advantage": torus[-1].water_retention - linear[-1].water_retention,
            },
            "linear_history": linear,
            "torus_history": torus
        }

    # ------------------------------------------------------------------
    # Antifragility (PLAN_FORWARD 2.3)
    # ------------------------------------------------------------------

    # Mean stressor severity, held fixed while volatility varies. Taleb's test
    # is a *mean-preserving spread*: same average drought, more dispersion. A
    # system that gains from that is antifragile; one that loses is fragile.
    MEAN_SEVERITY = 0.30

    # A response can be convex simply because yield has bottomed out at zero.
    # That is the convexity of ruin, not antifragility: losses stop growing
    # because there is nothing left to lose. A topology only counts as
    # antifragile if it stays above this fraction of its unstressed yield.
    VIABILITY_FRACTION = 0.10

    # Relative Jensen gap below which a system is neither gaining nor losing
    # from volatility — Taleb's middle category, robust.
    GAP_TOLERANCE = 0.001

    def stress_path(self, years: int, sigma: float, seed: int) -> List[float]:
        """A mean-preserving two-point stressor path.

        Each year the drought is either mean+sigma or mean-sigma, chosen by a
        seeded coin. The *same* coin sequence is reused for every sigma (common
        random numbers), so f(sigma) is smooth in sigma and the second
        difference below measures curvature rather than sampling noise.
        """
        rng = random.Random(seed)
        flips = [rng.random() < 0.5 for _ in range(years + 1)]
        return [max(0.0, min(1.0, self.MEAN_SEVERITY + (sigma if up else -sigma)))
                for up in flips]

    def run_stressed(self, topology: str, severities: Sequence[float]) -> List[FarmState]:
        """Run a topology against an explicit per-year drought severity path.

        The two topologies differ in *how* damage scales, which is the whole
        question:

        LINE — damage compounds. A drought both cuts this year's yield and
        degrades the soil, which lowers the ceiling for every year after. Losses
        accelerate with severity, so the response curve bends downward.

        TORUS — damage is bounded. Water retention absorbs the first part of any
        drought outright, and soil organic matter puts a floor under what a bad
        year can take. Mild stress slightly *raises* biodiversity (hormesis).
        Bounded downside is what makes a response convex.

        Neither shape is imposed; both fall out of the mechanism, and
        `antifragility_claim` measures which way each one actually bends.
        """
        if topology not in ("LINE", "TORUS"):
            raise ValueError(f"topology must be LINE or TORUS, got {topology!r}")

        states: List[FarmState] = []
        if topology == "LINE":
            soil, water, biodiversity, fertilizer = 2.0, 0.35, 0.20, 0.5
        else:
            soil, water, biodiversity, fertilizer = 2.0, 0.35, 0.20, 0.0

        for year, severity in enumerate(severities):
            if topology == "LINE":
                soil = max(0.5, 2.0 - year * 0.08)
                water = max(0.15, 0.35 - year * 0.01)
                fertilizer = min(1.2, 0.5 + year * 0.04)
                biodiversity = max(0.05, 0.20 - year * 0.008)
                base = max(0.5, 3.5 + 0.1 * year - 0.005 * year ** 2)
                # Compounding: the drought scars the soil it depends on, and a
                # thinner soil amplifies the next drought.
                soil = max(0.1, soil - severity * 0.6)
                scarcity = 1.0 + (2.0 - soil) / 2.0        # >1 once soil is thin
                crop = max(0.0, base * (1.0 - severity * scarcity))
                resilience = max(0.05, 0.3 - year * 0.015)
            else:
                if year <= 5:
                    soil = min(8.0, soil + 0.4)
                    water = min(0.95, water + 0.10)
                    biodiversity = min(1.0, biodiversity + 0.10)
                else:
                    soil = min(8.0, soil + 0.05)
                    water = min(0.95, water + 0.02)
                    biodiversity = min(1.0, biodiversity + 0.01)
                base = min(6.0, 3.0 + 0.18 * year)
                # Buffered: retention absorbs the first slice of any drought,
                # and soil organic matter floors the damage from the rest.
                effective = max(0.0, severity - water)
                floor = 0.35 + 0.05 * soil                 # what the soil holds back
                crop = base * max(floor, 1.0 - effective)
                # Hormesis: a stressor the buffer absorbs still exercises the
                # system, and diversity answers.
                if 0.0 < severity <= water:
                    biodiversity = min(1.0, biodiversity + 0.01)
                resilience = 0.3 * water + 0.3 * biodiversity + 0.4 * (soil / 8.0)

            states.append(FarmState(year, soil, water, crop, biodiversity,
                                    fertilizer, resilience))
        return states

    def yield_under_volatility(self, topology: str, sigma: float, years: int = 20,
                               seeds: Sequence[int] = range(24)) -> float:
        """f(sigma): mean total yield at drought volatility `sigma`."""
        return self._response(topology, sigma, years, seeds)[0]

    def _response(self, topology: str, sigma: float, years: int,
                  seeds: Sequence[int]) -> Tuple[float, float]:
        """(mean total yield, worst single-year yield) at this volatility."""
        totals, worst = [], float("inf")
        for seed in seeds:
            states = self.run_stressed(topology, self.stress_path(years, sigma, seed))
            totals.append(sum(s.yield_per_acre for s in states))
            worst = min(worst, min(s.yield_per_acre for s in states))
        return sum(totals) / len(totals), worst

    def unstressed_yield(self, topology: str, years: int = 20) -> float:
        """Best single-year yield with no drought at all — the viability yardstick."""
        states = self.run_stressed(topology, [0.0] * (years + 1))
        return max(s.yield_per_acre for s in states)

    def convexity(self, topology: str, sigma: float = 0.15, step: float = 0.05,
                  years: int = 20, seeds: Sequence[int] = range(24)) -> Dict[str, float]:
        """Second derivative of yield with respect to stressor volatility.

        Central second difference of f(sigma). Positive means convex — the
        system gains more from the good half of the spread than it loses to the
        bad half, which is Taleb's Jensen gap and the operational definition of
        antifragile. Negative means fragile.
        """
        low, _ = self._response(topology, sigma - step, years, seeds)
        mid, _ = self._response(topology, sigma, years, seeds)
        high, worst = self._response(topology, sigma + step, years, seeds)
        second = (high - 2 * mid + low) / (step ** 2)

        # Viability at the widest spread tested: if the worst year has collapsed,
        # any convexity here is the floor at ruin, not resilience.
        baseline = self.unstressed_yield(topology, years)
        viable = worst >= self.VIABILITY_FRACTION * baseline

        # Taleb's triad, not a binary. Relative Jensen gap keeps the tolerance
        # scale-free so topologies with different yield levels compare fairly.
        gap = (low + high) / 2 - mid
        relative_gap = gap / mid if mid else 0.0
        if not viable:
            triad = "fragile (ruined)"
        elif relative_gap > self.GAP_TOLERANCE:
            triad = "antifragile"
        elif relative_gap < -self.GAP_TOLERANCE:
            triad = "fragile"
        else:
            triad = "robust"

        return {
            "topology": topology,
            "sigma": sigma,
            "step": step,
            "f_low": round(low, 4),
            "f_mid": round(mid, 4),
            "f_high": round(high, 4),
            "d2f_dsigma2": round(second, 4),
            "jensen_gap": round((low + high) / 2 - mid, 4),
            "shape": "convex" if second > 0 else "concave" if second < 0 else "linear",
            "relative_gap": round(relative_gap, 6),
            "worst_year_yield": round(worst, 4),
            "unstressed_yield": round(baseline, 4),
            "viable": viable,
            "triad": triad,
            "antifragile": bool(second > 0 and viable),
        }

    def antifragility_claim(self, topology: str, sigma: float = 0.15,
                            step: float = 0.05, years: int = 20,
                            seeds: Sequence[int] = range(24)) -> Tuple[Claim, Dict[str, float]]:
        """Stake 'convex under bounded volatility' as a testable claim.

        The falsification condition lives in the logical form, so the claim text
        and the check cannot drift: the claim holds iff the measured second
        derivative is positive. Returns the claim (already evaluated, so its
        Beta posterior has one observation) and the measurement.
        """
        measurement = self.convexity(topology, sigma, step, years, seeds)
        claim = Claim(
            text=(f"{topology} farm yield is convex in drought volatility around "
                  f"sigma={sigma} while staying viable: a mean-preserving spread "
                  f"raises total yield without collapsing any year"),
            falsification=(f"the central second difference of yield with respect to "
                           f"sigma is <= 0 at sigma={sigma} (step {step}), or the "
                           f"worst year falls below {self.VIABILITY_FRACTION:.0%} of "
                           f"unstressed yield"),
            # The condition is a conjunction, which the logical_form op vocabulary
            # cannot express, so it goes in the executable refutation_test — still
            # machine-checkable, still the single source of truth.
            refutation_test=lambda b: not (b["d2f_dsigma2"] > 0 and b["viable"]),
            scope={"topology": topology, "sigma": sigma, "step": step,
                   "years": years, "n_seeds": len(list(seeds)),
                   "mean_severity": self.MEAN_SEVERITY},
            reference_class=f"{topology} farms under mean-preserving drought spreads",
        )
        claim.evaluate({"d2f_dsigma2": measurement["d2f_dsigma2"],
                        "viable": measurement["viable"]})
        return claim, measurement

    def regime_scan(self, topology: str, means: Sequence[float] = (0.2, 0.4, 0.6, 0.8),
                    sigma: float = 0.15, step: float = 0.05,
                    years: int = 20) -> List[Dict[str, float]]:
        """Where in stressor space is this topology convex, and is it still alive?

        The single-point answer turned out to be the wrong question. Curvature
        depends on which bound is binding: a buffer that absorbs small stressors
        makes the response *concave* at the scale it covers, while a floor that
        caps large damage makes it convex. Scanning the mean severity is what
        shows which regime a topology is actually in.
        """
        original = self.MEAN_SEVERITY
        rows = []
        try:
            for mean in means:
                self.MEAN_SEVERITY = mean
                row = self.convexity(topology, sigma, step, years)
                row["mean_severity"] = mean
                rows.append(row)
        finally:
            self.MEAN_SEVERITY = original
        return rows

    def antifragility_report(self, sigma: float = 0.15, step: float = 0.05,
                             years: int = 20) -> str:
        lines = ["ANTIFRAGILITY UNDER MEAN-PRESERVING DROUGHT SPREAD",
                 "=" * 60,
                 f"Mean severity held at {self.MEAN_SEVERITY}; only the spread varies.",
                 ""]
        for topology in ("LINE", "TORUS"):
            claim, m = self.antifragility_claim(topology, sigma, step, years)
            lines.append(f"{topology}:")
            lines.append(f"  f(sigma-step)={m['f_low']:.2f}  f(sigma)={m['f_mid']:.2f}  "
                         f"f(sigma+step)={m['f_high']:.2f}")
            lines.append(f"  d2f/dsigma2 = {m['d2f_dsigma2']:+.2f}  ->  {m['shape']}")
            lines.append(f"  Jensen gap  = {m['jensen_gap']:+.3f} tons "
                         f"({'gains' if m['jensen_gap'] > 0 else 'loses'} from volatility)")
            lines.append(f"  worst year  = {m['worst_year_yield']:.2f} of "
                         f"{m['unstressed_yield']:.2f} unstressed "
                         f"({'viable' if m['viable'] else 'RUINED'})")
            lines.append(f"  verdict: {m['triad'].upper()} "
                         f"(relative Jensen gap {m['relative_gap']:+.4f}) — "
                         f"convexity claim {'held' if claim.passed else 'FALSIFIED'}")
            lines.append("")

        lines.append("REGIME SCAN — curvature depends on which bound is binding")
        lines.append("-" * 60)
        lines.append(f"  {'mean':>6} {'topology':>9} {'d2f/dsigma2':>13} {'shape':>9} "
                     f"{'verdict':>18}")
        for topology in ("LINE", "TORUS"):
            for row in self.regime_scan(topology, sigma=sigma, step=step, years=years):
                lines.append(f"  {row['mean_severity']:>6.2f} {topology:>9} "
                             f"{row['d2f_dsigma2']:>+13.2f} {row['shape']:>9} "
                             f"{row['triad']:>18}")
        lines.append("")
        lines.append("Read the scan, not the single point: a buffer that absorbs small")
        lines.append("stressors bends the response concave at the scale it covers, and")
        lines.append("only a floor capping large damage bends it convex. Convexity while")
        lines.append("ruined is the floor at zero, not resilience.")
        return "\n".join(lines)

    def generate_report(self, results: Dict) -> str:
        """Generate comparison report."""
        comp = results["comparison"]
        linear = results["linear_final"]
        torus = results["torus_final"]

        lines = [
            "=" * 60,
            "TRANSITION SIMULATION: LINEAR vs TORUS",
            "=" * 60,
            "",
            f"Final State (Year {linear['year']}):",
            f"  {'Metric':<25} {'Linear':>12} {'Torus':>12}",
            f"  {'-'*25} {'-'*12} {'-'*12}",
            f"  {'Soil Organic Matter (%)':<25} {linear['soil_organic_matter']:>12.2f} {torus['soil_organic_matter']:>12.2f}",
            f"  {'Water Retention (WRC)':<25} {linear['water_retention']:>12.2f} {torus['water_retention']:>12.2f}",
            f"  {'Yield (tons/acre)':<25} {linear['yield_per_acre']:>12.2f} {torus['yield_per_acre']:>12.2f}",
            f"  {'Biodiversity Index':<25} {linear['biodiversity_index']:>12.2f} {torus['biodiversity_index']:>12.2f}",
            f"  {'Resilience Score':<25} {linear['resilience_score']:>12.2f} {torus['resilience_score']:>12.2f}",
            "",
            "Advantages (Torus - Linear):",
            f"  Soil: +{comp['soil_advantage']:.2f}%",
            f"  Yield: +{comp['yield_advantage']:.2f} tons/acre",
            f"  Resilience: +{comp['resilience_advantage']:.2f}",
            f"  Water Retention: +{comp['water_advantage']:.2f}",
            "",
            "CONCLUSION:",
            "  The Torus system outperforms the Linear system in all metrics.",
            "  The transition takes 5 years to complete.",
            "  After Year 5, the system is self-sustaining and regenerative.",
            "=" * 60
        ]
        return "\n".join(lines)
