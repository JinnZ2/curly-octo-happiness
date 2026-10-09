"""Coupling from physics: when a network of units can hold together, and when not.

"Too weak = fragmented, too strong = rigid" is a real phenomenon, but written as
a bump around a chosen optimum it is an assertion dressed as a measurement —
move the chosen centre and the optimum moves with it. Synchronization theory
derives the same shape from the dynamics, with no aesthetic parameter.

For N identical units coupled through a network, the Master Stability Function
(Pecora & Carroll 1998, PRL 80:2109) reduces stability of the synchronous state
to one scalar condition. With Laplacian eigenvalues
0 = L1 <= L2 <= ... <= LN and coupling strength `sigma`, the synchronous state
is stable exactly when every scaled eigenvalue lands in the MSF's negative
region:

    nu_1 < sigma * L_i < nu_2      for i = 2..N

Huang, Chen, Lai & Pecora (2009, PRE 80:036204): only three behaviours are
possible for any pair of node dynamics and coupling function.

    Class I    the MSF never goes negative — no coupling strength synchronizes,
               and there is no optimum because there is no stable region.
    Class II   one crossing. Stable for every sigma above a threshold. Physics
               gives a threshold, not an optimum: more coupling is never worse.
    Class III  two crossings. Stable only inside a bounded window — the slowest
               mode never locks below it, the fastest goes unstable above it.

**The interior optimum is a Class III property, not a law.** Asserting one for a
Class II system invents a penalty the dynamics do not impose, so this module
reports the class rather than assuming it — and `estimate_msf_window` *computes*
the class from the node dynamics rather than taking it on faith. A supplied
window would only relocate the assertion.

Two consequences worth the space
--------------------------------
1. **Fragmentation is structural, not a mistuning.** A disconnected network has
   L2 = 0, so no sigma satisfies the lower bound. "Too weak" is not a statement
   about turning coupling down far enough; it is a statement that the network
   has no path.

2. **Some networks cannot be fixed by tuning at all.** Both bounds hold together
   only when the eigenratio criterion is met (Barahona & Pecora 2002,
   PRL 89:054101):

       L_N / L_2  <  nu_2 / nu_1

   Left side pure topology, right side pure dynamics. Exceed it and *no*
   coupling strength works; the only remedy is a different network.

Measurement, not control
------------------------
Reporting that a network sits outside its window is not an instruction to retune
it. Plenty of real systems should not be synchronized, and a high eigenratio is
sometimes exactly what keeps a failure local — which is the same insight the
safety layer reaches from the other direction.

Stdlib only (numpy accelerates the eigensolve, see `core/linalg.py`).
"""

from dataclasses import dataclass, field
from math import inf, isinf, log, sqrt
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from grounding.core.linalg import symmetric_eigenvalues

__all__ = [
    "CouplingReading",
    "MSFWindow",
    "SpectrumReading",
    "components",
    "coupling_coherence",
    "estimate_msf_window",
    "format_coupling",
    "laplacian",
    "optimal_coupling",
    "spectrum",
    "synchronizable",
]

# Eigenvalues below this are the Laplacian's structural zeros rather than small
# positive numbers. Every Laplacian has at least one exact zero; floating point
# puts it near, not at, zero.
CONNECTIVITY_TOLERANCE = 1e-9

Matrix = Sequence[Sequence[float]]


