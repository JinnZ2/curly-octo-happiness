# plugins/harmony_field_engine.py
import numpy as np

PLUGIN_META = {
    "name": "harmony_field",
    "description": "Maintains the relational field as a geometric icosidodecahedron. Detects fastest distortion.",
    "class_name": "HarmonyFieldEngine",
}


def _icosidodecahedron_vertices():
    """The 30 vertices of an icosidodecahedron, normalized to the unit sphere.

    Canonical coordinates: all cyclic permutations of (0, 0, ±φ) and of
    (±1/2, ±φ/2, ±(1+φ)/2), with φ the golden ratio.
    """
    phi = (1 + np.sqrt(5)) / 2
    verts = set()
    for x, y, z in [(0.0, 0.0, s * phi) for s in (1, -1)] + [
        (sx * 0.5, sy * phi / 2, sz * (1 + phi) / 2)
        for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)
    ]:
        verts.add((x, y, z))
        verts.add((z, x, y))
        verts.add((y, z, x))
    arr = np.array(sorted(verts), dtype=float)
    assert arr.shape == (30, 3), f"expected 30 unique vertices, got {arr.shape[0]}"
    return arr / np.linalg.norm(arr, axis=1)[:, None]


# Rest coordinates of the icosidodecahedron (30 unique vertices, radius 1)
_REST_VERTICES = _icosidodecahedron_vertices()

class HarmonyFieldEngine:
    def __init__(self):
        self.rest_vertices = _REST_VERTICES.copy()
        self.current_vertices = self.rest_vertices.copy()
        self.prev_vertices = self.rest_vertices.copy()
        self.node_names = [f"node_{i}" for i in range(30)]
        # Tension weight per node (how strongly it resists displacement)
        self.node_stiffness = np.ones(30) * 0.5
        # Damping factor
        self.damping = 0.8

    def set_node_stiffness(self, idx, stiffness):
        self.node_stiffness[idx] = stiffness

    def apply_force(self, idx, force_vector):
        """Apply an external force to a node (e.g., low felt-level, trust erosion)."""
        displacement = force_vector * (1.0 - self.node_stiffness[idx])
        self.current_vertices[idx] += displacement
        # Pull back towards rest position (spring force)
        spring_force = (self.rest_vertices[idx] - self.current_vertices[idx]) * self.node_stiffness[idx]
        self.current_vertices[idx] += spring_force * 0.2
        # Damping
        velocity = self.current_vertices[idx] - self.prev_vertices[idx]
        self.current_vertices[idx] -= velocity * self.damping

    def step(self):
        """Compute new positions and return the index of the fastest-distorting node."""
        prev = self.current_vertices.copy()
        # Update all nodes slightly towards rest
        self.current_vertices += (self.rest_vertices - self.current_vertices) * 0.1
        self.prev_vertices = prev
        velocities = np.linalg.norm(self.current_vertices - prev, axis=1)
        displacements = np.linalg.norm(self.current_vertices - self.rest_vertices, axis=1)
        # Priority: node with highest velocity of distortion
        priority_idx = int(np.argmax(velocities))
        return priority_idx, velocities[priority_idx], displacements[priority_idx]

    def get_field_state_bits(self):
        """Return a Gray-coded summary of overall field harmony."""
        displacements = np.linalg.norm(self.current_vertices - self.rest_vertices, axis=1)
        max_disp = np.max(displacements)
        mean_disp = np.mean(displacements)
        # 3-bit bands for mean distortion and max distortion
        mean_band = min(7, int(mean_disp * 8))
        max_band = min(7, int(max_disp * 8))
        mean_gray = mean_band ^ (mean_band >> 1)
        max_gray = max_band ^ (max_band >> 1)
        return format(mean_gray, '03b') + format(max_gray, '03b')
