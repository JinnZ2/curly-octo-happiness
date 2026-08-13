# main.py
"""
Systems Diagnostic Suite (SDS)

Integrates GAE, HND, and FDM into a single diagnostic pipeline.
"""

from typing import Dict, List, Tuple

from gae import GeometricApplicabilityEngine
from hnd import HiddenNodeDetector
from fdm import FractalDependencyMapper

def diagnose_system(
    nodes: List[str],
    edges: List[Tuple[str, str]],
    knowledge_base: Dict[str, List[str]],
    residuals: List[float] = None,
    environment: Dict = None,
    complexity_scoring: bool = False,
    hnd_acceptance: str = "correlation"
) -> Dict:
    """
    Run full diagnostic on a system.

    Args:
        complexity_scoring: let structural complexity and attack tolerance
            adjust the GAE geometry scores (see GeometricApplicabilityEngine).
        hnd_acceptance: "correlation" or "epsilon_machine" (see
            HiddenNodeDetector.scan). The ε-machine criterion treats the
            correlation thresholds as a candidate generator and only accepts
            variables that measurably simplify the residual stream.

    Returns:
        {
            "gae": GAE output,
            "hnd": HND output (if residuals provided),
            "fdm": FDM output for each root node
        }
    """
    results = {}

    # 1. Run GAE
    gae = GeometricApplicabilityEngine(complexity_scoring=complexity_scoring)
    results["gae"] = gae.analyze(nodes, edges)

    # 2. Run HND if residuals provided
    if residuals is not None:
        # HND expects dependencies as {source: [targets]}, not an edge list
        dependencies = {}
        for src, dst in edges:
            dependencies.setdefault(src, []).append(dst)
        hnd = HiddenNodeDetector(
            model={"nodes": nodes, "dependencies": dependencies},
            environment=environment or {}
        )
        suggestions = hnd.scan(residuals, acceptance=hnd_acceptance)
        results["hnd"] = {
            "suggestions": [s.__dict__ for s in suggestions],
            "rejected": [s.__dict__ for s in hnd.rejected],
            "report": hnd.generate_report()
        }

    # 3. Run FDM for each node
    fdm = FractalDependencyMapper(knowledge_base)
    results["fdm"] = {}
    for node in nodes:
        tree = fdm.trace(node)
        results["fdm"][node] = {
            "max_depth": tree.max_depth,
            "primitive_roots": list(tree.primitive_roots),
            "active_branches": tree.active_branches,
            "broken_branches": tree.broken_branches,
            "report": fdm.generate_report(tree)
        }

    return results

# Example usage
if __name__ == "__main__":
    # Chemical Plant nodes and edges
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

    # Knowledge base for FDM — shared data file (data/chemical_plant_kb.json)
    import os
    from fdm import load_knowledge_base
    _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    knowledge_base = load_knowledge_base(os.path.join(_data_dir, "chemical_plant_kb.json"))

    # A residual stream driven by an unmodelled seasonal variable, plus a decoy
    # that merely echoes the residual back. Correlation alone cannot tell them
    # apart; the eps-machine acceptance criterion can.
    import random
    random.seed(7)
    # 320 samples: the acceptance criterion refuses to answer below roughly
    # MIN_SAMPLES_PER_HISTORY * |alphabet|^L, and a demo that gets refused
    # teaches the wrong lesson.
    season = [float((i // 7) % 3) for i in range(320)]
    residuals = [0.4 * s + 0.25 + random.gauss(0, 0.05) for s in season]
    environment = {
        "variables": {},
        "time_series": {
            "Seasonal_Water_Table": season,
            "Ledger_Copy": [r * 2.0 + random.gauss(0, 0.02) for r in residuals],
        },
    }

    # Run full diagnostic with both Phase 0 upgrades enabled
    results = diagnose_system(nodes, edges, knowledge_base,
                              residuals=residuals, environment=environment,
                              complexity_scoring=True,
                              hnd_acceptance="epsilon_machine")

    # Print GAE results
    print(results["gae"]["diagnostic"])

    # Print HND results
    print(results["hnd"]["report"])

    # Print FDM for Fresnel_Lens
    print(results["fdm"]["Fresnel_Lens"]["report"])
