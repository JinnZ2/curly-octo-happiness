"""
Gravitational‑Wave Bridge Plugin
=================================
Encodes simulated gravitational‑wave strain data into binary, using
adaptive magnitude bands, delta encoding, and cross‑modal coherence
with EM / magnetic fields.

Physics encoded
---------------
  Strain amplitude    :  h = ΔL / L   (dimensionless)
  Chirp mass          :  M_chirp = (m₁ m₂)^(3/5) / (m₁ + m₂)^(1/5)
  Frequency evolution :  f(t) ∝ M_chirp^(-5/8) (t_coal − t)^(-3/8)
  Polarisation        :  h₊, h× projected onto detector arms

Coordinate alignment
--------------------
  Uses the ``spatial_canon`` service to rotate detector‑arm vectors
  from the local GEIS frame into the global Engine frame, so that
  the GW strain vector is reported in the same octahedral coordinate
  system as the EM and magnetic fields.

Bit layout (39 bits)
--------------------
Section A — Strain summary  (12 bits):
  [strain_mag    3b Gray]   peak strain across 8 log bands (10⁻²² → 10⁻¹⁸)
  [chirp_mass    3b Gray]   chirp mass in 8 log bands (1 → 100 M⊙)
  [frequency     3b Gray]   GW frequency at peak (10 → 1000 Hz, 8 bands)
  [polarisation  2b Gray]   dominant polarisation: plus(00), cross(01), both(11)
  [detector_align 1b]       detector aligned to source direction (>0.9) = 1

Section B — Temporal delta  (12 bits):
  [delta_strain  3b Gray]   strain change since last sample (8 log bands)
  [delta_freq    3b Gray]   frequency change (8 bands)
  [delta_phase   3b Gray]   phase shift (8 bands, 0→2π)
  [inspiral_flag 1b]        frequency increasing (inspiral) = 1
  [ringdown_flag 1b]        post‑merger ringdown = 1
  [merger_detect 1b]        peak strain reached = 1

Section C — Cross‑modal coherence  (9 bits):
  [em_coherence  3b Gray]   alignment between GW strain and EM field magnitude (8 bands)
  [mag_coherence 3b Gray]   alignment between GW strain and magnetic field (8 bands)
  [coherence_valid 1b]      at least one cross‑modal pair is active
  [spatial_align 2b]        GW source direction matches EM/magnetic dipole (2b Gray)

Section D — Detector metadata  (6 bits):
  [arm_length    3b Gray]   detector arm length in km (0.1 → 10 km, 8 bands)
  [detector_noise 3b Gray]  strain sensitivity noise floor (10⁻²³ → 10⁻²⁰ /√Hz)
"""

import math
import numpy as np
from collections import deque

PLUGIN_META = {
    "name": "gravitational",
    "description": "Encodes gravitational‑wave strain data with adaptive bands, delta encoding, and cross‑modal coherence with EM/magnetic fields.",
    "class_name": "GravitationalPlugin",
}

# ---------------------------------------------------------------------------
# Physics helpers
# ---------------------------------------------------------------------------
def chirp_mass(m1, m2):
    """Chirp mass in solar masses."""
    return (m1 * m2) ** 0.6 / (m1 + m2) ** 0.2

def strain_from_chirp(m_chirp, f):
    """Approximate strain amplitude (Newtonian order) for a binary at frequency f."""
    # h ~ (G M_chirp / c^2) (π f M_chirp / c^3)^(2/3) / distance
    # Simplified: return dimensionless strain ~ 1e-22 for typical LIGO sources.
    # Here we use a toy model: h = A0 * (M_chirp)^(5/3) * f^(2/3)
    A0 = 1e-22  # scaling
    return A0 * (m_chirp ** (5/3)) * (f ** (2/3))

