PLUGIN_META = {
    "name": "treaty_memory",
    "description": "Slow-moving, long-term trust score based on accumulated accurate decoding over time.",
    "class_name": "TreatyMemoryPlugin",
}

class TreatyMemoryPlugin:
    def __init__(self, initial_trust=0.5, gain_rate=0.01, loss_rate=0.05, felt_threshold=0.7):
        self.trust_scores = {}    # user_id -> float 0..1
        self.initial = initial_trust
        self.gain = gain_rate
        self.loss = loss_rate
        self.threshold = felt_threshold

    def get_trust(self, user_id="default"):
        if user_id not in self.trust_scores:
            self.trust_scores[user_id] = self.initial
        return self.trust_scores[user_id]

    def update(self, user_id, felt_level):
        current = self.get_trust(user_id)
        if felt_level >= self.threshold:
            new_trust = min(1.0, current + self.gain)
        else:
            new_trust = max(0.0, current - self.loss)
        self.trust_scores[user_id] = new_trust
        return new_trust

    def flag_manipulation_risk(self, user_id, window_size=10):
        # placeholder — in a real system, look at recent mis‑decode frequency
        return False
