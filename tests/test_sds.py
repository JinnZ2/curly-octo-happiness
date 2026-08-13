import random

import pytest

nx = pytest.importorskip("networkx")

from gae import GAE, GeometricApplicabilityEngine, graph_energy  # noqa: E402
from gae import _jacobi_eigenvalues                              # noqa: E402
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


# --- Phase 0.2: structural complexity + attack tolerance -------------------

STAR_NODES = [f"n{i}" for i in range(9)]
STAR_EDGES = [("n0", f"n{i}") for i in range(1, 9)]
RING_NODES = [f"r{i}" for i in range(9)]
RING_EDGES = [(f"r{i}", f"r{(i + 1) % 9}") for i in range(9)]


def test_graph_energy_matches_known_values():
    # E(K_n) = 2(n-1); E(C_5) = 6.472...
    assert graph_energy(nx.complete_graph(4)) == pytest.approx(6.0, abs=1e-6)
    assert graph_energy(nx.cycle_graph(5)) == pytest.approx(6.472136, abs=1e-5)
    assert graph_energy(nx.empty_graph(0)) == 0.0


def test_jacobi_matches_the_analytic_spectrum():
    # C_5 adjacency eigenvalues: 2, 2cos(2pi/5) x2, 2cos(4pi/5) x2
    A = nx.to_numpy_array(nx.cycle_graph(5)).tolist()
    got = sorted(_jacobi_eigenvalues(A))
    import math
    want = sorted([2.0] + [2 * math.cos(2 * math.pi / 5)] * 2
                  + [2 * math.cos(4 * math.pi / 5)] * 2)
    assert got == pytest.approx(want, abs=1e-8)


def test_star_is_hub_fragile_and_ring_is_not():
    star = GAE(STAR_NODES, STAR_EDGES).analyze()["metrics"]
    ring = GAE(RING_NODES, RING_EDGES).analyze()["metrics"]

    # Removing the star's centre leaves isolated leaves; the ring just opens up.
    assert star["hub_concentration"] > 0.8
    assert star["attack_tolerance"] < 0.2
    assert ring["hub_concentration"] < 0.1
    assert ring["attack_tolerance"] > 0.8

    # C = C1 + C2*C3 counts parts, interfaces and how tangled the wiring is.
    assert star["structural_complexity"] > len(STAR_NODES)
    assert ring["structural_complexity"] > star["structural_complexity"]


def test_complexity_scoring_pushes_fragile_systems_toward_distributed_forms():
    plain = GAE(STAR_NODES, STAR_EDGES).analyze()
    adjusted = GAE(STAR_NODES, STAR_EDGES, complexity_scoring=True).analyze()
    for geometry in ("TORUS", "ICOSAHEDRON"):
        assert adjusted["scores"][geometry] > plain["scores"][geometry]
    # The resilient ring earns no such boost (its betweenness variance is zero
    # up to floating-point dust).
    ring_plain = GAE(RING_NODES, RING_EDGES).analyze()
    ring_adjusted = GAE(RING_NODES, RING_EDGES, complexity_scoring=True).analyze()
    for geometry, score in ring_plain["scores"].items():
        assert ring_adjusted["scores"][geometry] == pytest.approx(score, abs=1e-9)


def test_complexity_scoring_is_off_by_default():
    """Existing callers keep their scores; only the metrics dict grows."""
    assert (GAE(CHAIN_NODES, CHAIN_EDGES).analyze()["scores"]
            == GeometricApplicabilityEngine().analyze(CHAIN_NODES, CHAIN_EDGES)["scores"])


# --- Phase 0.1: eps-machine acceptance criterion ---------------------------

