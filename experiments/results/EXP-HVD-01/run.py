#!/usr/bin/env python3
"""EXP-HVD-01 PILOT: reduced grid, linear-Gaussian only, H2 only.

Generator (fixed before running): 5 observed series X0..X4 plus one latent L.
  X_i,t = a X_i,t-1 + (observed links) + noise,  noise N(0,1)
  observed links: X0 -> X1 lag 1 (0.4), X2 -> X4 lag 1 (0.4)
  latent L_t = rho_Z L_t-1 + N(0,1), rho_Z = 0.5 (fixed in the reduced grid)
  L -> X1 at lag 0 (0.7) and L -> X3 at lag `lag` (0.7)
  induced latent-confounded pair: X1(t-lag) <-> X3(t)
Grid: a in {0.2, 0.5, 0.8, 0.95} x lag in {0, 1, 2} x T in {200, 1000, 5000}.
Methods (tigramite): LPCMCI (latent-aware), PCMCI+ (assumes no latents).
  ParCorr, tau_max = 3, pc_alpha = 0.01 (fixed; no tuning).
Metrics on the induced pair: adjacency recall (any mark), and for LPCMCI
bidirected recall ('<->'). False-positive rate on truly non-adjacent pairs
with no latent path, for context.
"""
import json, platform, sys, time, warnings
from multiprocessing import Pool
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
from tigramite import data_processing as pp
from tigramite.pcmci import PCMCI
from tigramite.lpcmci import LPCMCI
from tigramite.independence_tests.parcorr import ParCorr
import tigramite

OUT = Path(__file__).resolve().parent / "raw"
TAU_MAX, ALPHA = 3, 0.01
AS, LAGS, TS = [0.2, 0.5, 0.8, 0.95], [0, 1, 2], [200, 1000, 5000]

def gen(a, lag, T, rng, rho=0.5):
    n = T + 200
    X = np.zeros((n, 5)); L = np.zeros(n)
    for t in range(3, n):
        L[t] = rho * L[t - 1] + rng.standard_normal()
        e = rng.standard_normal(5)
        x = a * X[t - 1] + e
        x[1] += 0.4 * X[t - 1, 0] + 0.7 * L[t]
        x[4] += 0.4 * X[t - 1, 2]
        x[3] += 0.7 * L[t - lag]
        X[t] = x
    return X[200:]

def mark(graph, i, j, tau):
    """Edge mark between X_i(t-tau) and X_j(t) in tigramite's graph array."""
    return graph[i, j, tau] if tau > 0 else (graph[i, j, 0] or graph[j, i, 0])

def job(args):
    a, lag, T, seed = args
    rng = np.random.default_rng(seed * 7919 + int(a * 100) * 31 + lag * 7 + T)
    X = gen(a, lag, T, rng)
    df = pp.DataFrame(X)
    out = {"a": a, "lag": lag, "T": T, "seed": seed}
    # non-adjacent pairs without latent path (X0,X2),(X0,X4),(X2,X3)? X3 is linked to X1 via L only
    null_pairs = [(0, 2), (0, 3), (2, 3), (0, 4), (2, 1), (4, 3)]
    for name in ("lpcmci", "pcmciplus"):
        t0 = time.time()
        if name == "lpcmci":
            res = LPCMCI(dataframe=df, cond_ind_test=ParCorr(), verbosity=0).run_lpcmci(tau_max=TAU_MAX, pc_alpha=ALPHA)
        else:
            res = PCMCI(dataframe=df, cond_ind_test=ParCorr(), verbosity=0).run_pcmciplus(tau_min=0, tau_max=TAU_MAX, pc_alpha=ALPHA)
        g = res["graph"]
        m = mark(g, 1, 3, lag) if lag > 0 else (g[1, 3, 0] if g[1, 3, 0] else g[3, 1, 0])
        fp, tot = 0, 0
        for i, j in null_pairs:
            for tau in range(0, TAU_MAX + 1):
                if tau == 0 and i > j:
                    continue
                tot += 1; fp += bool(g[i, j, tau]) or (tau == 0 and bool(g[j, i, 0]))
        out[name] = {"mark": str(m), "adj": bool(m), "bidirected": m == "<->",
                     "fpr": fp / tot, "runtime_s": round(time.time() - t0, 2)}
    return out

def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    jobs = [(a, lag, T, s) for T in TS for a in AS for lag in LAGS for s in range(seeds)]
    rows = []
    with Pool(workers) as p:
        for i, r in enumerate(p.imap_unordered(job, jobs)):
            rows.append(r)
            if i % 20 == 0:
                print(i, len(jobs), round(time.time() - t0), flush=True)
    env = dict(python=platform.python_version(), numpy=np.__version__, tigramite="5.2.10.1",
               seeds=seeds, runtime_s=round(time.time() - t0, 1))
    (OUT / "rows.json").write_text(json.dumps({"env": env, "rows": rows}, indent=1))
    print("runtime_s", env["runtime_s"])

if __name__ == "__main__":
    main()
