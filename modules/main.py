# main.py
"""
Systems Diagnostic Suite (SDS)

Integrates GAE, HND, and FDM into a single diagnostic pipeline.
"""

from gae import GeometricApplicabilityEngine
from hnd import HiddenNodeDetector
from fdm import FractalDependencyMapper

def diagnose_system(
    nodes: List[str],
    edges: List[Tuple[str, str]],
    knowledge_base: Dict[str, List[str]],
    residuals: List[float] = None,
    environment: Dict = None
) -> Dict:
    """
    Run full diagnostic on a system.

    Returns:
        {
            "gae": GAE output,
            "hnd": HND output (if residuals provided),
            "fdm": FDM output for each root node
        }
    """
    results = {}

    # 1. Run GAE
    gae = GeometricApplicabilityEngine()
    results["gae"] = gae.analyze(nodes, edges)

    # 2. Run HND if residuals provided
    if residuals is not None:
        hnd = HiddenNodeDetector(
            model={"nodes": nodes, "dependencies": edges},
            environment=environment or {}
        )
        suggestions = hnd.scan(residuals)
        results["hnd"] = {
            "suggestions": [s.__dict__ for s in suggestions],
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

    # Knowledge base for FDM
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
        "Scrap_Metal": ["Recycling", "Steel_Tools"],
        "Trees": ["Seeds", "Soil", "Water", "Sunlight"],
        "Soil": [],  # Primitive
        "Water": [], # Primitive
        "Sunlight": [], # Primitive
        "Muscle": [], # Primitive
        "Seeds": [], # Primitive
    }

    # Run full diagnostic
    results = diagnose_system(nodes, edges, knowledge_base)

    # Print GAE results
    print(results["gae"]["diagnostic"])

    # Print FDM for Fresnel_Lens
    print(results["fdm"]["Fresnel_Lens"]["report"])
