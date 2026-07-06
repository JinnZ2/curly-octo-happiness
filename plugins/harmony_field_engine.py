# plugins/harmony_field_engine.py
import numpy as np
from scipy.spatial.transform import Rotation  # for initial placement; fallback if not available

PLUGIN_META = {
    "name": "harmony_field",
    "description": "Maintains the relational field as a geometric icosidodecahedron. Detects fastest distortion.",
    "class_name": "HarmonyFieldEngine",
}

# Rest coordinates of the icosidodecahedron (30 vertices, radius 1)
# Generated from canonical coordinates; we can hard-code the 30 points.
_REST_VERTICES = np.array([
    [ 0.000000,  0.000000,  1.000000],
    [ 0.000000,  0.000000, -1.000000],
    [ 0.850651,  0.000000,  0.525731],
    [-0.850651,  0.000000,  0.525731],
    [ 0.850651,  0.000000, -0.525731],
    [-0.850651,  0.000000, -0.525731],
    [ 0.525731,  0.850651,  0.000000],
    [ 0.525731, -0.850651,  0.000000],
    [-0.525731,  0.850651,  0.000000],
    [-0.525731, -0.850651,  0.000000],
    [ 0.000000,  0.525731,  0.850651],
    [ 0.000000, -0.525731,  0.850651],
    [ 0.000000,  0.525731, -0.850651],
    [ 0.000000, -0.525731, -0.850651],
    [ 0.525731,  0.000000,  0.850651],
    [-0.525731,  0.000000,  0.850651],
    [ 0.525731,  0.000000, -0.850651],
    [-0.525731,  0.000000, -0.850651],
    [ 0.850651,  0.525731,  0.000000],
    [-0.850651,  0.525731,  0.000000],
    [ 0.850651, -0.525731,  0.000000],
    [-0.850651, -0.525731,  0.000000],
    [ 0.000000,  0.850651,  0.525731],
    [ 0.000000, -0.850651,  0.525731],
    [ 0.000000,  0.850651, -0.525731],
    [ 0.000000, -0.850651, -0.525731],
    [ 0.525731,  0.850651,  0.000000],
    [-0.525731,  0.850651,  0.000000],
    [ 0.525731, -0.850651,  0.000000],
    [-0.525731, -0.850651,  0.000000],
], dtype=float)
# Remove duplicates (some lists above are duplicated due to manual generation; we should have exactly 30 unique vertices)
_REST_VERTICES = np.unique(_REST_VERTICES, axis=0)
# Ensure exactly 30 by using known formula: vertices = (0, ±1, ±φ), (±1, ±φ, 0), (±φ, 0, ±1) with φ=(1+√5)/2
phi = (1+np.sqrt(5))/2
_REST_VERTICES = np.array([
    [0, 1, phi], [0, -1, phi], [0, 1, -phi], [0, -1, -phi],
    [1, phi, 0], [-1, phi, 0], [1, -phi, 0], [-1, -phi, 0],
    [phi, 0, 1], [-phi, 0, 1], [phi, 0, -1], [-phi, 0, -1],
    [1, -phi, 0], [-1, -phi, 0], [1, phi, 0], [-1, phi, 0],
    [phi, 0, -1], [-phi, 0, -1], [phi, 0, 1], [-phi, 0, 1],
    [0, phi, 1], [0, -phi, 1], [0, phi, -1], [0, -phi, -1],
    [1, 0, phi], [-1, 0, phi], [1, 0, -phi], [-1, 0, -phi],
    [phi, 1, 0], [-phi, 1, 0],
], dtype=float)
# Normalize to unit sphere
_REST_VERTICES = _REST_VERTICES / np.linalg.norm(_REST_VERTICES, axis=1)[:, None]

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
        self.prev_vertices = self.current_vertices.copy()
        displacements = np.linalg.norm(self.current_vertices - self.rest_vertices, axis=1)
        velocities = np.linalg.norm(self.current_vertices - self.prev_vertices, axis=1)
        # Priority: node with highest velocity of distortion
        priority_idx = np.argmax(velocities)
        # Update all nodes slightly towards rest
        self.current_vertices += (self.rest_vertices - self.current_vertices) * 0.1
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
