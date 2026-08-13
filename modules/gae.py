# gae.py
"""
Geometric Applicability Engine (GAE) v1.0

Given a system's dependency graph, calculate its topological
fingerprint and recommend the optimal geometry for analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
import networkx as nx
import math

try:                     # numpy is optional here; Jacobi below covers its absence
    import numpy as _np
except ImportError:      # pragma: no cover - exercised only on numpy-less installs
    _np = None

# Above this size the pure-Python eigensolver is too slow to be worth running;
# fall back to McClelland's bound instead. numpy, when present, has no cap.
_ENERGY_NODE_CAP = 120


@dataclass
class SystemMetrics:
    """Topological fingerprint of a system."""
    cycle_density: float          # C: proportion of closed loops
    critical_nodes: int           # N: nodes above avg degree
    linearity: float              # L: degree of sequential flow
    recursive_variance: float     # R: branching depth uniformity
    # Structural-complexity block (Sinha & de Weck) + attack tolerance
    # (Barabási). Always measured; only used for scoring when the engine is
    # constructed with complexity_scoring=True.
    graph_energy: float = 0.0         # E(A): sum |eigenvalues| of the adjacency
    structural_complexity: float = 0.0  # C = C1 + C2*C3
    hub_concentration: float = 0.0    # spread of betweenness, 0 = flat, 1 = hub-dominated
    attack_tolerance: float = 1.0     # largest component left after targeted removal


def _jacobi_eigenvalues(matrix: List[List[float]], sweeps: int = 60,
                        tol: float = 1e-9) -> List[float]:
    """Eigenvalues of a real symmetric matrix, cyclic Jacobi rotations.

    Pure stdlib so that modules/ keeps networkx as its only hard dependency.
    """
    n = len(matrix)
    a = [row[:] for row in matrix]
    for _ in range(sweeps):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off <= tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-12:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                sign = 1.0 if theta >= 0 else -1.0
                t = sign / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return [a[i][i] for i in range(n)]


def graph_energy(G: nx.Graph) -> float:
    """E(A) = sum of |eigenvalues| of the (symmetrised, unweighted) adjacency.

    Graph energy is the C3 term of the Sinha & de Weck structural-complexity
    measure: it grows with how densely and evenly connected the graph is, and
    is what separates "many parts, many interfaces, simple wiring" from
    "many parts, many interfaces, tangled wiring".
    """
    U = nx.Graph()
    U.add_nodes_from(G.nodes)
    U.add_edges_from((u, v) for u, v in G.edges if u != v)
    n = U.number_of_nodes()
    if n == 0:
        return 0.0
    m = U.number_of_edges()
    if _np is None and n > _ENERGY_NODE_CAP:
        # McClelland's bound, E(A) <= sqrt(2*m*n); good enough as a stand-in
        # when the exact solve would be too slow.
        return math.sqrt(2.0 * m * n)

    order = list(U.nodes)
    index = {node: i for i, node in enumerate(order)}
    A = [[0.0] * n for _ in range(n)]
    for u, v in U.edges:
        A[index[u]][index[v]] = 1.0
        A[index[v]][index[u]] = 1.0

    if _np is not None:
        eigenvalues = _np.linalg.eigvalsh(_np.array(A))
        return float(_np.abs(eigenvalues).sum())
    return sum(abs(e) for e in _jacobi_eigenvalues(A))


class GeometricApplicabilityEngine:
    """Diagnoses the shape of a system and recommends geometry."""

    GEOMETRIES = [
        "LINE",
        "TRIANGLE",
        "TETRAHEDRON",
        "TORUS",
        "ICOSAHEDRON",
        "FRACTAL"
    ]

    def __init__(self, complexity_scoring: bool = False):
        """
        Args:
            complexity_scoring: when True, the structural-complexity and
                attack-tolerance metrics feed the geometry scores -- a system
                whose betweenness is concentrated in a few nodes, and which
                fragments when those nodes are removed, is pushed toward the
                distributed geometries (TORUS, ICOSAHEDRON). Off by default so
                that scores stay comparable with earlier runs; the metrics
                themselves are always reported.
        """
        self.complexity_scoring = complexity_scoring
        self.metrics: Optional[SystemMetrics] = None
        self.scores: Dict[str, float] = {}
        self.recommendation: str = ""
        self.forbidden: str = ""

    def analyze(self, nodes: List[str], edges: List[Tuple[str, str]]) -> Dict:
        """
        Analyze a system and return full diagnostic.

        Args:
            nodes: List of node names
            edges: List of (from, to) tuples
        """
        # Build graph
        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)

        # Calculate metrics
        self.metrics = self._calculate_metrics(G)
        self.scores = self._score_geometries(self.metrics)
        self.recommendation = max(self.scores, key=self.scores.get)
        self.forbidden = min(self.scores, key=self.scores.get)

        return {
            "metrics": self.metrics.__dict__,
            "scores": self.scores,
            "recommendation": self.recommendation,
            "forbidden": self.forbidden,
            "diagnostic": self._generate_diagnostic()
        }

    def _calculate_metrics(self, G: nx.DiGraph) -> SystemMetrics:
        """Extract the topological fingerprint."""
        n_nodes = len(G.nodes)
        n_edges = len(G.edges)

        # Cycle Density (C)
        # Find all simple cycles
        cycles = list(nx.simple_cycles(G))
        cycle_edges = set()
        for cycle in cycles:
            for i in range(len(cycle)):
                cycle_edges.add((cycle[i], cycle[(i+1) % len(cycle)]))
        cycle_density = len(cycle_edges) / n_edges if n_edges > 0 else 0.0

        # Critical Nodes (N): nodes with degree > average
        degrees = [d for _, d in G.degree()]
        avg_degree = sum(degrees) / n_nodes if n_nodes > 0 else 0
        critical_nodes = sum(1 for d in degrees if d > avg_degree)

        # Linearity (L): proportion of nodes with in/out degree <= 1
        linear_nodes = 0
        for node in G.nodes:
            in_deg = G.in_degree(node)
            out_deg = G.out_degree(node)
            if in_deg <= 1 and out_deg <= 1:
                linear_nodes += 1
        linearity = linear_nodes / n_nodes if n_nodes > 0 else 0.0

        # Recursive Variance (R): uniformity of branching depth
        depths = [self._max_depth(G, node, set()) for node in G.nodes]
        if depths:
            mean_depth = sum(depths) / len(depths)
            variance = sum((d - mean_depth)**2 for d in depths) / len(depths)
            # Normalize variance to [0, 1]
            recursive_variance = min(1.0, variance / 100.0)  # cap for large graphs
        else:
            recursive_variance = 0.0

        # Structural complexity, Sinha & de Weck: C = C1 + C2*C3 with unit
        # component/interface complexities -- C1 = #components, C2 = #interfaces,
        # C3 = E(A)/n (normalised graph energy).
        energy = graph_energy(G)
        undirected_edges = len({(u, v) if u <= v else (v, u)
                                for u, v in G.edges if u != v})
        c3 = energy / n_nodes if n_nodes > 0 else 0.0
        structural_complexity = n_nodes + undirected_edges * c3

        hub_concentration, attack_tolerance = self._attack_profile(G)

        return SystemMetrics(
            cycle_density=cycle_density,
            critical_nodes=critical_nodes,
            linearity=linearity,
            recursive_variance=recursive_variance,
            graph_energy=energy,
            structural_complexity=structural_complexity,
            hub_concentration=hub_concentration,
            attack_tolerance=attack_tolerance,
        )

    def _attack_profile(self, G: nx.DiGraph) -> Tuple[float, float]:
        """How hub-dependent is this system, and what survives losing its hubs?

        Barabási's result: scale-free topologies shrug off random failure but
        fall apart when their highest-betweenness nodes are removed. So measure
        both halves -- how unevenly betweenness is distributed
        (`hub_concentration`, 0 = flat, 1 = one node carries everything) and how
        much of the system stays connected once the top hubs are gone
        (`attack_tolerance`, as a fraction of the original node count).
        """
        n = G.number_of_nodes()
        if n < 2:
            return 0.0, 1.0

        betweenness = nx.betweenness_centrality(G.to_undirected())
        values = list(betweenness.values())
        mean = sum(values) / len(values)
        if mean <= 0:
            # No node sits on any shortest path between others: no hubs at all.
            hub_concentration = 0.0
        else:
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            cv2 = variance / (mean ** 2)          # squared coefficient of variation
            hub_concentration = cv2 / (1.0 + cv2)  # squash to [0, 1)

        k = max(1, round(0.05 * n))
        targets = sorted(betweenness, key=betweenness.get, reverse=True)[:k]
        attacked = G.to_undirected()
        attacked.remove_nodes_from(targets)
        if attacked.number_of_nodes() == 0:
            return hub_concentration, 0.0
        largest = max(len(c) for c in nx.connected_components(attacked))
        return hub_concentration, largest / n

    def _max_depth(self, G: nx.DiGraph, node: str, visited: Set[str]) -> int:
        """Longest downstream chain from node; visited-set guards against cycles."""
        if node in visited:
            return 0
        visited.add(node)
        successors = list(G.successors(node))
        if not successors:
            return 0
        return 1 + max(self._max_depth(G, child, visited) for child in successors)

    def _score_geometries(self, m: SystemMetrics) -> Dict[str, float]:
        """Score each geometry based on the system metrics."""
        C, N, L, R = m.cycle_density, m.critical_nodes, m.linearity, m.recursive_variance

        scores = {}

        # LINE: high linearity, low cycles
        scores["LINE"] = max(0, min(100, (L * 80) - (C * 60) - (abs(N - 2) * 10)))

        # TRIANGLE: exactly 3 nodes, moderate everything
        triangle_score = 50 if N == 3 else -abs(N - 3) * 20
        scores["TRIANGLE"] = max(0, min(100, triangle_score + (L * 20) + ((1 - R) * 20)))

        # TETRAHEDRON: 4-5 critical nodes
        tetra_score = 60 if N in [4, 5] else -abs(N - 4) * 15
        scores["TETRAHEDRON"] = max(0, min(100, tetra_score + (C * 30) + ((1 - R) * 10)))

        # TORUS: high cycles, enough nodes
        torus_score = (C * 80) + (20 if N >= 4 else -20) + (30 if R < 0.4 else -10)
        scores["TORUS"] = max(0, min(100, torus_score))

        # ICOSAHEDRON: many nodes, low linearity
        ico_score = (60 if N >= 6 else -(6 - N) * 15) + ((1 - L) * 30) + (R * 10)
        scores["ICOSAHEDRON"] = max(0, min(100, ico_score))

        # FRACTAL: low recursive variance
        fractal_score = (80 if R < 0.3 else -20) + (C * 20)
        scores["FRACTAL"] = max(0, min(100, fractal_score))

        if self.complexity_scoring:
            scores = self._apply_fragility(scores, m)

        return scores

    def _apply_fragility(self, scores: Dict[str, float],
                         m: SystemMetrics) -> Dict[str, float]:
        """Push hub-fragile systems toward the distributed geometries.

        `fragility` combines the two halves of the attack profile: betweenness
        piled into a few nodes AND the system fragmenting when they are removed.
        Either alone is survivable -- a hub that nothing depends on is fine, and
        so is a system that fragments but has no hub to lose. Together they are
        the failure mode TORUS and ICOSAHEDRON exist to answer, so the boost is
        their product rather than their sum. This quantifies the claim the
        diagnostic used to assert: distributed forms are the resilient ones.
        """
        fragility = m.hub_concentration * (1.0 - m.attack_tolerance)
        adjusted = dict(scores)
        for geometry in ("TORUS", "ICOSAHEDRON"):
            adjusted[geometry] = max(0, min(100, adjusted[geometry] + fragility * 30))
        return adjusted

    def _generate_diagnostic(self) -> str:
        """Generate human-readable diagnostic."""
        if not self.metrics:
            return "No system analyzed."

        m = self.metrics
        rec = self.recommendation
        forb = self.forbidden

        rec_status = f"RECOMMENDED (Score: {self.scores[rec]:.0f})"
        forb_status = f"AVOID (Score: {self.scores[forb]:.0f})"

        return f"""