# ---------------------------------------------------------------------------
# the dynamics half
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MSFWindow:
    """The negative region of a Master Stability Function.

    A property of the *node dynamics and coupling function*, not of any network.
    Prefer `estimate_msf_window` to construct one: a hand-supplied window makes
    the MSF class an input, which is the assertion this module exists to avoid.
    """

    nu_lower: float
    nu_upper: float = inf
    source: str = ""
    system: str = ""

    def __post_init__(self) -> None:
        if self.nu_lower <= 0:
            raise ValueError(
                "nu_lower must be positive; a non-positive lower crossing makes "
                "the scaled coupling condition vacuous")
        if self.nu_upper <= self.nu_lower:
            raise ValueError("nu_upper must exceed nu_lower")

    @property
    def msf_class(self) -> str:
        """"II" (threshold only) or "III" (bounded window).

        Class I cannot be expressed as a window at all; `estimate_msf_window`
        returns None for it rather than inventing bounds.
        """
        return "II" if isinf(self.nu_upper) else "III"

    @property
    def width_ratio(self) -> float:
        """nu_2 / nu_1 — the dynamics' tolerance for spectral spread.

        The quantity a network's eigenratio must come in under. Infinite for
        Class II: those dynamics tolerate any spread.
        """
        return inf if isinf(self.nu_upper) else self.nu_upper / self.nu_lower

    @property
    def has_interior_optimum(self) -> bool:
        """True only for Class III. Class II has a threshold, not a peak."""
        return self.msf_class == "III"


State = Sequence[float]


def _transverse_exponent(jacobian: Callable[[State], Sequence[Sequence[float]]],
                         flow: Callable[[State, float], State],
                         coupling: Sequence[Sequence[float]],
                         state: State, alpha: float,
                         horizon: int, dt: float) -> float:
    """Max Lyapunov exponent of zeta' = [Df(s) - alpha*H] zeta along the flow."""
    dimension = len(coupling)
    zeta = [1.0] + [0.0] * (dimension - 1)
    total, current = 0.0, list(state)

    for _ in range(horizon):
        J = jacobian(current)
        # zeta' = M zeta, integrated with a small explicit step. dt must be
        # small relative to 1/|M| or the *integrator* goes unstable and gets
        # reported as the dynamics doing so.
        derivative = [sum((J[i][j] - alpha * coupling[i][j]) * zeta[j]
                          for j in range(dimension))
                      for i in range(dimension)]
        zeta = [zeta[i] + dt * derivative[i] for i in range(dimension)]

        norm = sqrt(sum(v * v for v in zeta))
        if norm <= 0.0:
            return -inf
        total += log(norm)
        zeta = [v / norm for v in zeta]
        current = list(flow(current, dt))

    return total / (horizon * dt)


def estimate_msf_window(jacobian, flow=None, coupling=None, state=None,
                        alpha_max: float = 20.0, resolution: int = 200,
                        horizon: int = 4000, dt: float = 0.01,
                        system: str = "") -> Optional[MSFWindow]:
    """Compute the MSF's negative region from the node dynamics.

    The transverse perturbation of a synchronized state obeys

        zeta' = [ Df(s) - alpha * H ] zeta

    so the MSF is the maximum Lyapunov exponent of that equation as a function
    of the scaled coupling `alpha = sigma * lambda`. This scans alpha and
    returns the interval where the exponent is negative.

    Args:
        jacobian: Df. Either a callable state -> matrix, or a plain number for
            scalar linear dynamics (see the note below).
        flow: state -> next state along the synchronization manifold. Only
            needed when the Jacobian is state-dependent.
        coupling: H, the coupling matrix. Defaults to the identity.
        state: starting point on the manifold.
        alpha_max, resolution: the scan.
        horizon, dt: integration for each exponent. `dt` must be small relative
            to the fastest timescale in Df — an Euler step too large makes the
            *integrator* unstable at high alpha and reports a spurious upper
            crossing, which would manufacture a Class III window out of Class II
            dynamics. That is the exact failure this module exists to prevent,
            so the default is conservative.

    Returns:
        An `MSFWindow`, or **None** for Class I dynamics where the exponent is
        never negative and no coupling strength synchronizes. None is the honest
        answer there; a window would be a fabrication.

    Note on scalar dynamics: for one-dimensional real node dynamics with scalar
    coupling the exponent is `mean(Df) - alpha*Dh`, strictly decreasing in
    alpha, so it crosses zero exactly once. **Scalar dynamics are therefore
    always Class I or Class II and can never be Class III** — a bounded window
    needs a vector variational equation, where raising alpha can destabilise a
    different mode than it stabilised. Anything reporting an interior optimum
    for a scalar system has found a numerical artefact.
    """
    if not callable(jacobian):
        constant = float(jacobian)
        jacobian_fn = lambda s: [[constant]]
        dimension = 1
    else:
        probe = jacobian(state if state is not None else [0.0])
        dimension = len(probe)
        jacobian_fn = jacobian

    if coupling is None:
        coupling = [[1.0 if i == j else 0.0 for j in range(dimension)]
                    for i in range(dimension)]
    if flow is None:
        flow = lambda s, step: s
    if state is None:
        state = [0.0] * dimension

    def exponent(alpha: float) -> float:
        return _transverse_exponent(jacobian_fn, flow, coupling, state,
                                    alpha, horizon, dt)

    alphas = [alpha_max * i / resolution for i in range(resolution + 1)]
    negative = [a for a in alphas if a > 0 and exponent(a) < 0]
    if not negative:
        return None                      # Class I: never stable

    lower, upper = negative[0], negative[-1]
    # Still negative at the top of the scan: unbounded above (Class II). Report
    # that rather than passing the scan's own edge off as physics.
    if upper >= alphas[-1] - 1e-12:
        return MSFWindow(nu_lower=lower, nu_upper=inf,
                         source="estimated by transverse Lyapunov exponent",
                         system=system)
    return MSFWindow(nu_lower=lower, nu_upper=upper,
                     source="estimated by transverse Lyapunov exponent",
                     system=system)


