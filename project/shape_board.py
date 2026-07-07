"""
shape_board.py
==============
Interactive Shape Board for Geometric Coordination.

Represents any project as a 3D shape (octahedron, torus, etc.)
with nodes (tasks) and connections (dependencies).

Features:
- Visualize the shape in 3D
- See node status (empty, filled, in progress, verified)
- Self-assign to nodes
- Verify others' work
- Monitor shape integrity
"""

import plotly.graph_objects as go
import networkx as nx
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum
import random

# ============================================================================
# Core Data Structures
# ============================================================================

class NodeStatus(Enum):
    EMPTY = "empty"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    FILLED = "filled"
    VERIFIED = "verified"
    BLOCKED = "blocked"

class ShapeType(Enum):
    OCTAHEDRON = "octahedron"
    TORUS = "torus"
    TETRAHEDRON = "tetrahedron"
    DODECAHEDRON = "dodecahedron"
    ICOSAHEDRON = "icosahedron"
    CUSTOM = "custom"

@dataclass
class TaskNode:
    """A node in the task shape."""
    id: str
    name: str
    description: str
    status: NodeStatus = NodeStatus.EMPTY
    assigned_to: Optional[str] = None
    verified_by: Optional[str] = None
    capacity_required: float = 1.0  # 0-1, how much skill/capacity needed
    dependencies: List[str] = field(default_factory=list)
    position: Tuple[float, float, float] = (0, 0, 0)  # 3D coordinates

@dataclass
class ShapeProject:
    """A project defined as a geometric shape."""
    name: str
    shape_type: ShapeType
    nodes: List[TaskNode]
    connections: List[Tuple[str, str]]
    guardian: Optional[str] = None
    status: str = "active"

# ============================================================================
# Shape Generator
# ============================================================================

class ShapeGenerator:
    """Generates 3D shapes with task nodes."""
    
    @staticmethod
    def octahedron_nodes(base_name: str = "Task") -> List[TaskNode]:
        """Generate 8 nodes arranged as an octahedron."""
        vertices = [
            (0, 1, 0),   # top
            (0, -1, 0),  # bottom
            (1, 0, 0),   # front
            (-1, 0, 0),  # back
            (0, 0, 1),   # right
            (0, 0, -1),  # left
            (0.7, 0.7, 0.7),  # front-top-right
            (-0.7, -0.7, -0.7), # back-bottom-left
        ]
        
        names = [
            "Foundation",
            "Structure",
            "Enclosure",
            "Systems",
            "Finishes",
            "Landscaping",
            "Verification",
            "Documentation"
        ]
        
        nodes = []
        for i, (pos, name) in enumerate(zip(vertices, names)):
            nodes.append(TaskNode(
                id=f"{base_name}_{i+1}",
                name=name,
                description=f"{name} task",
                position=pos,
                status=NodeStatus.EMPTY
            ))
        return nodes
    
    @staticmethod
    def octahedron_connections(nodes: List[TaskNode]) -> List[Tuple[str, str]]:
        """Generate connections for octahedron (edges between adjacent vertices)."""
        edges = []
        # Connect each vertex to its 4 nearest neighbors
        for i, node_a in enumerate(nodes):
            for j, node_b in enumerate(nodes):
                if i >= j:
                    continue
                # Calculate distance
                dist = sum((a - b) ** 2 for a, b in zip(node_a.position, node_b.position))
                if dist < 3.0:  # Adjacent vertices
                    edges.append((node_a.id, node_b.id))
        return edges
    
    @staticmethod
    def torus_nodes(n: int = 12, base_name: str = "Task") -> List[TaskNode]:
        """Generate n nodes arranged as a torus."""
        import math
        nodes = []
        R = 2.0  # Major radius
        r = 0.8  # Minor radius
        for i in range(n):
            theta = 2 * math.pi * i / n
            phi = 2 * math.pi * i / n * 0.5  # Twist for 3D effect
            x = (R + r * math.cos(phi)) * math.cos(theta)
            y = (R + r * math.cos(phi)) * math.sin(theta)
            z = r * math.sin(phi)
            nodes.append(TaskNode(
                id=f"{base_name}_{i+1}",
                name=f"Task {i+1}",
                description=f"Node {i+1} on the torus",
                position=(x, y, z),
                status=NodeStatus.EMPTY
            ))
        return nodes
    
    @staticmethod
    def tetrahedron_nodes(base_name: str = "Task") -> List[TaskNode]:
        """Generate 4 nodes arranged as a tetrahedron."""
        vertices = [
            (1, 1, 1),
            (1, -1, -1),
            (-1, 1, -1),
            (-1, -1, 1)
        ]
        names = ["Energy", "Water", "Materials", "Knowledge"]
        nodes = []
        for i, (pos, name) in enumerate(zip(vertices, names)):
            nodes.append(TaskNode(
                id=f"{base_name}_{i+1}",
                name=name,
                description=f"{name} pillar",
                position=pos,
                status=NodeStatus.EMPTY
            ))
        return nodes

