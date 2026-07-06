PLUGIN_META = {
    "name": "emf_sensor",
    "description": "Electromagnetic field strength encoder.",
    "geometry_keys": ["field_strength_v_m", "frequency_hz"],
    "encoder_class": "EMFEncoder",
}

class EMFEncoder:
    def __init__(self):
        self.data = None
    def from_geometry(self, geo):
        self.data = geo
        return self
    def to_binary(self):
        if not self.data:
            return ""
        # simple 8-bit: 4-bit field magnitude, 4-bit frequency band
        field = self.data.get("field_strength_v_m", 0)
        freq = self.data.get("frequency_hz", 0)
        field_band = min(15, int(abs(field)*10))  # 0-15
        freq_band = min(15, int(freq/1000))       # kHz bands
        return format(field_band, '04b') + format(freq_band, '04b')
    def report(self):
        return f"EMF: {self.data}"
