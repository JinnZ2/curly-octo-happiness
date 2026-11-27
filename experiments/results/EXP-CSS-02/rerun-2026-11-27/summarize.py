#!/usr/bin/env python3
"""Summarise raw/rows.json -> raw/summary.json + stdout table, with the original
EXP-CSS-02 numbers (../raw/summary.json, the pre-fix estimator) alongside.
Tolerance definition identical to ../summarize.py: |dC| <= 0.05 and |dh| <= 0.02."""
import json, statistics as st
from pathlib import Path
H = Path(__file__).resolve().parent
d = json.loads((H / "raw" / "rows.json").read_text()); A = d["env"]["analytic"]
old = {(o["proc"], o["T"], o["L"]): o for o in json.loads((H.parent / "raw" / "summary.json").read_text())}
out = []
for proc in A:
    for T in (1000, 10000, 100000):
        for L in range(2, 11):
            rs = [r for r in d["rows"] if r["proc"] == proc and r["T"] == T and r["L"] == L]
            o = dict(proc=proc, T=T, L=L, n=len(rs))
            for arm, kc, kh, ks in (("tv", "C_tv", "h_tv", "states_tv"), ("chi2", "C_hat", "h_hat", "states")):
                eC = [r[kc] - A[proc]["C"] for r in rs]; eh = [r[kh] - A[proc]["h"] for r in rs]
                o[arm] = dict(C_err_mean=st.mean(eC), C_err_sd=st.pstdev(eC), h_err_mean=st.mean(eh),
                              h_err_sd=st.pstdev(eh),
                              frac_within_tol=sum(abs(c) <= 0.05 and abs(h) <= 0.02 for c, h in zip(eC, eh)) / len(rs),
                              states_median=st.median(r[ks] for r in rs))
            p = old[(proc, T, L)]
            o["old"] = {k: p[k] for k in ("C_err_mean", "C_err_sd", "h_err_mean", "frac_within_tol", "states_median")}
            out.append(o)
(H / "raw" / "summary.json").write_text(json.dumps(out, indent=1))
print("proc         T      L  | old: dC     ok   st | chi2+III (shipped): dC ok st | tv+III: dC ok st")
for o in out:
    if o["L"] in (2, 3, 5, 10):
        a, b, c = o["old"], o["chi2"], o["tv"]
        print(f"{o['proc']:12s} {o['T']:<6d} {o['L']:<2d} | {a['C_err_mean']:+.3f} {a['frac_within_tol']:.2f} {a['states_median']:>4} "
              f"| {b['C_err_mean']:+.3f} {b['frac_within_tol']:.2f} {b['states_median']:>4} "
              f"| {c['C_err_mean']:+.3f} {c['frac_within_tol']:.2f} {c['states_median']:>4}")
