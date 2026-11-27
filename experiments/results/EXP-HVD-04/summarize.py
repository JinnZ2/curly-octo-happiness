#!/usr/bin/env python3
"""Summarise raw/rows.json for EXP-HVD-04 -> raw/summary.json + stdout.

Per (sim) and per session length Nt: mean recall on induced pairs, mean
baseline (adjacency rate on control pairs, same run), and the difference,
with a 95% bootstrap CI resampling (sim, subject) units (2000 reps, seed 0).
Only rows that have >= 1 induced pair and >= 1 control pair enter.
"""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
R = Path(__file__).resolve().parent / "raw"
d = json.loads((R / "rows.json").read_text())
rows = [r for r in d["rows"] if r.get("lpcmci") and r["lpcmci"]["baseline"] is not None]
rng = np.random.default_rng(0)

def summ(rs):
    out = {"n_rows": len(rs), "n_units": len({(r["sim"], r["subject"]) for r in rs})}
    units = defaultdict(list)
    for r in rs:
        units[(r["sim"], r["subject"])].append(r)
    keys = list(units)
    for m in ("lpcmci", "pcmciplus"):
        rec = np.array([r[m]["recall"] for r in rs]); base = np.array([r[m]["baseline"] for r in rs])
        bid = np.array([r[m]["bidirected_on_induced"] for r in rs])
        boots = []
        for _ in range(2000):
            pick = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
            sel = [r for k in pick for r in units[k]]
            boots.append(np.mean([r[m]["recall"] - r[m]["baseline"] for r in sel]))
        out[m] = {"recall": float(rec.mean()), "baseline": float(base.mean()),
                  "diff": float((rec - base).mean()), "diff_ci95": np.percentile(boots, [2.5, 97.5]).tolist(),
                  "bidirected_on_induced": float(bid.mean())}
    return out

res = {"by_sim": {}, "by_Nt": {}, "all": summ(rows)}
for s in sorted({r["sim"] for r in rows}):
    rs = [r for r in rows if r["sim"] == s]
    res["by_sim"][s] = {"Nnodes": rs[0]["Nnodes"], "Nt": rs[0]["Nt"], **summ(rs)}
for nt in sorted({r["Nt"] for r in rows}):
    res["by_Nt"][nt] = summ([r for r in rows if r["Nt"] == nt])
res["sims_without_eligible_rows"] = sorted(set(range(1, 29)) - {4} - {r["sim"] for r in rows})
(R / "summary.json").write_text(json.dumps(res, indent=1))
def line(lbl, o):
    print(lbl, o["n_rows"], *(f"{m}: rec={o[m]['recall']:.3f} base={o[m]['baseline']:.3f} diff={o[m]['diff']:+.3f} "
          f"[{o[m]['diff_ci95'][0]:+.3f},{o[m]['diff_ci95'][1]:+.3f}] bid={o[m]['bidirected_on_induced']:.2f}" for m in ("lpcmci", "pcmciplus")))
line("ALL", res["all"])
for k, o in res["by_Nt"].items(): line(f"Nt={k}", o)
for k, o in res["by_sim"].items(): line(f"sim{k} N={o['Nnodes']} Nt={o['Nt']}", o)
print("no eligible rows:", res["sims_without_eligible_rows"])
