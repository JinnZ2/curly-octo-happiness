#!/usr/bin/env python3
"""EXP-CSS-02 run: does grounding.core.epsilon_machine.reconstruct() recover
known h_mu and C_mu?

Processes (binary unless noted), analytic values:
  biased_coin  P(1)=0.3              h = H(0.3),        C = 0
  period3      ...001001... random phase   h = 0,       C = log2 3
  golden_mean  no two 1s in a row    h = 2/3,           C = H(2/3,1/3)
  even         1s in even blocks     h = 2/3,           C = H(2/3,1/3)
  sns          simple nonunifilar source (hidden A/B, see below); values
               computed numerically here from its mixed-state recursion
               (countably infinite causal states n = #1s since last 0).
Grid: T in {1e3, 1e4, 1e5} x L in {2..10} x 50 seeds (pre-registered).
Primary L for the pre-registered tolerance check: L = 2, the library default
used by HiddenNodeDetector (the design said "L chosen by
equalized_history_length", which for a single stream returns the base L).
Baseline: plug-in block-entropy h(L) = H(L) - H(L-1) (from the sketch).
"""
import json, math, platform, random, sys, time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from grounding.core.epsilon_machine import reconstruct  # noqa: E402

OUT = Path(__file__).resolve().parent / "raw"
TS = [1000, 10000, 100000]
LS = list(range(2, 11))
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 50
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 2

def H(ps):
    return -sum(p * math.log2(p) for p in ps if p > 0)

def sns_analytic(nmax=2000):
    """SNS: from A emit 1 -> A or B (1/2 each); from B emit 1 -> B (1/2) or
    emit 0 -> A (1/2). After a 0 the process is in A. Mixed state after n 1s
    since the last 0: P(B | n) = b_n; causal state n. Exact up to truncation."""
    # P(A)=a, P(B)=1-a after n ones. Start n=0: a=1.
    a = 1.0
    probs_next1, a_list = [], []
    for n in range(nmax):
        a_list.append(a)
        p1 = a * 1.0 + (1 - a) * 0.5          # A always emits 1; B emits 1 w.p. 1/2
        probs_next1.append(p1)
        # update on seeing 1: A->A 1/2, A->B 1/2 ; B->B (via 1) 1/2
        na = a * 0.5
        nb = a * 0.5 + (1 - a) * 0.5
        a = na / (na + nb)
    # stationary distribution over n: pi_n proportional to prod_{k<n} p1_k
    w, cur = [], 1.0
    for n in range(nmax):
        w.append(cur); cur *= probs_next1[n]
    Z = sum(w); pi = [x / Z for x in w]
    C = H(pi)
    h = sum(pi[n] * H([probs_next1[n], 1 - probs_next1[n]]) for n in range(nmax))
    return h, C

GM_C = H([2 / 3, 1 / 3])
SNS_H, SNS_C = sns_analytic()
ANALYTIC = {"biased_coin": (H([0.3, 0.7]), 0.0), "period3": (0.0, math.log2(3)),
            "golden_mean": (2 / 3, GM_C), "even": (2 / 3, GM_C), "sns": (SNS_H, SNS_C)}

def gen(proc, n, rng):
    out = []
    if proc == "biased_coin":
        return [1 if rng.random() < 0.3 else 0 for _ in range(n)]
    if proc == "period3":
        ph = rng.randrange(3)
        return [1 if (i + ph) % 3 == 2 else 0 for i in range(n)]
    s = "A"
    for _ in range(n):
        if proc == "golden_mean":
            if s == "A":
                b = rng.randint(0, 1); s = "B" if b else "A"
            else:
                b, s = 0, "A"
        elif proc == "even":
            if s == "A":
                b = rng.randint(0, 1); s = "B" if b else "A"
            else:
                b, s = 1, "A"
        else:  # sns
            if s == "A":
                b = 1; s = "A" if rng.random() < 0.5 else "B"
            else:
                if rng.random() < 0.5:
                    b, s = 1, "B"
                else:
                    b, s = 0, "A"
        out.append(b)
    # burn-in: drop first 100 symbols (process starts in a fixed state)
    return out

def block_h(seq, L):
    def BH(L):
        if L == 0:
            return 0.0
        c = Counter(tuple(seq[i:i + L]) for i in range(len(seq) - L + 1))
        n = sum(c.values())
        return -sum(v / n * math.log2(v / n) for v in c.values())
    return BH(L) - BH(L - 1)

def job(args):
    proc, T, seed = args
    rng = random.Random(hash((proc, T, seed)) & 0xFFFFFFFF if False else (1_000_003 * seed + 97 * T + len(proc)))
    seq = gen(proc, T + 100, rng)[100:]
    rows = []
    for L in LS:
        m = reconstruct(seq, max_history=L)
        rows.append({"proc": proc, "T": T, "seed": seed, "L": L,
                     "C_hat": m.statistical_complexity, "h_hat": m.entropy_rate,
                     "states": m.n_states, "block_h": block_h(seq, L)})
    return rows

def main():
    t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(p, T, s) for p in ANALYTIC for T in TS for s in range(SEEDS)]
    rows = []
    with Pool(WORKERS) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=4)):
            rows.extend(r)
            if i % 50 == 0:
                print(i, len(jobs), round(time.time() - t0), flush=True)
    env = dict(python=platform.python_version(), seeds=SEEDS, workers=WORKERS,
               analytic={k: {"h": v[0], "C": v[1]} for k, v in ANALYTIC.items()},
               runtime_s=round(time.time() - t0, 1))
    (OUT / "rows.json").write_text(json.dumps({"env": env, "rows": rows}))
    print("runtime_s", env["runtime_s"], "analytic", env["analytic"])

if __name__ == "__main__":
    main()
