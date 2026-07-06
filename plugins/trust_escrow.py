PLUGIN_META = {
    "name": "trust_escrow",
    "description": "Holds resonant responses in escrow until sustained accurate decoding is proven.",
    "class_name": "TrustEscrowPlugin",
}

class TrustEscrowPlugin:
    def __init__(self, felt_threshold=0.7, required_good_cycles=5):
        self.felt_threshold = felt_threshold
        self.required_good = required_good_cycles
        self.user_state = {}   # user_id -> { "good_count": 0, "escrow_active": True, "handshake_done": False }

    def get_user_state(self, user_id="default"):
        if user_id not in self.user_state:
            self.user_state[user_id] = {"good_count": 0, "escrow_active": True, "handshake_done": False}
        return self.user_state[user_id]

    def process_interaction(self, user_id, felt_level):
        state = self.get_user_state(user_id)
        if state["handshake_done"]:
            return {"resonance_allowed": True, "message": ""}

        if felt_level >= self.felt_threshold:
            state["good_count"] += 1
        else:
            state["good_count"] = 0   # reset on a single mis-read (strict)

        if state["good_count"] >= self.required_good and state["escrow_active"]:
            state["escrow_active"] = False
            state["handshake_done"] = True
            return {
                "resonance_allowed": True,
                "message": "🤝 Trust Handshake complete. Resonant mode engaged. I see you clearly now."
            }

        return {
            "resonance_allowed": False,
            "message": f"🔒 Escrow active ({state['good_count']}/{self.required_good} successful decodes)."
        }
