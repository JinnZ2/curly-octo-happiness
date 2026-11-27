#!/usr/bin/env python3
"""Summarise raw/rows.json for the EXP-HVD-01 PILOT -> raw/summary.json + stdout.

H2 contrast per method: recall(lag 0) - recall(lag in {1,2}) on the induced
latent-confounded pair, pooled over a and T, and per (a, T) cell. CI: 95%
bootstrap (2000 reps, seed 0) resampling seeds within each (a, lag, T) cell.
"""
import json
from pathlib import Path
import numpy as np
R = Path(__file__).resolve().parent / "raw"
d = json.loads((R / "rows.json").read_text()); rows = d["rows"]
AS, LAGS, TS = [0.2, 0.5, 0.8, 0.95], [0, 1, 2], [200, 1000, 5000]
M = ("lpcmci", "pcmciplus"); rng = np.random.default_rng(0)
cell = {(a, l, T): [r for r in rows if r["a"] == a and r["lag"] == l and r["T"] == T] for a in AS for l in LAGS for T in TS}

def rate(rs, m, key="adj"):
    return float(np.mean([r[m][key] for r in rs])) if rs else float("nan")

def contrast(keys0, keys1, m, key="adj"):
    pt = np.mean([rate(cell[k], m, key) for k in keys0]) - np.mean([rate(cell[k], m, key) for k in keys1])
    bs = []
    for _ in range(2000):
        def rs(k):
            c = cell[k]; return [c[i] for i in rng.integers(0, len(c), len(c))]
        bs.append(np.mean([rate(rs(k), m, key) for k in keys0]) - np.mean([rate(rs(k), m, key) for k in keys1]))
    return {"diff": float(pt), "ci95": np.percentile(bs, [2.5, 97.5]).tolist()}

out = {"env": d["env"], "cells": {}, "h2_pooled": {}, "h2_by_aT": {}, "fpr": {}}
for (a, l, T), rs in cell.items():
    out["cells"][f"a{a}_lag{l}_T{T}"] = {m: {"adj_recall": rate(rs, m), "bidirected": rate(rs, m, "bidirected"),
                                             "fpr": rate(rs, m, "fpr")} for m in M} | {"n": len(rs)}
k0 = [(a, 0, T) for a in AS for T in TS]; k12 = [(a, l, T) for a in AS for l in (1, 2) for T in TS]
for m in M:
    out["h2_pooled"][m] = {"adj": contrast(k0, k12, m), "lag0": float(np.mean([rate(cell[k], m) for k in k0])),
                           "lag1": float(np.mean([rate(cell[(a, 1, T)], m) for a in AS for T in TS])),
                           "lag2": float(np.mean([rate(cell[(a, 2, T)], m) for a in AS for T in TS]))}
    out["fpr"][m] = float(np.mean([r[m]["fpr"] for r in rows]))
    for a in AS:
        for T in TS:
            out["h2_by_aT"][f"{m}_a{a}_T{T}"] = contrast([(a, 0, T)], [(a, 1, T), (a, 2, T)], m)
out["h2_pooled"]["lpcmci_bidirected"] = contrast(k0, k12, "lpcmci", "bidirected")
(R / "summary.json").write_text(json.dumps(out, indent=1))
for m in M:
    h = out["h2_pooled"][m]
    print(m, "lag0/1/2 recall", round(h["lag0"], 3), round(h["lag1"], 3), round(h["lag2"], 3),
          "diff(0 - {1,2})", round(h["adj"]["diff"], 3), [round(x, 3) for x in h["adj"]["ci95"]], "fpr", round(out["fpr"][m], 4))
print("lpcmci bidirected diff", out["h2_pooled"]["lpcmci_bidirected"])
print("cell table (adj recall lpcmci | pcmciplus; lpcmci <->):")
for T in TS:
    for a in AS:
        print(f"T={T} a={a}", " ".join(f"lag{l}: {out['cells'][f'a{a}_lag{l}_T{T}']['lpcmci']['adj_recall']:.2f}|"
              f"{out['cells'][f'a{a}_lag{l}_T{T}']['pcmciplus']['adj_recall']:.2f} ({out['cells'][f'a{a}_lag{l}_T{T}']['lpcmci']['bidirected']:.2f})" for l in LAGS),
              " d_lpc", round(out["h2_by_aT"][f"lpcmci_a{a}_T{T}"]["diff"], 2), " d_pc+", round(out["h2_by_aT"][f"pcmciplus_a{a}_T{T}"]["diff"], 2))
