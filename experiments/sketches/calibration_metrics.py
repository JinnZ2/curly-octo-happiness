#!/usr/bin/env python3
"""SKETCH (not results): calibration / selective-prediction metrics for EXP-CFA-*.

Stdlib only. Shared by every CFA experiment so that "calibrated" means one
thing across them. Provides:

  ece(p, y, n_bins, scheme)  expected calibration error, equal-width or
                             equal-mass bins (the choice moves the number;
                             report both, see EXP-CFA-01 analysis plan)
  brier(p, y)                Brier score
  auroc(s, y)                rank AUROC (Mann-Whitney), ties counted 1/2
  aurc(conf, correct)        area under risk-coverage curve (selective risk)
  bootstrap_ci(fn, *cols)    percentile bootstrap CI, fixed seed
  ece_consistency_null(p)    ECE null distribution under perfect calibration

`self_check()` runs on synthetic data with known calibration and asserts only
properties that must hold by construction (e.g. an overconfident transform of a
calibrated predictor has higher ECE in expectation). Its printed numbers are a
demonstration of the code, not a finding about any model.
"""
import math
import random


def _bins(p, n_bins, scheme):
    idx = list(range(len(p)))
    if scheme == "width":
        groups = [[] for _ in range(n_bins)]
        for i in idx:
            groups[min(int(p[i] * n_bins), n_bins - 1)].append(i)
        return [g for g in groups if g]
    if scheme == "mass":
        idx.sort(key=lambda i: p[i])
        size = max(1, len(idx) // n_bins)
        return [idx[k:k + size] for k in range(0, len(idx), size)]
    raise ValueError(scheme)


def ece(p, y, n_bins=15, scheme="width"):
    n = len(p)
    total = 0.0
    for g in _bins(p, n_bins, scheme):
        conf = sum(p[i] for i in g) / len(g)
        acc = sum(y[i] for i in g) / len(g)
        total += len(g) / n * abs(conf - acc)
    return total


def brier(p, y):
    return sum((pi - yi) ** 2 for pi, yi in zip(p, y)) / len(p)


def auroc(s, y):
    pos = [si for si, yi in zip(s, y) if yi]
    neg = [si for si, yi in zip(s, y) if not yi]
    if not pos or not neg:
        return float("nan")
    order = sorted(range(len(s)), key=lambda i: s[i])
    ranks = [0.0] * len(s)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and s[order[j + 1]] == s[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    rpos = sum(r for r, yi in zip(ranks, y) if yi)
    return (rpos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def aurc(conf, correct):
    """Mean selective risk over coverages k/n, most-confident first."""
    order = sorted(range(len(conf)), key=lambda i: -conf[i])
    errs = 0
    area = 0.0
    for k, i in enumerate(order, 1):
        errs += 0 if correct[i] else 1
        area += errs / k
    return area / len(conf)


def bootstrap_ci(fn, *cols, n_boot=500, alpha=0.05, seed=0):
    rng = random.Random(seed)
    n = len(cols[0])
    stats = []
    for _ in range(n_boot):
        ix = [rng.randrange(n) for _ in range(n)]
        stats.append(fn(*[[c[i] for i in ix] for c in cols]))
    stats.sort()
    lo = stats[int(alpha / 2 * n_boot)]
    hi = stats[int((1 - alpha / 2) * n_boot) - 1]
    return lo, hi


def ece_consistency_null(p, n_bins=15, scheme="width", n_rep=200, seed=0):
    """ECE distribution if the model were perfectly calibrated at these p.

    Consistency resampling (Broecker & Smith 2007): draw y* ~ Bernoulli(p) and
    recompute ECE. Plug-in ECE is biased upward at finite n, and a bootstrap
    of ECE inherits and compounds that bias (see self_check), so the test of
    "miscalibrated" is observed ECE against this null, not ECE > 0.
    Returns the sorted null sample.
    """
    rng = random.Random(seed)
    out = []
    for _ in range(n_rep):
        ys = [1 if rng.random() < pi else 0 for pi in p]
        out.append(ece(p, ys, n_bins, scheme))
    return sorted(out)


def synthetic(n, seed, temperature=1.0):
    """True p ~ Beta-ish; label ~ Bernoulli(p); reported conf = sharpened p."""
    rng = random.Random(seed)
    p, y, q = [], [], []
    for _ in range(n):
        t = rng.betavariate(2, 2)
        p.append(t)
        y.append(1 if rng.random() < t else 0)
        logit = math.log(t / (1 - t)) / temperature
        q.append(1 / (1 + math.exp(-logit)))
    return p, y, q


def self_check(n=4000, seed=1):
    p, y, _ = synthetic(n, seed)
    _, _, over = synthetic(n, seed, temperature=0.5)  # same draws, sharpened
    e_cal = ece(p, y)
    e_over = ece(over, y)
    assert e_over > e_cal, (e_cal, e_over)
    assert abs(auroc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]) - 0.75) < 1e-12
    # sharpening a score monotonically cannot change AUROC
    assert abs(auroc(p, y) - auroc(over, y)) < 1e-12
    return {"ece_calibrated": e_cal, "ece_overconfident": e_over,
            "ece_mass_overconfident": ece(over, y, scheme="mass"),
            "ece_by_bins_overconfident": {b: ece(over, y, n_bins=b) for b in (5, 10, 15, 30)},
            "auroc": auroc(p, y), "brier_cal": brier(p, y), "brier_over": brier(over, y),
            "aurc": aurc(p, [bool(v) for v in y]),
            "ece_cal_bootstrap_ci95 (biased up)": bootstrap_ci(ece, p, y, n_boot=200),
            "ece_cal_consistency_null_95pct": ece_consistency_null(p, n_rep=200)[189],
            "ece_over_consistency_null_95pct": ece_consistency_null(over, n_rep=200)[189]}


if __name__ == "__main__":
    for k, v in self_check().items():
        print(f"{k:36s} {v}")
    print("(demonstration on synthetic data; not a measurement of any model)")
