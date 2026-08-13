"""The 1-D bumpy world and its online linear world model."""

import math
from collections import deque


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
