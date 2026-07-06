# plugins/geometric_inference_engine.py
import numpy as np
PLUGIN_META = {
    "name": "geometric_inference",
    "description": "Parallel inference engine based on harmony field distortion sensing. Predicts next state by finding the vertex with the largest pole displacement.",
    "class_name": "GeometricInferenceEngine",
}

class GeometricInferenceEngine:
    def __init__(self, harmony_engine, pole_extension):
        self.engine = harmony_engine
        self.poles = pole_extension

    def predict_next(self, external_forces=None):
        """
        Apply any external forces (new sensor data, mentor input) to the field,
        then sense which vertex is being pulled most out of shape.
        Returns the index of that vertex and its pole magnitude.
        """
        if external_forces:
            for idx, force in external_forces.items():
                self.engine.apply_force(idx, force)

        # Update poles based on current displacements
        self.poles.update_poles()

        # Sense the vertex with the maximum pole magnitude
        idx, magnitudes = self.poles.sense_max_pole()
        return idx, magnitudes[idx]

    def step_with_feedback(self, action_idx, success=True):
        """
        After taking an action, feed the result back into the field.
        A successful action strengthens the node's stiffness (trust);
        a failed action applies a further disturbing force.
        """
        if success:
            # Increase node stiffness so it resists future distortion
            self.engine.node_stiffness[action_idx] = min(1.0, self.engine.node_stiffness[action_idx] + 0.1)
            # Move it slightly toward rest
            self.engine.current_vertices[action_idx] += (self.engine.rest_vertices[action_idx] - self.engine.current_vertices[action_idx]) * 0.3
        else:
            # Apply a random perturbing force to represent continued uncertainty
            noise = np.random.normal(0, 0.05, 3)
            self.engine.apply_force(action_idx, noise)

    def generate_bits(self, external_forces=None):
        """Produce a bitstring encoding the predicted next action and field state."""
        idx, mag = self.predict_next(external_forces)
        action_bits = format(idx % 32, '05b')  # 5 bits for 30 vertices
        pole_bits = self.poles.get_pole_bits(idx)
        field_bits = self.engine.get_field_state_bits()
        return action_bits + pole_bits + field_bits