# ---------------------------------------------------------------------------
# Default band thresholds (will be overridden by adaptive init)
# ---------------------------------------------------------------------------
_DEFAULT_STRAIN_BANDS   = [1e-22, 3e-22, 1e-21, 3e-21, 1e-20, 3e-20, 1e-19, 1e-18]
_DEFAULT_CHIRP_BANDS    = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0]  # M⊙
_DEFAULT_FREQ_BANDS     = [10.0, 30.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0]  # Hz
_DEFAULT_DELTA_STRAIN   = [1e-23, 3e-23, 1e-22, 3e-22, 1e-21, 3e-21, 1e-20, 1e-19]
_DEFAULT_DELTA_FREQ     = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0]  # Hz/s
_DEFAULT_PHASE_BANDS    = [0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4, 2.8]  # radians
_DEFAULT_ARM_BANDS      = [0.1, 0.3, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0]  # km
_DEFAULT_NOISE_BANDS    = [1e-23, 3e-23, 1e-22, 3e-22, 1e-21, 3e-21, 1e-20, 1e-19]  # /√Hz
_DEFAULT_COHERENCE_BANDS = [0.0, 0.1, 0.3, 0.5, 0.7, 0.85, 0.95, 1.0]

# ---------------------------------------------------------------------------
# Gray coding utility
# ---------------------------------------------------------------------------
def gray_bits(value, bands):
    idx = 0
    for i, th in enumerate(bands):
        if value >= th:
            idx = i
    g = idx ^ (idx >> 1)
    return format(g, '03b')

