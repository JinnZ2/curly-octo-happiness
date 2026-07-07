"""
gae_shape_connector.py
======================
Connects GAE diagnostics to Shape Board generation.

Given a system (nodes + edges), run GAE to diagnose geometry,
then generate a Shape Board with the recommended shape,
using the system's nodes as tasks.
"""

from gae import GAE
from shape_board import ShapeBoard, ShapeProject, ShapeGenerator, NodeStatus, ShapeType
from typing import Dict, List, Tuple, Any

def map_geometry_to_shape_type(geometry_name: str) -> str:
    """Map GAE geometry name to ShapeType."""
    mapping = {
        "LINE": "torus",  # Line maps to a collapsed torus / chain
        "TRIANGLE": "tetrahedron",  # Triangle is 2D, but we use 3D minimal
        "TETRAHEDRON": "tetrahedron",
        "TORUS": "torus",
        "ICOSAHEDRON": "icosahedron",
        "FRACTAL": "dodecahedron",  # Fractal maps to high-symmetry dodecahedron
    }
    return mapping.get(geometry_name, "torus")

def create_shape_project_from_system(
    system_name: str,
    system_nodes: List[str],
    system_edges: List[Tuple[str, str]],
    node_descriptions: Dict[str, str] = None,
) -> ShapeProject:
    """
    Run GAE on a system and create a ShapeProject with the recommended geometry.
    
    Args:
        system_name: Name of the system (e.g., "Chemical Plant")
        system_nodes: List of node names
        system_edges: List of (source, target) tuples
        node_descriptions: Optional dict mapping node names to descriptions
    
    Returns:
        ShapeProject with the recommended geometry and tasks populated.
    """
    # 1. Run GAE
    gae = GAE(system_nodes, system_edges)
    gae_results = gae.analyze()
    recommendation = gae_results["recommendation"]
    shape_type_str = map_geometry_to_shape_type(recommendation)
    
    # 2. Create node data for the shape
    # If we have more nodes than the shape supports, we need to group them
    # For now, we map them directly; larger shapes like dodecahedron (20) / icosahedron (12) can handle many
    nodes_data = []
    for node in system_nodes:
        desc = node_descriptions.get(node, f"{node} task") if node_descriptions else f"{node} task"
        nodes_data.append((node, desc))
    
    # If the system has more nodes than the shape can hold, we prioritize
    # the most critical ones (those with highest degree)
    if len(nodes_data) > 20:  # Max for dodecahedron
        # Sort by degree (importance) and take top 20
        degree = {node: 0 for node in system_nodes}
        for src, dst in system_edges:
            degree[src] = degree.get(src, 0) + 1
            degree[dst] = degree.get(dst, 0) + 1
        # Reorder nodes by degree descending
        sorted_nodes = sorted(system_nodes, key=lambda x: degree.get(x, 0), reverse=True)
        nodes_data = [(n, node_descriptions.get(n, f"{n} task")) for n in sorted_nodes[:20]]
    
    # 3. Generate shape nodes and edges
    shape_nodes, shape_edges = ShapeGenerator.create_shape(
        shape_type_str, 
        nodes_data=nodes_data,
        base_name=system_name.replace(" ", "_")
    )
    
    # 4. Create ShapeProject
    # Map shape_type_str to ShapeType enum
    shape_type_enum = {
        "octahedron": ShapeType.OCTAHEDRON,
        "torus": ShapeType.TORUS,
        "tetrahedron": ShapeType.TETRAHEDRON,
        "dodecahedron": ShapeType.DODECAHEDRON,
        "icosahedron": ShapeType.ICOSAHEDRON,
    }.get(shape_type_str, ShapeType.OCTAHEDRON)
    
    project = ShapeProject(
        name=f"{system_name} - {recommendation} Shape",
        shape_type=shape_type_enum,
        nodes=shape_nodes,
        connections=shape_edges,
        guardian="GAE Shape Steward"
    )
    
    return project, gae_results

def create_and_visualize_system(system_name: str, nodes: List[str], edges: List[Tuple[str, str]], descriptions: Dict[str, str] = None):
    """
    Full pipeline: GAE diagnostic + Shape Board visualization.
    """
    print(f"\n{'='*80}")
    print(f"SYSTEM: {system_name}")
    print(f"{'='*80}")
    
    # 1. Run GAE
    gae = GAE(nodes, edges)
    results = gae.analyze()
    print(results["diagnostic"])
    
    # 2. Create Shape Project
    project, gae_results = create_shape_project_from_system(
        system_name, nodes, edges, descriptions
    )
    
    # 3. Create Shape Board
    board = ShapeBoard(project)
    
    # 4. Print the Shape Guardian's initial report
    guardian = ShapeGuardian(board)
    print(f"\n{guardian.diagnose()}")
    
    # 5. Return the board for visualization
    return board, results
