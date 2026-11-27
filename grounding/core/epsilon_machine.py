"""Causal-state reconstruction (CSSR-style) for finite-alphabet streams.

Crutchfield's ε-machine is the provably minimal, unique, optimal predictor of a
stationary process: causal states are equivalence classes of pasts that induce
the same conditional distribution over futures,

    S = eps(past),   two pasts share a state iff P(future | past) matches.

Two numbers summarise the machine:

    C_mu = H[S]                    statistical complexity  (bits of memory)
    h_mu = sum_s P(s) H[X | s]     entropy rate            (bits of surprise)

Both are estimated here from the state occupation counts.

Scope of this implementation
----------------------------
This is CSSR (Shalizi & Shalizi 2004, "Blind Construction of Optimal Nonlinear
Recursive Predictors for Discrete Sequences", UAI 2004, arXiv:cs/0406011,
Fig. 1), phases I-III:

* I  initialisation -- one state holding the null history;
* II homogenisation -- each suffix, shortest first, is tested against its
  parent's state with a chi-squared homogeneity test of size `alpha`
  (default 1e-3, the paper's experimental value), then against the other
  states; it founds a new state if every test rejects;
* III determinisation -- transient states are removed (closed strongly
  connected components are kept), then states are split until every symbol
  takes all histories of a state to one state. The machine is unifilar, so
  two histories share a state only if they agree on the whole future, not
  just the next symbol.

State weights are the counts of the longest-suffix layer (the paper does not
specify how to estimate state probabilities; this is our choice).

Dated note, 2026-11-27: before this date Phase II used a fixed
total-variation threshold (`tolerance`, default 0.2) and there was no Phase
III, so C_mu merged states with equal next-symbol morphs and undercounted,
e.g. 2 states / 0.918 bits instead of 3 / log2(3) for a period-3 process.
`test="tv"` keeps the threshold rule (now followed by Phase III) for
comparison and for callers that need its small-sample power; it is not
consistent as n grows. Evidence: experiments/results/EXP-CSS-02 and its
rerun-2026-11-27 folder.

Limits: like any finite-L estimator this cannot recover processes with
infinitely many causal states (e.g. the simple nonunifilar source, which it
undercounts); with L too large for the data, false rejections at size alpha
across many histories found spurious states that Phase III then propagates;
and processes whose length-L histories do not all synchronise (e.g. the even
process, where a run of L ones leaves the parity unknown) get extra states.
The intended use is *comparative* -- two machines built the same way from the
same stream length. Do not read a single absolute C_mu as Crutchfield's
quantity without checking L against the data.

Stdlib only; the band convention comes from `graycode` so symbolisation here
matches every encoder plugin in the repo.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import exp, lgamma, log, log2
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



def _determinise(partition: List[List[Tuple]], history_symbols: Sequence,
                 length: int) -> List[List[Tuple]]:
    """CSSR Phase III on length-`length` histories (Shalizi & Shalizi 2004, Fig. 1).

    Transient blocks are removed first (`_drop_transients`). The successor of
    history x on symbol b is the length-`length` suffix of xb.
    A block is split whenever two of its histories send the same symbol to
    different blocks; this repeats until no block splits. Transitions never
    observed in the data impose no constraint (the history stays with the
    first group). Splits only refine the partition, so next-symbol morphs
    inside a block stay homogeneous and the loop terminates.
    """
    succ: Dict[Tuple, Dict] = defaultdict(dict)
    n = len(history_symbols)
    for i in range(length, n):
        x = tuple(history_symbols[i - length:i])
        b = history_symbols[i]
        succ[x][b] = tuple(history_symbols[i - length + 1:i + 1])

    # Transient states first, as in the paper's Phase III.
    blocks = [list(block) for block in _drop_transients(partition, succ)]
    changed = True
    while changed:
        changed = False
        label = {h: k for k, block in enumerate(blocks) for h in block}
        for k, block in enumerate(blocks):
            symbols = sorted({b for h in block for b in succ.get(h, {})}, key=repr)
            for b in symbols:
                groups: Dict[int, List[Tuple]] = {}
                unconstrained: List[Tuple] = []
                for h in block:
                    target = succ.get(h, {}).get(b)
                    if target is None or target not in label:
                        unconstrained.append(h)
                    else:
                        groups.setdefault(label[target], []).append(h)
                if len(groups) > 1:
                    ordered = list(groups.values())   # first-seen order: x0's group first
                    ordered[0].extend(unconstrained)
                    blocks[k] = sorted(ordered[0])
                    blocks.extend(sorted(g) for g in ordered[1:])
                    changed = True
                    break
            if changed:
                break
    return blocks

def _gammaincc(a: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(a, x), stdlib only.

    Series for x < a + 1, Lentz continued fraction otherwise (the standard
    pair, e.g. Numerical Recipes 6.2). Used for chi-squared tail probabilities.
    """
    if x <= 0:
        return 1.0
    log_prefactor = -x + a * log(x) - lgamma(a)
    if x < a + 1:
        term = total = 1.0 / a
        ap = a
        for _ in range(1000):
            ap += 1
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        return max(0.0, 1.0 - total * exp(log_prefactor))
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-14:
            break
    return exp(log_prefactor) * h


