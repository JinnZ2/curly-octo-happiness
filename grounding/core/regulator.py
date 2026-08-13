"""Good-regulator grounding: is the agent's model actually a model of the world?

Conant & Ashby (1970): every good regulator of a system must be a model of that
system, and the optimal regulator is a *homomorphism* of it. Richens & Everitt
(2024) sharpen this — an agent robust to distributional shift must have learned
an approximate causal model, not merely a correlational one.

This module makes both halves checkable for the repo's worlds:

**The world's causal structure becomes explicit.** A `CausalDAG` states what
causes what. Without it, "the agent modelled the world" has no truth condition.

**The homomorphism is verified, not assumed.** `check_homomorphism` takes the
mapping from world variables to model concepts and reports which world edges
survive it. An unmapped world variable and a dropped causal edge are not
bookkeeping failures — they are exactly where an unmodelled variable lives, so
the report hands them to hidden-node detection rather than swallowing them.

**Regulation is scored by outcome entropy.** Conant & Ashby's regulator
minimises the variety of the outcome. If the agent's claims resolve like coin
flips, the model is not regulating whatever else it is doing;
`regulator_score` is 1 - H(outcomes)/H_max, so 1.0 means fully determined
outcomes and 0.0 means maximum surprise.

Primitive roots are the invariant. A homomorphism may collapse detail, but it
must not invent or lose exogenous sources — the FDM sense of a root, something
you cannot manufacture. `check_homomorphism` checks roots separately for that
reason.

Stdlib only.
"""

from math import log2
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

__all__ = ["CausalDAG", "check_homomorphism", "outcome_entropy", "regulator_score"]


class CausalDAG:
    """A world's causal structure: variables and the arrows between them."""

    def __init__(self, name: str = ""):
        self.name = name
        self.nodes: Set[str] = set()
        self.edges: Set[Tuple[str, str]] = set()

    def add_edge(self, cause: str, effect: str) -> "CausalDAG":
        self.nodes.add(cause)
        self.nodes.add(effect)
        self.edges.add((cause, effect))
        return self

    def add_edges(self, edges: Iterable[Tuple[str, str]]) -> "CausalDAG":
        for cause, effect in edges:
            self.add_edge(cause, effect)
        return self

    def parents(self, node: str) -> Set[str]:
        return {c for c, e in self.edges if e == node}

    def children(self, node: str) -> Set[str]:
        return {e for c, e in self.edges if c == node}

    def roots(self) -> Set[str]:
        """Exogenous variables: nothing in this DAG causes them."""
        return {n for n in self.nodes if not self.parents(n)}

    def ancestors(self, node: str) -> Set[str]:
        seen: Set[str] = set()
        frontier = list(self.parents(node))
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            frontier.extend(self.parents(current))
        return seen

    def has_cycle(self) -> bool:
        """A causal DAG with a cycle is not a DAG; feedback needs time indices."""
        colour: Dict[str, int] = {}

        def visit(node: str) -> bool:
            colour[node] = 1
            for child in self.children(node):
                state = colour.get(child, 0)
                if state == 1 or (state == 0 and visit(child)):
                    return True
            colour[node] = 2
            return False

        return any(colour.get(n, 0) == 0 and visit(n) for n in sorted(self.nodes))

    def report(self) -> str:
        label = f" {self.name}" if self.name else ""
        lines = [f"Causal DAG{label}: {len(self.nodes)} variables, "
                 f"{len(self.edges)} edges, roots {sorted(self.roots())}"]
        for cause, effect in sorted(self.edges):
            lines.append(f"  {cause} -> {effect}")
        if self.has_cycle():
            lines.append("  ⚠ contains a cycle — index the feedback by time step")
        return "\n".join(lines)


def outcome_entropy(resolutions: Sequence) -> float:
    """H over claim outcomes, in bits. Accepts booleans or status strings."""
    counts: Dict[str, int] = {}
    for outcome in resolutions:
        key = str(outcome)
        counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((c / total) * log2(c / total) for c in counts.values() if c)


