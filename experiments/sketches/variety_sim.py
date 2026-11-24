#!/usr/bin/env python3
"""SKETCH (not results): Ashby's law in the regulation game, as a checkable bound.

Supports EXP-RVC-01/02. Disturbance D (n values), regulator response R,
outcome E = (D - R) mod n -- a Latin-square table, so for each fixed R the map
D -> E is injective. For any regulator R = f(observation of D):

    H(E) >= H(E | R) = H(D | R) = H(D) - I(D; R) >= H(D) - H(R)

This is an identity-plus-inequality, true for empirical (plug-in)
distributions as well, so the sketch can assert it on every sample. That is a
check of *mathematical validity in a toy model*. The empirical question in
requisite-variety-and-cybernetic-regulation.md is different: whether a measured
variety margin predicts regulation failure in real systems, where the outcome
table is not a Latin square, responses are delayed, and "variety" must be
operationalised. Nothing here speaks to that.

Regulators simulated:
  limited(m)  perfect observation, only m distinct responses
  noisy(eps)  full repertoire, observation replaced by noise w.p. eps
"""
import math
import random
from collections import Counter


def H(samples):
    c = Counter(samples)
    n = len(samples)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def run(n, T, regulator, rng):
    D, R, E = [], [], []
    for _ in range(T):
        d = rng.randrange(n)
        r = regulator(d, rng)
        D.append(d); R.append(r); E.append((d - r) % n)
    hd, hr, he = H(D), H(R), H(E)
    i_dr = hd + hr - H(list(zip(D, R)))
    return {"H(D)": hd, "H(R)": hr, "H(E)": he, "I(D;R)": i_dr}


def limited(m, n):
    return lambda d, rng: (d * m // n) * (n // m)


def noisy(eps, n):
    return lambda d, rng: d if rng.random() >= eps else rng.randrange(n)


def self_check(n=16, T=20_000, seed=7):
    rng = random.Random(seed)
    rows = {}
    for name, reg in [("limited(16)", limited(16, n)), ("limited(4)", limited(4, n)),
                      ("limited(1)", limited(1, n)), ("noisy(0.25)", noisy(0.25, n)),
                      ("noisy(1.0)", noisy(1.0, n))]:
        s = run(n, T, reg, rng)
        assert s["H(E)"] >= s["H(D)"] - s["I(D;R)"] - 1e-9, (name, s)
        assert s["H(D)"] - s["I(D;R)"] >= s["H(D)"] - s["H(R)"] - 1e-9, (name, s)
        rows[name] = {k: round(v, 3) + 0.0 for k, v in s.items()}
    return rows


if __name__ == "__main__":
    for k, v in self_check().items():
        print(f"{k:12s} {v}")
    print("bound H(E) >= H(D) - I(D;R) >= H(D) - H(R) held on every run (toy game; not a finding)")