def _same_distribution(a: Dict[int, int], b: Dict[int, int], alpha: float) -> bool:
    """Chi-squared homogeneity test of two count morphs at size `alpha`.

    True when the hypothesis "same next-symbol distribution" is *not*
    rejected. This is CSSR's Phase II test (Shalizi & Shalizi 2004 allow
    chi-squared or KS; their experiments use alpha = 1e-3). Unlike a fixed
    total-variation threshold its power grows with the counts, so the
    estimator stays consistent as the stream lengthens.
    """
    ta, tb = sum(a.values()), sum(b.values())
    if ta == 0 or tb == 0:
        return True
    grand = ta + tb
    statistic = 0.0
    columns = 0
    for key in set(a) | set(b):
        col = a.get(key, 0) + b.get(key, 0)
        if col == 0:
            continue
        columns += 1
        for observed, row in ((a.get(key, 0), ta), (b.get(key, 0), tb)):
            expected = row * col / grand
            statistic += (observed - expected) ** 2 / expected
    dof = columns - 1
    if dof <= 0:
        return True
    return _gammaincc(dof / 2, statistic / 2) > alpha


def _drop_transients(partition: List[List[Tuple]], succ: Dict[Tuple, Dict]) -> List[List[Tuple]]:
    """Keep only recurrent blocks: the closed strongly connected components.

    Shalizi & Shalizi 2004, Phase III: "Remove transient states", by finding
    the strongly connected components of the state-transition graph and
    keeping the recurrent part of the component graph. If that would remove
    everything (too little data for a closed class), the partition is kept.
    """
    label = {h: k for k, block in enumerate(partition) for h in block}
    edges = [set() for _ in partition]
    for k, block in enumerate(partition):
        for h in block:
            for target in succ.get(h, {}).values():
                if target in label:
                    edges[k].add(label[target])
    # Tarjan's SCC, iterative.
    index, low, on_stack, stack, comp = {}, {}, set(), [], {}
    counter = [0]
    n_comp = 0
    for root in range(len(partition)):
        if root in index:
            continue
        work = [(root, iter(sorted(edges[root])))]
        index[root] = low[root] = counter[0]; counter[0] += 1
        stack.append(root); on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]; counter[0] += 1
                    stack.append(nxt); on_stack.add(nxt)
                    work.append((nxt, iter(sorted(edges[nxt]))))
                    advanced = True
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                while True:
                    member = stack.pop(); on_stack.discard(member)
                    comp[member] = n_comp
                    if member == node:
                        break
                n_comp += 1
    closed = [all(comp[t] == c for k in range(len(partition)) if comp[k] == c for t in edges[k])
              for c in range(n_comp)]
    kept = [block for k, block in enumerate(partition) if closed[comp[k]]]
    return kept or partition


def reconstruct(future_symbols: Sequence[int],
                history_symbols: Optional[Sequence] = None,
                max_history: int = 2,
                tolerance: float = 0.2,
                min_count: int = 2,
                alpha: float = 0.001,
                test: str = "chi2") -> EpsilonMachine:
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
            same causal state; used only when ``test="tv"``.
        min_count: histories observed fewer times than this are pooled into the
            nearest state rather than founding one; keeps short streams from
            manufacturing spurious states.
        alpha: size of the chi-squared homogeneity test (``test="chi2"``);
            1e-3 is the value Shalizi & Shalizi 2004 use in their experiments.
        test: ``"chi2"`` (default, canonical CSSR: parent state first, then the
            other states) or ``"tv"`` (the pre-2026-11-27 fixed-threshold rule,
            kept for comparison; it is not consistent as n grows).

    Returns:
        EpsilonMachine with `statistical_complexity` and `entropy_rate` set.
    """
    if test not in ("chi2", "tv"):
        raise ValueError("test must be 'chi2' or 'tv'")
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
    where: Dict[Tuple, int] = {(): 0}

    # Phase II (homogenisation): each suffix, shortest first, joins a state
    # whose morph it matches or founds a new one.
    ordered = sorted((h for h in morphs if h), key=lambda h: (len(h), h))
    for history in ordered:
        morph = morphs[history]
        if sum(morph.values()) < min_count:
            continue
        if test == "tv":
            best, best_distance = None, None
            for k, state in enumerate(states):
                distance = _total_variation(morph, state.morph)
                if best_distance is None or distance < best_distance:
                    best, best_distance = k, distance
            target = best if best is not None and best_distance <= tolerance else None
        else:
            # CSSR: test against the parent's state (history minus its oldest
            # symbol) first; if rejected, the closest other state that passes.
            parent = where.get(history[1:])
            if parent is not None and _same_distribution(morph, states[parent].morph, alpha):
                target = parent
            else:
                passing = [(_total_variation(morph, st.morph), k) for k, st in enumerate(states)
                           if k != parent and _same_distribution(morph, st.morph, alpha)]
                target = min(passing)[1] if passing else None
        if target is None:
            states.append(CausalState(morph=dict(morph), histories=[history]))
            where[history] = len(states) - 1
        else:
            states[target].absorb(morph, history)
            where[history] = target

    # Only the longest-suffix layer carries the occupancy estimate; the shorter
    # suffixes were scaffolding for the split decisions above.
    deepest = max((len(h) for st in states for h in st.histories), default=0)
    deep_partition = [sorted(h for h in st.histories if len(h) == deepest)
                      for st in states]
    deep_partition = [block for block in deep_partition if block]

    # Phase III (determinisation): split states until transitions are
    # deterministic, so that two histories share a state only if they also
    # agree on where every next symbol takes them -- i.e. on the whole future,
    # not just the next symbol.
    if deepest > 0 and deep_partition:
        deep_partition = _determinise(deep_partition, history_symbols, deepest)

    weighted: List[CausalState] = []
    for block in deep_partition:
        merged: Dict[int, int] = {}
        for h in block:
            for sym, count in morphs[h].items():
                merged[sym] = merged.get(sym, 0) + count
        if merged:
            weighted.append(CausalState(morph=merged, histories=list(block)))
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
