#!/usr/bin/env python3
"""Summarise raw/rows.json for EXP-CSS-02 -> raw/summary.json + stdout table."""
import json, statistics as st
from pathlib import Path
R = Path(__file__).resolve().parent / "raw"
d = json.loads((R / "rows.json").read_text()); A = d["env"]["analytic"]
out = []
for proc in A:
    for T in (1000, 10000, 100000):
        for L in range(2, 11):
            rs = [r for r in d["rows"] if r["proc"] == proc and r["T"] == T and r["L"] == L]
            eC = [r["C_hat"] - A[proc]["C"] for r in rs]; eh = [r["h_hat"] - A[proc]["h"] for r in rs]
            eb = [r["block_h"] - A[proc]["h"] for r in rs]
            ok = [abs(c) <= 0.05 and abs(h) <= 0.02 for c, h in zip(eC, eh)]
            out.append(dict(proc=proc, T=T, L=L, n=len(rs),
                            C_err_mean=st.mean(eC), C_err_sd=st.pstdev(eC),
                            h_err_mean=st.mean(eh), h_err_sd=st.pstdev(eh),
                            block_h_err_mean=st.mean(eb),
                            frac_within_tol=sum(ok) / len(ok),
                            states_median=st.median(r["states"] for r in rs)))
(R / "summary.json").write_text(json.dumps(out, indent=1))
for o in out:
    if o["L"] in (2, 3, 5, 10):
        print(f"{o['proc']:12s} T={o['T']:<6d} L={o['L']:<2d} dC={o['C_err_mean']:+.3f}±{o['C_err_sd']:.3f} "
              f"dh={o['h_err_mean']:+.3f}±{o['h_err_sd']:.3f} blk_dh={o['block_h_err_mean']:+.3f} "
              f"ok={o['frac_within_tol']:.2f} states={o['states_median']}")