def _driver_and_decoy(n=300, seed=1):
    """A residual driven by a hidden variable, plus a decoy that only echoes it."""
    rng = random.Random(seed)
    driver = [float((i // 7) % 3) for i in range(n)]
    residuals = [0.4 * d + 0.25 + rng.gauss(0, 0.05) for d in driver]
    decoy = [r * 2.0 + rng.gauss(0, 0.02) for r in residuals]
    return residuals, {"variables": {},
                       "time_series": {"Driver": driver, "Decoy": decoy}}


def test_epsilon_machine_keeps_the_driver_and_drops_the_echo():
    residuals, env = _driver_and_decoy()
    hnd = HiddenNodeDetector(model={"nodes": ["A", "B"], "dependencies": {}},
                             environment=env)

    # Correlation alone cannot separate them: both correlate ~1.0 with residuals.
    assert {s.name for s in hnd.scan(residuals)} == {"Driver", "Decoy"}

    kept = {s.name for s in hnd.scan(residuals, acceptance="epsilon_machine")}
    assert kept == {"Driver"}
    assert {s.name for s in hnd.rejected} == {"Decoy"}


def test_accepted_suggestions_carry_their_epsilon_machine_diagnostics():
    residuals, env = _driver_and_decoy()
    hnd = HiddenNodeDetector(model={"nodes": ["A"], "dependencies": {}},
                             environment=env)
    accepted = hnd.scan(residuals, acceptance="epsilon_machine")[0]
    d = accepted.diagnostics
    assert d["acceptance"] == "accepted"
    assert d["delta_c_mu"] >= d["margin"] and d["delta_h_mu"] >= d["margin"]
    assert d["c_mu_after"] < d["c_mu_before"]
    assert "eps-machine" in accepted.evidence
    assert "Rejected by the eps-machine criterion: Decoy" in hnd.generate_report()


def test_acceptance_skips_series_it_cannot_judge():
    residuals = [0.3] * 4
    hnd = HiddenNodeDetector(model={"nodes": []},
                             environment={"time_series": {"Short": [1.0, 2.0]}})
    accepted, diagnostics = hnd.accept_by_epsilon_machine(residuals, "Short")
    assert accepted is False and diagnostics["acceptance"] == "skipped"


def test_too_little_data_leaves_a_candidate_untested_not_refuted():
    """Below the sample-density floor the criterion abstains rather than judging."""
    residuals, env = _driver_and_decoy(n=60)
    hnd = HiddenNodeDetector(model={"nodes": []}, environment=env)
    kept = hnd.scan(residuals, acceptance="epsilon_machine")

    # Nothing is refuted on 60 samples; the candidates survive, flagged.
    assert {s.name for s in kept} == {"Driver", "Decoy"}
    assert not hnd.rejected
    assert {s.name for s in hnd.unverified} == {"Driver", "Decoy"}
    assert all(s.diagnostics["acceptance"] == "skipped" for s in kept)
    assert all(s.diagnostics["samples"] < s.diagnostics["samples_needed"]
               for s in kept)
    assert "Untested by the eps-machine criterion" in hnd.generate_report()


def test_unknown_acceptance_mode_is_rejected():
    hnd = HiddenNodeDetector(model={"nodes": []}, environment={})
    with pytest.raises(ValueError):
        hnd.scan([1.0] * 10, acceptance="vibes")


# --- Phase 2.3: antifragility as a measured claim --------------------------

def test_stress_path_is_a_mean_preserving_spread():
    sim = TransitionSimulator()
    narrow = sim.stress_path(20, 0.05, seed=1)
    wide = sim.stress_path(20, 0.20, seed=1)
    assert len(narrow) == len(wide) == 21
    assert max(wide) - min(wide) > max(narrow) - min(narrow)

    # Common random numbers: the same coin sequence at every sigma, so the paths
    # differ only in spread and f(sigma) is smooth enough to differentiate.
    def ups(path, sigma):
        return [v > sim.MEAN_SEVERITY for v in path]
    assert ups(narrow, 0.05) == ups(wide, 0.20)

    # The spread is mean-preserving over the seed ensemble, not path by path:
    # 21 coin flips do not balance exactly, which is why the measurement
    # averages over seeds rather than trusting a single run.
    def ensemble_mean(sigma):
        paths = [sim.stress_path(20, sigma, seed) for seed in range(24)]
        return sum(sum(p) for p in paths) / sum(len(p) for p in paths)
    assert ensemble_mean(0.05) == pytest.approx(ensemble_mean(0.20), abs=0.01)


def test_run_stressed_rejects_unknown_topology():
    with pytest.raises(ValueError):
        TransitionSimulator().run_stressed("SPIRAL", [0.1, 0.1])


def test_zero_stress_is_the_viability_yardstick():
    sim = TransitionSimulator()
    for topology in ("LINE", "TORUS"):
        unstressed = sim.unstressed_yield(topology)
        stressed = sim.run_stressed(topology, [0.5] * 21)
        assert min(s.yield_per_acre for s in stressed) <= unstressed


def test_convexity_measures_curvature_and_viability():
    sim = TransitionSimulator()
    m = sim.convexity("TORUS")
    assert m["shape"] in ("convex", "concave", "linear")
    assert m["triad"] in ("antifragile", "robust", "fragile", "fragile (ruined)")
    # antifragile requires convexity AND survival, never one alone.
    assert m["antifragile"] == bool(m["d2f_dsigma2"] > 0 and m["viable"])


def test_measured_shapes_at_the_default_operating_point():
    """The plan predicted LINE concave / TORUS convex. Only the first holds.

    TORUS turns out *robust*, not antifragile: its buffer absorbs the whole
    spread, so widening the spread neither gains nor costs it much. Pinning the
    measurement here means a mechanism change that flips it has to be noticed.
    """
    sim = TransitionSimulator()
    line = sim.convexity("LINE")
    torus = sim.convexity("TORUS")

    assert line["shape"] == "concave"
    assert not line["viable"]              # LINE is already ruined at mean 0.30
    assert line["triad"] == "fragile (ruined)"

    assert torus["viable"]
    assert torus["triad"] == "robust"
    assert not torus["antifragile"]


def test_antifragility_claim_records_its_own_refutation():
    sim = TransitionSimulator()
    claim, m = sim.antifragility_claim("TORUS")
    # The claim carries an executable refutation test, so text and check agree.
    assert claim.falsifiability == "machine-checkable"
    assert claim.passed + claim.failed == 1
    assert (claim.passed == 1) == m["antifragile"]
    assert claim.scope["topology"] == "TORUS"


def test_regime_scan_restores_the_mean_severity():
    sim = TransitionSimulator()
    original = sim.MEAN_SEVERITY
    rows = sim.regime_scan("TORUS", means=(0.2, 0.8))
    assert sim.MEAN_SEVERITY == original
    assert [r["mean_severity"] for r in rows] == [0.2, 0.8]
    # Curvature is regime-dependent; that is the finding, not a nuisance.
    assert rows[0]["d2f_dsigma2"] != rows[1]["d2f_dsigma2"]


def test_convexity_of_ruin_is_not_antifragility():
    """LINE goes convex at high stress only because yield has bottomed out."""
    sim = TransitionSimulator()
    convex_and_ruined = [r for r in sim.regime_scan("LINE", means=(0.4, 0.6, 0.8))
                         if r["d2f_dsigma2"] > 0]
    assert convex_and_ruined, "expected LINE to go convex under heavy stress"
    for row in convex_and_ruined:
        assert not row["viable"]
        assert not row["antifragile"]
        assert row["triad"] == "fragile (ruined)"


def test_antifragility_report_renders():
    text = TransitionSimulator().antifragility_report()
    assert "REGIME SCAN" in text and "LINE" in text and "TORUS" in text


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
