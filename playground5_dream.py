#!/usr/bin/env python3
"""Dream Space – recombining memory fragments."""
import random
from shared import SharedMemory

class Dreamer:
    def __init__(self, memory: SharedMemory):
        self.memory = memory

    def sleep(self):
        fragments = [e.get('description', 'empty') for e in self.memory.recent(10)]
        if len(fragments) < 2:
            return "Not enough experience to dream."
        a, b = random.sample(fragments, 2)
        dream = f"💤 In the dream, {a} and {b} merged into something new."
        self.memory.add({"type": "dream", "content": dream, "fragments": [a, b]})
        return dream

if __name__ == "__main__":
    mem = SharedMemory()
    mem.add({"description": "I touched a cold stone"})
    mem.add({"description": "I heard a distant bell"})
    d = Dreamer(mem)
    print(d.sleep())
