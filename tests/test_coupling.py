"""Coupling from physics: the MSF class, the eigenratio criterion, partitions."""

import math
from math import inf

import pytest

from grounding.core.coupling import (
    MSFWindow,
    components,
    coupling_coherence,
    estimate_msf_window,
    format_coupling,
    laplacian,
    optimal_coupling,
    spectrum,
    synchronizable,
)
from grounding.core.linalg import symmetric_eigenvalues
from grounding.worlds.thermal import ThermalWorld

RING5 = [[0, 1, 0, 0, 1],
         [1, 0, 1, 0, 0],
         [0, 1, 0, 1, 0],
         [0, 0, 1, 0, 1],
         [1, 0, 0, 1, 0]]

SPLIT = [[0, 1, 0, 0],
         [1, 0, 0, 0],
         [0, 0, 0, 1],
         [0, 0, 1, 0]]


def star(n):
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(1, n):
        matrix[0][i] = matrix[i][0] = 1.0
    return matrix


CLASS_III = MSFWindow(nu_lower=0.2, nu_upper=4.0, system="illustrative")
CLASS_II = MSFWindow(nu_lower=0.2, nu_upper=inf, system="illustrative")


# --- the shared eigensolver -------------------------------------------------

def test_symmetric_eigenvalues_matches_a_known_spectrum():
    # Path graph P_3 Laplacian: eigenvalues 0, 1, 3.
    L = [[1, -1, 0], [-1, 2, -1], [0, -1, 1]]
    assert symmetric_eigenvalues(L) == pytest.approx([0.0, 1.0, 3.0], abs=1e-9)


def test_eigensolver_refuses_a_hopeless_stdlib_solve_rather_than_hanging():
    import grounding.core.linalg as linalg
    if linalg._np is not None:
        pytest.skip("numpy present: no cap applies")
    with pytest.raises(ValueError):
        symmetric_eigenvalues([[0.0] * 200 for _ in range(200)], cap=160)


# --- the topology half ------------------------------------------------------

def test_laplacian_rows_sum_to_zero():
    L = laplacian(RING5)
    assert all(sum(row) == pytest.approx(0.0, abs=1e-12) for row in L)


def test_laplacian_rejects_directed_and_negative_coupling():
    with pytest.raises(ValueError):
        laplacian([[0, 1], [0, 0]])          # asymmetric
    with pytest.raises(ValueError):
        laplacian([[0, -1], [-1, 0]])        # negative weight
    with pytest.raises(ValueError):
        laplacian([[0]])                     # a network needs two units


def test_ring_spectrum_and_eigenratio():
    spec = spectrum(RING5)
    assert spec.connected and spec.n_components == 1
    assert spec.lambda_2 > 0
    assert spec.eigenratio == pytest.approx(spec.lambda_n / spec.lambda_2)


def test_a_star_is_harder_to_synchronize_than_a_ring():
    """Eigenratio is the topology half, and a hub concentrates it."""
    assert spectrum(star(8)).eigenratio > spectrum(RING5).eigenratio


def test_disconnected_network_has_zero_connectivity_and_infinite_eigenratio():
    spec = spectrum(SPLIT)
    assert not spec.connected
    assert spec.n_components == 2
    assert spec.lambda_2 == 0.0
    assert spec.eigenratio == inf
    assert "fragmentation as a structural fact" in " ".join(spec.warnings)


def test_components_say_who_is_on_which_side():
    """When a network splits, the operator needs the partition, not the count."""
    assert components(SPLIT) == [[0, 1], [2, 3]]
    assert components(RING5) == [[0, 1, 2, 3, 4]]


# --- the MSF class is computed, not assumed ---------------------------------

def test_scalar_linear_dynamics_are_class_ii_not_class_iii():
    """The repo's own thermal unit, and the module's central warning.

    Df = -k < 0 for a thermal unit, so the transverse exponent is strictly
    decreasing in alpha and crosses zero once. Asserting an interior coupling
    optimum for these dynamics would invent a penalty physics does not impose —
    which is exactly what a hand-supplied Gaussian bump would have done.
    """
    window = estimate_msf_window(-ThermalWorld.COOLING, system="ThermalWorld unit")
    assert window is not None
    assert window.msf_class == "II"
    assert window.nu_upper == inf
    assert not window.has_interior_optimum
    assert window.width_ratio == inf


def test_an_unstable_node_gets_a_threshold_at_its_growth_rate():
    window = estimate_msf_window(0.5, alpha_max=4.0, resolution=80)
    assert window.msf_class == "II"
    assert window.nu_lower == pytest.approx(0.5, abs=0.1)


def test_class_i_returns_none_rather_than_a_fabricated_window():
    """Coupling with no leverage on the unstable direction never stabilises."""
    assert estimate_msf_window(0.5, coupling=[[0.0]]) is None


