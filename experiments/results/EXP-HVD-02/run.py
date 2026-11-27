#!/usr/bin/env python3
"""EXP-HVD-02 run: Type I error of residual-based hidden-confounder detection
under non-latent causes of residual dependence.

Regimes (ground truth known; parameters fixed before running):
  null      VAR(1), no latent, no contemporaneous edge         -> Type I under independence
  hidden    AR(1) latent Z (rho 0.7) drives X1, X2 at lag 0 (loading 0.8) -> power
  instant   no latent; contemporaneous X1 -> X2 (0.8 x X1 innovation)       (i)
  wronglag  no latent; true VAR(2) with X1 -> X2 at lag 2, fitted as VAR(1)  (ii)
  aggregate no latent; fine-scale VAR(1) with X1 -> X2 at lag 1 (0.5),
            observed every k=3 steps                                           (iii)
  shift     no latent; deterministic mean shift +1.0 in X1 and X2 at T/2       (iv)
Dimensions: bivariate (X1, X2) and 5-variable (X1..X5; X3..X5 are AR(1) with
weak lag-1 couplings 0.2 X3->X4, X4->X5). T in {200, 1000}. 1000 reps/cell.

Detectors:
  D1 residual-correlation: OLS VAR(1) with intercept on the observed
     variables; Fisher-z test of the contemporaneous residual correlation.
     Bivariate: one test at alpha=0.05. 5-var: all 10 pairs, Bonferroni,
     "detect" if any pair rejects (family-wise).
  D2 repo HiddenNodeDetector(acceptance="epsilon_machine"), bivariate only.
     Operationalisation (ours; the design did not fix one): the model is the
     VAR(1) fitted to (X1, X2) with nodes ["X1","X2"]; residuals = X2's VAR
     residual; the candidate offered is "C" = the series the detector would
     have to vet in practice: the latent Z in `hidden` (a true confounder),
     and the contemporaneous X1 series in every regime (an observed variable,
     not a latent). "Detect" = C returned as a suggestion; reported separately
     as accepted-by-eps-machine and kept-unverified.
  BiKCD: not run (code availability UNCHECKED).
"""
import json, math, platform, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "modules"))
from hnd import HiddenNodeDetector  # noqa: E402

OUT = Path(__file__).resolve().parent / "raw"
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
REPS_D2 = int(sys.argv[2]) if len(sys.argv) > 2 else 300
ALPHA = 0.05
REGIMES = ["null", "hidden", "instant", "wronglag", "aggregate", "shift"]
BURN = 100