# ---------------------------------------------------------------------------
# the topology half
# ---------------------------------------------------------------------------

@dataclass
class SpectrumReading:
    """Laplacian spectrum of a coupling network."""

    eigenvalues: List[float]
    lambda_2: float                  # algebraic connectivity (Fiedler value)
    lambda_n: float                  # largest Laplacian eigenvalue
    eigenratio: float                # L_N / L_2, inf if disconnected
    connected: bool = True
    n_components: int = 1
    warnings: List[str] = field(default_factory=list)


def laplacian(adjacency: Matrix) -> List[List[float]]:
    """Combinatorial graph Laplacian L = D - A. Self-loops are ignored."""
    rows = [list(row) for row in adjacency]
    n = len(rows)
    if n < 2 or any(len(r) != n for r in rows):
        raise ValueError("adjacency must be square with at least two units")
    for i in range(n):
        for j in range(n):
            if abs(rows[i][j] - rows[j][i]) > 1e-9:
                raise ValueError(
                    "adjacency must be symmetric; the eigenratio criterion is "
                    "derived for undirected coupling, and a directed network "
                    "needs the complex-plane form of the condition instead")
            if rows[i][j] < 0:
                raise ValueError("adjacency weights must be non-negative")
        rows[i][i] = 0.0

    L = [[-rows[i][j] for j in range(n)] for i in range(n)]
    for i in range(n):
        L[i][i] = sum(rows[i])
    return L


def components(adjacency: Matrix) -> List[List[int]]:
    """Connected components as index lists — who can still reach whom.

    The spectrum says *how many* components there are; when a network
    fragments, what an operator needs is *which units are on which side*.
    """
    rows = [list(row) for row in adjacency]
    n = len(rows)
    seen, groups = set(), []
    for start in range(n):
        if start in seen:
            continue
        group, frontier = [], [start]
        seen.add(start)
        while frontier:
            node = frontier.pop()
            group.append(node)
            for other in range(n):
                if other not in seen and rows[node][other] > 0:
                    seen.add(other)
                    frontier.append(other)
        groups.append(sorted(group))
    return groups


