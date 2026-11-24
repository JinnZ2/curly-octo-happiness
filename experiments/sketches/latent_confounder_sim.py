#!/usr/bin/env python3
"""SKETCH (not results): residual-correlation test for a hidden common driver.

Supports EXP-HVD-02. Two observed series X, Y and an optional hidden AR(1)
driver Z. We fit a VAR(1) on (X, Y) only and test whether the contemporaneous
correlation of the two residual series differs from 0 (Fisher z).

Three generating regimes, ground truth known:
  null      no Z, no instantaneous X->Y          -> estimates type-I error
  hidden    Z drives X and Y at lag 0            -> estimates power
  instant   no Z, instantaneous X->Y at lag 0    -> a *non-latent* cause of
                                                    residual correlation

The `instant` regime is the point of the sketch: residual correlation is a
symptom shared by a latent confounder and an unmodelled contemporaneous edge,
so on its own it cannot identify a hidden variable. Any HVD method claiming to
detect confounders from residuals must separate these regimes; the experiment
in hidden-variable-detection-causal-discovery-from-residuals.md tests that.

Stdlib only; deterministic seeds. Printed rates are Monte-Carlo properties of
this toy generator, not findings about any published method.
"""
import math
import random


def simulate(T, regime, rng, a=0.5, c=0.3, conf=0.8, inst=0.8):
    x = y = z = 0.0
    xs, ys = [], []
    for _ in range(T + 50):
        z = 0.7 * z + rng.gauss(0, 1)
        zx = conf * z if regime == "hidden" else 0.0
        nx = a * x + zx + rng.gauss(0, 1)
        ny = a * y + c * x + (conf * z if regime == "hidden" else 0.0) \
            + (inst * nx if regime == "instant" else 0.0) + rng.gauss(0, 1)
        x, y = nx, ny
        xs.append(x)
        ys.append(y)
    return xs[50:], ys[50:]


def _ols2(target, r1, r2):
    s11 = sum(u * u for u in r1); s22 = sum(v * v for v in r2)
    s12 = sum(u * v for u, v in zip(r1, r2))
    t1 = sum(u * t for u, t in zip(r1, target)); t2 = sum(v * t for v, t in zip(r2, target))
    det = s11 * s22 - s12 * s12
    b1 = (s22 * t1 - s12 * t2) / det
    b2 = (s11 * t2 - s12 * t1) / det
    return [t - b1 * u - b2 * v for t, u, v in zip(target, r1, r2)]


def residual_corr_p(xs, ys):
    x0, y0, x1, y1 = xs[:-1], ys[:-1], xs[1:], ys[1:]
    ex = _ols2(x1, x0, y0)
    ey = _ols2(y1, x0, y0)
    n = len(ex)
    mx, my = sum(ex) / n, sum(ey) / n
    sxy = sum((u - mx) * (v - my) for u, v in zip(ex, ey))
    sxx = sum((u - mx) ** 2 for u in ex); syy = sum((v - my) ** 2 for v in ey)
    r = sxy / math.sqrt(sxx * syy)
    z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(n - 3)
    p = math.erfc(abs(z) / math.sqrt(2))
    return r, p


def rejection_rate(regime, T=300, reps=200, alpha=0.05, seed=0):
    rng = random.Random(seed)
    hits = 0
    for _ in range(reps):
        xs, ys = simulate(T, regime, rng)
        _, p = residual_corr_p(xs, ys)
        hits += p < alpha
    return hits / reps


def self_check():
    out = {r: rejection_rate(r, reps=120) for r in ("null", "hidden", "instant")}
    # Loose by-construction checks only.
    assert out["null"] < 0.15, out
    assert out["hidden"] > 0.5 and out["instant"] > 0.5, out
    return out


if __name__ == "__main__":
    res = self_check()
    for k, v in res.items():
        print(f"rejection rate, regime={k:8s} {v:.3f}")
    print("hidden and instant are both rejected: residual correlation alone does not\n"
          "identify a latent variable (toy generator; not a finding about any method).")
