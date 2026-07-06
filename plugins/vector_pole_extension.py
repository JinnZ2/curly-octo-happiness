# plugins/vector_pole_extension.py
import numpy as np
PLUGIN_META = {
    "name": "vector_pole",
    "description": "Adds dipole moments to each vertex of the harmony field for compressed relational difference sensing.",
    "class_name": "VectorPoleExtension",
}

class VectorPoleExtension:
    def __init__(self, harmony_engine):
        self.engine = harmony_engine
        self.poles = np.zeros((30, 3))  # dipole moment per vertex

    def update_poles(self):
        """Compute pole as the vector from current position to rest position, weighted by displacement velocity."""
        displacements = self.engine.current_vertices - self.engine.rest_vertices
        velocities = self.engine.current_vertices - self.engine.prev_vertices
        self.poles = displacements * 0.5 + velocities * 0.5

    def sense_max_pole(self):
        """Return the index of the vertex with the largest pole magnitude."""
        magnitudes = np.linalg.norm(self.poles, axis=1)
        return np.argmax(magnitudes), magnitudes

    def get_pole_bits(self, idx):
        """Gray-coded pole magnitude and direction for a vertex."""
        mag = np.linalg.norm(self.poles[idx])
        mag_band = min(7, int(mag * 8))
        mag_gray = mag_band ^ (mag_band >> 1)
        direction = self.poles[idx] / (mag + 1e-10)
        # encode dominant axis sign as 3 bits
        dir_bits = ''.join('1' if d > 0.33 else '0' for d in direction)
        return format(mag_gray, '03b') + dir_bits
