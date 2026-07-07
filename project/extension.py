# Add these methods to the ShapeGenerator class in shape_board.py

import math
from typing import List, Tuple

# ============================================================================
# Extended Shape Generators
# ============================================================================

class ShapeGenerator:
    # ... (existing octahedron, tetrahedron methods) ...

    @staticmethod
    def torus_nodes(n: int = 12, base_name: str = "Task") -> List[TaskNode]:
        """Generate n nodes arranged as a torus (doughnut shape)."""
        nodes = []
        R = 2.0  # Major radius
        r = 0.8  # Minor radius
        
        # Create a Fibonacci spiral on the torus for even distribution
        for i in range(n):
            theta = 2 * math.pi * i / n
            phi = 2 * math.pi * (i * 0.618033988749895)  # Golden ratio for even spread
            
            x = (R + r * math.cos(phi)) * math.cos(theta)
            y = (R + r * math.cos(phi)) * math.sin(theta)
            z = r * math.sin(phi)
            
            nodes.append(TaskNode(
                id=f"{base_name}_torus_{i+1}",
                name=f"Loop {i+1}",
                description=f"Node on the torus cycle",
                position=(x, y, z),
                status=NodeStatus.EMPTY
            ))
        return nodes

    @staticmethod
    def torus_connections(nodes: List[TaskNode]) -> List[Tuple[str, str]]:
        """Generate connections for a torus: each node connects to its 2 nearest neighbors, plus a cross-loop."""
        n = len(nodes)
        edges = []
        for i in range(n):
            # Connect to next and previous (major loop)
            edges.append((nodes[i].id, nodes[(i + 1) % n].id))
            # Connect to node i + n//2 (minor loop, cross-section)
            edges.append((nodes[i].id, nodes[(i + n // 2) % n].id))
        return edges

    @staticmethod
    def dodecahedron_nodes(base_name: str = "Task") -> List[TaskNode]:
        """Generate 20 nodes arranged as a dodecahedron."""
        # Golden ratio
        phi = (1 + math.sqrt(5)) / 2
        
        # Vertices of a dodecahedron (20 vertices)
        vertices = []
        
        # 1. (±1, ±1, ±1) — 8 vertices
        for x in [-1, 1]:
            for y in [-1, 1]:
                for z in [-1, 1]:
                    vertices.append((x, y, z))
        
        # 2. (0, ±1/φ, ±φ) — 4 vertices (actually 12, but we loop)
        for sign_y in [-1, 1]:
            for sign_z in [-1, 1]:
                vertices.append((0, sign_y * (1/phi), sign_z * phi))
        for sign_x in [-1, 1]:
            for sign_z in [-1, 1]:
                vertices.append((sign_x * (1/phi), 0, sign_z * phi))
        for sign_x in [-1, 1]:
            for sign_y in [-1, 1]:
                vertices.append((sign_x * phi, sign_y * (1/phi), 0))
        
        # Map names to vertices
        name_list = [
            "Foundation", "Structure", "Enclosure", "Systems", "Finishes",
            "Landscaping", "Verification", "Documentation", "Permits", "Site Prep",
            "Framing", "Roofing", "Insulation", "HVAC", "Plumbing",
            "Electrical", "Interior", "Exterior", "Testing", "Handover"
        ]
        
        nodes = []
        # Normalize vertices to a nice scale
        scale = 1.5
        for i, (pos, name) in enumerate(zip(vertices[:20], name_list[:20])):
            x, y, z = pos
            nodes.append(TaskNode(
                id=f"{base_name}_dodeca_{i+1}",
                name=name,
                description=f"{name} node",
                position=(x * scale, y * scale, z * scale),
                status=NodeStatus.EMPTY
            ))
        return nodes[:20]  # Ensure exactly 20

    @staticmethod
    def dodecahedron_connections(nodes: List[TaskNode]) -> List[Tuple[str, str]]:
        """Generate edges for a dodecahedron (30 edges)."""
        # Use the positions to calculate nearest neighbors
        edges = []
        n = len(nodes)
        for i in range(n):
            for j in range(i + 1, n):
                x1, y1, z1 = nodes[i].position
                x2, y2, z2 = nodes[j].position
                dist = (x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2
                # Dodecahedron edges have distance ~ (2*scale)^2 * some factor
                # We'll just connect the nearest neighbors
                if dist < 2.5:  # Threshold for edges
                    edges.append((nodes[i].id, nodes[j].id))
        return edges

    @staticmethod
    def icosahedron_nodes(base_name: str = "Task") -> List[TaskNode]:
        """Generate 12 nodes arranged as an icosahedron."""
        phi = (1 + math.sqrt(5)) / 2
        vertices = [
            (0, 1, phi), (0, -1, phi), (0, 1, -phi), (0, -1, -phi),
            (1, phi, 0), (-1, phi, 0), (1, -phi, 0), (-1, -phi, 0),
            (phi, 0, 1), (-phi, 0, 1), (phi, 0, -1), (-phi, 0, -1)
        ]
        
        name_list = [
            "Core", "Energy", "Water", "Materials", "Knowledge",
            "Food", "Shelter", "Community", "Health", "Education",
            "Transport", "Governance"
        ]
        
        nodes = []
        scale = 1.5
        for i, (pos, name) in enumerate(zip(vertices, name_list)):
            x, y, z = pos
            nodes.append(TaskNode(
                id=f"{base_name}_icosa_{i+1}",
                name=name,
                description=f"{name} node",
                position=(x * scale, y * scale, z * scale),
                status=NodeStatus.EMPTY
            ))
        return nodes

    @staticmethod
    def icosahedron_connections(nodes: List[TaskNode]) -> List[Tuple[str, str]]:
        """Generate edges for an icosahedron (30 edges)."""
        edges = []
        n = len(nodes)
        for i in range(n):
            for j in range(i + 1, n):
                x1, y1, z1 = nodes[i].position
                x2, y2, z2 = nodes[j].position
                dist = (x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2
                if dist < 3.0:
                    edges.append((nodes[i].id, nodes[j].id))
        return edges

    @staticmethod
    def create_shape(shape_type: str, nodes_data: List[Tuple[str, str]] = None, base_name: str = "Task") -> Tuple[List[TaskNode], List[Tuple[str, str]]]:
        """
        Factory method to create any shape with custom node labels.
        
        Args:
            shape_type: "octahedron", "torus", "tetrahedron", "dodecahedron", "icosahedron"
            nodes_data: Optional list of (name, description) tuples to label the nodes.
            base_name: Base name for node IDs.
        """
        if shape_type == "octahedron":
            nodes = ShapeGenerator.octahedron_nodes(base_name)
            edges = ShapeGenerator.octahedron_connections(nodes)
        elif shape_type == "torus":
            nodes = ShapeGenerator.torus_nodes(12, base_name)
            edges = ShapeGenerator.torus_connections(nodes)
        elif shape_type == "tetrahedron":
            nodes = ShapeGenerator.tetrahedron_nodes(base_name)
            # Simple tetrahedron connections: all pairs
            edges = []
            for i in range(4):
                for j in range(i+1, 4):
                    edges.append((nodes[i].id, nodes[j].id))
        elif shape_type == "dodecahedron":
            nodes = ShapeGenerator.dodecahedron_nodes(base_name)
            edges = ShapeGenerator.dodecahedron_connections(nodes)
        elif shape_type == "icosahedron":
            nodes = ShapeGenerator.icosahedron_nodes(base_name)
            edges = ShapeGenerator.icosahedron_connections(nodes)
        else:
            raise ValueError(f"Unknown shape type: {shape_type}")
        
        # Apply custom labels if provided
        if nodes_data:
            for i, (name, desc) in enumerate(nodes_data):
                if i < len(nodes):
                    nodes[i].name = name
                    nodes[i].description = desc
        
        return nodes, edges
