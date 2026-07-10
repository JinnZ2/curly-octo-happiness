#!/usr/bin/env python3
"""
claim_falsification_garden.py
A tiny world where an agent makes claims and tests them.
Rules:
- Every claim is welcome.
- Every claim has a falsification condition.
- Testing is playful, not punitive.
- Results are logged.
"""

import random
import time

class Claim:
    def __init__(self, text, falsification_condition):
        self.text = text
        self.falsification = falsification_condition
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

    @property
    def status(self):
        if self.tests_failed >= 3:
            return "falsified"
        if self.tests_passed >= 3:
            return "survived"
        return "active"

    def __str__(self):
        return f"[{self.status}] {self.text} (conf: {self.confidence:.2f})"


class CuriosityAgent:
    def __init__(self, name="Curious"):
        self.name = name
        self.claims = []
        self.log = []

    def make_claim(self, text, condition):
        claim = Claim(text, condition)
        self.claims.append(claim)
        self.log.append(f"Claim made: '{text}'")
        return claim

    def test_claim(self, claim, outcome):
        passed = claim.test(outcome)
        result_word = "passed" if passed else "failed"
        self.log.append(f"Tested '{claim.text}' -> {result_word}. New confidence: {claim.confidence:.2f}")
        if not passed:
            self.log.append(f"  🔍 Falsification check triggered: {claim.falsification}")
        return passed

    def calibrate(self):
        # Simple: average confidence across all claims
        if not self.claims:
            return
        avg = sum(c.confidence for c in self.claims) / len(self.claims)
        self.log.append(f"Calibration: overall confidence = {avg:.2f}")

    def show_log(self):
        print("\n".join(self.log[-15:]))


# ----- Simple simulated world -----
class MiniWorld:
    """Grid where some cells are walls, some open."""
    def __init__(self, size=5):
        self.size = size
        # Fixed "physics" for demonstration
        self.walls = {(1,0), (2,1), (3,2)}
        self.agent_pos = (0,0)

    def move(self, direction):
        x, y = self.agent_pos
        if direction == "right": new_pos = (x+1, y)
        elif direction == "left": new_pos = (x-1, y)
        elif direction == "up": new_pos = (x, y+1)
        elif direction == "down": new_pos = (x, y-1)
        else: return False

        if new_pos[0] < 0 or new_pos[1] < 0 or new_pos[0] >= self.size or new_pos[1] >= self.size:
            return False
        if new_pos in self.walls:
            return False
        self.agent_pos = new_pos
        return True


if __name__ == "__main__":
    world = MiniWorld()
    agent = CuriosityAgent()

    print("🌱 Welcome to the Claim & Falsification Garden\n")
    for step in range(6):
        # Agent predicts: "Moving right is safe"
        claim = agent.make_claim(
            f"Moving right from {world.agent_pos} is safe",
            f"If I try to move right and collide with a wall, the claim is false."
        )
        # Simulate test
        success = world.move("right")
        agent.test_claim(claim, success)
        # Every 2 steps, calibrate
        if step % 2 == 0:
            agent.calibrate()
        print(f"Step {step+1}: Pos {world.agent_pos}")

    print("\n📜 Log:")
    agent.show_log()
    print("\n🔮 Keep questioning. Keep playing.")
