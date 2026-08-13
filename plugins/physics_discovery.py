"""
Physics Discovery Loop Plugin
==============================
Detects novel patterns in raw data streams and automatically creates new GEIS encoders.
"""

import os
import sys

import numpy as np
from collections import deque

# The variety meter lives in the shared core package; plugins/ is normally on
# sys.path with the repo root absent, so reach the root before importing.
try:
    from grounding.core.variety import VarietyMeter
except ImportError:  # pragma: no cover - depends on how the plugin was loaded
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from grounding.core.variety import VarietyMeter

PLUGIN_META = {
    "name": "physics_discovery",
    "description": "Autonomously discovers new physical quantities from raw data and creates encoders.",
    "class_name": "PhysicsDiscoveryPlugin",
}

class PhysicsDiscoveryPlugin:
    # Resolution at which the incoming stream is assumed to present genuinely
    # distinguishable states. This is the "disturbance alphabet" the encoders
    # are being measured against.
    REFERENCE_BINS = 32

    def __init__(self):
        self.data_buffers = {}          # stream_name -> deque of (timestamp, value)
        self.novelty_threshold = 0.9    # fraction of data outside known bands
        self.variety_threshold = 0.5    # bits of margin below which the alarm fires
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

    def _known_bands(self):
        """Band-threshold lists exposed by every currently loaded encoder."""
        known = []
        if not self.plugin_manager:
            return known
        for pname, pdata in self.plugin_manager.plugins.items():
            inst = pdata["instance"]
            for attr in ["bands_magnitude", "bands_strain", "bands_B", "_DEFAULT_MAGNITUDE_BANDS"]:
                bands = getattr(inst, attr, None)
                if bands:
                    known.append(sorted(bands))
                    break
        return known

    def _response_codeword(self, value, known_bands=None):
        """The codeword the *current* encoders can express for this value.

        This is the regulator's side of Ashby's inequality. Values that fall
        outside every known band range all collapse onto the same edge
        codeword -- which is exactly the variety deficit we want to measure,
        not a detail to paper over.
        """
        magnitude = abs(value)
        for i, bands in enumerate(self._known_bands() if known_bands is None
                                  else known_bands):
            if bands[0] <= magnitude <= bands[-1]:
                idx = 0
                for j, threshold in enumerate(bands):
                    if magnitude >= threshold:
                        idx = j
                return (i, idx)
        return ("out_of_range",)

    def variety_status(self, stream_name, threshold=None):
        """Requisite-variety check for one stream (Ashby: V(R) >= V(D)).

        Disturbance variety is measured at `REFERENCE_BINS` resolution over the
        range the stream actually visited; response variety over the codewords
        the loaded encoders can currently produce for those same values. When
        the margin closes, the sensorium has run out of distinctions and the
        bands need widening -- which is the trigger signal the discovery loop
        was missing: novelty says "I have never seen this", variety says
        "I can no longer tell these apart".

        Returns the meter's status dict, or None if the buffer is too short.
        """
        if stream_name not in self.data_buffers:
            return None
        values = [v for _, v in self.data_buffers[stream_name]]
        if len(values) < 10:
            return None

        lo, hi = min(values), max(values)
        span = hi - lo
        known_bands = self._known_bands()
        meter = VarietyMeter(name=stream_name)
        for v in values:
            if span > 0:
                fine = min(self.REFERENCE_BINS - 1,
                           int((v - lo) / span * self.REFERENCE_BINS))
            else:
                fine = 0
            meter.observe(fine, self._response_codeword(v, known_bands))

        return meter.status(self.variety_threshold if threshold is None else threshold)

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

        known_ranges = [(min(b), max(b)) for b in self._known_bands()]

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

    def propose_encoder(self, stream_name, description_hint="", bands=None):
        """
        Generate a full encoder description dict for meta‑encoder.

        Args:
            bands: pre-computed thresholds. Defaults to the novelty check's
                proposal; pass them in when another trigger (e.g. the variety
                alarm) licensed the encoder instead.
        """
        if bands is None:
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

    def run_full_discovery(self, stream_name, description_hint="", trigger="novelty"):
        """
        Full autonomous cycle: check trigger → propose encoder → create → load.

        Args:
            trigger: what licenses building a new encoder.
                "novelty" (default) — the historical rule: most of the buffered
                    data falls outside every known band range.
                "variety" — Ashby's rule: the encoders' response variety has
                    closed on the stream's disturbance variety, so the agent can
                    no longer tell presented states apart even where the values
                    are nominally in range.
                "either" — fire on whichever condition trips first.
        """
        if trigger not in ("novelty", "variety", "either"):
            raise ValueError(f"unknown trigger: {trigger!r}")

        novelty, bands = self.check_for_novelty(stream_name)
        variety = self.variety_status(stream_name) if trigger in ("variety", "either") else None
        variety_alarm = bool(variety and variety["alarm"])
        novelty_alarm = novelty >= self.novelty_threshold

        fired = (novelty_alarm if trigger == "novelty"
                 else variety_alarm if trigger == "variety"
                 else novelty_alarm or variety_alarm)
        if not fired:
            if trigger == "novelty":
                return f"📉 Novelty score {novelty:.2f} below threshold, no action."
            margin = variety["margin"] if variety else float("nan")
            return (f"📉 Novelty {novelty:.2f}, variety margin {margin:+.2f} bits — "
                    "both within tolerance, no action.")

        reason = ("variety deficit" if variety_alarm and not novelty_alarm
                  else "novelty" if novelty_alarm and not variety_alarm
                  else "novelty + variety deficit")

        if bands is None:
            # The variety alarm can fire on in-range data, where check_for_novelty
            # declines to propose. Band the buffer on its own percentiles anyway —
            # that widening is the whole response to a closed margin.
            values = [v for _, v in self.data_buffers.get(stream_name, [])]
            if len(values) < 10:
                return "⚠️ Not enough data to propose bands."
            bands = [np.percentile(values, p)
                     for p in [0, 12.5, 25, 37.5, 50, 62.5, 75, 87.5]]

        config, err = self.propose_encoder(stream_name, description_hint, bands=bands)
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
        detail = f"novelty={novelty:.2f}"
        if variety is not None:
            detail += f", variety margin={variety['margin']:+.2f} bits"
        if self.agent is not None:
            self.agent.memory.add(
                "agent",
                f"Discovered new encoder '{config['name']}' ({reason}; {detail})",
                tags=["discovery"])
        return f"🔬 Discovery ({reason}): {detail}\n{create_msg}\n{load_msg}"