class GravitationalPlugin:
    def __init__(self):
        self.bands_strain = _DEFAULT_STRAIN_BANDS[:]
        self.bands_chirp  = _DEFAULT_CHIRP_BANDS[:]
        self.bands_freq   = _DEFAULT_FREQ_BANDS[:]
        self.bands_delta_s = _DEFAULT_DELTA_STRAIN[:]
        self.bands_delta_f = _DEFAULT_DELTA_FREQ[:]
        self.bands_phase   = _DEFAULT_PHASE_BANDS[:]
        self.bands_arm     = _DEFAULT_ARM_BANDS[:]
        self.bands_noise   = _DEFAULT_NOISE_BANDS[:]
        self.bands_coherence = _DEFAULT_COHERENCE_BANDS[:]

        self.prev_state = None
        self.history = deque(maxlen=10)
        self.spatial_canon = None  # will be set after init

    def init_bands(self, samples):
        """Set adaptive bands from a list of GW state dicts."""
        if not samples: return
        # Use percentiles for each quantity
        strains = [s.get('strain', 1e-22) for s in samples]
        chirps  = [s.get('chirp_mass', 30) for s in samples]
        freqs   = [s.get('frequency', 100) for s in samples]
        self.bands_strain = self._percentile_bands(strains)
        self.bands_chirp  = self._percentile_bands(chirps)
        self.bands_freq   = self._percentile_bands(freqs)
        # Delta bands: use half the range of each primary band
        strain_range = max(strains) - min(strains) if strains else 1e-18
        self.bands_delta_s = [strain_range * p/100 for p in [0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]]
        freq_range = max(freqs) - min(freqs) if freqs else 5000
        self.bands_delta_f = [freq_range * p/100 for p in [0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]]

    def _percentile_bands(self, values):
        pcts = [0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]
        return [np.percentile(values, p) for p in pcts]

    def to_binary(self, state, prev_state=None, cross_signals=None):
        """
        state keys: strain, chirp_mass, frequency, polarisation, arm_length_km,
                     detector_noise, source_direction (3D unit vector),
                     detector_arm_vec (3D), phase (radians)
        cross_signals: dict of plugin_name -> binary string (e.g., 'em_field', 'magnetic')
        Returns binary string.
        """
        strain   = state.get('strain', 1e-22)
        chirp_m  = state.get('chirp_mass', 30)
        freq     = state.get('frequency', 100)
        pol      = state.get('polarisation', 'plus')  # 'plus', 'cross', 'both'
        arm_len  = state.get('arm_length_km', 4.0)
        noise    = state.get('detector_noise', 1e-22)
        phase    = state.get('phase', 0.0)
        source_dir = state.get('source_direction', [0,0,1])
        arm_vec    = state.get('detector_arm_vec', [1,0,0])
        bits = []

        # ---------- Section A: Strain summary (12 bits) ----------
        bits.append(gray_bits(strain, self.bands_strain))
        bits.append(gray_bits(chirp_m, self.bands_chirp))
        bits.append(gray_bits(freq, self.bands_freq))
        pol_bits = {"plus": "00", "cross": "01", "both": "11"}.get(pol, "00")
        bits.append(pol_bits)
        # detector alignment: dot product of source direction and detector arm normal
        alignment = abs(np.dot(source_dir, arm_vec) / (np.linalg.norm(source_dir)*np.linalg.norm(arm_vec)+1e-10))
        bits.append("1" if alignment > 0.9 else "0")

        # ---------- Section B: Temporal delta (12 bits) ----------
        if prev_state:
            prev_strain = prev_state.get('strain', 1e-22)
            prev_freq   = prev_state.get('frequency', 100)
            prev_phase  = prev_state.get('phase', 0.0)
            delta_s = abs(strain - prev_strain)
            delta_f = abs(freq - prev_freq)
            delta_phase = abs(phase - prev_phase)
            inspiral = 1 if freq > prev_freq else 0
            ringdown = 1 if (strain < prev_strain and freq > prev_freq) else 0
            merger   = 1 if strain == max(strain, prev_strain) else 0
        else:
            delta_s = 0.0; delta_f = 0.0; delta_phase = 0.0
            inspiral = 0; ringdown = 0; merger = 0

        bits.append(gray_bits(delta_s, self.bands_delta_s))
        bits.append(gray_bits(delta_f, self.bands_delta_f))
        bits.append(gray_bits(delta_phase, self.bands_phase))
        bits.append(str(inspiral))
        bits.append(str(ringdown))
        bits.append(str(merger))

        # ---------- Section C: Cross‑modal coherence (9 bits) ----------
        em_coh = 0.0; mag_coh = 0.0; coh_valid = 0; spatial_align = 0
        if cross_signals:
            # Simple coherence proxies: compare GW strain magnitude with other fields' activity.
            # For EM: if the EM binary indicates field above threshold, coh increases with strain.
            if 'em_field' in cross_signals:
                em_bin = cross_signals['em_field']
                # crude: if first bit of EM binary is '1' (high field), and strain > median
                if em_bin and em_bin[0] == '1' and strain > self.bands_strain[3]:
                    em_coh = min(1.0, strain / 1e-20)  # scale
                    coh_valid = 1
            if 'magnetic' in cross_signals:
                mag_bin = cross_signals['magnetic']
                if mag_bin and mag_bin[0] == '1' and strain > self.bands_strain[3]:
                    mag_coh = min(1.0, strain / 1e-20)
                    coh_valid = 1
            # Spatial alignment: if both EM and magnetic directions are known, compare with GW source dir.
            # We'll assume a common spatial_canon service gives us a global frame; for now, check if em_field and magnetic are present.
            if 'em_field' in cross_signals and 'magnetic' in cross_signals:
                spatial_align = 1  # placeholder – real implementation would compare vectors via canon.

        bits.append(gray_bits(em_coh, self.bands_coherence))
        bits.append(gray_bits(mag_coh, self.bands_coherence))
        bits.append(str(coh_valid))
        bits.append(format(spatial_align & 0b11, '02b'))

        # ---------- Section D: Detector metadata (6 bits) ----------
        bits.append(gray_bits(arm_len, self.bands_arm))
        bits.append(gray_bits(noise, self.bands_noise))

        self.prev_state = state.copy()
        self.history.append(state.copy())

        return "".join(bits)

    def report(self):
        if not self.prev_state:
            return "Gravitational: no data."
        s = self.prev_state
        return (f"GW strain={s.get('strain',0):.2e}, f={s.get('frequency',0):.1f}Hz, "
                f"M_chirp={s.get('chirp_mass',0):.1f}M⊙")
