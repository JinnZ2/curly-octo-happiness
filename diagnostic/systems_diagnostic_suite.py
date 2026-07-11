"""
systems_diagnostic_suite.py
===========================
Systems Diagnostic Suite — compatibility shim + interactive demo.

The canonical implementations live in modules/ (gae.py, hnd.py, fdm.py,
transition.py); this file used to carry a second, diverged copy of GAE/
HND/FDM (see REVIEW.md §1.2/§4.6). It now re-exports the modules/
classes under the old short names and keeps the runnable demo.

Requires: networkx (see requirements.txt).

Usage:
    python diagnostic/systems_diagnostic_suite.py

    # or, as a library (short names preserved):
    from systems_diagnostic_suite import GAE, HND, FDM, TransitionSimulator
    print(GAE(nodes, edges).analyze()["diagnostic"])
"""

import os
import sys

# The canonical SDS lives in modules/; there are no packages in this repo,
# so extend sys.path relative to this file.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules"))

from gae import GAE, GeometricApplicabilityEngine, SystemMetrics            # noqa: E402
from hnd import HiddenNodeDetector, HiddenNodeSuggestion                    # noqa: E402
from fdm import (FractalDependencyMapper, FractalTree, DependencyNode,      # noqa: E402
                 NodeStatus)
from transition import TransitionSimulator, FarmState                       # noqa: E402

# Short alias kept from the old self-contained suite.
FDM = FractalDependencyMapper


class HND(HiddenNodeDetector):
    """Compatibility wrapper with the old suite's API:
    HND(nodes, edges).scan(residuals, environment)."""

    def __init__(self, nodes, edges):
        dependencies = {}
        for src, dst in edges:
            dependencies.setdefault(src, []).append(dst)
        super().__init__(model={"nodes": nodes, "dependencies": dependencies},
                         environment={})

    def scan(self, residuals, environment=None, threshold=0.1):
        if environment is not None:
            # Old API passed {var: [series]} directly.
            self.environment = {"time_series": environment, "variables": {}}
        return super().scan(residuals, threshold)


# ============================================================================
# Demo — Chemical Plant, Global Food System, Transition Simulator
# ============================================================================

def main():
    """Run the full prototype on the Chemical Plant and Global Food System."""

    print("\n" + "=" * 80)
    print("SYSTEMS DIAGNOSTIC SUITE - PROTOTYPE")
    print("=" * 80)

    # ------------------------------------------------------------------------
    # TEST 1: Chemical Plant
    # ------------------------------------------------------------------------

    print("\n\n" + "=" * 80)
    print("TEST 1: CHEMICAL PLANT")
    print("=" * 80)

    nodes = ["Sun", "Fresnel_Lens", "Pyrite", "Qanat", "Clay", "Apprentices", "Acid", "Brine", "Sage"]
    edges = [
        ("Sun", "Fresnel_Lens"),
        ("Fresnel_Lens", "Pyrite"),
        ("Pyrite", "Acid"),
        ("Qanat", "Brine"),
        ("Brine", "Sage"),
        ("Apprentices", "Fresnel_Lens"),
        ("Apprentices", "Qanat"),
        ("Apprentices", "Clay"),
        ("Clay", "Acid"),
    ]

    # GAE
    gae = GAE(nodes, edges)
    results = gae.analyze()
    print(results["diagnostic"])

    # FDM
    knowledge_base = {
        "Fresnel_Lens": ["Lens_Optics", "Lens_Frame", "Lens_Alignment"],
        "Lens_Optics": ["Glass", "Silica", "Molding"],
        "Lens_Frame": ["Scrap_Metal", "Bolts", "Wood"],
        "Lens_Alignment": ["Manual_Tracker", "Gears"],
        "Pyrite": ["Mining", "Crushing", "Transport"],
        "Mining": ["Access", "Breaking_Rock", "Lifting"],
        "Breaking_Rock": ["Steel_Tools", "Muscle"],
        "Steel_Tools": ["Scrap_Steel", "Forge", "Charcoal"],
        "Charcoal": ["Biomass", "Pyrolysis"],
        "Biomass": ["Trees", "Soil", "Water"],
        "Glass": ["Sand", "Soda_Ash", "Heat"],
        "Sand": ["Mining", "Soil"],
        "Soda_Ash": ["Chemistry", "Brine"],
        "Gears": ["Scrap_Metal", "Machining"],
        "Trees": ["Seeds", "Soil", "Water", "Sunlight"],
        "Soil": [],
        "Water": [],
        "Sunlight": [],
        "Muscle": [],
        "Seeds": [],
    }

    fdm = FDM(knowledge_base)
    tree = fdm.trace("Fresnel_Lens")
    print(fdm.generate_report(tree))

    # ------------------------------------------------------------------------
    # TEST 2: Global Food System
    # ------------------------------------------------------------------------

    print("\n\n" + "=" * 80)
    print("TEST 2: GLOBAL FOOD SYSTEM")
    print("=" * 80)

    food_nodes = ["Cropland", "Freshwater", "Fertilizer", "Fossil_Fuel", "Global_Trade", "Seed_Stock"]
    food_edges = [
        ("Fossil_Fuel", "Fertilizer"),
        ("Fertilizer", "Cropland"),
        ("Freshwater", "Cropland"),
        ("Cropland", "Global_Trade"),
        ("Global_Trade", "Seed_Stock"),
        ("Seed_Stock", "Cropland"),
    ]

    gae_food = GAE(food_nodes, food_edges)
    food_results = gae_food.analyze()
    print(food_results["diagnostic"])

    # Run HND on food system with simulated environment data
    print("\n" + "-" * 60)
    print("HIDDEN NODE DETECTION (Simulated Data)")
    print("-" * 60)

    environment = {
        "Soil_Microbiome": [0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35],
        "Pollinators": [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45],
        "Groundwater": [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55],
        "TEK": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
    }

    # Simulated residuals (model overestimates yield because hidden nodes are missing)
    residuals = [0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.32, 0.35, 0.38]

    hnd = HND(food_nodes, food_edges)
    hnd.scan(residuals, environment)
    print(hnd.generate_report())

    # ------------------------------------------------------------------------
    # TEST 3: Transition Simulator
    # ------------------------------------------------------------------------

    print("\n\n" + "=" * 80)
    print("TEST 3: TRANSITION SIMULATOR")
    print("=" * 80)

    sim = TransitionSimulator()
    results = sim.compare()
    print(sim.generate_report(results))

    print("\n" + "=" * 80)
    print("PROTOTYPE COMPLETE")
    print("=" * 80)
    print("\nThis prototype demonstrates the full Systems Diagnostic Suite.")
    print("Canonical implementations: modules/gae.py, hnd.py, fdm.py, transition.py")
    print("")


if __name__ == "__main__":
    main()
