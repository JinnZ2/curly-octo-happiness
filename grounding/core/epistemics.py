"""Epistemics helpers — mitigations for the limitations checklist (REVIEW.md §5).

Covers, in stdlib-only form:

* §5.1 Symbolic–subsymbolic gap: `evaluate_logical_form` executes a claim's
  structured `logical_form` ({"op": ..., "args": [...]}) against concrete
  bindings, so the falsification condition lives in ONE machine-checkable
  place instead of being duplicated between claim text and inline code.
  `check_with_z3` cross-checks the same form with the Z3 SMT solver when
  z3-solver is installed (returns "unavailable" otherwise).

* §5.2 Grounding problem: `check_geometry_units` validates geometry dicts
  against the repo's unit-suffix naming convention (voltage_v, T_K, P_pa,
  ...) with plausible physical ranges. This is a lightweight stand-in for
  a full unit system like `pint`; it catches wrong-unit and impossible
  values, not dimensional algebra.

* §5.4 Falsifiability paradox: `classify_falsifiability` sorts claims into
  machine-checkable / falsifiable / unfalsifiable, so unfalsifiable ones
  can be routed to the UnknownJournal instead of the dependency tree.

* §5.6 Carrier check: `carrier_check` applies a claim's OWN criterion to
  what the claim needs in order to be stated at all (its carrier) and to
  what it leans on (its supports), following dependency chains. A claim
  whose carrier fails its own rule SELF_DELETES; one that can be stated
  but whose supports fail is HOLLOW. Passes earned only by an exemption the
  claim grants itself are counted, and dependencies missing from the graph
  are reported as unrecorded rather than read as passing.
"""

from typing import Any, Callable, Dict, Iterable, List

# ---------------------------------------------------------------------------
# §5.1 — structured logical forms
# ---------------------------------------------------------------------------

_OPS = {
    "abs_diff_lt": lambda a, b, tol: abs(a - b) < tol,
    "abs_diff_le": lambda a, b, tol: abs(a - b) <= tol,
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "eq_within": lambda a, b, tol: abs(a - b) <= tol,
}


def _resolve(arg, bindings: Dict[str, Any]):
    """String args are variable names looked up in bindings; numbers are literals."""
    if isinstance(arg, str):
        if arg not in bindings:
            raise ValueError(f"logical_form references unbound variable '{arg}'")
        return bindings[arg]
    return arg


def evaluate_logical_form(logical_form: Dict[str, Any], bindings: Dict[str, Any]) -> bool:
    """Evaluate {"op": <name>, "args": [...]} against concrete bindings.

    Returns True iff the claim HOLDS for these observations."""
    op = logical_form.get("op")
    if op not in _OPS:
        raise ValueError(f"unknown logical_form op '{op}' (known: {sorted(_OPS)})")
    args = [_resolve(a, bindings) for a in logical_form.get("args", [])]
    return bool(_OPS[op](*args))


def check_with_z3(logical_form: Dict[str, Any], bindings: Dict[str, Any]) -> str:
    """Cross-check a logical form with the Z3 SMT solver, if installed.

    Returns "consistent" if the claim holds for the bindings, "falsified"
    if its negation is satisfiable under them, or "unavailable" when
    z3-solver is not installed. Currently supports the comparison ops above.
    """
    try:
        import z3  # optional dependency
    except ImportError:
        return "unavailable"

    op = logical_form.get("op")
    args = [_resolve(a, bindings) for a in logical_form.get("args", [])]
    s = z3.Solver()
    if op in ("abs_diff_lt", "abs_diff_le", "eq_within"):
        a, b, tol = (z3.RealVal(v) for v in args)
        diff = a - b
        absdiff = z3.If(diff >= 0, diff, -diff)
        holds = absdiff < tol if op == "abs_diff_lt" else absdiff <= tol
    elif op in ("lt", "le", "gt", "ge"):
        a, b = (z3.RealVal(v) for v in args)
        holds = {"lt": a < b, "le": a <= b, "gt": a > b, "ge": a >= b}[op]
    else:
        return "unavailable"
    s.add(z3.Not(holds))
    return "falsified" if s.check() == z3.sat else "consistent"


# ---------------------------------------------------------------------------
# §5.2 — unit-suffix / plausibility checks for geometry dicts
# ---------------------------------------------------------------------------

# suffix (lowercased key endswith) -> (unit name, plausible min, plausible max)
UNIT_RANGES = {
    "_v": ("volts", -1e6, 1e6),
    "_mv": ("millivolts", -1e9, 1e9),
    "_a": ("amperes", -1e4, 1e4),
    "_c": ("degrees Celsius", -273.15, 1e5),
    "_k": ("kelvin", 0.0, 1e9),
    "_pa": ("pascals", 0.0, 1e12),
    "_hz": ("hertz", 0.0, 1e15),
    "_nm": ("nanometres", 0.0, 1e9),
    "_km": ("kilometres", 0.0, 1e9),
    "_kj": ("kilojoules", -1e9, 1e9),
    "_ev": ("electronvolts", -1e6, 1e6),
    "_pct": ("percent", -1e4, 1e4),
    "_hours": ("hours", 0.0, 1e12),
    "_m_s2": ("metres per second squared", -1e6, 1e6),
}

