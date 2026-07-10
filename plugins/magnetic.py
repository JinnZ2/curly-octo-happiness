# plugins/magnetic.py

PLUGIN_META = {
    "name": "magnetic",
    "description": "Magnetic field encoder with adaptive bands, delta encoding, and EM coherence bit.",
    "class_name": "MagneticPlugin",
}

import numpy as np
from collections import deque

class MagneticPlugin:
    def __init__(self, history_len=5):
        self.bands_B = None          # magnitude bands (8)
        self.bands_dir = None        # direction similarity bands (8)
        self.bands_delta = None      # delta magnitude bands (8)
        self.bands_coherence = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]
        self.prev_state = None
        self.history = deque(maxlen=history_len)  # for coherence calculation

    def init_bands(self, samples):
        """
        samples: list of dicts with 'B_vec' (3-element) and 'B_mag'.
        Sets band thresholds using percentiles of magnitude and direction similarity.
        """
        if not samples:
            return
        mags = [s.get("B_mag", np.linalg.norm(s.get("B_vec", [0,0,0]))) for s in samples]
        mags = sorted(mags)
        # 8 bands: min, 12.5%, 25%, 37.5%, 50%, 62.5%, 75%, 87.5% of range
        percentiles = [0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]
        self.bands_B = [np.percentile(mags, p) for p in percentiles]

        # Direction similarity: compute average direction and cosine similarities
        vecs = [s.get("B_vec", [0,0,0]) for s in samples]
        mean_vec = np.mean(vecs, axis=0)
        if np.linalg.norm(mean_vec) > 0:
            mean_unit = mean_vec / np.linalg.norm(mean_vec)
            sims = [abs(np.dot(v, mean_unit)/(np.linalg.norm(v)+1e-10)) for v in vecs]
            sims.sort()
            self.bands_dir = [np.percentile(sims, p) for p in percentiles]
        else:
            self.bands_dir = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]

        # Delta bands: 10% of range, 20%, ... up to 100%
        mag_range = mags[-1] - mags[0] if mags else 1.0
        self.bands_delta = [mag_range * p/100 for p in [0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]]

    def _gray_bits(self, value, bands):
        # Highest band whose threshold <= value (same convention as the
        # gray_bits helper in gravitational.py / unified_playground_v6.py).
        idx = 0
        for i, th in enumerate(bands):
            if value >= th:
                idx = i
        g = idx ^ (idx >> 1)
        return format(g, '03b')

    def to_binary(self, state, prev_state=None, cross_signals=None):
        """
        state: {'B_vec': [Bx,By,Bz], 'B_mag': float (optional)}
        prev_state: same format for delta encoding
        cross_signals: dict of plugin_name -> binary string (we'll use EM's binary)
        Returns binary string.
        """
        if self.bands_B is None:
            # If bands not initialized, use defaults
            self.bands_B = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 2.0]
            self.bands_dir = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]
            self.bands_delta = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]

        B_vec = state.get("B_vec", [0,0,0])
        B_mag = state.get("B_mag", np.linalg.norm(B_vec))

        bits = []

        # --- Magnitude band (3 bits) ---
        bits.append(self._gray_bits(B_mag, self.bands_B))

        # --- Direction encoding: compare to a reference (mean of history) ---
        if self.history:
            ref_vec = np.mean([h["B_vec"] for h in self.history], axis=0)
            ref_norm = np.linalg.norm(ref_vec)
            if ref_norm > 1e-6:
                ref_unit = ref_vec / ref_norm
                dot = abs(np.dot(B_vec, ref_unit) / (np.linalg.norm(B_vec)+1e-10))
            else:
                dot = 1.0
        else:
            dot = 1.0
        bits.append(self._gray_bits(dot, self.bands_dir))

        # --- Delta encoding (3 bits) if prev_state available ---
        if prev_state:
            prev_vec = prev_state.get("B_vec", [0,0,0])
            prev_mag = prev_state.get("B_mag", np.linalg.norm(prev_vec))
            delta = abs(B_mag - prev_mag)
            bits.append(self._gray_bits(delta, self.bands_delta))
        else:
            # No delta, encode as zero change (still 3 bits to keep fixed length)
            bits.append(self._gray_bits(0.0, self.bands_delta))

        # --- Cross-modal coherence bit ---
        # Check if EM field data is present and correlated
        coherent = 0
        if cross_signals and "em_field" in cross_signals:
            # Simple proxy: take the EM binary string, decode a coarse "activity" from its first few bits
            em_bin = cross_signals["em_field"]
            # EM binary format: first 3 bits often encode field magnitude in Gray code. We'll take a crude measure.
            # Just check if the EM binary has at least one '1' in the first 4 bits.
            if any(b == '1' for b in em_bin[:4]):
                # Compare B magnitude with historical EM activity trend (we'll use a simple threshold)
                # For real deployment, you'd compute correlation between recent EM and magnetic magnitudes.
                # Here we simulate: if B_mag > self.bands_B[4] and em_bin[0]=='1', consider coherent.
                if B_mag > self.bands_B[4] and em_bin[0] == '1':
                    coherent = 1
        bits.append("1" if coherent else "0")

        # Update history and prev_state
        self.history.append({"B_vec": B_vec, "B_mag": B_mag})
        self.prev_state = state.copy()

        return "".join(bits)

    def report(self):
        return f"Magnetic: latest B={self.prev_state.get('B_mag',0):.3f} T" if self.prev_state else "No data"