def simulate(regime, T, d, rng):
    k = 3 if regime == "aggregate" else 1
    n = T * k + BURN
    A = np.zeros((d, d)); np.fill_diagonal(A, 0.5)
    A[1, 0] = 0.3                      # X1 -> X2 at lag 1 (all regimes)
    if d == 5:
        A[3, 2] = 0.2; A[4, 3] = 0.2
    if regime == "aggregate":
        A[1, 0] = 0.5
    A2 = np.zeros((d, d))
    if regime == "wronglag":
        A[1, 0] = 0.0; A2[1, 0] = 0.5; A2[1, 1] = 0.2; A[1, 1] = 0.3
    X = np.zeros((n, d)); z = 0.0; Z = np.zeros(n)
    for t in range(2, n):
        e = rng.standard_normal(d)
        z = 0.7 * z + rng.standard_normal()
        Z[t] = z
        if regime == "hidden":
            e[0] += 0.8 * z; e[1] += 0.8 * z
        if regime == "instant":
            e[1] += 0.8 * e[0]
        X[t] = A @ X[t - 1] + A2 @ X[t - 2] + e
    X = X[BURN:]; Z = Z[BURN:]
    if regime == "aggregate":
        X = X[::k]; Z = Z[::k]
    if regime == "shift":
        X[T // 2:, 0] += 1.0; X[T // 2:, 1] += 1.0
    return X[:T], Z[:T]

def var1_resid(X):
    Y = X[1:]; R = np.hstack([np.ones((len(Y), 1)), X[:-1]])
    B, *_ = np.linalg.lstsq(R, Y, rcond=None)
    return Y - R @ B

def fisher_p(r, n):
    r = max(min(r, 0.999999), -0.999999)
    z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(n - 3)
    return math.erfc(abs(z) / math.sqrt(2)), abs(z)

def d1(X):
    E = var1_resid(X); d = X.shape[1]; n = len(E)
    C = np.corrcoef(E.T)
    pairs = [(i, j) for i in range(d) for j in range(i + 1, d)]
    ps = [fisher_p(C[i, j], n) for i, j in pairs]
    m = len(pairs)
    reject = any(p < ALPHA / m for p, _ in ps)
    return reject, max(z for _, z in ps)

def d2(X, Z, regime):
    E = var1_resid(X)
    resid = E[:, 1].tolist()
    out = {}
    cands = {"X1_now": X[1:, 0].tolist()}
    if regime == "hidden":
        cands["Z_now"] = Z[1:].tolist()
    for name, series in cands.items():
        det = HiddenNodeDetector({"nodes": ["X1", "X2"], "dependencies": {"X1": ["X2"]},
                                  "predicted_outputs": []},
                                 {"variables": {}, "time_series": {"C": series}})
        sugg = det.scan(resid, threshold=0.1, acceptance="epsilon_machine")
        kept = any(s.name == "C" for s in sugg)
        unver = any(s.name == "C" for s in det.unverified)
        out[name] = {"returned": kept, "unverified": unver, "accepted": kept and not unver}
    return out

def wilson(k, n, z=1.96):
    if n == 0:
        return [float("nan")] * 2
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [c - h, c + h]

def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    allv = np.concatenate([pos, neg]); r = allv.argsort().argsort() + 1.0
    # average ranks for ties
    from scipy.stats import rankdata
    r = rankdata(allv)
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))

def main():
    t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True)
    res = {"env": dict(python=platform.python_version(), numpy=np.__version__,
                       reps=REPS, reps_d2=REPS_D2, alpha=ALPHA), "d1": {}, "d2": {}, "roc": {}}
    stats = {}
    for d in (2, 5):
        for T in (200, 1000):
            for ri, reg in enumerate(REGIMES):
                rng = np.random.default_rng(10_000 * d + 10 * T + ri)
                rej = 0; zs = []
                for _ in range(REPS):
                    X, Z = simulate(reg, T, d, rng)
                    r, z = d1(X); rej += r; zs.append(z)
                key = f"d{d}_T{T}_{reg}"
                res["d1"][key] = {"rate": rej / REPS, "wilson95": wilson(rej, REPS), "k": rej}
                stats[key] = zs
                print("D1", key, rej / REPS, flush=True)
            for reg in REGIMES:
                if reg in ("hidden",):
                    continue
                res["roc"][f"d{d}_T{T}_hidden_vs_{reg}"] = auc(stats[f"d{d}_T{T}_hidden"], stats[f"d{d}_T{T}_{reg}"])
    for T in (200, 1000):
        for ri, reg in enumerate(REGIMES):
            rng = np.random.default_rng(777_000 + 10 * T + ri)
            tally = {}
            for _ in range(REPS_D2):
                X, Z = simulate(reg, T, 2, rng)
                for cand, o in d2(X, Z, reg).items():
                    t = tally.setdefault(cand, {"returned": 0, "unverified": 0, "accepted": 0})
                    for kk in t:
                        t[kk] += o[kk]
            for cand, t in tally.items():
                key = f"T{T}_{reg}_{cand}"
                res["d2"][key] = {kk: {"rate": v / REPS_D2, "wilson95": wilson(v, REPS_D2)} for kk, v in t.items()}
                print("D2", key, {kk: v / REPS_D2 for kk, v in t.items()}, flush=True)
    res["env"]["runtime_s"] = round(time.time() - t0, 1)
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
    print("runtime_s", res["env"]["runtime_s"])

if __name__ == "__main__":
    main()
