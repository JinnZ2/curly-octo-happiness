#!/usr/bin/env python3
"""
garden_with_tree.py – Claim & Falsification Garden with Dependency Tree
"""

import random, math, time
from collections import deque

# ---------- Simple Dependency Tree ----------
class DepNode:
    def __init__(self, concept):
        self.concept = concept
        self.confidence = 0.5
        self.deps = set()          # concepts this depends on
        self.claims = []

class DependencyTree:
    def __init__(self):
        self.nodes = {}

    def get_or_create(self, concept):
        if concept not in self.nodes:
            self.nodes[concept] = DepNode(concept)
        return self.nodes[concept]

    def add_dependency(self, concept, depends_on):
        self.get_or_create(concept).deps.add(depends_on)
        self.get_or_create(depends_on)

    def add_claim(self, concept, claim):
        node = self.get_or_create(concept)
        node.claims.append(claim)

    def propagate_confidence(self):
        # bottom-up: confidence of a node is average of its claims and its deps
        for node in self.nodes.values():
            if node.claims:
                claim_conf = sum(c.confidence for c in node.claims) / len(node.claims)
            else:
                claim_conf = 0.5
            dep_conf = 0.5
            if node.deps:
                dep_vals = [self.nodes[d].confidence for d in node.deps if d in self.nodes]
                if dep_vals:
                    dep_conf = sum(dep_vals) / len(dep_vals)
            node.confidence = (claim_conf + dep_conf) / 2

    def summary(self):
        lines = ["🌳 Dependency Tree:"]
        for name, node in self.nodes.items():
            lines.append(f"  {name} (conf:{node.confidence:.2f}) depends on {node.deps}")
            for c in node.claims[-2:]:
                lines.append(f"    [{c.status()}] {c.text}")
        return "\n".join(lines)

# ---------- Bumpy World & World Model (as before) ----------
class BumpyWorld:
    def __init__(self):
        self.x = 0.0
        self.v = 0.0
        self.terrain = lambda x: math.sin(x) * 0.5

    def step(self, force):
        slope = math.cos(self.x) * 0.5
        self.v += force - slope * 0.1
        self.v *= 0.9
        self.x += self.v
        return self.x, self.terrain(self.x)

class WorldModel:
    def __init__(self):
        self.w = [0.5, -0.2]
        self.b = 0.0
        self.error_hist = deque(maxlen=50)

    def predict(self, x, a):
        return self.w[0]*x + self.w[1]*a + self.b

    def update(self, x, a, target):
        pred = self.predict(x, a)
        error = target - pred
        self.error_hist.append(abs(error))
        lr = 0.01
        self.w[0] += lr * error * x
        self.w[1] += lr * error * a
        self.b    += lr * error
        return error

    def avg_error(self):
        if not self.error_hist: return 1.0
        return sum(self.error_hist)/len(self.error_hist)

class Claim:
    def __init__(self, text, falsification):
        self.text = text
        self.falsification = falsification
        self.confidence = 0.5
        self.passed = 0
        self.failed = 0

    def test(self, outcome):
        if outcome:
            self.passed += 1
            self.confidence = min(1.0, self.confidence+0.1)
        else:
            self.failed += 1
            self.confidence = max(0.0, self.confidence-0.2)
        return outcome

    def status(self):
        if self.failed >= 3: return "falsified"
        if self.passed >= 3: return "survived"
        return "active"

    def __str__(self):
        return f"[{self.status()}] {self.text} (conf:{self.confidence:.2f})"

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
