#!/usr/bin/env python3
"""
garden.py – Claim & Falsification Garden (enhanced)
A ball rolling in a 1D bumpy world. The agent learns to predict outcomes,
makes claims about what will happen, tests them, and updates its understanding.
Curiosity is rewarded when its world model gets better.
"""

import random
import math
import time
from collections import deque

# ---------- Environment: 1D bumpy terrain ----------
class BumpyWorld:
    def __init__(self):
        self.x = 0.0
        self.v = 0.0
        self.terrain = lambda x: math.sin(x) * 0.5  # heights between -0.5 and 0.5
        self.step_count = 0

    def step(self, force: float):
        # Simple dynamics with gravity toward slope
        slope = math.cos(self.x) * 0.5
        self.v += force - slope * 0.1
        self.v *= 0.9          # friction
        self.x += self.v
        self.step_count += 1
        return self.x, self.terrain(self.x)

# ---------- Simple world model (online linear regression) ----------
class WorldModel:
    def __init__(self):
        self.w = [0.5, -0.2]  # weights for (x, action)
        self.b = 0.0
        self.error_history = deque(maxlen=50)

    def predict(self, x, action):
        return self.w[0] * x + self.w[1] * action + self.b

    def update(self, x, action, target):
        pred = self.predict(x, action)
        error = target - pred
        self.error_history.append(abs(error))
        # SGD
        lr = 0.01
        self.w[0] += lr * error * x
        self.w[1] += lr * error * action
        self.b   += lr * error
        return error

    def average_error(self):
        if not self.error_history:
            return 1.0
        return sum(self.error_history) / len(self.error_history)

# ---------- Claim system ----------
class Claim:
    def __init__(self, description, condition_text):
        self.text = description
        self.falsification = condition_text
        self.confidence = 0.5
        self.tests_passed = 0
        self.tests_failed = 0

    def test(self, outcome: bool):
        if outcome:
            self.tests_passed += 1
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.tests_failed += 1
            self.confidence = max(0.0, self.confidence - 0.2)
        return outcome

    def status(self):
        if self.tests_failed >= 3:
            return "falsified"
        if self.tests_passed >= 3:
            return "survived"
        return "active"

    def __str__(self):
        return f"[{self.status()}] {self.text} (conf:{self.confidence:.2f})"

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
