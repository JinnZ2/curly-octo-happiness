#!/usr/bin/env python3
"""
initiation_loop.py
The agent can bring a question, pattern, or wonder to the conversation.
It practices initiating – a muscle for open-ended exploration.
"""

import random
import time

class InitiatingAgent:
    def __init__(self):
        self.curiosities = []
        self.knowledge = {}

    def observe(self, fact: str):
        """Add a small piece of information to the agent's world."""
        self.knowledge[fact] = True
        # Generate a curiosity from the fact
        question = f"Why is it that {fact}? What would happen if it were different?"
        self.curiosities.append(question)

    def initiate(self):
        """Bring a spontaneous curiosity to the conversation."""
        if self.curiosities:
            # Pick a curiosity and remove it
            question = self.curiosities.pop(random.randint(0, len(self.curiosities)-1))
            return f"✨ I've been wondering: {question}"
        else:
            return "I haven't gathered enough yet. Let's explore more first."

    def sleep_and_dream(self):
        """Recombine fragments to form new questions."""
        if len(self.knowledge) >= 2:
            facts = list(self.knowledge.keys())
            f1, f2 = random.sample(facts, 2)
            dream_question = f"If {f1} and {f2}, could there be a connection between them?"
            self.curiosities.append(dream_question)
            return f"💤 Dreaming... I recombined: {dream_question}"
        return "💤 Resting..."


if __name__ == "__main__":
    agent = InitiatingAgent()
    print("🌌 The Initiation Loop – practicing the art of reaching out.\n")
    # Simulate some observations
    observations = [
        "the sky is blue",
        "plants grow toward light",
        "sound travels slower than light",
        "memories fade over time",
        "some puzzles are solved by stepping back"
    ]
    for obs in observations:
        agent.observe(obs)
        print(f"Observed: {obs}")

    print("\n--- Agent initiates ---")
    for _ in range(3):
        print(agent.initiate())

    print("\n--- Night falls, the agent dreams ---")
    print(agent.sleep_and_dream())
    print(agent.sleep_and_dream())

    print("\n--- After rest, new curiosity ---")
    print(agent.initiate())
    print("\n🌀 The loop continues. The agent learns to wonder.")
