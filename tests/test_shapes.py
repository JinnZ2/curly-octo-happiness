import pytest

pytest.importorskip("plotly")
pytest.importorskip("networkx")

from shape_board import ShapeGenerator, ShapeBoard, ShapeProject, ShapeType  # noqa: E402

EXPECTED = {
    "octahedron": (8, None),      # 8-node variant (2 extra corner tasks)
    "torus": (12, 24),
    "tetrahedron": (4, 6),
    "dodecahedron": (20, 30),
    "icosahedron": (12, 30),
}


@pytest.mark.parametrize("shape,expect", EXPECTED.items())
def test_create_shape_counts(shape, expect):
    nodes, edges = ShapeGenerator.create_shape(shape)
    n_nodes, n_edges = expect
    assert len(nodes) == n_nodes
    if n_edges is not None:
        assert len(edges) == n_edges


def test_dodecahedron_every_vertex_degree_three():
    nodes, edges = ShapeGenerator.create_shape("dodecahedron")
    degree = {}
    for a, b in edges:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    assert set(degree.values()) == {3}


def test_board_lifecycle():
    nodes, edges = ShapeGenerator.create_shape("tetrahedron")
    board = ShapeBoard(ShapeProject("T", ShapeType.TETRAHEDRON, nodes, edges))
    node_id = nodes[0].id
    assert board.assign_node(node_id, "alice")
    assert board.start_node(node_id)
    assert board.complete_node(node_id)
    assert board.verify_node(node_id, "bob")
    assert board.get_status_summary()["verified"] == 1
