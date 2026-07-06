PLUGIN_META = {
    "name": "thermal_camera",
    "description": "Encodes infrared thermal image into binary.",
    "geometry_keys": ["pixels", "emissivity"],
}

class ThermalCameraEncoder:
    def from_geometry(self, geometry_data):
        ...
    def to_binary(self) -> str:
        ...
    def report(self):
        ...
