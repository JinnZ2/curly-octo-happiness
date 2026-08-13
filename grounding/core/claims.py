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

Epistemics extensions (REVIEW.md §5) — all optional, all default-off:

  logical_form      structured refutation condition, evaluated by
                    claim.evaluate(bindings) so text and check can't drift (§5.1)
  scope             explicit temporal/spatial/ontological scope dict (§5.3)
  reference_class   what population the confidence refers to (§5.3)
  refutation_test   callable(bindings) -> True iff observation refutes (§5.4)
  reformulate()     escape-hatch counter: edits after failures are logged,
                    not silent (§5.4)
  beta_confidence   calibrated Beta(1+passed, 1+failed) posterior mean —
                    an interpretable alternative to the ±0.1/−0.2
                    `confidence` heuristic, which is kept for backward
                    compatibility (§5.5)
  meta_flags        DependencyTree.add_claim marks "revolutionary" claims
                    that contradict well-grounded nodes (§5.2)
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from grounding.core.epistemics import classify_falsifiability, evaluate_logical_form


@dataclass
class Claim:
    text: str
    falsification: str
    confidence: float = 0.5
    passed: int = 0
    failed: int = 0
    # --- epistemics extensions (§5), all optional ---
    logical_form: Optional[Dict[str, Any]] = None
    scope: Optional[Dict[str, Any]] = None
    reference_class: Optional[str] = None
    refutation_test: Optional[Callable[[Dict[str, Any]], bool]] = None
    reformulation_count: int = 0
    meta_flags: List[str] = field(default_factory=list)

    def test(self, outcome: bool) -> bool:
        if outcome:
            self.passed += 1
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.failed += 1
            self.confidence = max(0.0, self.confidence - 0.2)
        return outcome

    def evaluate(self, bindings: Dict[str, Any]) -> Optional[bool]:
        """Test the claim against observations using its executable
        refutation condition (refutation_test, else logical_form).
        Returns the outcome, or None if the claim has neither."""
        if self.refutation_test is not None:
            outcome = not self.refutation_test(bindings)
        elif self.logical_form is not None:
            outcome = evaluate_logical_form(self.logical_form, bindings)
        else:
            return None
        self.test(outcome)
        return outcome

    def reformulate(self, text: Optional[str] = None,
                    falsification: Optional[str] = None) -> bool:
        """Rewrite the claim and reset its track record. Each call is
        counted — reformulating after failures is the classic escape
        hatch, so it must be visible (§5.4). Returns True when the
        pattern looks suspicious."""
        if text is not None:
            self.text = text
        if falsification is not None:
            self.falsification = falsification
        self.passed = 0
        self.failed = 0
        self.confidence = 0.5
        self.reformulation_count += 1
        if self.escape_hatch_suspected:
            flag = f"escape-hatch: reformulated {self.reformulation_count}x"
            if flag not in self.meta_flags:
                self.meta_flags.append(flag)
        return self.escape_hatch_suspected

    @property
    def escape_hatch_suspected(self) -> bool:
        return self.reformulation_count >= 3

    @property
    def falsifiability(self) -> str:
        return classify_falsifiability(self)

    @property
    def falsifiable(self) -> bool:
        return self.falsifiability != "unfalsifiable"

    @property
    def beta_confidence(self) -> float:
        """Beta(1+passed, 1+failed) posterior mean — a calibrated
        probability, unlike the step-heuristic `confidence`."""
        return (1 + self.passed) / (2 + self.passed + self.failed)

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
        node = self.get(concept)
        # Meta-grounding flag (§5.2): a low-confidence claim attached to a
        # well-grounded concept is "revolutionary" — it needs either much
        # stronger evidence or an error in the node's grounding.
        if (node.confidence > 0.9 and claim.confidence < 0.3
                and hasattr(claim, "meta_flags")):
            claim.meta_flags.append(
                f"revolutionary: contradicts well-grounded '{concept}' "
                f"(node conf {node.confidence:.2f})")
        node.claims.append(claim)

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
