"""Causal-state reconstruction (CSSR-style) for finite-alphabet streams.

Crutchfield's ε-machine is the provably minimal, unique, optimal predictor of a
stationary process: causal states are equivalence classes of pasts that induce
the same conditional distribution over futures,

    S = eps(past),   two pasts share a state iff P(next | past) matches.

Two numbers summarise the machine:

    C_mu = H[S]                    statistical complexity  (bits of memory)
    h_mu = sum_s P(s) H[X | s]     entropy rate            (bits of surprise)

Both are estimated here from the state occupation counts.

Scope of this implementation
----------------------------
This is phases I-II of CSSR (Shalizi & Shalizi 2004): initialisation and
homogenisation. Phase III (determinisation, which splits states until the
transition structure is deterministic) is **not** implemented, so `C_mu` is a
lower bound on the determinised machine's statistical complexity. Morph
equality is tested with a total-variation threshold rather than the KS test
canonical CSSR uses, because the alphabets here are small and the streams
short. The intended use is *comparative* -- two machines built the same way
from the same stream length -- where the bias of both simplifications largely
cancels. Do not read a single absolute C_mu as Crutchfield's quantity.

Stdlib only; the band convention comes from `graycode` so symbolisation here
matches every encoder plugin in the repo.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import log2
from typing import Dict, List, Optional, Sequence, Tuple

from .graycode import gray_bits, gray_to_index

__all__ = [
    "CausalState",
    "EpsilonMachine",
    "entropy",
    "equalized_history_length",
    "percentile_bands",
    "reconstruct",
    "symbolize",
]


def entropy(counts) -> float:
    """Shannon entropy in bits of a count mapping (or iterable of counts)."""
    values = list(counts.values()) if hasattr(counts, "values") else list(counts)
    total = sum(values)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in values:
        if c > 0:
            p = c / total
            h -= p * log2(p)
    return h


def percentile_bands(values: Sequence[float], n_bands: int = 4) -> List[float]:
    """Equal-occupancy band thresholds, the `init_bands` convention.

    Returns `n_bands` ascending thresholds taken at percentiles
    0, 100/n, ... so each band holds roughly the same number of samples.
    """
    ordered = sorted(values)
    if not ordered:
        return [0.0]
    bands = []
    for i in range(n_bands):
        pos = (len(ordered) - 1) * (i / n_bands)
        lo = int(pos)
        hi = min(lo + 1, len(ordered) - 1)
        bands.append(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))
    # Thresholds must be strictly usable: collapse duplicates to keep the
    # "highest band whose threshold <= value" rule well behaved.
    dedup = [bands[0]]
    for b in bands[1:]:
        dedup.append(b if b > dedup[-1] else dedup[-1])
    return dedup


def symbolize(values: Sequence[float], bands: Optional[Sequence[float]] = None,
              n_bands: int = 4) -> List[int]:
    """Quantise a float series into band indices.

    Uses `graycode.gray_bits` and decodes back, so the banding rule is
    literally the one every encoder plugin follows (highest band whose
    threshold <= value). `bands` defaults to equal-occupancy thresholds
    derived from the series itself.
    """
    if bands is None:
        bands = percentile_bands(values, n_bands)
    # Gray coding needs enough bits to round-trip the largest band index.
    n_bits = max(1, (len(bands) - 1).bit_length())
    return [gray_to_index(gray_bits(v, bands, n_bits=n_bits)) for v in values]


def equalized_history_length(base_alphabet: int, augmented_alphabet: int,
                             base_history: int) -> int:
    """History length that gives an augmented machine the same search space.

    Conditioning on extra observables multiplies the alphabet, so at the same L
    the augmented machine sees far more distinct histories and estimates more
    causal states *from the same amount of data* -- C_mu rises for a purely
    finite-sample reason, before any question of the process being genuinely
    more complex. Choosing L_aug such that

        |A_aug| ** L_aug  ~=  |A_base| ** L_base

    holds the estimation bias roughly fixed across the comparison. Without this
    correction the before/after test is biased against every candidate; with it,
    a rise in C_mu means the candidate really did complicate the process.

    Returns at least 1.
    """
    if augmented_alphabet <= 1 or base_alphabet <= 1:
        return max(1, base_history)
    space = base_history * log2(base_alphabet)
    return max(1, int(space / log2(augmented_alphabet)))


@dataclass
class CausalState:
    """One equivalence class of histories sharing a conditional morph."""

    morph: Dict[int, int] = field(default_factory=dict)   # next symbol -> count
    histories: List[Tuple] = field(default_factory=list)

    @property
    def weight(self) -> int:
        return sum(self.morph.values())

    @property
    def distribution(self) -> Dict[int, float]:
        total = self.weight
        return {s: c / total for s, c in self.morph.items()} if total else {}

    def uncertainty(self) -> float:
        """H[X | this state], in bits."""
        return entropy(self.morph)

    def absorb(self, morph: Dict[int, int], history: Tuple) -> None:
        for sym, count in morph.items():
            self.morph[sym] = self.morph.get(sym, 0) + count
        self.histories.append(history)


@dataclass
class EpsilonMachine:
    """Reconstructed causal-state machine plus its two summary statistics."""

    states: List[CausalState]
    alphabet: Tuple[int, ...]
    statistical_complexity: float   # C_mu = H[S]
    entropy_rate: float             # h_mu = sum_s P(s) H[X|s]
    max_history: int
    n_samples: int

    @property
    def n_states(self) -> int:
        return len(self.states)

    def summary(self) -> str:
        return (f"eps-machine: {self.n_states} causal states, "
                f"C_mu={self.statistical_complexity:.3f} bits, "
                f"h_mu={self.entropy_rate:.3f} bits/symbol "
                f"(|A|={len(self.alphabet)}, L={self.max_history}, "
                f"n={self.n_samples})")


def _total_variation(a: Dict[int, int], b: Dict[int, int]) -> float:
    """Total-variation distance between two count distributions."""
    ta, tb = sum(a.values()), sum(b.values())
    if ta == 0 or tb == 0:
        return 1.0
    keys = set(a) | set(b)
    return 0.5 * sum(abs(a.get(k, 0) / ta - b.get(k, 0) / tb) for k in keys)


def reconstruct(future_symbols: Sequence[int],
                history_symbols: Optional[Sequence] = None,
                max_history: int = 2,
                tolerance: float = 0.2,
                min_count: int = 2) -> EpsilonMachine:
    """Reconstruct causal states predicting `future_symbols`.

    Args:
        future_symbols: the stream being predicted (one symbol per step).
        history_symbols: what the predictor is allowed to condition on. Defaults
            to `future_symbols` (the ordinary ε-machine). Pass a parallel stream
            of tuples to condition on an *augmented* past -- that is how a
            candidate hidden variable is tested: does knowing it collapse the
            causal states needed to predict the residual?
        max_history: longest suffix considered (CSSR's L_max).
        tolerance: total-variation distance below which two morphs count as the
            same causal state.
        min_count: histories observed fewer times than this are pooled into the
            nearest state rather than founding one; keeps short streams from
            manufacturing spurious states.

    Returns:
        EpsilonMachine with `statistical_complexity` and `entropy_rate` set.
    """
    if history_symbols is None:
        history_symbols = future_symbols
    if len(history_symbols) != len(future_symbols):
        raise ValueError("history_symbols and future_symbols must be the same length")

    alphabet = tuple(sorted(set(future_symbols)))
    n = len(future_symbols)
    if n < 2 or len(alphabet) < 2:
        # A constant (or empty) stream has one state and no surprise.
        state = CausalState(morph=dict(Counter(future_symbols)), histories=[()])
        return EpsilonMachine([state], alphabet, 0.0, 0.0, max_history, n)

    # Morph counts for every suffix of every length up to max_history.
    morphs: Dict[Tuple, Dict[int, int]] = defaultdict(dict)
    for length in range(0, max_history + 1):
        for i in range(length, n):
            history = tuple(history_symbols[i - length:i])
            nxt = future_symbols[i]
            morphs[history][nxt] = morphs[history].get(nxt, 0) + 1

    # Phase I: the null history seeds the single initial state.
    states: List[CausalState] = [CausalState(morph=dict(morphs[()]), histories=[()])]

    # Phase II (homogenisation): longer suffixes either join a state whose morph
    # they match or found a new one.
    ordered = sorted((h for h in morphs if h), key=lambda h: (len(h), h))
    for history in ordered:
        morph = morphs[history]
        if sum(morph.values()) < min_count:
            continue
        best, best_distance = None, None
        for state in states:
            distance = _total_variation(morph, state.morph)
            if best_distance is None or distance < best_distance:
                best, best_distance = state, distance
        if best is not None and best_distance <= tolerance:
            best.absorb(morph, history)
        else:
            states.append(CausalState(morph=dict(morph), histories=[history]))

    # Only the longest-suffix layer carries the occupancy estimate; the shorter
    # suffixes were scaffolding for the split decisions above. Re-weight states
    # by the deepest histories assigned to them, falling back to all of them
    # when the deepest layer is too sparse to be informative.
    deepest = max((len(h) for st in states for h in st.histories), default=0)
    weighted: List[CausalState] = []
    for state in states:
        deep = [h for h in state.histories if len(h) == deepest]
        if not deep:
            continue
        merged: Dict[int, int] = {}
        for h in deep:
            for sym, count in morphs[h].items():
                merged[sym] = merged.get(sym, 0) + count
        if merged:
            weighted.append(CausalState(morph=merged, histories=deep))
    if not weighted:
        weighted = states

    total = sum(st.weight for st in weighted) or 1
    c_mu = entropy([st.weight for st in weighted])
    h_mu = sum((st.weight / total) * st.uncertainty() for st in weighted)

    return EpsilonMachine(
        states=weighted,
        alphabet=alphabet,
        statistical_complexity=c_mu,
        entropy_rate=h_mu,
        max_history=max_history,
        n_samples=n,
    )
