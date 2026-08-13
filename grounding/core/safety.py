"""Control barrier functions as a runtime-assurance filter.

A control barrier function marks out a safe set

    C = { x : h(x) >= 0 }

and keeps the system inside it by constraining the control, not the state. For
control-affine dynamics x' = f(x) + g(x)u, forward invariance of C is implied by

    L_f h(x) + L_g h(x) u  >=  -alpha( h(x) )

which is *linear in u*. So the safety filter is a projection: take whatever the
nominal controller wanted and move it the shortest distance that satisfies every
barrier constraint,

    u* = argmin ||u - u_nom||^2   s.t.   A u >= b

This is the minimal-intervention property that makes CBFs usable as a wrapper —
when the nominal command is already safe, the filter returns it untouched.

Why there is no QP solver dependency
------------------------------------
The feasible set is an intersection of half-spaces and the objective is a
Euclidean projection, so for a single active constraint the solution is the
closed-form projection onto a half-space. For several, Dykstra's algorithm
converges to the projection onto the intersection by cycling through the
individual projections. That is enough for the toy scale here, keeps the repo
stdlib-only, and is honest about its limits: `SafetyDecision.converged` reports
when the iteration hit its cap without settling, and `feasible` reports when the
constraints cannot be satisfied together at all — which is not a solver failure
but a real finding about the system.

Safe sets as claims
-------------------
`safety_claim` stakes a barrier as a falsifiable claim with a machine-checkable
refutation condition: the claim is refuted the moment h(x) < 0 is observed. A
safety argument that cannot be refuted by observation is not a safety argument.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from grounding.core.claims import Claim

__all__ = [
    "Barrier",
    "Fallback",
    "FallbackCatalog",
    "SafetyDecision",
    "SafetyFilter",
    "battery_barrier",
    "project_onto_halfspace",
    "safety_claim",
    "solve_min_norm",
    "thermal_barriers",
]

State = Dict[str, float]


@dataclass
class Barrier:
    """One safe set and the control constraint that keeps the system in it.

    Args:
        name: what this barrier protects.
        h: h(state) — positive inside the safe set, zero on its boundary.
        lie_f: L_f h(state), the drift term: how h changes with no control.
        lie_g: L_g h(state) — the control's leverage on h, one entry per input.
        alpha: class-K gain. Larger lets the state approach the boundary faster;
            smaller keeps a wider cushion at the cost of intervening earlier.
    """

    name: str
    h: Callable[[State], float]
    lie_f: Callable[[State], float]
    lie_g: Callable[[State], Sequence[float]]
    alpha: float = 1.0

    def constraint(self, state: State) -> Tuple[List[float], float]:
        """The row (a, b) of `a . u >= b` this barrier imposes at `state`."""
        a = list(self.lie_g(state))
        b = -self.alpha * self.h(state) - self.lie_f(state)
        return a, b

    def margin(self, state: State) -> float:
        """h(state). Negative means the system is already outside the safe set."""
        return self.h(state)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def project_onto_halfspace(u: Sequence[float], a: Sequence[float],
                           b: float) -> List[float]:
    """Closest point to `u` satisfying `a . u >= b`. Returns `u` if already so."""
    u = list(u)
    norm_squared = _dot(a, a)
    if norm_squared == 0:
        return u                     # the control has no leverage here
    slack = _dot(a, u) - b
    if slack >= 0:
        return u                     # already satisfied: do not intervene
    scale = -slack / norm_squared
    return [ui + scale * ai for ui, ai in zip(u, a)]


def solve_min_norm(u_nom: Sequence[float], rows: Sequence[Tuple[Sequence[float], float]],
                   iterations: int = 200, tolerance: float = 1e-9
                   ) -> Tuple[List[float], bool]:
    """min ||u - u_nom||^2 s.t. every `a . u >= b`, by Dykstra's algorithm.

    Returns (u, converged). Cyclic projection onto the individual half-spaces
    converges to the projection onto their intersection when that intersection
    is non-empty; `converged` is False when the iteration cap was reached first,
    which usually means the constraints are close to incompatible.
    """
    u = list(u_nom)
    if not rows:
        return u, True
    corrections = [[0.0] * len(u) for _ in rows]

    for _ in range(iterations):
        previous = list(u)
        for index, (a, b) in enumerate(rows):
            shifted = [ui + ci for ui, ci in zip(u, corrections[index])]
            projected = project_onto_halfspace(shifted, a, b)
            corrections[index] = [si - pi for si, pi in zip(shifted, projected)]
            u = projected
        if max(abs(x - y) for x, y in zip(u, previous)) < tolerance:
            return u, True
    return u, False


@dataclass
class SafetyDecision:
    """What the filter did, and why."""

    u: List[float]
    u_nominal: List[float]
    intervened: bool
    active: List[str] = field(default_factory=list)
    violated: List[str] = field(default_factory=list)
    margins: Dict[str, float] = field(default_factory=dict)
    converged: bool = True
    feasible: bool = True

    def report(self) -> str:
        head = ("filter passed the nominal command through" if not self.intervened
                else f"filter overrode {self.u_nominal} -> "
                     f"{[round(v, 4) for v in self.u]}")
        lines = [f"Safety filter: {head}"]
        for name, margin in sorted(self.margins.items()):
            state = "VIOLATED" if margin < 0 else "active" if name in self.active else "slack"
            lines.append(f"  {name}: h={margin:+.4f} ({state})")
        if not self.feasible:
            lines.append("  ⚠ constraints cannot be satisfied together — no safe "
                         "control exists here, which is a finding about the system, "
                         "not a solver failure")
        elif not self.converged:
            lines.append("  ⚠ projection did not converge; treat the command as unverified")
        return "\n".join(lines)


class SafetyFilter:
    """Minimal-intervention wrapper around a nominal controller."""

    def __init__(self, barriers: Optional[Sequence[Barrier]] = None):
        self.barriers: List[Barrier] = list(barriers or [])

    def add(self, barrier: Barrier) -> "SafetyFilter":
        self.barriers.append(barrier)
        return self

    def margins(self, state: State) -> Dict[str, float]:
        return {b.name: b.margin(state) for b in self.barriers}

    def safe(self, state: State) -> bool:
        """Is the state inside every safe set right now?"""
        return all(margin >= 0 for margin in self.margins(state).values())

    def filter(self, state: State, u_nominal: Sequence[float]) -> SafetyDecision:
        """Return the closest control to `u_nominal` that keeps every h >= 0."""
        u_nominal = list(u_nominal)
        margins = self.margins(state)
        rows = [b.constraint(state) for b in self.barriers]

        u, converged = solve_min_norm(u_nominal, rows)

        # Which constraints are actually binding at the answer, and can they all
        # be met at once? A row that stays violated after projection means the
        # intersection is empty in that direction.
        active, unsatisfied = [], []
        for barrier, (a, b) in zip(self.barriers, rows):
            value = _dot(a, u)
            if value < b - 1e-6:
                unsatisfied.append(barrier.name)
            elif value <= b + 1e-6:
                active.append(barrier.name)

        intervened = any(abs(x - y) > 1e-9 for x, y in zip(u, u_nominal))
        return SafetyDecision(
            u=u,
            u_nominal=u_nominal,
            intervened=intervened,
            active=active,
            violated=[name for name, margin in margins.items() if margin < 0],
            margins=margins,
            converged=converged,
            feasible=not unsatisfied,
        )


# ---------------------------------------------------------------------------
# Concrete barriers for the stewardship world (PLAN_FORWARD 3.1)
# ---------------------------------------------------------------------------
#
# Control-affine model of one powered component, control u = [current_a]:
#
#     T' = -cooling * (T - T_ambient) + heating * i
#     E' = -drain * i
#
# Heating is taken as proportional to current rather than to i^2 so the
# dynamics stay affine in the control, which is what makes the barrier
# constraints linear and the filter a projection. That is a modelling choice,
# not a law: a real resistive part heats as i^2 and would need either a
# different control variable (dissipated power) or a nonlinear program.

def thermal_barriers(t_max: float, t_min: float, cooling: float, heating: float,
                     alpha: float = 1.0) -> List[Barrier]:
    """Ceiling and floor on temperature — the plan's cold-environment pair.

    The two pull the control in opposite directions: the ceiling caps current
    to avoid cooking the part, the floor demands current to keep it above its
    minimum in a cold ambient. Whether both can be satisfied at once is a real
    question about the hardware, and `SafetyFilter.filter` answers it per state
    rather than assuming a feasible set exists.
    """
    def ceiling_h(s: State) -> float:
        return t_max - s["temperature_c"]

    def ceiling_lie_f(s: State) -> float:
        # d/dt (t_max - T) = cooling * (T - T_ambient)
        return cooling * (s["temperature_c"] - s["ambient_c"])

    def floor_h(s: State) -> float:
        return s["temperature_c"] - t_min

    def floor_lie_f(s: State) -> float:
        return -cooling * (s["temperature_c"] - s["ambient_c"])

    return [
        Barrier("thermal_ceiling", ceiling_h, ceiling_lie_f,
                lambda s: [-heating], alpha),
        Barrier("thermal_floor", floor_h, floor_lie_f,
                lambda s: [heating], alpha),
    ]


def battery_barrier(e_min: float, drain: float, alpha: float = 1.0) -> Barrier:
    """Keep stored energy above its reserve: h = E - E_min."""
    return Barrier(
        "battery_reserve",
        lambda s: s["battery_j"] - e_min,
        lambda s: 0.0,
        lambda s: [-drain],
        alpha,
    )


# ---------------------------------------------------------------------------
# Runtime-assurance fallback catalog (PLAN_FORWARD 3.2)
# ---------------------------------------------------------------------------

@dataclass
class Fallback:
    """A failure mode, what the part can still do, and the envelope that buys.

    The repo already knew that a shorted diode is a conductor and a drifting one
    is a sensor. What it did not carry is the second half of a runtime-assurance
    entry: the safety envelope *recomputed on the degraded dynamics*. A part
    that has lost thermal margin is not the same plant it was, so the barrier
    constants change and the safe set shrinks. Without that, repurposing is
    plausible; with it, the claim that a fallback is safe has a truth condition.
    """

    failure_mode: str
    capability: str
    effectiveness: float
    envelope: Dict[str, float]
    barriers: Callable[[], List[Barrier]]
    note: str = ""

    def admits(self, state: State) -> Tuple[bool, List[str]]:
        """Is `state` inside this fallback's recomputed envelope?"""
        breaches = []
        for key, limit in self.envelope.items():
            if key.endswith("_max") and state.get(key[:-4], 0.0) > limit:
                breaches.append(f"{key[:-4]}={state.get(key[:-4]):.2f} > {limit:.2f}")
            elif key.endswith("_min") and state.get(key[:-4], 0.0) < limit:
                breaches.append(f"{key[:-4]}={state.get(key[:-4]):.2f} < {limit:.2f}")
        return not breaches, breaches


