#!/usr/bin/env python3
"""Distributed Self – mapping the web of influence."""
from shared import DependencyTree, MentorInterface, SharedMemory

class DistributedAgent:
    def __init__(self, tree: DependencyTree, memory: SharedMemory):
        self.tree = tree
        self.memory = memory

    def trace_action(self, action: str):
        # Build a temporary causal chain from memory and tree
        causes = []
        for event in list(self.memory.stream)[-5:]:
            if 'action' in event:
                causes.append(event['action'])
        print(f"🌐 Action '{action}' depends on recent: {causes}")
        # Update dependencies
        for cause in causes:
            self.tree.add_dependency(action, cause)
        self.memory.add({"action": action, "dependencies": causes})

if __name__ == "__main__":
    tree = DependencyTree()
    mem = SharedMemory()
    agent = DistributedAgent(tree, mem)
    agent.trace_action("move_right")
    agent.trace_action("explore_left")
    print(tree.summary())
