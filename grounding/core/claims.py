"""Claims and the dependency-confidence tree.

One implementation replacing the drifted copies that previously lived in
claim_falsification_garden.py, garden.py, garden_with_tree.py, shared.py
and every unified_playground version. Method aliases keep all historical
call sites working:

  tree.get / tree.get_or_create / tree.add_node
  tree.propagate_confidence / tree.recalibrate
  tree.summary_text / tree.summary
  node.deps / node.dependencies
  claim.status is a property (a string), matching shared.py's dataclass
  style — call sites that used the old method form `claim.status()` were
  updated when they migrated to this module.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Claim:
    text: str
    falsification: str
    confidence: float = 0.5
    passed: int = 0
    failed: int = 0

    def test(self, outcome: bool) -> bool:
        if outcome:
            self.passed += 1
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.failed += 1
            self.confidence = max(0.0, self.confidence - 0.2)
        return outcome

    @property
    def status(self) -> str:
        if self.failed >= 3:
            return "falsified"
        if self.passed >= 3:
            return "survived"
        return "active"

    def __str__(self):
        return f"[{self.status}] {self.text} (conf:{self.confidence:.2f})"


class DepNode:
    def __init__(self, concept: str):
        self.concept = concept
        self.confidence = 0.5
        self.deps: Set[str] = set()
        self.claims: List[Claim] = []

    @property
    def dependencies(self) -> Set[str]:
        return self.deps


class DependencyTree:
    def __init__(self):
        self.nodes: Dict[str, DepNode] = {}

    def get(self, concept: str) -> DepNode:
        if concept not in self.nodes:
            self.nodes[concept] = DepNode(concept)
        return self.nodes[concept]

    # Historical aliases
    get_or_create = get

    def add_node(self, concept: str) -> DepNode:
        return self.get(concept)

    def add_dependency(self, concept: str, depends_on: str):
        self.get(concept).deps.add(depends_on)
        self.get(depends_on)

    def add_claim(self, concept: str, claim: Claim):
        self.get(concept).claims.append(claim)

    def propagate_confidence(self):
        """Node confidence = mean(claim confidences) averaged with
        mean(dependency confidences); order-independent."""
        for node in self.nodes.values():
            if node.claims:
                claim_conf = sum(c.confidence for c in node.claims) / len(node.claims)
            else:
                claim_conf = 0.5
            dep_vals = [self.nodes[d].confidence for d in node.deps if d in self.nodes]
            dep_conf = sum(dep_vals) / len(dep_vals) if dep_vals else 0.5
            node.confidence = (claim_conf + dep_conf) / 2

    def recalibrate(self):
        self.propagate_confidence()

    def summary_text(self) -> str:
        lines = ["Dependency Tree:"]
        for name, node in self.nodes.items():
            lines.append(f"  {name} (conf:{node.confidence:.2f}) deps:{node.deps}")
            for c in node.claims[-2:]:
                lines.append(f"    [{c.status}] {c.text}")
        return "\n".join(lines)

    def summary(self) -> str:
        return self.summary_text()
