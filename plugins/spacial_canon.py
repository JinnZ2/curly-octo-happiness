# plugins/spatial_canon.py
"""
Spatial Canon Plugin – provides coordinate conversion between GEIS and Engine conventions.
Does not encode sensor data, but offers utility functions to other plugins.
"""

from octahedral_canon import swap_geis_engine, geis_position_to_engine_position, engine_position_to_geis_position, is_bijection_intact, reconciliation_table

PLUGIN_META = {
    "name": "spatial_canon",
    "description": "Coordinate bijection between GEIS and Engine octahedral conventions. Provides index and position conversion.",
    "class_name": "SpatialCanonPlugin",
}

class SpatialCanonPlugin:
    def __init__(self):
        self.verify()  # ensure bijection is intact on load

    def verify(self):
        if not is_bijection_intact():
            raise RuntimeError("Octahedral canon bijection is broken!")
        return True

    def convert_index(self, index, direction="geis_to_engine"):
        if direction == "geis_to_engine":
            return swap_geis_engine(index)
        else:
            return swap_geis_engine(index)  # involution

    def convert_position(self, pos, direction="geis_to_engine", magnitude=0.25):
        if direction == "geis_to_engine":
            return geis_position_to_engine_position(pos)
        else:
            return engine_position_to_geis_position(pos, magnitude=magnitude)

    # The plugin doesn't produce binary data, but we can still give a report.
    def report(self):
        return "Spatial canon intact: " + str(reconciliation_table())
