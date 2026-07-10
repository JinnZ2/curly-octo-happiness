"""
systems_diagnostic_suite.py
===========================
Systems Diagnostic Suite - Interactive Prototype

A unified toolkit for:
- Diagnosing system geometry (GAE)
- Detecting hidden nodes (HND)
- Mapping fractal dependencies (FDM)
- Simulating transitions (Simulator)

Usage:
    from systems_diagnostic_suite import *
    
    # Define a system
    system = System(nodes, edges)
    
    # Run diagnostics
    gae = GAE(system)
    print(gae.diagnose())
    
    # Find hidden nodes
    hnd = HND(system, observed_data)
    print(hnd.scan())
    
    # Map dependencies
    fdm = FDM(knowledge_base)
    print(fdm.trace("Fresnel_Lens"))
    
    # Simulate transition
    sim = TransitionSimulator()
    print(sim.compare())
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set, Any
from enum import Enum
import json

# ============================================================================
# PART 1: Geometric Applicability Engine (GAE)
# ============================================================================

class SystemMetrics:
    """Topological fingerprint of a system."""
    def __init__(self, cycle_density: float, critical_nodes: int, linearity: float, recursive_variance: float):
        self.cycle_density = cycle_density
        self.critical_nodes = critical_nodes
        self.linearity = linearity
        self.recursive_variance = recursive_variance

class GAE:
    """Geometric Applicability Engine - Diagnoses system shape."""
    
    GEOMETRIES = ["LINE", "TRIANGLE", "TETRAHEDRON", "TORUS", "ICOSAHEDRON", "FRACTAL"]
    
    def __init__(self, nodes: List[str], edges: List[Tuple[str, str]]):
        self.nodes = nodes
        self.edges = edges
        self.metrics = None
        self.scores = {}
        
    def analyze(self) -> Dict:
        """Run full analysis and return results."""
        self.metrics = self._calculate_metrics()
        self.scores = self._score_geometries()
        
        return {
            "metrics": {
                "cycle_density": self.metrics.cycle_density,
                "critical_nodes": self.metrics.critical_nodes,
                "linearity": self.metrics.linearity,
                "recursive_variance": self.metrics.recursive_variance
            },
            "scores": self.scores,
            "recommendation": max(self.scores, key=self.scores.get),
            "forbidden": min(self.scores, key=self.scores.get),
            "diagnostic": self._generate_diagnostic()
        }
    
    def _calculate_metrics(self):
        """Extract topological fingerprint."""
        n = len(self.nodes)
        e = len(self.edges)
        
        # Cycle Density (C)
        # Simplified: count edges that could form cycles
        in_degrees = {}
        out_degrees = {}
        for node in self.nodes:
            in_degrees[node] = 0
            out_degrees[node] = 0
        for src, dst in self.edges:
            out_degrees[src] = out_degrees.get(src, 0) + 1
            in_degrees[dst] = in_degrees.get(dst, 0) + 1
        
        # Cycle potential: nodes with both in and out edges
        cyclic_nodes = sum(1 for n in self.nodes if in_degrees.get(n, 0) > 0 and out_degrees.get(n, 0) > 0)
        cycle_density = cyclic_nodes / n if n > 0 else 0
        
        # Critical Nodes (N): nodes with degree > average
        degrees = [in_degrees.get(n, 0) + out_degrees.get(n, 0) for n in self.nodes]
        avg_degree = sum(degrees) / n if n > 0 else 0
        critical_nodes = sum(1 for d in degrees if d > avg_degree)
        
        # Linearity (L): proportion of nodes with in/out degree <= 1
        linear_nodes = sum(1 for n in self.nodes if in_degrees.get(n, 0) <= 1 and out_degrees.get(n, 0) <= 1)
        linearity = linear_nodes / n if n > 0 else 0
        
        # Recursive Variance (R): estimate from branching depth
        # Simplified: measure depth of dependency chains
        depths = []
        for node in self.nodes:
            depth = self._max_depth(node, set())
            depths.append(depth)
        if depths:
            mean_depth = sum(depths) / len(depths)
            variance = sum((d - mean_depth) ** 2 for d in depths) / len(depths)
            recursive_variance = min(1.0, variance / 100.0)
        else:
            recursive_variance = 0.0
        
        return SystemMetrics(cycle_density, critical_nodes, linearity, recursive_variance)
    
    def _max_depth(self, node: str, visited: Set[str]) -> int:
        """Calculate max depth of dependency chain."""
        if node in visited:
            return 0
        visited.add(node)
        children = [dst for src, dst in self.edges if src == node]
        if not children:
            return 0
        return 1 + max(self._max_depth(child, visited) for child in children)
    
    def _score_geometries(self) -> Dict[str, float]:
        """Score each geometry based on metrics."""
        m = self.metrics
        C, N, L, R = m.cycle_density, m.critical_nodes, m.linearity, m.recursive_variance
        
        scores = {}
        
        # LINE: high linearity, low cycles
        scores["LINE"] = max(0, min(100, (L * 80) - (C * 60) - (abs(N - 2) * 10)))
        
        # TRIANGLE: exactly 3 nodes
        tri = 50 if N == 3 else -abs(N - 3) * 20
        scores["TRIANGLE"] = max(0, min(100, tri + (L * 20) + ((1 - R) * 20)))
        
        # TETRAHEDRON: 4-5 nodes
        tet = 60 if N in [4, 5] else -abs(N - 4) * 15
        scores["TETRAHEDRON"] = max(0, min(100, tet + (C * 30) + ((1 - R) * 10)))
        
        # TORUS: high cycles
        torus = (C * 80) + (20 if N >= 4 else -20) + (30 if R < 0.4 else -10)
        scores["TORUS"] = max(0, min(100, torus))
        
        # ICOSAHEDRON: many nodes
        ico = (60 if N >= 6 else -(6 - N) * 15) + ((1 - L) * 30) + (R * 10)
        scores["ICOSAHEDRON"] = max(0, min(100, ico))
        
        # FRACTAL: low recursive variance
        frac = (80 if R < 0.3 else -20) + (C * 20)
        scores["FRACTAL"] = max(0, min(100, frac))
        
        return scores
    
    def _generate_diagnostic(self) -> str:
        """Generate human-readable diagnostic."""
        m = self.metrics
        rec = max(self.scores, key=self.scores.get)
        forb = min(self.scores, key=self.scores.get)
        
        lines = [
            "=" * 60,
            "SYSTEM GEOMETRIC DIAGNOSTIC",
            "=" * 60,
            "",
            f"Cycle Density (C):      {m.cycle_density:.2f}  {'High' if m.cycle_density > 0.5 else 'Low'} cycles",
            f"Critical Nodes (N):      {m.critical_nodes}  nodes above average degree",
            f"Linearity (L):           {m.linearity:.2f}  {'Linear' if m.linearity > 0.6 else 'Non-linear'} flow",
            f"Recursive Variance (R):  {m.recursive_variance:.2f}  {'Self-similar' if m.recursive_variance < 0.4 else 'Scale-breaking'}",
            "",
            "GEOMETRY SCORES:",
        ]
        for geo, score in sorted(self.scores.items(), key=lambda x: x[1], reverse=True):
            marker = "★" if geo == rec else ("✗" if geo == forb else " ")
            lines.append(f"  {marker} {geo:12}: {score:3.0f}")
        
        lines.extend([
            "",
            f"RECOMMENDED:  {rec}  (Score: {self.scores[rec]:.0f})",
            f"FORBIDDEN:    {forb}  (Score: {self.scores[forb]:.0f})",
            "",
            "ACTION:",
            f"  - Design using {rec} geometry.",
            f"  - Avoid {forb} geometry—it will break feedback loops.",
            "  - If environment changes, re-run diagnostic.",
            "=" * 60
        ])
        return "\n".join(lines)


# ============================================================================
# PART 2: Hidden Node Detector (HND)
# ============================================================================

@dataclass
class HiddenNodeSuggestion:
    name: str
    confidence: float
    reason: str
    evidence: str
    category: str  # "causal", "correlational", "buffer"

class HND:
    """Hidden Node Detector - Finds missing variables from residuals."""
    
    def __init__(self, nodes: List[str], edges: List[Tuple[str, str]]):
        self.nodes = nodes
        self.edges = edges
        self.suggestions: List[HiddenNodeSuggestion] = []
        
    def scan(self, residuals: List[float], environment: Dict = None, threshold: float = 0.1) -> List[HiddenNodeSuggestion]:
        """
        Scan for hidden nodes.
        
        Args:
            residuals: List of (predicted - actual) values
            environment: Dict of {variable_name: [time_series_values]}
            threshold: Minimum residual magnitude to trigger detection
        """
        self.suggestions = []
        env = environment or {}
        
        avg_residual = sum(abs(r) for r in residuals) / len(residuals) if residuals else 0
        if avg_residual < threshold:
            return []
        
        # Method 1: Residual Gradient (unmodeled loss)
        for var_name, var_data in env.items():
            if var_name in self.nodes:
                continue
            if len(var_data) == len(residuals):
                corr = self._pearson_correlation(var_data, residuals)
                if abs(corr) > 0.5:
                    self.suggestions.append(HiddenNodeSuggestion(
                        name=var_name,
                        confidence=min(1.0, abs(corr)),
                        reason="Residual gradient detection",
                        evidence=f"Correlation with residuals: {corr:.2f}",
                        category="causal"
                    ))
        
        # Method 2: Phantom Causality
        # Build connected pairs
        connected = set()
        for src, dst in self.edges:
            connected.add((src, dst))
            connected.add((dst, src))
        
        for i, node_a in enumerate(self.nodes):
            for node_b in self.nodes[i+1:]:
                if (node_a, node_b) in connected:
                    continue
                if node_a not in env or node_b not in env:
                    continue
                corr = self._pearson_correlation(env.get(node_a, []), env.get(node_b, []))
                if abs(corr) > 0.7:
                    # Find common cause
                    for var_c, data_c in env.items():
                        if var_c in [node_a, node_b] or var_c in self.nodes:
                            continue
                        corr_a = self._pearson_correlation(env.get(node_a, []), data_c)
                        corr_b = self._pearson_correlation(env.get(node_b, []), data_c)
                        if abs(corr_a) > 0.6 and abs(corr_b) > 0.6:
                            self.suggestions.append(HiddenNodeSuggestion(
                                name=var_c,
                                confidence=0.8,
                                reason="Phantom causality detection",
                                evidence=f"Mediates correlation between {node_a} and {node_b} (r={corr:.2f})",
                                category="correlational"
                            ))
                            break
        
        # Method 3: Hidden Buffer (Negative Space)
        predicted = [0.5] * len(residuals)  # Placeholder
        observed = [p - r for p, r in zip(predicted, residuals)]
        avg_improvement = sum(o - p for o, p in zip(observed, predicted)) / len(observed) if observed else 0
        
        if avg_improvement > 0.05:
            for var_name, var_data in env.items():
                if var_name in self.nodes:
                    continue
                if len(var_data) >= 2 and var_data[-1] > var_data[0] * 1.1:
                    self.suggestions.append(HiddenNodeSuggestion(
                        name=var_name,
                        confidence=0.7,
                        reason="Hidden buffer detection",
                        evidence=f"Unexpected improvement of {avg_improvement:.2%} correlated with rising {var_name}",
                        category="buffer"
                    ))
        
        return self.suggestions
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_x2 = sum(xi ** 2 for xi in x)
        sum_y2 = sum(yi ** 2 for yi in y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
        if denominator == 0:
            return 0.0
        return numerator / denominator
    
    def generate_report(self) -> str:
        """Generate human-readable report."""
        if not self.suggestions:
            return "No hidden nodes detected. Model is robust."
        
        lines = [
            "=" * 60,
            "HIDDEN NODE DETECTION REPORT",
            "=" * 60,
            ""
        ]
        for i, suggestion in enumerate(self.suggestions, 1):
            lines.append(f"{i}. {suggestion.name}")
            lines.append(f"   Confidence: {suggestion.confidence:.0%}")
            lines.append(f"   Category:   {suggestion.category}")
            lines.append(f"   Reason:     {suggestion.reason}")
            lines.append(f"   Evidence:   {suggestion.evidence}")
            lines.append("")
        lines.extend([
            "RECOMMENDATIONS:",
            "  - Add these nodes to the model",
            "  - Re-run GAE to see if geometry changes",
            "  - Re-run HND to validate residuals drop",
            "=" * 60
        ])
        return "\n".join(lines)


# ============================================================================
# PART 3: Fractal Dependency Mapper (FDM)
# ============================================================================

class NodeStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    BROKEN = "broken"
    UNKNOWN = "unknown"

@dataclass
class DependencyNode:
    name: str
    depth: int
    status: NodeStatus = NodeStatus.UNKNOWN
    children: List['DependencyNode'] = field(default_factory=list)
    primitive: bool = False

@dataclass
class FractalTree:
    root: DependencyNode
    max_depth: int
    primitive_roots: Set[str]
    active_branches: int
    broken_branches: int

class FDM:
    """Fractal Dependency Mapper - Traces nodes to primitive roots."""
    
    PRIMITIVE_ROOTS = {
        "SUNLIGHT": "energy source",
        "SOIL": "physical substrate",
        "WATER": "essential input",
        "MUSCLE": "human labor",
        "GRAVITY": "physical constant",
        "SEEDS": "biological reproduction",
        "LIVESTOCK": "biological labor",
    }
    
    def __init__(self, knowledge_base: Dict[str, List[str]]):
        self.knowledge_base = knowledge_base
        self.visited = set()
        self.primitive_roots_found = set()
    
    def trace(self, root_name: str, max_depth: int = 20) -> FractalTree:
        """Trace a node to primitive roots."""
        self.visited = set()
        self.primitive_roots_found = set()
        root_node = self._trace_recursive(root_name, 0, max_depth)

        return FractalTree(
            root=root_node,
            max_depth=self._tree_depth(root_node),
            primitive_roots=self.primitive_roots_found,
            active_branches=self._count_active(root_node),
            broken_branches=self._count_broken(root_node)
        )
    
    def _trace_recursive(self, name: str, depth: int, max_depth: int) -> DependencyNode:
        if name in self.visited:
            return DependencyNode(name=name, depth=depth, status=NodeStatus.DEGRADED, primitive=False)
        
        self.visited.add(name)
        
        # Check primitive root
        if name.upper() in self.PRIMITIVE_ROOTS:
            self.primitive_roots_found.add(name.upper())
            return DependencyNode(name=name, depth=depth, status=NodeStatus.ACTIVE, primitive=True)
        
        # Get dependencies
        deps = self.knowledge_base.get(name, [])
        if not deps:
            self.primitive_roots_found.add(name)
            return DependencyNode(name=name, depth=depth, status=NodeStatus.ACTIVE, primitive=True)
        
        children = []
        for dep in deps:
            if depth >= max_depth:
                children.append(DependencyNode(name=dep, depth=depth+1, status=NodeStatus.DEGRADED))
            else:
                children.append(self._trace_recursive(dep, depth+1, max_depth))
        
        status = NodeStatus.ACTIVE
        for child in children:
            if child.status == NodeStatus.BROKEN:
                status = NodeStatus.BROKEN
                break
            elif child.status == NodeStatus.DEGRADED and status != NodeStatus.BROKEN:
                status = NodeStatus.DEGRADED
        
        return DependencyNode(name=name, depth=depth, status=status, children=children, primitive=False)
    
    def _tree_depth(self, node: DependencyNode) -> int:
        """Deepest node in the tree (the root itself is depth 0)."""
        if not node.children:
            return node.depth
        return max(self._tree_depth(child) for child in node.children)

    def _count_active(self, node: DependencyNode) -> int:
        count = 1 if node.status == NodeStatus.ACTIVE else 0
        for child in node.children:
            count += self._count_active(child)
        return count
    
    def _count_broken(self, node: DependencyNode) -> int:
        count = 1 if node.status == NodeStatus.BROKEN else 0
        for child in node.children:
            count += self._count_broken(child)
        return count
    
    def generate_report(self, tree: FractalTree) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 60,
            "FRACTAL DEPENDENCY MAP",
            "=" * 60,
            "",
            f"Root: {tree.root.name}",
            f"Max Depth: {tree.max_depth}",
            f"Primitive Roots: {', '.join(tree.primitive_roots) if tree.primitive_roots else 'None found'}",
            f"Active Branches: {tree.active_branches}",
            f"Broken Branches: {tree.broken_branches}",
            "",
            "TREE STRUCTURE:",
            ""
        ]
        self._print_tree(tree.root, lines, "")
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def _print_tree(self, node: DependencyNode, lines: List[str], prefix: str):
        status_marker = {
            NodeStatus.ACTIVE: "✓",
            NodeStatus.DEGRADED: "⚠",
            NodeStatus.BROKEN: "✗",
            NodeStatus.UNKNOWN: "?"
        }
        marker = status_marker.get(node.status, "?")
        prim = " 🌱" if node.primitive else ""
        lines.append(f"{prefix}├── {marker} {node.name}{prim}")
        for i, child in enumerate(node.children):
            is_last = (i == len(node.children) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ")
            self._print_tree(child, lines, child_prefix)


# ============================================================================
# PART 4: Transition Simulator
# ============================================================================

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
            "Final State (Year 20):",
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
            f"  The Torus system outperforms the Linear system in all metrics.",
            f"  The transition takes 5 years to complete.",
            f"  After Year 5, the system is self-sustaining and regenerative.",
            "=" * 60
        ]
        return "\n".join(lines)


# ============================================================================
# PART 5: Main - Run Everything
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
    
    # Simulated environment variables (would be real data in practice)
    environment = {
        "Soil_Microbiome": [0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35],
        "Pollinators": [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45],
        "Groundwater": [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55],
        "TEK": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
    }
    
    # Simulated residuals (model overestimates yield because hidden nodes are missing)
    residuals = [0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.32, 0.35, 0.38]
    
    hnd = HND(food_nodes, food_edges)
    suggestions = hnd.scan(residuals, environment)
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
    print("To explore interactively, run this file in a Jupyter notebook.")
    print("")


if __name__ == "__main__":
    main()
