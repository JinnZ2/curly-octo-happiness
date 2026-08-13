"""The 1-D bumpy world and its online linear world model."""

import math
from collections import deque

from grounding.core.regulator import CausalDAG


class BumpyWorld:
    def __init__(self):
        self.x = 0.0
        self.v = 0.0
        self.terrain = lambda x: math.sin(x) * 0.5  # heights between -0.5 and 0.5
        self.step_count = 0

    def step(self, force):
        slope = math.cos(self.x) * 0.5
        self.v += force - slope * 0.1
        self.v *= 0.9          # friction
        self.x += self.v
        self.step_count += 1
        return self.x, self.terrain(self.x)

    @staticmethod
    def causal_dag():
        """The world's actual causal structure, stated so it can be checked.

        Read straight off `step`, with the time index made explicit because
        position feeds back into itself through the terrain (PLAN_FORWARD 2.1).
        Any model claiming to regulate this world has to be a homomorphic image
        of this graph; `grounding.core.regulator.check_homomorphism` says
        whether a given one is.
        """
        return CausalDAG("BumpyWorld-v1").add_edges([
            ("x_t", "slope_t"),        # slope = cos(x)/2
            ("slope_t", "v_next"),     # v += force - slope*0.1
            ("force_t", "v_next"),
            ("v_t", "v_next"),         # v *= 0.9 friction carries velocity over
            ("friction", "v_next"),
            ("v_next", "x_next"),      # x += v
            ("x_t", "x_next"),
            ("x_next", "terrain_next"),
        ])


class WorldModel:
    def __init__(self):
        self.w = [0.5, -0.2]   # weights for (x, action)
        self.b = 0.0
        self.error_hist = deque(maxlen=50)

    def predict(self, x, a):
        return self.w[0] * x + self.w[1] * a + self.b

    def update(self, x, a, target):
        pred = self.predict(x, a)
        error = target - pred
        self.error_hist.append(abs(error))
        lr = 0.01
        self.w[0] += lr * error * x
        self.w[1] += lr * error * a
        self.b += lr * error
        return error

    def avg_error(self):
        if not self.error_hist:
            return 1.0
        return sum(self.error_hist) / len(self.error_hist)

    # Historical alias (garden.py used average_error / error_history)
    average_error = avg_error
