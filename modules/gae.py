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

@dataclass
class SystemMetrics:
    """Topological fingerprint of a system."""
    cycle_density: float          # C: proportion of closed loops
    critical_nodes: int           # N: nodes above avg degree
    linearity: float              # L: degree of sequential flow
    recursive_variance: float     # R: branching depth uniformity

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

    def __init__(self):
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

        return SystemMetrics(
            cycle_density=cycle_density,
            critical_nodes=critical_nodes,
            linearity=linearity,
            recursive_variance=recursive_variance
        )

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

        return scores

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