def regulator_score(resolutions: Sequence) -> float:
    """1 - H(outcomes)/H_max: how far the model drives outcome variety to zero.

    Conant & Ashby's regulator succeeds exactly insofar as the outcome stops
    varying. Claims that resolve unpredictably mean the model is not regulating,
    however confident its individual claims may be. Returns 1.0 for a
    fully-determined outcome and 0.0 when every outcome is equally likely.
    """
    distinct = len({str(o) for o in resolutions})
    if distinct <= 1:
        return 1.0
    return 1.0 - outcome_entropy(resolutions) / log2(distinct)


def check_homomorphism(world: CausalDAG, model: CausalDAG,
                       mapping: Dict[str, str]) -> Dict[str, object]:
    """Does `mapping` carry the world's causal structure into the model?

    A homomorphism h: world -> model must send every world edge (u, v) to an
    edge (h(u), h(v)) that the model has — unless h collapses both endpoints to
    the same concept, which is legitimate abstraction rather than a lost cause.

    Returns a report with:
        preserved / broken     world edges that survived, and that did not
        unmapped               world variables the model has no concept for
        missing_roots          exogenous world variables absent from the model:
                               the invariant that abstraction may not discard
        invented_roots         model concepts with no exogenous world source
        fidelity               fraction of world edges preserved
        is_homomorphism        every edge preserved and every root present
        hidden_node_candidates what to hand to HND — the unmapped variables and
                               the causes of broken edges are where the world is
                               doing work the model cannot see
    """
    unmapped = sorted(n for n in world.nodes if n not in mapping)
    preserved: List[Tuple[str, str]] = []
    broken: List[Tuple[str, str]] = []

    for cause, effect in sorted(world.edges):
        if cause not in mapping or effect not in mapping:
            broken.append((cause, effect))
            continue
        image = (mapping[cause], mapping[effect])
        if image[0] == image[1] or image in model.edges:
            preserved.append((cause, effect))
        else:
            broken.append((cause, effect))

    world_root_images = {mapping[r] for r in world.roots() if r in mapping}
    missing_roots = sorted(r for r in world.roots() if r not in mapping)
    invented_roots = sorted(model.roots() - world_root_images)

    total = len(world.edges)
    fidelity = len(preserved) / total if total else 1.0
    candidates = sorted(set(unmapped) | {c for c, _ in broken})

    return {
        "preserved": preserved,
        "broken": broken,
        "unmapped": unmapped,
        "missing_roots": missing_roots,
        "invented_roots": invented_roots,
        "fidelity": round(fidelity, 4),
        "is_homomorphism": not broken and not missing_roots,
        "hidden_node_candidates": candidates,
    }


def homomorphism_report(world: CausalDAG, model: CausalDAG,
                        mapping: Dict[str, str]) -> str:
    result = check_homomorphism(world, model, mapping)
    lines = [
        "GOOD-REGULATOR CHECK",
        "=" * 40,
        f"World: {world.name or 'unnamed'} ({len(world.edges)} causal edges)",
        f"Model: {model.name or 'unnamed'} ({len(model.edges)} concept edges)",
        f"Fidelity: {result['fidelity']:.0%} of world edges preserved",
        f"Homomorphism: {result['is_homomorphism']}",
    ]
    if result["broken"]:
        lines.append("Broken edges (world causality the model cannot express):")
        for cause, effect in result["broken"]:
            lines.append(f"  {cause} -> {effect}")
    if result["missing_roots"]:
        lines.append(f"Missing primitive roots: {result['missing_roots']} "
                     "— abstraction may collapse detail but not lose sources")
    if result["invented_roots"]:
        lines.append(f"Invented roots (model sources with no world cause): "
                     f"{result['invented_roots']}")
    if result["hidden_node_candidates"]:
        lines.append(f"Hand to hidden-node detection: "
                     f"{result['hidden_node_candidates']}")
    return "\n".join(lines)
