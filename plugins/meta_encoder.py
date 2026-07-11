"""
Meta‑Encoder Studio Plugin
===========================
Allows the agent to design, generate, test, and hot‑load new GEIS encoders
for novel physical domains. This is the "language creation" tool.
"""

import os
import importlib
import sys
import json

PLUGIN_META = {
    "name": "meta_encoder",
    "description": "Studio for designing new GEIS encoders on the fly.",
    "class_name": "MetaEncoderPlugin",
}

# A minimal encoder template that any new plugin can start from.
ENCODER_TEMPLATE = '''
PLUGIN_META = {{
    "name": "{name}",
    "description": "{description}",
    "class_name": "{class_name}",
}}

import math
import numpy as np
from collections import deque

# Physics functions (stubs for now; user can fill in)
{physics_functions}

# Band thresholds
{bands_definition}

def gray_bits(value, bands):
    idx = 0
    for i, th in enumerate(bands):
        if value >= th:
            idx = i
    g = idx ^ (idx >> 1)
    return format(g, '0{nbits}b')

class {class_name}:
    def __init__(self):
        # Initialize bands (maybe adaptive)
        self.bands_magnitude = _DEFAULT_MAGNITUDE_BANDS[:]
        self.bands_delta = _DEFAULT_DELTA_BANDS[:]
        self.prev_state = None
        self.history = deque(maxlen=10)

    def from_geometry(self, geometry_data):
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if self.input_geometry is None:
            raise ValueError("No geometry loaded.")
        data = self.input_geometry
        # Encode magnitude band(s)
        value = data.get("{primary_key}", 0.0)
        bits = []
        bits.append(gray_bits(value, self.bands_magnitude))
        # Add delta if available
        if self.prev_state:
            prev_val = self.prev_state.get("{primary_key}", 0.0)
            delta = abs(value - prev_val)
            bits.append(gray_bits(delta, self.bands_delta))
        else:
            bits.append(gray_bits(0.0, self.bands_delta))
        # Store state
        self.prev_state = data.copy()
        return "".join(bits)

    def report(self):
        if self.prev_state is None:
            return "No data."
        return "{name}: current value={prev_val:.3f}"
'''.lstrip()


class MetaEncoderPlugin:
    def __init__(self):
        pass

    def create_encoder(self, name, description, primary_key, magnitude_bands, delta_bands=None, physics_funcs=""):
        """
        Generate a new encoder plugin file.

        Parameters
        ----------
        name : str
            Short name for the encoder (e.g., 'seismic').
        description : str
            Human‑readable description.
        primary_key : str
            The main geometry key to encode (e.g., 'acceleration_m_s2').
        magnitude_bands : list of float
            Band thresholds for the primary magnitude.
        delta_bands : list of float or None
            Band thresholds for the delta between samples.
        physics_funcs : str
            Python code string containing any physics functions needed.
        """
        class_name = f"{name.capitalize()}Encoder"
        nbits = 3  # standard: 8 bands -> 3 bits
        bands_code = f"_DEFAULT_MAGNITUDE_BANDS = {magnitude_bands}\n_DEFAULT_DELTA_BANDS = {delta_bands if delta_bands else [0.0]*len(magnitude_bands)}"
        code = ENCODER_TEMPLATE.format(
            name=name,
            description=description,
            class_name=class_name,
            physics_functions=physics_funcs,
            bands_definition=bands_code,
            primary_key=primary_key,
            nbits=nbits
        )
        # Write next to this module so the result doesn't depend on the CWD.
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(plugin_dir, f"{name}.py")
        with open(filepath, "w") as f:
            f.write(code)
        return f"✅ Encoder '{name}' created at {filepath}"

    def load_new_encoder(self, name, plugin_manager):
        """Hot‑load a freshly created encoder into the running PluginManager."""
        # Force re‑scan of plugins directory
        plugin_manager._scan()  # we might need to expose this
        # Then load the plugin as usual
        return plugin_manager.load_plugin(name)