def spectrum(adjacency: Matrix) -> SpectrumReading:
    """Laplacian spectrum and eigenratio of a coupling network.

    The eigenratio L_N / L_2 is the topology half of synchronizability: smaller
    means a wider range of coupling strengths keeps every mode stable. A
    disconnected network has L_2 = 0 and an infinite eigenratio — no coupling
    strength synchronizes it, at any setting.
    """
    values = symmetric_eigenvalues(laplacian(adjacency))
    values = [0.0 if abs(v) < CONNECTIVITY_TOLERANCE else v for v in values]

    n_zero = sum(1 for v in values if v == 0.0)
    lambda_2, lambda_n = values[1], values[-1]
    connected = n_zero == 1
    warnings: List[str] = []

    if not connected:
        ratio = inf
        warnings.append(
            f"network splits into {n_zero} components (lambda_2 = 0). No "
            "coupling strength synchronizes a disconnected network — this is "
            "fragmentation as a structural fact, not a tuning problem.")
    else:
        ratio = lambda_n / lambda_2

    return SpectrumReading(eigenvalues=values, lambda_2=lambda_2,
                           lambda_n=lambda_n, eigenratio=ratio,
                           connected=connected, n_components=n_zero,
                           warnings=warnings)


# ---------------------------------------------------------------------------
# path parity: which similarity readings can see a coupled pair at all
# ---------------------------------------------------------------------------
#
# A Laplacian spectrum says whether units can hold together. A different
# question comes up whenever a network is *read* for relatedness -- by
# shared neighbours, by a factorization, by an embedding: can the reading see
# that two units are coupled? In a two-colourable (bipartite) component every
# path between two units has the same parity. Readings built from even powers
# of the adjacency (shared neighbours, A^2, unsigned SVD of A) link only
# same-colour pairs; readings built from odd powers (direct links, A, the
# signed metric) link only opposite-colour pairs. Each family is blind to the
# other half of the coupled pairs, exactly, at any distance. One odd cycle in
# the component opens both parities and the blindness becomes a matter of
# degree. (Worked toy: PPMI->SVD read every even path at 1.00 and every odd
# path at or below chance; JinnZ2/measurement-scope-gaps, cut-recoverability
# runs 6-8.)

@dataclass
class ParityReading:
    """Two-colouring of each component; None where an odd cycle exists."""

    colouring: Dict[int, int]            # unit -> 0/1, bipartite components only
    bipartite_components: List[List[int]]
    odd_cycle_components: List[List[int]]


def parity(adjacency: Matrix) -> ParityReading:
    """Two-colour each connected component by BFS, or report its odd cycle."""
    rows = [list(row) for row in adjacency]
    n = len(rows)
    colouring: Dict[int, int] = {}
    bipartite, odd = [], []
    for group in components(adjacency):
        local = {group[0]: 0}
        frontier, ok = [group[0]], True
        while frontier and ok:
            node = frontier.pop()
            for other in range(n):
                if other == node or rows[node][other] <= 0:
                    continue
                if other not in local:
                    local[other] = 1 - local[node]
                    frontier.append(other)
                elif local[other] == local[node]:
                    ok = False
                    break
        if ok:
            colouring.update(local)
            bipartite.append(group)
        else:
            odd.append(group)
    return ParityReading(colouring=colouring, bipartite_components=bipartite,
                         odd_cycle_components=odd)


def pair_visibility(adjacency: Matrix, i: int, j: int,
                    reading: Optional[ParityReading] = None) -> str:
    """Which reading family can see the coupling between units i and j.

    "none"       no path: different components (no reading can recover it)
    "even-only"  bipartite, same colour: shared-neighbour / A^2 readings see
                 it, direct / odd readings cannot
    "odd-only"   bipartite, opposite colours: the reverse
    "both"       the component holds an odd cycle, so paths of both parities
                 exist (strength still varies by reading)
    """
    reading = reading or parity(adjacency)
    for group in reading.odd_cycle_components:
        if i in group:
            return "both" if j in group else "none"
    for group in reading.bipartite_components:
        if i in group:
            if j not in group:
                return "none"
            same = reading.colouring[i] == reading.colouring[j]
            return "even-only" if same else "odd-only"
    return "none"


