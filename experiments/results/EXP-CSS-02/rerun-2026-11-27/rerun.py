#!/usr/bin/env python3
"""EXP-CSS-02 rerun (2026-11-27) after adding CSSR Phase III to reconstruct().

Same pre-registered grid, processes, seeds and analytic values as ../run.py
(imported from it, not copied): 5 processes x T in {1e3,1e4,1e5} x L in 2..10
x 50 seeds. Two estimator arms, both from grounding.core.epsilon_machine.reconstruct on
branch fix/cssr-determinisation:

  chi2 (C_hat, h_hat, states)   the shipped default: CSSR Phase II with a
        chi-squared homogeneity test, parent state first (Shalizi & Shalizi
        2004, Fig. 1; alpha = 1e-3 as in their experiments), then Phase III
        (transient removal + determinisation).
  tv (C_tv, h_tv, states_tv)    reconstruct(..., test="tv"): the old fixed
        total-variation 0.2 merge rule followed by the same Phase III.

The pre-fix estimator's numbers are ../raw/summary.json (not recomputed).

Usage: python3 rerun.py [seeds=50] [workers=3]
"""
import json, math, platform, sys, time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import run as base                                       # noqa: E402  (../run.py)
from grounding.core.epsilon_machine import reconstruct  # noqa: E402

def job(args):
    proc, T, seed = args
    rng = base.random.Random(1_000_003 * seed + 97 * T + len(proc))   # identical to ../run.py
    seq = base.gen(proc, T + 100, rng)[100:]
    rows = []
    for L in base.LS:
        m = reconstruct(seq, max_history=L)                 # shipped default: chi2 + Phase III
        t = reconstruct(seq, max_history=L, test="tv")      # comparison: TV 0.2 + Phase III
        rows.append({"proc": proc, "T": T, "seed": seed, "L": L,
                     "C_hat": m.statistical_complexity, "h_hat": m.entropy_rate, "states": m.n_states,
                     "C_tv": t.statistical_complexity, "h_tv": t.entropy_rate, "states_tv": t.n_states})
    return rows

def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    t0 = time.time(); (HERE / "raw").mkdir(exist_ok=True)
    jobs = [(p, T, s) for p in base.ANALYTIC for T in base.TS for s in range(seeds)]
    rows = []
    with Pool(workers) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=4)):
            rows.extend(r)
            if i % 50 == 0:
                print(i, len(jobs), round(time.time() - t0), flush=True)
    env = dict(python=platform.python_version(), seeds=seeds, workers=workers, alpha_chi2=0.001,
               analytic={k: {"h": v[0], "C": v[1]} for k, v in base.ANALYTIC.items()},
               runtime_s=round(time.time() - t0, 1))
    (HERE / "raw" / "rows.json").write_text(json.dumps({"env": env, "rows": rows}))
    print("runtime_s", env["runtime_s"])

if __name__ == "__main__":
    main()