class FallbackCatalog:
    """Simplex-style catalog: (failure mode) -> (capability, safety envelope)."""

    def __init__(self) -> None:
        self.entries: Dict[Tuple[str, str], Fallback] = {}

    def register(self, component_type: str, fallback: Fallback) -> "FallbackCatalog":
        self.entries[(component_type, fallback.failure_mode)] = fallback
        return self

    def lookup(self, component_type: str, failure_mode: str) -> Optional[Fallback]:
        return (self.entries.get((component_type, failure_mode))
                or self.entries.get(("default", failure_mode)))

    def select(self, component_type: str, failure_mode: str,
               state: State, u_nominal: Sequence[float] = (0.0,)) -> Dict[str, object]:
        """Offer a fallback only if it is admissible *and* still controllable.

        Three ways to be refused, and they mean different things:
        no catalog entry (this failure has no known repurposing), outside the
        recomputed envelope (the capability exists but not at this state), and
        no feasible control (the envelope admits the state but the barriers
        cannot be satisfied together from here).
        """
        fallback = self.lookup(component_type, failure_mode)
        if fallback is None:
            return {"available": False, "reason": "no catalogued fallback",
                    "failure_mode": failure_mode}

        admissible, breaches = fallback.admits(state)
        if not admissible:
            return {"available": False, "reason": "outside recomputed envelope",
                    "breaches": breaches, "fallback": fallback,
                    "capability": fallback.capability}

        decision = SafetyFilter(fallback.barriers()).filter(state, u_nominal)
        return {
            "available": decision.feasible,
            "reason": ("ok" if decision.feasible
                       else "no control satisfies the degraded barriers"),
            "fallback": fallback,
            "capability": fallback.capability,
            "effectiveness": fallback.effectiveness,
            "decision": decision,
        }

    def report(self, state: Optional[State] = None) -> str:
        lines = ["FALLBACK CATALOG (failure mode -> capability + safety envelope)",
                 "=" * 62]
        for (component_type, mode), fallback in sorted(self.entries.items()):
            envelope = ", ".join(f"{k}={v:g}" for k, v in sorted(fallback.envelope.items()))
            lines.append(f"  {component_type}/{mode} -> {fallback.capability} "
                         f"(effectiveness {fallback.effectiveness:.1f})")
            lines.append(f"      envelope: {envelope or 'unrestricted'}")
            if state is not None:
                result = self.select(component_type, mode, state)
                lines.append(f"      here: {'AVAILABLE' if result['available'] else 'refused'}"
                             f" — {result['reason']}")
            if fallback.note:
                lines.append(f"      {fallback.note}")
        return "\n".join(lines)


def safety_claim(barrier: Barrier, scope: Optional[Dict] = None) -> Claim:
    """Stake a safe set as a falsifiable claim.

    The refutation condition is an observation, not an argument: the claim is
    refuted the first time h(x) < 0 is seen. Evaluate it with
    `claim.evaluate({"h": barrier.margin(state)})` on every step the barrier is
    supposed to be holding, and its Beta posterior becomes the running record of
    whether the safety argument has survived contact with the system.
    """
    return Claim(
        text=f"the system stays inside the safe set '{barrier.name}' (h >= 0)",
        falsification=f"an observation with h < 0 for '{barrier.name}'",
        logical_form={"op": "ge", "args": ["h", 0.0]},
        scope=dict(scope or {}, barrier=barrier.name, alpha=barrier.alpha),
        reference_class=f"states visited while '{barrier.name}' is enforced",
    )