def shared_neighbour_similarity(adjacency: Matrix, i: int, j: int) -> float:
    """Cosine of adjacency rows -- the even-path (A^2) reading of a pair."""
    a, b = list(adjacency[i]), list(adjacency[j])
    a[i] = a[j] = b[i] = b[j] = 0.0       # direct link is the odd-path reading
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def reading_blindspots(adjacency: Matrix,
                       pairs: Sequence[Tuple[int, int]]) -> List[Dict[str, Any]]:
    """Coupled pairs a shared-neighbour reading scores at zero, and why.

    Each row: the pair, its visibility class, the even-path score. A pair that
    is connected but scores 0 is not unrelated -- if its class is "odd-only"
    the reading is structurally blind to it, not merely weak.
    """
    reading = parity(adjacency)
    out = []
    for i, j in pairs:
        vis = pair_visibility(adjacency, i, j, reading)
        score = shared_neighbour_similarity(adjacency, i, j)
        if vis != "none" and score == 0.0:
            out.append({"pair": (i, j), "visibility": vis,
                        "shared_neighbour": score,
                        "blind_by_structure": vis == "odd-only"})
    return out


# ---------------------------------------------------------------------------
# the two halves together
# ---------------------------------------------------------------------------

@dataclass
class CouplingReading:
    """Where a coupling strength sits relative to the stable window."""

    coherence: float                      # f(C) in [0, 1]
    synchronizable: bool
    sigma_min: Optional[float] = None
    sigma_max: Optional[float] = None
    sigma_optimal: Optional[float] = None
    margin: Optional[float] = None
    msf_class: str = ""
    regime: str = ""                      # FRAGMENTED | STABLE | RIGID | ...
    n_components: int = 1
    source: str = ""
    notes: List[str] = field(default_factory=list)


def synchronizable(spec: SpectrumReading, window: MSFWindow) -> bool:
    """Does *any* coupling strength stabilize this network?

    True exactly when the topology's eigenratio comes in under the dynamics'
    window ratio. The two sides are independent — topology left, dynamics right.
    """
    return spec.connected and spec.eigenratio < window.width_ratio


def optimal_coupling(spec: SpectrumReading,
                     window: MSFWindow) -> Optional[float]:
    """Coupling strength furthest from both stability boundaries.

    Derived, not chosen: maximising the smaller of the two logarithmic margins,
    ln(sigma*L2/nu_1) and ln(nu_2/(sigma*LN)), equalises them, giving

        sigma* = sqrt(nu_1 * nu_2 / (L2 * LN))

    the geometric centre of the window. Log-margins are the natural measure
    because both boundaries are multiplicative in sigma. None for Class II,
    which has no upper boundary to be far from.
    """
    if not synchronizable(spec, window) or not window.has_interior_optimum:
        return None
    return sqrt(window.nu_lower * window.nu_upper
                / (spec.lambda_2 * spec.lambda_n))