# ============================================================================
# Shape Board (Interactive Visualization)
# ============================================================================

class ShapeBoard:
    """Interactive 3D shape board for coordination."""
    
    def __init__(self, project: ShapeProject):
        self.project = project
        self.G = nx.Graph()
        self._build_graph()
        
    def _build_graph(self):
        """Build networkx graph from project nodes and connections."""
        for node in self.project.nodes:
            self.G.add_node(
                node.id,
                name=node.name,
                description=node.description,
                status=node.status.value,
                assigned_to=node.assigned_to,
                verified_by=node.verified_by,
                position=node.position
            )
        for src, dst in self.project.connections:
            self.G.add_edge(src, dst)
    
    def visualize(self) -> go.Figure:
        """Create interactive 3D visualization."""
        pos = {n: self.G.nodes[n]["position"] for n in self.G.nodes}
        
        # Node colors based on status
        status_colors = {
            NodeStatus.EMPTY.value: "gray",
            NodeStatus.ASSIGNED.value: "blue",
            NodeStatus.IN_PROGRESS.value: "orange",
            NodeStatus.FILLED.value: "green",
            NodeStatus.VERIFIED.value: "purple",
            NodeStatus.BLOCKED.value: "red",
        }
        
        # Create node traces
        node_x, node_y, node_z = [], [], []
        node_colors, node_text = [], []
        
        for node_id in self.G.nodes:
            x, y, z = pos[node_id]
            node_x.append(x)
            node_y.append(y)
            node_z.append(z)
            status = self.G.nodes[node_id]["status"]
            node_colors.append(status_colors.get(status, "gray"))
            node_text.append(
                f"{self.G.nodes[node_id]['name']}<br>"
                f"Status: {status}<br>"
                f"Assigned: {self.G.nodes[node_id]['assigned_to'] or 'None'}"
            )
        
        node_trace = go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers+text',
            text=node_text,
            textposition='top center',
            marker=dict(
                size=15,
                color=node_colors,
                opacity=0.8,
                line=dict(width=2, color='darkblue')
            ),
            hoverinfo='text'
        )
        
        # Create edge traces
        edge_traces = []
        for u, v in self.G.edges:
            x_edges = [pos[u][0], pos[v][0], None]
            y_edges = [pos[u][1], pos[v][1], None]
            z_edges = [pos[u][2], pos[v][2], None]
            edge_trace = go.Scatter3d(
                x=x_edges, y=y_edges, z=z_edges,
                mode='lines',
                line=dict(width=2, color='lightgray'),
                hoverinfo='none'
            )
            edge_traces.append(edge_trace)
        
        # Create figure
        fig = go.Figure(data=edge_traces + [node_trace])
        fig.update_layout(
            title=f"Shape Board: {self.project.name}",
            scene=dict(
                xaxis_title='',
                yaxis_title='',
                zaxis_title='',
                bgcolor='white',
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                zaxis=dict(showgrid=False, showticklabels=False),
            ),
            showlegend=False,
            height=700,
            margin=dict(l=0, r=0, b=0, t=50)
        )
        return fig
    
    def get_status_summary(self) -> Dict:
        """Get summary of node statuses."""
        summary = {status.value: 0 for status in NodeStatus}
        for node in self.project.nodes:
            summary[node.status.value] += 1
        return summary
    
    def get_empty_nodes(self) -> List[TaskNode]:
        """Get all empty nodes."""
        return [n for n in self.project.nodes if n.status == NodeStatus.EMPTY]
    
    def assign_node(self, node_id: str, agent: str):
        """Assign a node to an agent."""
        for node in self.project.nodes:
            if node.id == node_id and node.status == NodeStatus.EMPTY:
                node.status = NodeStatus.ASSIGNED
                node.assigned_to = agent
                return True
        return False
    
    def start_node(self, node_id: str):
        """Mark a node as in progress."""
        for node in self.project.nodes:
            if node.id == node_id and node.status == NodeStatus.ASSIGNED:
                node.status = NodeStatus.IN_PROGRESS
                return True
        return False
    
    def complete_node(self, node_id: str):
        """Mark a node as filled."""
        for node in self.project.nodes:
            if node.id == node_id and node.status == NodeStatus.IN_PROGRESS:
                node.status = NodeStatus.FILLED
                return True
        return False
    
    def verify_node(self, node_id: str, verifier: str):
        """Verify a filled node."""
        for node in self.project.nodes:
            if node.id == node_id and node.status == NodeStatus.FILLED:
                node.status = NodeStatus.VERIFIED
                node.verified_by = verifier
                return True
        return False
    
    def check_integrity(self) -> Dict:
        """Check shape integrity."""
        issues = []
        
        # Check for empty nodes
        empty = self.get_empty_nodes()
        if empty:
            issues.append(f"Empty nodes: {len(empty)}")
        
        # Check for unverified filled nodes
        unverified = [n for n in self.project.nodes if n.status == NodeStatus.FILLED]
        if unverified:
            issues.append(f"Unverified nodes: {len(unverified)}")
        
        # Check for blocked nodes
        blocked = [n for n in self.project.nodes if n.status == NodeStatus.BLOCKED]
        if blocked:
            issues.append(f"Blocked nodes: {len(blocked)}")
        
        # Check connectivity
        # Are all connections between verified nodes?
        verified_ids = {n.id for n in self.project.nodes if n.status == NodeStatus.VERIFIED}
        weak_connections = []
        for src, dst in self.project.connections:
            if src in verified_ids and dst not in verified_ids:
                weak_connections.append((src, dst))
        if weak_connections:
            issues.append(f"Weak connections: {len(weak_connections)}")
        
        return {
            "is_healthy": len(issues) == 0,
            "issues": issues,
            "summary": self.get_status_summary()
        }

