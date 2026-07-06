# plugins/scheduling_entropy_monitor.py
import numpy as np
from collections import deque

PLUGIN_META = {
    "name": "scheduling_entropy",
    "description": "Monitors orchestrator decision entropy. Flags when the harmony field becomes incoherent.",
    "class_name": "SchedulingEntropyMonitor",
}

class SchedulingEntropyMonitor:
    def __init__(self, harmony_engine, window_size=20, entropy_threshold=0.7):
        self.engine = harmony_engine
        self.window = deque(maxlen=window_size)
        self.threshold = entropy_threshold

    def compute_entropy(self, velocities):
        """Entropy of the velocity distribution. High entropy = many nodes pulling equally; low = one clear priority."""
        v = np.array(velocities)
        if np.sum(v) == 0:
            return 0.0
        p = v / np.sum(v)
        p = p[p > 0]
        return -np.sum(p * np.log(p)) / np.log(len(v))  # normalized entropy 0..1

    def check(self):
        _, velocities, _ = self.engine.step()
        self.window.append(velocities)
        if len(self.window) < self.window.maxlen:
            return False, 0.0
        # Use mean velocities across the window for a stable reading
        mean_vels = np.mean(self.window, axis=0)
        entropy = self.compute_entropy(mean_vels)
        if entropy > self.threshold:
            return True, entropy  # coherence lost, need recalibration
        return False, entropy

    def report_bits(self):
        """Gray‑coded entropy level (3 bits)."""
        flagged, entropy = self.check()
        band = min(7, int(entropy * 8))
        gray = band ^ (band >> 1)
        return format(gray, '03b') + ('1' if flagged else '0')