def coupling_coherence(sigma: float, adjacency: Matrix,
                       window: MSFWindow) -> CouplingReading:
    """f(C) for a coupling strength on a network, from stability theory.

    Class III: a genuine interior maximum — 1 at the geometric centre of the
    window, falling linearly in log coupling to 0 at either boundary.
    Class II: binary. Physics gives a threshold and no gradient above it, and a
    smooth ramp there would be a manufactured penalty.
    """
    if sigma < 0:
        raise ValueError("coupling strength cannot be negative")

    spec = spectrum(adjacency)
    notes = list(spec.warnings)
    source = ("Pecora & Carroll 1998 PRL 80:2109; Barahona & Pecora 2002 "
              "PRL 89:054101; Huang et al. 2009 PRE 80:036204")

    if not spec.connected:
        groups = components(adjacency)
        notes.append(f"surviving components: {groups}")
        notes.append(
            "f(C) = 0 because the network has no path between all units, not "
            "because the coupling strength is mistuned. Whether a partition "
            "should be repaired, tolerated, or preserved is not a measurement.")
        return CouplingReading(
            coherence=0.0, synchronizable=False, msf_class=window.msf_class,
            regime="FRAGMENTED_STRUCTURALLY", n_components=spec.n_components,
            source=source, notes=notes)

    sigma_min = window.nu_lower / spec.lambda_2
    sigma_max = inf if isinf(window.nu_upper) else window.nu_upper / spec.lambda_n

    if not synchronizable(spec, window):
        notes.append(
            f"eigenratio {spec.eigenratio:.3f} exceeds the dynamics' window "
            f"ratio {window.width_ratio:.3f} — no coupling strength stabilizes "
            "this network. The remedy, if one is wanted, is a different "
            "network, not a different coupling strength.")
        return CouplingReading(
            coherence=0.0, synchronizable=False, sigma_min=sigma_min,
            sigma_max=sigma_max, msf_class=window.msf_class,
            regime="NO_STABLE_WINDOW", source=source, notes=notes)

    margin = (inf if isinf(window.width_ratio)
              else sqrt(window.width_ratio / spec.eigenratio))
    sigma_opt = optimal_coupling(spec, window)

    if sigma <= sigma_min:
        notes.append(
            f"sigma * lambda_2 = {sigma * spec.lambda_2:.4f} is at or below "
            f"nu_1 = {window.nu_lower:.4f} — the slowest mode never locks. "
            "This is the 'too weak' branch.")
        regime, coherence = "FRAGMENTED", 0.0
    elif sigma >= sigma_max:
        notes.append(
            f"sigma * lambda_N = {sigma * spec.lambda_n:.4f} is at or above "
            f"nu_2 = {window.nu_upper:.4f} — the fastest mode is driven "
            "unstable. This is the 'too strong' branch, and it exists only "
            "because these dynamics are Class III.")
        regime, coherence = "RIGID", 0.0
    else:
        regime = "STABLE"
        if window.has_interior_optimum:
            lower_margin = log(sigma * spec.lambda_2 / window.nu_lower)
            upper_margin = log(window.nu_upper / (sigma * spec.lambda_n))
            peak = log(margin)
            coherence = min(1.0, max(0.0, min(lower_margin, upper_margin) / peak))
            notes.append(
                f"stable window sigma in ({sigma_min:.4f}, {sigma_max:.4f}), "
                f"widest margin at sigma* = {sigma_opt:.4f}")
        else:
            coherence = 1.0
            notes.append(
                f"Class II dynamics: stable for every sigma above "
                f"{sigma_min:.4f}. Physics gives a threshold here, not an "
                "optimum, so f(C) is binary rather than an invented gradient.")

    if window.has_interior_optimum:
        notes.append(
            f"safety margin sqrt(window ratio / eigenratio) = {margin:.3f}; "
            "near 1 means the network barely fits inside the window at any "
            "coupling strength")

    return CouplingReading(
        coherence=coherence, synchronizable=True, sigma_min=sigma_min,
        sigma_max=sigma_max, sigma_optimal=sigma_opt, margin=margin,
        msf_class=window.msf_class, regime=regime, source=source, notes=notes)


def format_coupling(r: CouplingReading) -> str:
    """Human-readable rendering of a CouplingReading."""

    def num(value: Optional[float], fmt: str = "{:.4f}") -> str:
        if value is None:
            return "n/a"
        return "inf" if isinf(value) else fmt.format(value)

    lines = [
        "=" * 70,
        f"COUPLING: {r.regime}    f(C) = {r.coherence:.4f}    "
        f"MSF class {r.msf_class or '?'}",
        "=" * 70,
        f"  stable window   = ({num(r.sigma_min)}, {num(r.sigma_max)})",
        f"  optimal sigma   = {num(r.sigma_optimal)}",
        f"  safety margin   = {num(r.margin, '{:.3f}')}",
    ]
    if r.notes:
        lines.extend(["", "NOTES:"] + [f"  - {note}" for note in r.notes])
    if r.source:
        lines.extend(["", f"  source: {r.source}"])
    lines.extend(["", "Outside the window is a reading, not a fault. Some "
                  "systems should not synchronize.", "=" * 70])
    return "\n".join(lines)