# ============================================================================
# Shape Guardian Dashboard
# ============================================================================

class ShapeGuardian:
    """Monitor and maintain shape integrity."""
    
    def __init__(self, board: ShapeBoard):
        self.board = board
        self.history = []
    
    def diagnose(self) -> str:
        """Generate a diagnostic report."""
        integrity = self.board.check_integrity()
        
        lines = [
            "=" * 60,
            "SHAPE GUARDIAN REPORT",
            "=" * 60,
            "",
            f"Project: {self.board.project.name}",
            f"Shape: {self.board.project.shape_type.value}",
            f"Guardian: {self.board.project.guardian or 'Not assigned'}",
            f"Status: {'✅ Healthy' if integrity['is_healthy'] else '⚠️ Issues Detected'}",
            "",
            "NODE STATUS SUMMARY:",
        ]
        
        for status, count in integrity["summary"].items():
            if count > 0:
                lines.append(f"  {status}: {count}")
        
        if integrity["issues"]:
            lines.extend([
                "",
                "ISSUES:",
                f"  {chr(10).join('  • ' + issue for issue in integrity['issues'])}"
            ])
        
        # Recommendations
        empty_nodes = self.board.get_empty_nodes()
        if empty_nodes:
            lines.extend([
                "",
                "RECOMMENDATIONS:",
                f"  - {len(empty_nodes)} nodes are empty. Assign them to capable agents.",
                f"  - Priority nodes: {', '.join(n.name for n in empty_nodes[:3])}"
            ])
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def suggest_assignments(self, agent_capabilities: Dict[str, List[str]]) -> List[Tuple[str, str]]:
        """
        Suggest node assignments based on agent capabilities.
        
        Args:
            agent_capabilities: {"agent_name": ["skill1", "skill2", ...]}
        """
        suggestions = []
        empty_nodes = self.board.get_empty_nodes()
        
        for node in empty_nodes:
            # Find agent with matching skills
            for agent, skills in agent_capabilities.items():
                # Simple matching: node name contains skill keyword
                for skill in skills:
                    if skill.lower() in node.name.lower() or skill.lower() in node.description.lower():
                        suggestions.append((node.id, agent))
                        break
        
        return suggestions

# ============================================================================
# Interactive Session
# ============================================================================