def test_rossler_is_class_iii():
    """A bounded window needs vector dynamics; this is the textbook case."""
    a, b, c = 0.2, 0.2, 5.7

    def flow(s, dt):
        x, y, z = s
        return [x + dt * (-y - z), y + dt * (x + a * y),
                z + dt * (b + z * (x - c))]

    def jacobian(s):
        x, y, z = s
        return [[0.0, -1.0, -1.0], [1.0, a, 0.0], [z, 0.0, x - c]]

    state = [0.1, 0.1, 0.1]
    for _ in range(20000):
        state = flow(state, 0.01)

    window = estimate_msf_window(
        jacobian, flow=flow, coupling=[[1.0, 0, 0], [0, 0, 0], [0, 0, 0]],
        state=state, alpha_max=12.0, resolution=60, horizon=8000, dt=0.01,
        system="Rossler, x-coupled")
    assert window is not None
    assert window.msf_class == "III"
    assert window.has_interior_optimum
    # Literature: nu_1 ~ 0.19, nu_2 ~ 4.6 for a=b=0.2, c=5.7.
    assert 0.05 < window.nu_lower < 0.6
    assert 3.5 < window.nu_upper < 6.0


def test_window_construction_rejects_impossible_bounds():
    with pytest.raises(ValueError):
        MSFWindow(nu_lower=0.0)
    with pytest.raises(ValueError):
        MSFWindow(nu_lower=1.0, nu_upper=0.5)


# --- the two halves together ------------------------------------------------

def test_eigenratio_criterion_decides_synchronizability():
    ring, hub = spectrum(RING5), spectrum(star(24))
    assert synchronizable(ring, CLASS_III)
    # A star's Laplacian spectrum is {0, 1 (x n-2), n}, so its eigenratio *is*
    # its size: centralise hard enough and no coupling strength can hold it.
    assert hub.eigenratio == pytest.approx(24.0)
    assert hub.eigenratio > CLASS_III.width_ratio
    assert not synchronizable(hub, CLASS_III)
    # Class II tolerates any spread, because it has no upper bound to exceed.
    assert synchronizable(hub, CLASS_II)


def test_the_interior_optimum_is_the_geometric_centre():
    spec = spectrum(RING5)
    sigma = optimal_coupling(spec, CLASS_III)
    assert sigma == pytest.approx(
        math.sqrt(CLASS_III.nu_lower * CLASS_III.nu_upper
                  / (spec.lambda_2 * spec.lambda_n)))
    # ...and it is the peak: f(C) is 1 there and lower on both sides.
    peak = coupling_coherence(sigma, RING5, CLASS_III)
    assert peak.coherence == pytest.approx(1.0, abs=1e-9)
    assert coupling_coherence(sigma / 2, RING5, CLASS_III).coherence < peak.coherence
    assert coupling_coherence(sigma * 2, RING5, CLASS_III).coherence < peak.coherence


def test_class_ii_has_no_interior_optimum_to_report():
    assert optimal_coupling(spectrum(RING5), CLASS_II) is None
    reading = coupling_coherence(50.0, RING5, CLASS_II)
    assert reading.regime == "STABLE"
    assert reading.coherence == 1.0        # binary, not an invented gradient
    assert "threshold here, not an optimum" in " ".join(reading.notes)


def test_too_weak_and_too_strong_are_distinct_regimes():
    spec = spectrum(RING5)
    sigma = optimal_coupling(spec, CLASS_III)
    assert coupling_coherence(sigma / 100, RING5, CLASS_III).regime == "FRAGMENTED"
    assert coupling_coherence(sigma * 100, RING5, CLASS_III).regime == "RIGID"


def test_a_partition_is_reported_as_structure_not_mistuning():
    reading = coupling_coherence(1.0, SPLIT, CLASS_III)
    assert reading.regime == "FRAGMENTED_STRUCTURALLY"
    assert reading.coherence == 0.0
    assert not reading.synchronizable
    assert reading.n_components == 2
    joined = " ".join(reading.notes)
    assert "surviving components: [[0, 1], [2, 3]]" in joined
    assert "not because the coupling strength is mistuned" in joined


def test_a_star_grows_its_own_eigenratio():
    """Hub-and-spoke gets harder to hold together as it grows, linearly."""
    assert spectrum(star(6)).eigenratio == pytest.approx(6.0)
    assert spectrum(star(12)).eigenratio == pytest.approx(12.0)
    assert spectrum(star(24)).eigenratio == pytest.approx(24.0)


def test_a_network_no_coupling_can_fix_says_so():
    reading = coupling_coherence(1.0, star(24), CLASS_III)
    assert reading.regime == "NO_STABLE_WINDOW"
    assert not reading.synchronizable
    assert "a different network, not a different coupling strength" in \
        " ".join(reading.notes)


def test_negative_coupling_is_rejected():
    with pytest.raises(ValueError):
        coupling_coherence(-1.0, RING5, CLASS_III)


def test_format_renders_the_reading():
    text = format_coupling(coupling_coherence(1.0, SPLIT, CLASS_III))
    assert "FRAGMENTED_STRUCTURALLY" in text
    assert "Some systems should not synchronize" in text
