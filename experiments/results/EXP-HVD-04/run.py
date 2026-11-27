#!/usr/bin/env python3
"""EXP-HVD-04 PILOT: hide a common-parent node in NetSim BOLD simulations and
ask whether the induced latent-confounded pairs are recovered above a
density-matched baseline.

Data: NetSim sims 1-28 (Smith et al. 2011), fmrib.ox.ac.uk/datasets/netsim,
sims.tar.gz sha256 recorded in results. net[s, i, j] != 0 read as i -> j
(row -> column; consistent with sim1's documented 1->2->3->4->5, 1->5 chain).
For each sim and each node k with >= 2 children ("eligible"), drop k and run:
  LPCMCI and PCMCI+ (tigramite 5.2.10.1), ParCorr, tau_max = 1, pc_alpha = 0.01
  on each subject's series (subjects 0..S-1).
Induced pairs: children pairs (i, j) of k that are not directly connected.
Control pairs: pairs not directly connected in the true network and not
  both neighbours of k (no edge can be induced by removing k).
Recall = fraction of induced pairs output as adjacent (any lag <= tau_max,
any mark); baseline = same fraction on control pairs, same run.
PILOT deviations: S = 10 of 50 subjects; sim4 (50 nodes) excluded for runtime;
sims with a node-specific net (sim13 differs by subject) use each subject's net.
"""
import json, platform, sys, time, warnings
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import scipy.io as sio
warnings.filterwarnings("ignore")
from tigramite import data_processing as pp
from tigramite.pcmci import PCMCI
from tigramite.lpcmci import LPCMCI
from tigramite.independence_tests.parcorr import ParCorr

D = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/netsim")
S = int(sys.argv[2]) if len(sys.argv) > 2 else 10
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 2
OUT = Path(__file__).resolve().parent / "raw"
TAU, ALPHA = 1, 0.01
SKIP = {4}

def adj(g, i, j):
    return bool(g[i, j, :].any() or g[j, i, :].any())

def job(args):
    sim, s, k = args
    m = sio.loadmat(D / f"sim{sim}.mat")
    Nn, Nt = int(m["Nnodes"][0][0]), int(m["Ntimepoints"][0][0])
    A = (m["net"][s] != 0).astype(int); np.fill_diagonal(A, 0)
    keep = [v for v in range(Nn) if v != k]; idx = {v: a for a, v in enumerate(keep)}
    X = m["ts"][s * Nt:(s + 1) * Nt][:, keep]
    ch = [v for v in range(Nn) if A[k, v]]
    und = (A + A.T) > 0
    induced = [(a, b) for a in ch for b in ch if a < b and not und[a, b]]
    nb = set(np.where(und[k])[0])
    control = [(a, b) for a in keep for b in keep if a < b and not und[a, b] and not (a in nb and b in nb)]
    out = {"sim": sim, "subject": s, "k": k, "Nnodes": Nn, "Nt": Nt,
           "n_induced": len(induced), "n_control": len(control)}
    if not induced:
        return out
    df = pp.DataFrame(X)
    for name in ("lpcmci", "pcmciplus"):
        t0 = time.time()
        if name == "lpcmci":
            g = LPCMCI(dataframe=df, cond_ind_test=ParCorr(), verbosity=0).run_lpcmci(tau_max=TAU, pc_alpha=ALPHA)["graph"]
        else:
            g = PCMCI(dataframe=df, cond_ind_test=ParCorr(), verbosity=0).run_pcmciplus(tau_min=0, tau_max=TAU, pc_alpha=ALPHA)["graph"]
        out[name] = {"recall": float(np.mean([adj(g, idx[a], idx[b]) for a, b in induced])),
                     "baseline": float(np.mean([adj(g, idx[a], idx[b]) for a, b in control])) if control else None,
                     "bidirected_on_induced": float(np.mean([("<->" in (list(g[idx[a], idx[b], :]) + list(g[idx[b], idx[a], :]))) for a, b in induced])),
                     "runtime_s": round(time.time() - t0, 2)}
    return out

def main():
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    jobs = []
    for sim in range(1, 29):
        if sim in SKIP:
            continue
        m = sio.loadmat(D / f"sim{sim}.mat"); Nn = int(m["Nnodes"][0][0])
        for s in range(S):
            A = (m["net"][s] != 0).astype(int); np.fill_diagonal(A, 0)
            for k in range(Nn):
                if A[k].sum() >= 2:
                    jobs.append((sim, s, k))
    rows = []
    with Pool(WORKERS) as p:
        for i, r in enumerate(p.imap_unordered(job, jobs)):
            rows.append(r)
            if i % 25 == 0:
                print(i, len(jobs), round(time.time() - t0), flush=True)
    env = dict(python=platform.python_version(), numpy=np.__version__, tigramite="5.2.10.1",
               subjects=S, skipped_sims=sorted(SKIP), runtime_s=round(time.time() - t0, 1))
    (OUT / "rows.json").write_text(json.dumps({"env": env, "rows": rows}, indent=1))
    print("runtime_s", env["runtime_s"])

if __name__ == "__main__":
    main()
