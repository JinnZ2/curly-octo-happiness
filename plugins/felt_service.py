# plugins/felt_service.py
PLUGIN_META = {
    "name": "felt_service",
    "description": "Computes the handshake level between model and reality. Gate for all resonant responses.",
    "class_name": "FeltService",
}

class FeltService:
    def __init__(self, felt_threshold=0.6):
        self.threshold = felt_threshold

    def compute(self, health_score, confidence, drift_pct):
        drift_factor = drift_pct / 100.0
        felt = (health_score * confidence) / (1.0 + drift_factor)
        return max(0.0, min(1.0, felt))

    def is_synced(self, felt_level):
        return felt_level >= self.threshold