def create_passive_cooling_project() -> ShapeProject:
    """Create the Passive Cooling System project as a shape."""
    
    # Define the 8 nodes (octahedron)
    nodes = ShapeGenerator.octahedron_nodes("PassiveCooling")
    
    # Customize node names and descriptions
    node_details = [
        ("Foundation", "Site assessment and foundation preparation"),
        ("Structure", "Building frame and structural support"),
        ("Enclosure", "Walls, roof, and insulation"),
        ("Systems", "Thermal mass and passive heating/cooling"),
        ("Finishes", "Interior and exterior finishes"),
        ("Landscaping", "Shading, windbreaks, and outdoor spaces"),
        ("Verification", "Testing and quality assurance"),
        ("Documentation", "Plans, manuals, and maintenance guides")
    ]
    
    for node, (name, desc) in zip(nodes, node_details):
        node.name = name
        node.description = desc
    
    # Generate connections
    connections = ShapeGenerator.octahedron_connections(nodes)
    
    # Define specific dependencies
    # Foundation must be before Structure
    connections.append((nodes[0].id, nodes[1].id))
    # Structure before Enclosure
    connections.append((nodes[1].id, nodes[2].id))
    # Systems depends on Structure and Enclosure
    connections.append((nodes[1].id, nodes[3].id))
    connections.append((nodes[2].id, nodes[3].id))
    # Finishes depends on Enclosure and Systems
    connections.append((nodes[2].id, nodes[4].id))
    connections.append((nodes[3].id, nodes[4].id))
    # Verification depends on all previous
    for i in range(5):
        connections.append((nodes[i].id, nodes[6].id))
    
    return ShapeProject(
        name="Passive Cooling System",
        shape_type=ShapeType.OCTAHEDRON,
        nodes=nodes,
        connections=list(set(connections)),  # Remove duplicates
        guardian="Shape Steward"
    )

# ============================================================================
# Main: Run Interactive Session
# ============================================================================

def main():
    """Run the interactive Shape Board session."""
    
    print("\n" + "=" * 80)
    print("SHAPE BOARD - INTERACTIVE COORDINATION PROTOCOL")
    print("=" * 80)
    
    # Create the project
    project = create_passive_cooling_project()
    board = ShapeBoard(project)
    guardian = ShapeGuardian(board)
    
    print("\n" + guardian.diagnose())
    
    # Visualize the shape
    print("\n" + "-" * 60)
    print("VISUALIZATION")
    print("-" * 60)
    fig = board.visualize()
    fig.show()
    
    # Simulate agents and coordination
    print("\n" + "-" * 60)
    print("COORDINATION SIMULATION")
    print("-" * 60)
    
    agents = ["Alice (foundation)", "Bob (structure)", "Carol (systems)", "Dave (finishes)"]
    agent_capabilities = {
        "Alice": ["foundation", "digging", "concrete"],
        "Bob": ["structure", "framing", "carpentry"],
        "Carol": ["systems", "mechanical", "HVAC"],
        "Dave": ["finishes", "interior", "construction"],
        "Eve": ["verification", "testing", "quality"],
    }
    
    # Suggest assignments
    suggestions = guardian.suggest_assignments(agent_capabilities)
    print(f"\nSuggested assignments:")
    for node_id, agent in suggestions:
        node = next(n for n in board.project.nodes if n.id == node_id)
        print(f"  {node.name} → {agent}")
    
    # Simulate filling the shape
    print("\n" + "-" * 60)
    print("FILLING THE SHAPE")
    print("-" * 60)
    
    # Assign all suggested nodes
    for node_id, agent in suggestions:
        if board.assign_node(node_id, agent):
            print(f"✅ Assigned {node_id} to {agent}")
    
    # Simulate work
    print("\nWorking in parallel...")
    for node in board.project.nodes:
        if node.status == NodeStatus.ASSIGNED:
            board.start_node(node.id)
            print(f"  Started {node.name}")
            # Simulate completion
            import time
            time.sleep(0.1)  # Simulate work
            board.complete_node(node.id)
            print(f"  Completed {node.name}")
    
    # Verify
    print("\nVerifying...")
    for node in board.project.nodes:
        if node.status == NodeStatus.FILLED:
            board.verify_node(node.id, "Eve (Verifier)")
            print(f"  Verified {node.name}")
    
    print("\n" + "=" * 60)
    print("FINAL STATUS")
    print("=" * 60)
    print(guardian.diagnose())
    
    print("\n" + "=" * 80)
    print("SHAPE BOARD SESSION COMPLETE")
    print("=" * 80)
    print("\nThe shape is now filled and verified.")
    print("All nodes are complete. The project is structurally solid.")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
