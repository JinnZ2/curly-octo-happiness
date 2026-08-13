"""
Light Bridge Plugin – encodes optical photon geometry into binary.

Extracted from plugins/Light_bridge.md, where this plugin previously lived
only as a markdown code block and could never be loaded by the PluginManager.
"""

import math

PLUGIN_META = {
    "name": "light",
    "description": "Encodes photon samples (polarization, wavelength, interference, spin) via physics equations.",
    "class_name": "LightPlugin",
}

# Physical constants & band thresholds
HC_EV_NM = 1240.0
_WAVELENGTH_BANDS    = [0.0, 280.0, 315.0, 400.0, 450.0, 495.0, 570.0, 620.0]
_INTERFERENCE_BANDS  = [0.0, 0.125, 0.25,  0.375, 0.5,   0.625, 0.75,  0.875]
_ENERGY_BANDS        = [0.0, 0.1,   0.5,   1.0,   2.0,   3.0,   5.0,   10.0]
_VISIBILITY_BANDS    = [0.0, 0.125, 0.25,  0.375, 0.5,   0.625, 0.75,  0.875]

def _gray(n):
    return n ^ (n >> 1)

def _gray_bits(value, bands, n_bits=3):
    band = 0
    for i in range(len(bands)-1, -1, -1):
        if value >= bands[i]:
            band = i
            break
    return format(_gray(band), f'0{n_bits}b')

# Physics functions
def photon_energy_eV(wl):
    return HC_EV_NM / wl if wl > 0 else 0.0

def fringe_visibility(intensities):
    if not intensities: return 0.0
    i_max, i_min = max(intensities), min(intensities)
    total = i_max + i_min
    return (i_max - i_min) / total if total != 0 else 0.0

# Plugin class
class LightPlugin:
    def __init__(self):
        self.input_geometry = None

    def from_geometry(self, geometry_data):
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if self.input_geometry is None:
            raise ValueError("No geometry loaded. Call from_geometry() first.")
        data = self.input_geometry
        pol   = data.get("polarization", [])
        spec  = data.get("spectrum_nm", [])
        inter = data.get("interference_intensity", [])
        spin  = data.get("photon_spin", [])
        bits = []
        for p, lam, intensity, s in zip(pol, spec, inter, spin):
            bits.append("1" if p == "V" else "0")
            bits.append(_gray_bits(lam, _WAVELENGTH_BANDS))
            bits.append(_gray_bits(intensity, _INTERFERENCE_BANDS))
            bits.append("1" if s == "R" else "0")
        n = len(pol)
        if n > 0:
            energies = [photon_energy_eV(lam) for lam in spec]
            E_mean = sum(energies)/n
            vis = fringe_visibility(inter)
            bits.append("1" if E_mean > 2.5 else "0")
            bits.append(_gray_bits(E_mean, _ENERGY_BANDS))
            bits.append(_gray_bits(vis, _VISIBILITY_BANDS))
        return "".join(bits)

    def report(self):
        if not self.input_geometry:
            return "No light data."
        data = self.input_geometry
        wl = data.get("spectrum_nm", [])
        if wl:
            avg_wl = sum(wl)/len(wl)
            return f"Light: {len(wl)} photons, avg λ={avg_wl:.1f} nm"
        return "Light: no photons."
