#!/usr/bin/env python3
"""EXP-RVC-02 phase 1 (simulation only): does a measured variety margin
predict regulation failure, and does I(D;R) beat log|R|?

Pipeline check, pre-registered as such: it tests the measurement pipeline,
not any real system. Phase 2 (field data) is not run.

Regulation game (parameters fixed before running):
  n = 8 disturbance classes; D_t Markov: repeat previous class w.p. 0.5,
  else uniform -> stationary uniform, H(D) = 3 bits.
  Regulator r = (m, eps, c): repertoire of m in {1,2,4,8} responses (a fixed
  subset), observation noise eps in {0, .1, .2, .4, .6} (observed class replaced
  by a uniform draw), capacity c in {1, 2} responses/step with k = 2
  disturbances arriving per step (c = 2 means no capacity limit).
  Delay delta in {0, 1, 2, 4}: the response to the disturbance at t uses the
  observation of the class at t - delta (the class persists w.p. 0.5/step).
  Outcome table: 'latin'  e = (d - r) mod n  (injective in d for fixed r);
                 'random' e = T[d, r], a fixed random table (seed 0) with one
                 guaranteed zero per row, non-injective.
  Policy: respond with the repertoire element that best maps the observed
  class to the target e = 0 (lowest outcome index on ties); unserved
  disturbances (over capacity) get no response and fail unless d = 0.
  Failure: outcome != 0 for that disturbance (deadline = the same step).
Measured from the (d, r) log of each run (T = 4000 steps): log2|R| (repertoire
size m), H(R), I(D;R) (plug-in), margin = I(D;R) - H(D).
Units: every (m, eps, c) combination x 3 seeds = 120 regulators per
(table, delay) stratum. Prediction test: binomial logistic models of
per-disturbance failure on (a) I(D;R) - H(D), (b) log2|R| - H(D),
(c) H(R) - H(D); held-out log-loss by 5-fold CV over regulators;
difference (a) - (b) with a bootstrap CI over regulators (2000 reps).
"""
import json, math, platform, sys, time
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression

OUT = Path(__file__).resolve().parent / "raw"
N, K, TSTEPS = 8, 2, 4000
MS, EPS, CAPS, DELAYS, SEEDS = [1, 2, 4, 8], [0, .1, .2, .4, .6], [1, 2], [0, 1, 2, 4], 3

def tables():
    lat = np.array([[(d - r) % N for r in range(N)] for d in range(N)])
    rng = np.random.default_rng(0)
    rnd = rng.integers(1, N, size=(N, N))
    for d in range(N):
        rnd[d, rng.integers(N)] = 0
    return {"latin": lat, "random": rnd}

def H(counts):
    p = counts[counts > 0] / counts.sum(); return float(-(p * np.log2(p)).sum())

def run(table, m, eps, c, delta, seed):
    rng = np.random.default_rng(seed)
    rep = np.random.default_rng(1).permutation(N)[:m]      # fixed repertoire subset
    best = {}                                                # observed class -> response
    for o in range(N):
        outs = table[o, rep]; best[o] = int(rep[np.argmin(outs)])
    hist = []
    joint = np.zeros((N, N + 1)); fails = 0; total = 0
    d = rng.integers(N, size=K)
    for t in range(TSTEPS + delta):
        d = np.where(rng.random(K) < 0.5, d, rng.integers(N, size=K))
        hist.append(d.copy())
        if t < delta:
            continue
        seen = hist[t - delta]
        obs = np.where(rng.random(K) < eps, rng.integers(N, size=K), seen)
        for s in range(K):
            if s < c:
                r = best[int(obs[s])]; e = table[d[s], r]
            else:
                r = N; e = d[s]                               # no response
            joint[d[s], r] += 1; total += 1; fails += e != 0
    hd = H(joint.sum(1)); hr = H(joint.sum(0)); hdr = H(joint.ravel())
    return dict(m=m, eps=eps, c=c, delta=delta, seed=seed, fails=int(fails), n=int(total),
                HD=hd, HR=hr, IDR=hd + hr - hdr, logR=math.log2(m))

