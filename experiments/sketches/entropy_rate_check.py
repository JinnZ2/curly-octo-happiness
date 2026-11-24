#!/usr/bin/env python3
"""SKETCH (not results): estimator behaviour on processes with known h and C_mu.

Supports EXP-CSS-01/02. Two binary processes with identical entropy rate and
identical statistical complexity but different Markov order:

  golden mean  (no two 1s in a row; order-1 Markov)
  even process (1s come in even-length blocks; not finite-order Markov)

Analytic values for both (Crutchfield & Feldman 2003, "Regularities unseen,
randomness observed"): h_mu = 2/3 bit/symbol, C_mu = H(2/3, 1/3) ~= 0.9183 bit.

Block-entropy estimates h(L) = H(L) - H(L-1) converge to h_mu at L = 2 for the
golden mean but only asymptotically for the even process, and plug-in H(L) is
biased downward once 2^L approaches the sample size. That is the
operationalisation gap in CSS_001: "the entropy rate" of a source is a limit,
and every finite estimate carries a model-order and a sample-size assumption
that has to be reported with the number.

Stdlib only. Printed values describe the estimator on toy processes, not
English or any dataset.
"""
import math
import random
from collections import Counter

H_MU = 2 / 3
C_MU = -(2 / 3) * math.log2(2 / 3) - (1 / 3) * math.log2(1 / 3)


def golden_mean(n, rng):
    out, s = [], "A"
    for _ in range(n):
        if s == "A":
            b = rng.randint(0, 1)
            s = "B" if b else "A"
        else:
            b, s = 0, "A"
        out.append(b)
    return out


def even_process(n, rng):
    out, s = [], "A"
    for _ in range(n):
        if s == "A":
            b = rng.randint(0, 1)
            s = "B" if b else "A"
        else:
            b, s = 1, "A"
        out.append(b)
    return out


def block_entropy(seq, L):
    if L == 0:
        return 0.0
    c = Counter(tuple(seq[i:i + L]) for i in range(len(seq) - L + 1))
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values())


def h_estimates(seq, Lmax):
    H = [block_entropy(seq, L) for L in range(Lmax + 1)]
    return [H[L] - H[L - 1] for L in range(1, Lmax + 1)]


def self_check(n=200_000, seed=3):
    rng = random.Random(seed)
    gm = h_estimates(golden_mean(n, rng), 10)
    ev = h_estimates(even_process(n, rng), 10)
    assert abs(gm[1] - H_MU) < 0.01, gm      # exact from L=2 (order-1)
    assert ev[1] - H_MU > 0.02, ev           # even process still above at L=2
    # short-sample bias: with n=200 and L=8, plug-in underestimates
    short = h_estimates(golden_mean(200, random.Random(seed)), 8)
    return {"golden_mean_h(L)": [round(v, 4) for v in gm],
            "even_h(L)": [round(v, 4) for v in ev],
            "golden_mean_n200_h(L)": [round(v, 4) for v in short],
            "analytic_h_mu": H_MU, "analytic_C_mu": C_MU}


if __name__ == "__main__":
    for k, v in self_check().items():
        print(f"{k:24s} {v}")
    print("(estimator demonstration on toy processes; not a finding)")
