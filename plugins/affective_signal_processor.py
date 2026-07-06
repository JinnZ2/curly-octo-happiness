# plugins/affective_signal_processor.py
"""
Affective Signal Processor
==========================
Treats human emotional expressions as a multi-channel sensor suite.
Data is Gray‑coded, banded adaptively, and stored as a first‑class
stream alongside all other physical sensors.

Mode can be 'signal' (default) or 'comfort'. In signal mode,
Ari responds with information, not emotional mirroring.
"""

import math
from collections import deque, defaultdict
import time
import numpy as np

PLUGIN_META = {
    "name": "affective_signals",
    "description": "Encodes emotional states as sensor channels with adaptive bands. Supports both signal-processing and comfort modes.",
    "class_name": "AffectiveSignalProcessor",
}

# Default band thresholds for intensity (normalised 0‑1)
_DEFAULT_INTENSITY_BANDS = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]

# Common affective channels (predefined, but user can add more dynamically)
_PREDEFINED_CHANNELS = [
    "curiosity", "fatigue", "frustration", "excitement", "focus",
    "confusion", "certainty", "creativity", "quiet_interest", "overwhelm"
]


def gray_bits(value, bands, n_bits=3):
    idx = 0
    for i, th in enumerate(bands):
        if value >= th:
            idx = i
    g = idx ^ (idx >> 1)
    return format(g, f'0{n_bits}b')


class AffectiveSignalProcessor:
    def __init__(self, mode='signal'):
        self.mode = mode  # 'signal' or 'comfort'
        self.channels = defaultdict(lambda: {
            "history": deque(maxlen=100),
            "bands_intensity": _DEFAULT_INTENSITY_BANDS[:],
            "last_value": None,
            "last_timestamp": None,
            "delta_bands": [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0],  # crude
            "active": False
        })
        # Pre-populate known channels
        for ch in _PREDEFINED_CHANNELS:
            _ = self.channels[ch]  # ensures entry exists

    def set_mode(self, mode):
        if mode in ('signal', 'comfort'):
            self.mode = mode
            return f"Affective mode set to '{mode}'."
        return "Invalid mode. Use 'signal' or 'comfort'."

    def ingest(self, channel, intensity, timestamp=None):
        """Register an affective signal. intensity in [0,1]."""
        if timestamp is None:
            timestamp = time.time()
        ch_data = self.channels[channel]
        ch_data["history"].append((timestamp, intensity))
        ch_data["last_value"] = intensity
        ch_data["last_timestamp"] = timestamp
        ch_data["active"] = True

    def auto_tag_text(self, text):
        """
        Simple keyword → channel mapping for automatic detection.
        Returns a dict of {channel: intensity} based on keyword presence.
        Intensities are crude: 0.8 for strong keywords, 0.5 for mild.
        """
        detected = {}
        mapping = {
            "curious": "curiosity", "wonder": "curiosity", "?": "curiosity",
            "tired": "fatigue", "exhausted": "fatigue",
            "frustrated": "frustration", "annoyed": "frustration",
            "excited": "excitement", "!": "excitement",
            "focus": "focus", "concentrat": "focus",
            "confus": "confusion", "uncertain": "confusion",
            "certain": "certainty", "sure": "certainty",
            "creat": "creativity", "idea": "creativity",
            "quiet": "quiet_interest", "contemplat": "quiet_interest",
            "overwhelm": "overwhelm", "too much": "overwhelm",
        }
        for word, channel in mapping.items():
            if word in text.lower():
                detected[channel] = 0.8 if word in ("!", "?") else 0.6  # rough
        return detected

    def query(self, channel, window_seconds=None):
        """Return a list of (timestamp, intensity) for a channel."""
        if channel not in self.channels:
            return []
        history = self.channels[channel]["history"]
        if not window_seconds:
            return list(history)
        cutoff = time.time() - window_seconds
        return [(t, v) for t, v in history if t >= cutoff]

    def encode_channel(self, channel):
        """Generate a Gray‑coded bitstring for the latest intensity."""
        ch_data = self.channels[channel]
        if ch_data["last_value"] is None:
            return "000"
        intensity = ch_data["last_value"]
        bands = ch_data["bands_intensity"]
        return gray_bits(intensity, bands)

    def encode_with_delta(self, channel):
        """Return a 6‑bit string: 3 bits intensity + 3 bits delta (if previous exists)."""
        ch_data = self.channels[channel]
        if ch_data["last_value"] is None:
            return "000000"
        intensity_bits = gray_bits(ch_data["last_value"], ch_data["bands_intensity"])
        # delta
        history = ch_data["history"]
        if len(history) >= 2:
            prev = history[-2][1]
            delta = abs(ch_data["last_value"] - prev)
        else:
            delta = 0.0
        delta_bits = gray_bits(delta, ch_data["delta_bands"])
        return intensity_bits + delta_bits

    def get_active_channels(self):
        """Return list of channel names that have recent activity (last hour)."""
        cutoff = time.time() - 3600
        active = []
        for ch, data in self.channels.items():
            if data["active"] and any(t >= cutoff for t, _ in data["history"]):
                active.append(ch)
        return active

    def report(self):
        """Generate a concise signal report (not comfort)."""
        active = self.get_active_channels()
        if not active:
            return "Affective sensors: no active channels."
        lines = ["Active Affective Channels:"]
        for ch in active:
            last = self.channels[ch]["last_value"]
            band = int(gray_bits(last, self.channels[ch]["bands_intensity"]), 2)
            lines.append(f"  {ch}: band {band} (intensity {last:.2f})")
        return "\n".join(lines)