SYSTEM TOPOLOGICAL FINGERPRINT
===============================
Cycle Density (C):        {m.cycle_density:.2f}  {'High' if m.cycle_density > 0.5 else 'Low'} cycles
Critical Nodes (N):       {m.critical_nodes} nodes above average degree
Linearity (L):            {m.linearity:.2f}  {'Linear' if m.linearity > 0.6 else 'Non-linear'} flow
Recursive Variance (R):   {m.recursive_variance:.2f}  {'Self-similar' if m.recursive_variance < 0.4 else 'Scale-breaking'}

STRUCTURAL COMPLEXITY & ATTACK TOLERANCE
========================================
Graph Energy E(A):        {m.graph_energy:.2f}
Structural Complexity:    {m.structural_complexity:.2f}  (C = C1 + C2*C3, Sinha & de Weck)
Hub Concentration:        {m.hub_concentration:.2f}  {'Hub-dominated' if m.hub_concentration > 0.5 else 'Distributed'} betweenness
Attack Tolerance:         {m.attack_tolerance:.2f}  of the system survives losing its top hubs
Scoring:                  {'fragility-adjusted' if self.complexity_scoring else 'metrics only (complexity_scoring=False)'}

GEOMETRY RECOMMENDATION
=======================
Recommended:  {rec}  {rec_status}
Forbidden:    {forb}  {forb_status}

Full Scores:
{chr(10).join(f'  {g:12}: {self.scores[g]:.0f}' for g in self.GEOMETRIES)}

ACTION:
- Design using {rec} geometry.
- Avoid {forb} geometry—it will break feedback loops and reduce resilience.
- If environment changes, re-run diagnostic.
"""


class GAE(GeometricApplicabilityEngine):
    """Compatibility wrapper with the constructor-style API that the old
    diagnostic-suite copy exposed: GAE(nodes, edges).analyze()."""

    def __init__(self, nodes: List[str], edges: List[Tuple[str, str]],
                 complexity_scoring: bool = False):
        super().__init__(complexity_scoring=complexity_scoring)
        self._nodes = nodes
        self._edges = edges

    def analyze(self, nodes=None, edges=None) -> Dict:
        return super().analyze(nodes if nodes is not None else self._nodes,
                               edges if edges is not None else self._edges)