def cv_logloss(rows, feat, folds, rng):
    x = np.array([r[feat] for r in rows]).reshape(-1, 1)
    f = np.array([r["fails"] for r in rows]); n = np.array([r["n"] for r in rows])
    per_unit = np.zeros(len(rows))
    for k in range(folds.max() + 1):
        tr, te = folds != k, folds == k
        X = np.vstack([x[tr], x[tr]]); y = np.r_[np.ones(tr.sum()), np.zeros(tr.sum())]
        w = np.r_[f[tr], n[tr] - f[tr]]
        lr = LogisticRegression(C=1e6, max_iter=1000).fit(X, y, sample_weight=w)
        p = np.clip(lr.predict_proba(x[te])[:, 1], 1e-9, 1 - 1e-9)
        per_unit[te] = -(f[te] * np.log(p) + (n[te] - f[te]) * np.log(1 - p))
    return per_unit, n

def main():
    t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True)
    tabs = tables(); allrows = []; summary = []
    for tname, tab in tabs.items():
        for delta in DELAYS:
            rows = [run(tab, m, e, c, delta, 1000 * delta + 100 * MS.index(m) + 10 * EPS.index(e) + c * 3 + s)
                    for m in MS for e in EPS for c in CAPS for s in range(SEEDS)]
            for r in rows:
                r["table"] = tname; r["margin_I"] = r["IDR"] - r["HD"]
                r["margin_logR"] = r["logR"] - r["HD"]; r["margin_HR"] = r["HR"] - r["HD"]
                r["fail_rate"] = r["fails"] / r["n"]
            rng = np.random.default_rng(42)
            folds = rng.permutation(np.arange(len(rows)) % 5)
            ll = {k: cv_logloss(rows, k, folds, rng) for k in ("margin_I", "margin_logR", "margin_HR")}
            n = ll["margin_I"][1]
            d_unit = ll["margin_I"][0] - ll["margin_logR"][0]
            boots = []
            for _ in range(2000):
                idx = rng.integers(0, len(rows), len(rows))
                boots.append(d_unit[idx].sum() / n[idx].sum())
            # slope sign of failure on margin_I (full data, logistic)
            x = np.array([r["margin_I"] for r in rows]); f = np.array([r["fails"] for r in rows]); nn = np.array([r["n"] for r in rows])
            lr = LogisticRegression(C=1e6, max_iter=1000).fit(np.r_[x, x].reshape(-1, 1), np.r_[np.ones(len(x)), np.zeros(len(x))], sample_weight=np.r_[f, nn - f])
            bs = []
            for _ in range(500):
                idx = rng.integers(0, len(rows), len(rows)); xi, fi, ni = x[idx], f[idx], nn[idx]
                bs.append(LogisticRegression(C=1e6, max_iter=1000).fit(np.r_[xi, xi].reshape(-1, 1), np.r_[np.ones(len(xi)), np.zeros(len(xi))], sample_weight=np.r_[fi, ni - fi]).coef_[0, 0])
            s = dict(table=tname, delta=delta, units=len(rows),
                     logloss_per_dist={k: float(v[0].sum() / v[1].sum()) for k, v in ll.items()},
                     diff_I_minus_logR=float(d_unit.sum() / n.sum()),
                     diff_ci95=np.percentile(boots, [2.5, 97.5]).tolist(),
                     slope_margin_I=float(lr.coef_[0, 0]), slope_ci95=np.percentile(bs, [2.5, 97.5]).tolist(),
                     spearman_failrate_marginI=float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(f / nn)))[0, 1]))
            summary.append(s); allrows += rows
            print(json.dumps(s), flush=True)
    env = dict(python=platform.python_version(), numpy=np.__version__, runtime_s=round(time.time() - t0, 1))
    (OUT / "results.json").write_text(json.dumps({"env": env, "summary": summary, "rows": allrows}, indent=1))
    print("runtime_s", env["runtime_s"])

if __name__ == "__main__":
    main()
