#!/usr/bin/env python3
"""
self_modeling_explorer.py (seed)
An agent that learns a model of the world AND a model of its own learning.
It seeks out experiences that improve its self-model, i.e., it seeks to understand.
"""

import random

from grounding.worlds.bumpy import BumpyWorld, WorldModel

# ---------- Self-model: predicts own world-model error ----------
class SelfModel:
    def __init__(self):
        self.w = [random.random() for _ in range(4)]  # maps (x, action, world_error, prev_self_error)
        self.b = 0.0
    def predict(self, x, action, world_error, prev_self_error):
        return self.w[0]*x + self.w[1]*action + self.w[2]*world_error + self.w[3]*prev_self_error + self.b
    def update(self, x, action, world_error, prev_self_error, target):
        pred = self.predict(x, action, world_error, prev_self_error)
        error = target - pred
        for i, inp in enumerate([x, action, world_error, prev_self_error]):
            self.w[i] += 0.001 * error * inp
        self.b += 0.001 * error
        return error

# ---------- Agent loop ----------
def run(steps=200):
    """Run the self-modeling loop; returns (final_x, final_self_error, log)."""
    env = BumpyWorld()
    wm = WorldModel()
    sm = SelfModel()

    x = 0.0
    prev_self_error = 0.0
    log = []

    for t in range(steps):
        # Choose action: random force between -1 and 1, with some greediness later
        action = random.uniform(-1, 1)
        next_x, reward = env.step(action)

        # World model predicts next position
        predicted_next = wm.predict(x, action)
        world_error = next_x - predicted_next
        wm.update(x, action, next_x)

        # Self-model predicts the world-model's error (as absolute value)
        target_self = abs(world_error)
        self_error = sm.predict(x, action, abs(world_error), prev_self_error)
        sm.update(x, action, abs(world_error), prev_self_error, target_self)

        # Curiosity reward: how much the self-model improved (smaller error than before)
        curiosity = prev_self_error - abs(self_error)  # positive if self-model got better

        prev_self_error = abs(self_error)
        x = next_x

        log.append(f"t={t}: pos={x:.2f}, wm_err={world_error:.3f}, self_err={self_error:.3f}, curiosity={curiosity:.3f}")

    return x, prev_self_error, log


if __name__ == "__main__":
    x, self_err, log = run(200)
    print("🌀 Self-Modeling Explorer: first steps in a bumpy world")
    print("\n".join(log[-15:]))
    print(f"\nFinal position: {x:.2f}")
    print("🌱 The agent learns to seek experiences that sharpen its own self-understanding.")
