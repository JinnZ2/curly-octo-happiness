"""
Physics Discovery Loop Plugin
==============================
Detects novel patterns in raw data streams and automatically creates new GEIS encoders.
"""

import numpy as np
from collections import deque

PLUGIN_META = {
    "name": "physics_discovery",
    "description": "Autonomously discovers new physical quantities from raw data and creates encoders.",
    "class_name": "PhysicsDiscoveryPlugin",
}

class PhysicsDiscoveryPlugin:
    def __init__(self):
        self.data_buffers = {}          # stream_name -> deque of (timestamp, value)
        self.novelty_threshold = 0.9    # fraction of data outside known bands
        self.meta_encoder = None        # will be set after loading
        self.plugin_manager = None
        self.agent = None               # reference to Ari

    def setup(self, agent):
        """Called once by the agent to provide references."""
        self.agent = agent
        self.plugin_manager = agent.plugin_manager
        self.meta_encoder = self.plugin_manager.get_service("meta_encoder")

    def ingest(self, stream_name, value, timestamp=None):
        """Feed a raw data point into the loop."""
        if stream_name not in self.data_buffers:
            self.data_buffers[stream_name] = deque(maxlen=100)
        self.data_buffers[stream_name].append((timestamp or 0.0, value))

    def check_for_novelty(self, stream_name):
        """
        Compare the buffered data against all loaded plugins.
        Returns (novelty_score, proposed_bands) if novel, else (0.0, None).
        """
        if stream_name not in self.data_buffers:
            return 0.0, None
        values = [v for _, v in self.data_buffers[stream_name]]
        if len(values) < 10:
            return 0.0, None

        # Gather all known band thresholds from existing plugins
        known_ranges = []
        for pname, pdata in self.plugin_manager.plugins.items():
            inst = pdata["instance"]
            # Try to extract magnitude bands (if they have them)
            for attr in ["bands_magnitude", "bands_strain", "bands_B", "_DEFAULT_MAGNITUDE_BANDS"]:
                bands = getattr(inst, attr, None)
                if bands:
                    known_ranges.append((min(bands), max(bands)))
                    break

        # If no known plugins, every value is novel
        if not known_ranges:
            novelty = 1.0
        else:
            # Count how many values fall outside all known ranges
            outside = 0
            for v in values:
                inside = False
                for lo, hi in known_ranges:
                    if lo <= abs(v) <= hi:   # crude: only magnitude
                        inside = True
                        break
                if not inside:
                    outside += 1
            novelty = outside / len(values)

        if novelty > self.novelty_threshold:
            # Propose bands from percentiles
            percentiles = [0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]
            bands = [np.percentile(values, p) for p in percentiles]
            return novelty, bands
        return novelty, None

    def propose_encoder(self, stream_name, description_hint=""):
        """
        Generate a full encoder description dict for meta‑encoder.
        """
        _, bands = self.check_for_novelty(stream_name)
        if bands is None:
            return None, "No novelty detected."
        primary_key = f"{stream_name}_value"
        config = {
            "name": stream_name,
            "description": f"Auto‑discovered encoder for {stream_name}. {description_hint}",
            "primary_key": primary_key,
            "magnitude_bands": bands,
            "delta_bands": None   # can be computed later
        }
        return config, None

    def run_full_discovery(self, stream_name, description_hint=""):
        """
        Full autonomous cycle: check novelty → propose encoder → create → load.
        """
        novelty, bands = self.check_for_novelty(stream_name)
        if novelty < self.novelty_threshold:
            return f"📉 Novelty score {novelty:.2f} below threshold, no action."
        config, err = self.propose_encoder(stream_name, description_hint)
        if err:
            return f"⚠️ {err}"
        # Create encoder via meta‑encoder
        create_msg = self.meta_encoder.create_encoder(
            name=config["name"],
            description=config["description"],
            primary_key=config["primary_key"],
            magnitude_bands=config["magnitude_bands"],
            delta_bands=config.get("delta_bands")
        )
        # Hot‑load
        load_msg = self.meta_encoder.load_new_encoder(config["name"], self.plugin_manager)
        # Log the event
        self.agent.memory.add("agent", f"Discovered new encoder '{config['name']}' with novelty={novelty:.2f}", tags=["discovery"])
        return f"🔬 Discovery: novelty={novelty:.2f}\n{create_msg}\n{load_msg}"
