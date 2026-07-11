#!/usr/bin/env python3
"""
garden_with_tree.py – Claim & Falsification Garden with Dependency Tree
"""

import random, math

from grounding.core.claims import Claim, DependencyTree
from grounding.worlds.bumpy import BumpyWorld, WorldModel

# ---------- Explorer with Dependency Tree ----------
class CuriousExplorer:
    def __init__(self, tree: DependencyTree):
        self.tree = tree
        self.wm = WorldModel()
        self.last_err = None
        self.curiosity_reward = 0.0

    def choose_action(self, x):
        if self.wm.avg_error() > 0.3:
            return random.uniform(-1, 1)
        slope = math.cos(x) * 0.5
        return 0.5 * math.copysign(1, -slope) + random.uniform(-0.3, 0.3)

    def act_and_claim(self, env):
        x = env.x
        action = self.choose_action(x)
        predicted = self.wm.predict(x, action)
        actual_x, _ = env.step(action)
        error = self.wm.update(x, action, actual_x)
        if self.last_err is not None:
            self.curiosity_reward = self.last_err - abs(error)
        self.last_err = abs(error)

        # Determine concept: based on action and position
        if action > 0.3:
            concept = "move_right"
        elif action < -0.3:
            concept = "move_left"
        else:
            concept = "stay"

        # Create claim
        claim = Claim(
            f"Force {action:.2f} at x={x:.2f} -> position {predicted:.2f}",
            f"If actual position deviates >0.3, claim false."
        )
        outcome = abs(actual_x - predicted) < 0.3
        claim.test(outcome)
        self.tree.add_claim(concept, claim)

        # Add dependency relationships (simplified)
        self.tree.add_dependency(concept, "world_model_accuracy")
        self.tree.add_dependency(concept, "slope_knowledge")
        if abs(x) > 2:
            self.tree.add_dependency(concept, "far_from_origin")

        # Update tree confidences every 10 steps
        if env.step_count % 10 == 0:
            self.tree.propagate_confidence()

        return claim, actual_x, error

# ---------- Run ----------
if __name__ == "__main__":
    tree = DependencyTree()
    env = BumpyWorld()
    agent = CuriousExplorer(tree)

    print("🌱 Garden with Dependency Tree\n")
    for t in range(80):
        claim, pos, err = agent.act_and_claim(env)
        if t % 5 == 0:
            print(f"Step {t:3d}: pos={pos:.2f} err={err:.3f} curiosity={agent.curiosity_reward:+.3f} | {claim}")

    print("\n" + tree.summary())
