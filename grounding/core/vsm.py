"""Beer's Viable System Model as actual routing, not a diagram.

The five systems:

    S1  operations      autonomous units that do the work and stake claims
    S2  coordination    damps oscillation between S1 units (here: trust)
    S3  control         resource allocation and the inside-and-now audit
    S3* audit           the diagnostic channel that bypasses S3's own reporting
    S4  intelligence    the outside-and-future scan
    S5  policy          identity; adjudicates the S3/S4 homeostat

Two properties make this a model rather than a labelling exercise, and both are
tested:

**The algedonic channel really bypasses.** Beer's algedonic signal (from
*algos*/*hedone*, pain and pleasure) is the one path that does not wait its turn:
when an operational unit is in trouble, the signal goes straight to S5 without
S2's coordination or S3's resource arbitration getting a say. A normal signal
walks S1 -> S2 -> S3 -> S5 and can be attenuated or dropped at each hop. Every
signal carries the `path` it actually travelled, so "it bypassed" is a checkable
claim about a specific message, not an assertion about the architecture.

**Recursion.** Every viable system contains viable systems of the same form, and
an algedonic signal raised deep in a subsystem surfaces all the way up.

The channel is also rate-guarded. An algedonic channel that fires constantly has
stopped being an alarm and become the weather; `saturated()` reports when the
signal rate has crossed the point where S5 can no longer treat it as exceptional.

Stdlib only.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional

__all__ = [
    "AlgedonicSignal",
    "SecondOrderGuard",
    "Signal",
    "SYSTEM_NAMES",
    "ViableSystem",
]

SYSTEM_NAMES = {
    1: "S1 operations",
    2: "S2 coordination",
    3: "S3 control",
    4: "S4 intelligence",
    5: "S5 policy",
}


@dataclass
class Signal:
    """An ordinary message climbing the hierarchy, mediated at every hop."""

    source: str
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)
    path: List[str] = field(default_factory=list)
    attenuated_by: List[str] = field(default_factory=list)
    delivered: bool = False
    raised_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def bypassed_mediation(self) -> bool:
        """True when the signal reached S5 without S2/S3 handling it."""
        return self.delivered and not any(hop.startswith(("S2", "S3")) for hop in self.path)


@dataclass
class AlgedonicSignal(Signal):
    """Pain or pleasure from an operational unit, addressed straight to S5.

    `severity` is Beer's pain/pleasure axis: "pain" is the unit reporting that
    it cannot continue on its current terms, "pleasure" that something is going
    unexpectedly well and the policy level should know why.
    """

    severity: str = "pain"

    def __post_init__(self) -> None:
        if self.severity not in ("pain", "pleasure"):
            raise ValueError(f"severity must be 'pain' or 'pleasure', got {self.severity!r}")


class ViableSystem:
    """One viable system: five registries, two channels, and its subsystems."""

    def __init__(self, name: str, algedonic_window: int = 20,
                 saturation_rate: float = 0.25):
        """
        Args:
            algedonic_window: how many recent signals the rate guard remembers.
            saturation_rate: fraction of recent traffic that may be algedonic
                before the channel counts as saturated. Beer's point is that the
                channel works *because* it is rare.
        """
        self.name = name
        self.units: Dict[int, List[str]] = {n: [] for n in SYSTEM_NAMES}
        self.subsystems: List["ViableSystem"] = []
        self.parent: Optional["ViableSystem"] = None

        self.log: List[Signal] = []
        self.algedonic_log: List[AlgedonicSignal] = []
        self._recent: Deque[bool] = deque(maxlen=algedonic_window)
        self.saturation_rate = saturation_rate

        self._mediators: Dict[int, Callable[[Signal], bool]] = {}
        self._policy_handlers: List[Callable[[Signal], None]] = []

    # -- structure ------------------------------------------------------

    def register(self, system: int, unit: str) -> "ViableSystem":
        """Assign a named component to one of the five systems."""
        if system not in SYSTEM_NAMES:
            raise ValueError(f"system must be 1-5, got {system}")
        if unit not in self.units[system]:
            self.units[system].append(unit)
        return self

    def contains(self, subsystem: "ViableSystem") -> "ViableSystem":
        """Nest a viable system inside this one (S1 units are viable systems)."""
        subsystem.parent = self
        self.subsystems.append(subsystem)
        return self

    def mediator(self, system: int, handler: Callable[[Signal], bool]) -> None:
        """Install an S2/S3 handler. Returning False attenuates the signal away."""
        if system not in (2, 3, 4):
            raise ValueError("only S2, S3 and S4 mediate ordinary signals")
        self._mediators[system] = handler

    def on_policy(self, handler: Callable[[Signal], None]) -> None:
        """Register an S5 handler — the mentor/governance level."""
        self._policy_handlers.append(handler)

    # -- channels -------------------------------------------------------

    def route(self, signal: Signal) -> Signal:
        """Send a signal up the ordinary path, mediated at each hop."""
        signal.path.append(f"S1 {signal.source}")
        for system in (2, 3):
            hop = SYSTEM_NAMES[system]
            signal.path.append(hop)
            handler = self._mediators.get(system)
            if handler is not None and not handler(signal):
                signal.attenuated_by.append(hop)
                self._record(signal, algedonic=False)
                return signal
        signal.path.append(SYSTEM_NAMES[5])
        signal.delivered = True
        self._deliver(signal)
        self._record(signal, algedonic=False)
        return signal

    def raise_algedonic(self, signal: AlgedonicSignal) -> AlgedonicSignal:
        """Deliver straight to S5, and keep surfacing through every parent.

        No mediator is consulted. That is the entire point: a unit in pain does
        not have to win an argument with the coordination layer first.
        """
        signal.path.append(f"S1 {signal.source}")
        signal.path.append(f"{SYSTEM_NAMES[5]} (algedonic)")
        signal.delivered = True
        self._deliver(signal)
        self._record(signal, algedonic=True)
        if self.parent is not None:
            self.parent.raise_algedonic(signal)
        return signal

    def _deliver(self, signal: Signal) -> None:
        for handler in self._policy_handlers:
            handler(signal)

    def _record(self, signal: Signal, algedonic: bool) -> None:
        self.log.append(signal)
        self._recent.append(algedonic)
        if algedonic and isinstance(signal, AlgedonicSignal):
            if signal not in self.algedonic_log:
                self.algedonic_log.append(signal)

    # -- health ---------------------------------------------------------

    def algedonic_load(self) -> float:
        """Fraction of recent traffic that came up the algedonic channel."""
        if not self._recent:
            return 0.0
        return sum(1 for flag in self._recent if flag) / len(self._recent)

    def saturated(self) -> bool:
        """Has the alarm channel become the normal channel?

        A saturated algedonic channel is itself a diagnosis: either the
        operational units are genuinely failing en masse, or the pain threshold
        is set so low that S5 has lost the ability to tell exceptional from
        routine. Either way, S5 needs to know.
        """
        return len(self._recent) >= 4 and self.algedonic_load() > self.saturation_rate

    def report(self) -> str:
        lines = [f"Viable system: {self.name}"]
        for system in sorted(SYSTEM_NAMES):
            units = ", ".join(self.units[system]) or "—"
            lines.append(f"  {SYSTEM_NAMES[system]:18} {units}")
        if self.subsystems:
            lines.append(f"  contains: {', '.join(s.name for s in self.subsystems)}")
        lines.append(f"  signals: {len(self.log)} "
                     f"({len(self.algedonic_log)} algedonic, "
                     f"load {self.algedonic_load():.0%}"
                     f"{', SATURATED' if self.saturated() else ''})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1.4 — second-order guard
# ---------------------------------------------------------------------------

class SecondOrderGuard:
    """Catch a self-description that has become a fixed point of its own belief.

    Von Foerster's eigenvalue: a self-referential system settles on descriptions
    stable under its own operation — which is fine when the description is also
    true, and a trap when the only evidence for it is the system's own
    agreement. The guard is a second observer. It compares what the agent says
    about itself against a stream the self-model does not produce (world-model
    residuals, HND diagnostics), and flags two failures:

    * **overconfidence** — self-confidence high while independent error is high;
      the self-description is not tracking the diagnostics at all.
    * **drift** — self-confidence rising monotonically over several checks while
      independent error refuses to fall. This is the eigenvalue case, and it is
      the one that cannot be seen from a single snapshot, which is why the
      guard keeps history.

    Confidence and error are both on [0, 1]; error is "how wrong the independent
    stream says the agent is", so a well-calibrated agent has
    self_confidence ≈ 1 - independent_error.
    """

    def __init__(self, tolerance: float = 0.3, history: int = 4):
        """
        Args:
            tolerance: how far self-confidence may exceed what the independent
                stream supports before it counts as overconfidence, in [0, 1].
            history: consecutive checks inspected for drift (minimum 3 — two
                points are a line, not a trend).
        """
        self.tolerance = tolerance
        self.history = max(3, history)
        self.observations: List[Dict[str, float]] = []

    def observe(self, self_confidence: float, independent_error: float) -> Dict[str, float]:
        record = {"self_confidence": float(self_confidence),
                  "independent_error": float(independent_error),
                  "supported": 1.0 - float(independent_error)}
        self.observations.append(record)
        return record

    def check(self, self_confidence: Optional[float] = None,
              independent_error: Optional[float] = None) -> List[str]:
        """Record an observation (if given) and return any flags it raises."""
        if self_confidence is not None and independent_error is not None:
            self.observe(self_confidence, independent_error)
        if not self.observations:
            return []

        flags: List[str] = []
        latest = self.observations[-1]
        gap = latest["self_confidence"] - latest["supported"]
        if gap > self.tolerance:
            flags.append(
                f"overconfident: self-model confidence {latest['self_confidence']:.2f} "
                f"exceeds what independent diagnostics support "
                f"({latest['supported']:.2f}) by {gap:.2f}")

        window = self.observations[-self.history:]
        if len(window) >= self.history:
            confidences = [o["self_confidence"] for o in window]
            errors = [o["independent_error"] for o in window]
            rising = all(b > a for a, b in zip(confidences, confidences[1:]))
            not_improving = errors[-1] >= errors[0]
            if rising and not_improving:
                flags.append(
                    f"eigenvalue drift: self-model confidence rose "
                    f"{confidences[0]:.2f} -> {confidences[-1]:.2f} over "
                    f"{len(window)} checks while independent error did not fall "
                    f"({errors[0]:.2f} -> {errors[-1]:.2f}); the self-description "
                    "is confirming itself")
        return flags

    def report(self) -> str:
        if not self.observations:
            return "Second-order guard: nothing observed yet."
        flags = self.check()
        latest = self.observations[-1]
        head = (f"Second-order guard: self-confidence {latest['self_confidence']:.2f} "
                f"vs independently supported {latest['supported']:.2f} "
                f"over {len(self.observations)} checks")
        if not flags:
            return head + " — consistent."
        return "\n".join([head] + [f"  ⚠ {flag}" for flag in flags])
