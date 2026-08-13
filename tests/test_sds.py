import pytest

nx = pytest.importorskip("networkx")

from gae import GAE, GeometricApplicabilityEngine  # noqa: E402
from fdm import FractalDependencyMapper            # noqa: E402
from hnd import HiddenNodeDetector                 # noqa: E402
from transition import TransitionSimulator         # noqa: E402

CHAIN_NODES = ["A", "B", "C", "D"]
CHAIN_EDGES = [("A", "B"), ("B", "C"), ("C", "D")]
CYCLE_EDGES = [("A", "B"), ("B", "C"), ("C", "A")]

KNOWLEDGE_BASE = {
    "Fresnel_Lens": ["Lens_Optics", "Lens_Frame"],
    "Lens_Optics": ["Glass"],
    "Glass": ["Sand", "Heat"],
    "Lens_Frame": ["Wood"],
}


def test_gae_wrapper_and_depth_variance():
    res = GAE(CHAIN_NODES, CHAIN_EDGES).analyze()
    # A chain has strictly decreasing downstream depth -> nonzero variance
    # (this was always 0 before the dag_longest_path_length fix, §3.8)
    assert res["metrics"]["recursive_variance"] > 0
    assert res["metrics"]["cycle_density"] == 0
    assert res["recommendation"] in GeometricApplicabilityEngine.GEOMETRIES


def test_gae_detects_cycles():
    res = GAE(["A", "B", "C"], CYCLE_EDGES).analyze()
    assert res["metrics"]["cycle_density"] == 1.0
    assert res["scores"]["TORUS"] > 0


def test_fdm_max_depth_not_zero():
    fdm = FractalDependencyMapper(KNOWLEDGE_BASE)
    tree = fdm.trace("Fresnel_Lens")
    assert tree.max_depth == 3          # Fresnel_Lens > Lens_Optics > Glass > Sand
    assert "SAND" in tree.primitive_roots or "Sand" in tree.primitive_roots


def test_hnd_finds_correlated_hidden_variable():
    residuals = [0.1 * i + 0.2 for i in range(10)]
    env = {"time_series": {"Hidden_X": [0.1 * i for i in range(10)]}, "variables": {}}
    hnd = HiddenNodeDetector(model={"nodes": CHAIN_NODES, "dependencies": {}},
                             environment=env)
    names = [s.name for s in hnd.scan(residuals)]
    assert "Hidden_X" in names


def test_transition_years_advance():
    sim = TransitionSimulator()
    for states in (sim.run_linear(5), sim.run_torus(5)):
        assert [s.year for s in states] == list(range(6))


def test_diagnostic_shim_exports():
    from systems_diagnostic_suite import GAE as ShimGAE, HND, FDM
    res = ShimGAE(CHAIN_NODES, CHAIN_EDGES).analyze()
    assert "recommendation" in res
    hnd = HND(CHAIN_NODES, CHAIN_EDGES)
    residuals = [0.1 * i + 0.2 for i in range(10)]
    suggestions = hnd.scan(residuals, {"Hidden_X": [0.1 * i for i in range(10)]})
    assert any(s.name == "Hidden_X" for s in suggestions)
    assert FDM(KNOWLEDGE_BASE).trace("Glass").max_depth == 1
