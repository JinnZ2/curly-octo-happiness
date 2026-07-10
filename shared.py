#!/usr/bin/env python3
# shared.py – common dependency tree, memory, mentor

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any

@dataclass
class Claim:
    text: str
    falsification: str
    confidence: float = 0.5
    tests_passed: int = 0
    tests_failed: int = 0
    status: str = "active"

    def test(self, outcome: bool):
        if outcome:
            self.tests_passed += 1
            self.confidence = min(1.0, self.confidence + 0.1)
            self.status = "survived" if self.tests_passed >= 3 else "active"
        else:
            self.tests_failed += 1
            self.confidence = max(0.0, self.confidence - 0.2)
            if self.tests_failed >= 3:
                self.status = "falsified"
            else:
                self.status = "uncertain"

class DependencyNode:
    def __init__(self, concept: str):
        self.concept = concept
        self.confidence = 0.5
        self.dependencies: Set[str] = set()
        self.claims: List[Claim] = []

class DependencyTree:
    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}

    def add_node(self, concept: str):
        if concept not in self.nodes:
            self.nodes[concept] = DependencyNode(concept)

    def add_dependency(self, concept: str, depends_on: str):
        self.add_node(concept)
        self.add_node(depends_on)
        self.nodes[concept].dependencies.add(depends_on)

    def add_claim(self, concept: str, claim: Claim):
        self.add_node(concept)
        self.nodes[concept].claims.append(claim)

    def recalibrate(self):
        for node in self.nodes.values():
            if node.claims:
                claim_conf = sum(c.confidence for c in node.claims) / len(node.claims)
            else:
                claim_conf = 0.5
            # adjust by dependencies: average them once so the result doesn't
            # depend on set-iteration order
            dep_vals = [self.nodes[d].confidence for d in node.dependencies if d in self.nodes]
            dep_conf = sum(dep_vals) / len(dep_vals) if dep_vals else 0.5
            node.confidence = (claim_conf + dep_conf) / 2

    def summary(self):
        lines = ["Dependency Tree:"]
        for name, node in self.nodes.items():
            lines.append(f"  {name} (conf:{node.confidence:.2f}) deps:{node.dependencies}")
            for c in node.claims:
                lines.append(f"    [{c.status}] {c.text}")
        return "\n".join(lines)

class SharedMemory:
    def __init__(self, capacity=1000):
        self.stream = deque(maxlen=capacity)

    def add(self, event: Dict[str, Any]):
        event['timestamp'] = time.time()
        self.stream.append(event)

    def recent(self, n=10):
        return list(self.stream)[-n:]

class MentorInterface:
    def __init__(self):
        self.log = []

    def ask(self, question: str):
        self.log.append(("ask", question))
        print(f"🧑‍🏫 Mentor asks: {question}")

    def hint(self, hint: str):
        self.log.append(("hint", hint))
        print(f"💡 Hint: {hint}")

    def reflect(self, observation: str):
        self.log.append(("reflect", observation))
        print(f"🔍 Mentor reflects: {observation}")
