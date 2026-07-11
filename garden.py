#!/usr/bin/env python3
"""
garden.py – Claim & Falsification Garden (enhanced)
A ball rolling in a 1D bumpy world. The agent learns to predict outcomes,
makes claims about what will happen, tests them, and updates its understanding.
Curiosity is rewarded when its world model gets better.
"""

import random
import math

from grounding.core.claims import Claim
from grounding.worlds.bumpy import BumpyWorld, WorldModel

# ---------- Agent ----------
class CuriousExplorer:
    def __init__(self):
        self.claims = []
        self.world_model = WorldModel()
        self.last_prediction_error = None
        self.curiosity_reward = 0.0

    def make_claim(self, description, condition):
        claim = Claim(description, condition)
        self.claims.append(claim)
        return claim

    def choose_action(self, x):
        # Simple policy: if world model error is high, explore more (random force)
        # Otherwise, try to go uphill (force proportional to slope) – a weak bias
        if self.world_model.average_error() > 0.3:
            return random.uniform(-1, 1)
        else:
            # go against slope (uphill)
            slope = math.cos(x) * 0.5
            return 0.5 * math.copysign(1, -slope) + random.uniform(-0.3, 0.3)

    def act_and_claim(self, env: BumpyWorld):
        x = env.x
        action = self.choose_action(x)
        # Claim: predict next position
        predicted_next = self.world_model.predict(x, action)
        next_x, reward = env.step(action)
        # World model update and error
        error = self.world_model.update(x, action, next_x)
        # Curiosity: improvement in model's average error (before vs after)
        old_avg = self.world_model.average_error()  # won't reflect current yet
        # we approximate: difference in absolute error from previous step
        if self.last_prediction_error is not None:
            self.curiosity_reward = self.last_prediction_error - abs(error)
        self.last_prediction_error = abs(error)

        # Make a claim based on prediction
        claim = self.make_claim(
            f"Applying force {action:.2f} at x={x:.2f} will move the ball to about {predicted_next:.2f}",
            f"If the observed position differs by more than 0.3, the model is wrong here."
        )
        # Test: did it land within 0.3?
        test_passed = abs(next_x - predicted_next) < 0.3
        claim.test(test_passed)
        return {
            "action": action,
            "predicted": predicted_next,
            "actual": next_x,
            "error": abs(error),
            "curiosity": self.curiosity_reward,
            "claim": claim
        }

# ---------- Run the garden ----------
if __name__ == "__main__":
    env = BumpyWorld()
    agent = CuriousExplorer()

    print("🌱 Claim & Falsification Garden – Ball on a Bumpy Slope\n")
    for t in range(100):
        result = agent.act_and_claim(env)
        print(f"Step {t:3d} | action={result['action']:+.2f} | predicted {result['predicted']:.2f} "
              f"-> actual {result['actual']:.2f} | error {result['error']:.3f} | "
              f"curiosity {result['curiosity']:+.3f} | claim: {result['claim']}")

    print("\n📊 Final world model weights:", agent.world_model.w, "bias:", agent.world_model.b)
    print("🧠 Agent claims summary:")
    for c in agent.claims[-10:]:
        print(f"  {c}")