# Longest suffixes first so "_m_s2" wins over "_a"-style near-misses.
_SUFFIXES = sorted(UNIT_RANGES, key=len, reverse=True)


def check_geometry_units(geometry: Dict[str, Any]) -> List[str]:
    """Return advisory warnings for geometry values that violate the unit
    convention their key suffix declares (e.g. temperature_c = -400)."""
    warnings = []
    for key, value in geometry.items():
        key_lower = key.lower()
        for suffix in _SUFFIXES:
            if key_lower.endswith(suffix):
                unit, lo, hi = UNIT_RANGES[suffix]
                values = value if isinstance(value, (list, tuple)) else [value]
                for v in values:
                    if isinstance(v, (int, float)) and not (lo <= v <= hi):
                        warnings.append(
                            f"{key}={v} outside plausible {unit} range [{lo}, {hi}]")
                break
    return warnings


# ---------------------------------------------------------------------------
# §5.4 — falsifiability classifier
# ---------------------------------------------------------------------------

UNFALSIFIABLE_MARKERS = {
    "", "none", "n/a", "na", "unfalsifiable", "cannot be tested", "no test",
    "always true", "self-evident",
}


def classify_falsifiability(claim) -> str:
    """Classify a claim (duck-typed) as:

    "machine-checkable" — has an executable refutation_test or logical_form;
    "falsifiable"       — has a non-trivial textual falsification condition;
    "unfalsifiable"     — no usable refutation condition at all.
    """
    if getattr(claim, "refutation_test", None) is not None:
        return "machine-checkable"
    if getattr(claim, "logical_form", None):
        return "machine-checkable"
    text = (getattr(claim, "falsification", "") or "").strip().lower()
    if text in UNFALSIFIABLE_MARKERS or len(text) < 4:
        return "unfalsifiable"
    return "falsifiable"


# ---------------------------------------------------------------------------
# §5.6 — carrier check: a claim's own criterion, applied to itself
# ---------------------------------------------------------------------------
#
# Most audits check a claim's supports. Almost none check its carrier: the
# language, medium, institution or method the claim needs in order to be
# stated. "Only what is measured is real" is not itself measured; "trust only
# peer-reviewed evidence" was never reviewed. Running the claim's criterion on
# its own carrier is a cheap test with three outcomes worth keeping apart.

SELF_DELETES = "SELF_DELETES"   # the carrier fails the claim's own criterion
HOLLOW = "HOLLOW"               # stateable, but some support fails it
CONSISTENT = "CONSISTENT"       # carrier and supports pass


def carrier_check(criterion: Callable[[Dict[str, Any]], bool],
                  carrier: Iterable[str], supports: Iterable[str],
                  graph: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Apply `criterion(attrs)` to the carrier and supports, down every chain.

    `graph` maps node name -> {"attrs": {...}, "deps": [...], "note": str,
    "exempted": bool}. A node fails when its own attrs fail the criterion or
    any dependency fails; every failing chain is kept, not just the first.

    `exempted: True` marks an exemption the claim grants itself ("heirs
    count as originals"). Such a node is passed, as the claim asks -- and
    recorded, because a pass that exists only by self-exemption is the soft
    spot an outside reader needs to see. `exemption_load` is the share of
    passing nodes that pass only that way.

    A dependency named but absent from `graph` is NOT read as passing: an
    unrecorded link is an unknown, and reading it as clean is the false pass
    this check exists to avoid. It is listed under `unrecorded`.
    """
    carrier, supports = list(carrier), list(supports)
    memo: Dict[str, List[List[str]]] = {}
    exempted: set = set()
    unrecorded: set = set()

    def chains(name: str, stack: tuple = ()) -> List[List[str]]:
        if name in memo:
            return memo[name]
        if name in stack:
            return []                     # cycle: nothing new down this path
        node = graph.get(name)
        if node is None:
            unrecorded.add(name)
            return []
        found: List[List[str]] = []
        if not criterion(node.get("attrs", {})):
            if node.get("exempted"):
                exempted.add(name)
            else:
                found.append([name])
        for dep in node.get("deps", []):
            found += [[name] + c for c in chains(dep, stack + (name,))]
        memo[name] = found
        return found

    results = {n: chains(n) for n in carrier + supports}
    carrier_fail = {n: results[n] for n in carrier if results[n]}
    support_fail = {n: results[n] for n in supports if results[n]}
    if carrier_fail:
        status = SELF_DELETES
    elif support_fail:
        status = HOLLOW
    else:
        status = CONSISTENT
    retained = [n for n in carrier + supports if not results[n]]
    passing_nodes = {m for m in memo if not memo[m]}
    return {
        "status": status,
        "carrier_failures": carrier_fail,
        "support_failures": support_fail,
        "retained": retained,
        "exempted": sorted(exempted),
        "exemption_load": (len(exempted & passing_nodes) / len(passing_nodes)
                           if passing_nodes else 0.0),
        "unrecorded": sorted(unrecorded),
        "notes": {n: graph[n].get("note", "") for c in
                  list(carrier_fail.values()) + list(support_fail.values())
                  for chain in c for n in [chain[-1]] if n in graph},
    }
