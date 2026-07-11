# fdm.py
"""
Fractal Dependency Mapper (FDM) v1.0

Traces any node down to its primitive roots.
Identifies branching depth, root sets, and branch health.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from enum import Enum


def load_knowledge_base(path: str) -> Dict[str, List[str]]:
    """Load a {node: [dependencies]} knowledge base from a JSON file
    (see data/*.json in the repo root)."""
    with open(path) as f:
        return json.load(f)

class NodeStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    BROKEN = "broken"
    UNKNOWN = "unknown"

@dataclass
class DependencyNode:
    """A node in the dependency tree."""
    name: str
    depth: int
    status: NodeStatus = NodeStatus.UNKNOWN
    children: List['DependencyNode'] = field(default_factory=list)
    primitive: bool = False

@dataclass
class FractalTree:
    """Complete dependency tree."""
    root: DependencyNode
    max_depth: int
    primitive_roots: Set[str]
    active_branches: int
    broken_branches: int

class FractalDependencyMapper:
    """Maps dependencies down to primitive roots."""

    # Default primitive roots - cannot be broken down further
    PRIMITIVE_ROOTS = {
        "SUNLIGHT": "energy source, cannot be manufactured",
        "SOIL": "physical substrate, must be present",
        "WATER": "essential input, cannot be created from nothing",
        "MUSCLE": "human labor, cannot be automated away",
        "GRAVITY": "physical constant, can be used passively",
        "SEEDS": "biological reproduction, cannot be synthesized from scratch",
        "LIVESTOCK": "biological labor, can be bred",
    }

    def __init__(self, knowledge_base: Optional[Dict[str, List[str]]] = None,
                 primitive_roots: Optional[Dict[str, str]] = None):
        """
        Args:
            knowledge_base: {
                "node_name": ["dependency_1", "dependency_2", ...]
            }
            primitive_roots: optional {NAME: description} catalog overriding
                the class default (see data/primitive_roots.json).
        """
        self.knowledge_base = knowledge_base or {}
        self.primitive_catalog = primitive_roots or self.PRIMITIVE_ROOTS
        self.visited: Set[str] = set()
        self.primitive_roots_found: Set[str] = set()

    @classmethod
    def from_json(cls, kb_path: str, primitive_roots_path: Optional[str] = None):
        """Build a mapper from JSON files (background knowledge kept as
        data, not code — REVIEW.md §5.5)."""
        roots = load_knowledge_base(primitive_roots_path) if primitive_roots_path else None
        return cls(load_knowledge_base(kb_path), primitive_roots=roots)

    def trace(self, root_name: str, depth: int = 0, max_depth: int = 20) -> FractalTree:
        """
        Trace a node down to primitive roots.

        Args:
            root_name: The node to trace
            depth: Current depth (used internally)
            max_depth: Maximum depth to trace (prevents infinite loops)

        Returns:
            FractalTree: Complete dependency tree with primitive roots
        """
        self.visited = set()
        self.primitive_roots_found = set()

        root_node = self._trace_recursive(root_name, depth, max_depth)

        return FractalTree(
            root=root_node,
            max_depth=self._tree_depth(root_node),
            primitive_roots=self.primitive_roots_found,
            active_branches=self._count_active(root_node),
            broken_branches=self._count_broken(root_node)
        )

    def _trace_recursive(self, name: str, depth: int, max_depth: int) -> DependencyNode:
        """Recursive tracing function."""
        if name in self.visited:
            return DependencyNode(name=name, depth=depth, status=NodeStatus.DEGRADED, primitive=False)

        self.visited.add(name)

        # Check if this is a primitive root
        if name.upper() in self.primitive_catalog:
            self.primitive_roots_found.add(name.upper())
            return DependencyNode(name=name, depth=depth, status=NodeStatus.ACTIVE, primitive=True)

        # Check knowledge base for dependencies
        dependencies = self.knowledge_base.get(name, [])

        if not dependencies:
            # No dependencies found - treat as primitive
            self.primitive_roots_found.add(name)
            return DependencyNode(name=name, depth=depth, status=NodeStatus.ACTIVE, primitive=True)

        # Build children recursively
        children = []
        for dep in dependencies:
            if depth >= max_depth:
                child = DependencyNode(name=dep, depth=depth + 1, status=NodeStatus.DEGRADED)
            else:
                child = self._trace_recursive(dep, depth + 1, max_depth)
            children.append(child)

        # Determine status of this node
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
        """Count active branches in the tree."""
        count = 1 if node.status == NodeStatus.ACTIVE else 0
        for child in node.children:
            count += self._count_active(child)
        return count

    def _count_broken(self, node: DependencyNode) -> int:
        """Count broken branches in the tree."""
        count = 1 if node.status == NodeStatus.BROKEN else 0
        for child in node.children:
            count += self._count_broken(child)
        return count

    def generate_report(self, tree: FractalTree) -> str:
        """Generate a human-readable report of the dependency tree."""
        lines = [
            "FRACTAL DEPENDENCY MAP",
            "=" * 40,
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
        return "\n".join(lines)

    def _print_tree(self, node: DependencyNode, lines: List[str], prefix: str):
        """Recursively print the tree structure."""
        status_marker = {
            NodeStatus.ACTIVE: "✓",
            NodeStatus.DEGRADED: "⚠",
            NodeStatus.BROKEN: "✗",
            NodeStatus.UNKNOWN: "?"
        }
        marker = status_marker.get(node.status, "?")
        primitive_marker = " 🌱" if node.primitive else ""
        lines.append(f"{prefix}├── {marker} {node.name}{primitive_marker}")
        for i, child in enumerate(node.children):
            is_last = (i == len(node.children) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ")
            self._print_tree(child, lines, child_prefix)
