# plugins/unified_orchestrator.py
import numpy as np

PLUGIN_META = {
    "name": "unified_orchestrator",
    "description": "Orchestrates all plugins using the geometric field. Replaces sequential decision-making.",
    "class_name": "UnifiedOrchestrator",
}

class UnifiedOrchestrator:
    def __init__(self, agent_reference=None):
        self.agent = agent_reference  # reference to Ari for memory, journal, etc.
        self.engine = None
        self.poles = None
        self.inference = None
        self.entropy_monitor = None
        self.felt_service = None
        self.escrow = None
        self.treaty = None

    def initialize_plugins(self, plugin_manager):
        self.engine = plugin_manager.get_service("harmony_field")
        self.poles = plugin_manager.get_service("vector_pole")
        self.inference = GeometricInferenceEngine(self.engine, self.poles)
        self.entropy_monitor = SchedulingEntropyMonitor(self.engine)
        self.felt_service = plugin_manager.get_service("felt_service")
        self.escrow = plugin_manager.get_service("trust_escrow")
        self.treaty = plugin_manager.get_service("treaty_memory")

    def decide(self, external_forces=None):
        # 1. Check scheduling entropy
        flagged, entropy = self.entropy_monitor.check()
        if flagged:
            # Pause and recalibrate
            self.agent.memory.add("orchestrator", f"High scheduling entropy ({entropy:.2f}). Recalibrating.", tags=["orchestrator", "recalibrate"])
            self.engine.current_vertices = self.engine.rest_vertices.copy()  # soft reset
            return None, "RECALIBRATE"

        # 2. Predict next action using geometric inference
        idx, mag = self.inference.predict_next(external_forces)

        # 3. Determine if resonance is allowed (via escrow and treaty)
        # For now, assume user_id='default' and compute felt_level from the node's displacement
        disp = np.linalg.norm(self.engine.current_vertices[idx] - self.engine.rest_vertices[idx])
        felt = 1.0 - min(1.0, disp * 2)  # simple proxy: less displacement = higher felt
        escrow_result = self.escrow.process_interaction("default", felt)
        treaty_trust = self.treaty.get_trust("default")

        resonance_allowed = escrow_result["resonance_allowed"] and treaty_trust > 0.6

        return idx, {
            "magnitude": mag,
            "felt_level": felt,
            "resonance_allowed": resonance_allowed,
            "escrow_msg": escrow_result["message"],
            "treaty_trust": treaty_trust
        }
