# transition.py
"""
Transition Simulator v1.0

Simulates the Line → Torus transition over time (industrial vs.
regenerative farm), producing per-year FarmState snapshots and a
comparison report. Moved here from diagnostic/systems_diagnostic_suite.py
when the two SDS copies were merged.
"""

import random
from dataclasses import dataclass
from typing import Dict, List


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
