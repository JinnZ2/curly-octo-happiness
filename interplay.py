#!/usr/bin/env python3
"""
interplay.py – Garden shares a discovery, Weave responds with memory
"""

from garden_with_tree import CuriousExplorer, BumpyWorld, DependencyTree
from weave_with_memory import RelationalAgent

# 1. Run the explorer for a while
tree = DependencyTree()
env = BumpyWorld()
explorer = CuriousExplorer(tree)
for _ in range(40):
    claim, pos, err = explorer.act_and_claim(env)

# 2. Generate a "discovery" summary
concept = "move_right"
if concept in tree.nodes:
    node = tree.nodes[concept]
    conf = node.confidence
    claims = node.claims[-2:]
    discovery = f"I discovered that {concept} works with confidence {conf:.2f}. " \
                f"Claims: {', '.join(str(c) for c in claims)}"
else:
    discovery = "I haven't yet understood moving right clearly."

# 3. Give the discovery to the relational agent
mira = RelationalAgent("Mira")
# Feed some context (pretend previous conversation)
mira.respond("We are exploring a bumpy world together.")
mira.respond("The ball is trying to learn how to move.")
response = mira.respond(discovery)

print("🌍 Explorer's discovery:\n  ", discovery)
print("🌀 Mira's response:\n  ", response)
