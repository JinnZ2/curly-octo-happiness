#!/usr/bin/env python3
"""EXP-RVC-05 run: pre- vs post-publication Sharpe ratios of published equity
factors (Kenneth French data library), and power for a 17-year live record.

Inputs: unzipped French CSVs in argv[1] (default /tmp/ff):
  F-F_Research_Data_5_Factors_2x3.csv (SMB, HML, RMW, CMA; from 1963-07)
  F-F_Momentum_Factor.csv, F-F_ST_Reversal_Factor.csv, F-F_LT_Reversal_Factor.csv
Monthly returns only (the annual blocks in each file are ignored).

Publication dates (year-month of the original journal publication; entered
from memory, NOT verified against the journals; alternatives as sensitivity):
  SMB   Banz (1981, JFE)                         1981-03
  HML   Rosenberg, Reid & Lanstein (1985, JPM)   1985-04   alt Fama-French (1992, JF) 1992-06
  Mom   Jegadeesh & Titman (1993, JF)            1993-03
  RMW   Novy-Marx (2013, JFE)                    2013-04   alt Fama-French (2015, JFE) 2015-04
  CMA   Titman, Wei & Xie (2004, JFQA)           2004-12   alt Fama-French (2015, JFE) 2015-04
  STRev Jegadeesh (1990, JF)                     1990-07
  LTRev De Bondt & Thaler (1985, JF)             1985-07
Pre-sample = first available month to the month before publication;
post-sample = publication month to the last month in the file.

SR inference: annualised SR = sqrt(12) * mean/sd of monthly returns.
SE: delta method, iid-normal (Lo 2002 iid case) and a Newey-West (q=12)
version; the HAC one is used for tests (see sr_se). Difference test: the two SRs come from
disjoint periods, so they are treated as independent:
z = (SR_post - SR_pre) / sqrt(SE_pre^2 + SE_post^2).
(Deviation: the design named Jobson-Korkie-Memmel, which is for two return
series on the same dates; it does not apply to a split-sample comparison.)
Decay ratio SR_post/SR_pre with a stationary block bootstrap CI
(mean block 12 months, 5000 reps, seed 0), resampling each period separately.
"""
import csv, json, math, platform, sys, time
from pathlib import Path
import numpy as np

D = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ff")
OUT = Path(__file__).resolve().parent / "raw"
PUB = {"SMB": ["1981-03"], "HML": ["1985-04", "1992-06"], "Mom": ["1993-03"],
       "RMW": ["2013-04", "2015-04"], "CMA": ["2004-12", "2015-04"],
       "ST_Rev": ["1990-07"], "LT_Rev": ["1985-07"]}

def read_monthly(fname):
    """First block of YYYYMM rows after the first header line (monthly data)."""
    header, data = None, {}
    for r in csv.reader(open(D / fname, encoding="latin-1")):
        r = [c.strip() for c in r]
        if header is None:
            if len(r) > 1 and r[0] == "" and any(c for c in r[1:]):
                header = r[1:]
            continue
        if r and r[0].isdigit() and len(r[0]) == 6:
            data[f"{r[0][:4]}-{r[0][4:]}"] = {h: float(v) for h, v in zip(header, r[1:])
                                               if v not in ("", "-99.99", "-999")}
        elif data:
            break
    return data

def sr_se(x, q=12):
    """Annualised SR and two SEs for it (delta method on the monthly SR):
    iid-normal  Var = (1 + SR_m^2/2) / n           (Lo 2002, iid case)
    HAC         Var = (LRV/s^2 + SR_m^2/2) / n,   LRV Newey-West, Bartlett, q lags
    The HAC form keeps the iid kurtosis-free second term; it corrects the
    mean's variance for autocorrelation only."""
    x = np.asarray(x, float); n = len(x); s2 = x.var(ddof=1); srm = x.mean() / math.sqrt(s2)
    xc = x - x.mean()
    lrv = s2 * (n - 1) / n + 2 * sum((1 - k / (q + 1)) * (xc[:-k] @ xc[k:]) / n for k in range(1, q + 1))
    se_iid = math.sqrt((1 + 0.5 * srm ** 2) / n)
    se_hac = math.sqrt((max(lrv, 0) / s2 + 0.5 * srm ** 2) / n)
    return srm * math.sqrt(12), se_iid * math.sqrt(12), se_hac * math.sqrt(12)

def stat_boot(x, rng, reps, block=12):
    n = len(x); p = 1 / block; out = np.empty(reps)
    for b in range(reps):
        idx = np.empty(n, int); i = rng.integers(n)
        for t in range(n):
            if t and rng.random() < p:
                i = rng.integers(n)
            else:
                i = (i + 1) % n if t else i
            idx[t] = i
        s = x[idx]; out[b] = s.mean() / s.std(ddof=1) * math.sqrt(12)
    return out

def main():
    t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True)
    series = {}
    ff5 = read_monthly("F-F_Research_Data_5_Factors_2x3.csv")
    for f in ("SMB", "HML", "RMW", "CMA"):
        series[f] = {k: v[f] for k, v in ff5.items() if f in v}
    for fname, col in [("F-F_Momentum_Factor.csv", "Mom"), ("F-F_ST_Reversal_Factor.csv", "ST_Rev"),
                       ("F-F_LT_Reversal_Factor.csv", "LT_Rev")]:
        m = read_monthly(fname)
        key = next(iter(next(iter(m.values())).keys()))
        series[col] = {k: v[key] for k, v in m.items()}
    rng = np.random.default_rng(0)
    res = {"env": dict(python=platform.python_version(), numpy=np.__version__), "factors": []}
    for f, dates in PUB.items():
        s = series[f]; months = sorted(s)
        for j, pub in enumerate(dates):
            pre = np.array([s[m] for m in months if m < pub]); post = np.array([s[m] for m in months if m >= pub])
            sr1, se1, h1 = sr_se(pre); sr2, se2, h2 = sr_se(post)
            z = (sr2 - sr1) / math.sqrt(h1 ** 2 + h2 ** 2)
            b1 = stat_boot(pre, rng, 2000); b2 = stat_boot(post, rng, 2000)
            ratio = b2 / np.where(np.abs(b1) < 1e-9, np.nan, b1)
            rec = dict(factor=f, pub=pub, primary=(j == 0), start=months[0], end=months[-1],
                       n_pre=len(pre), n_post=len(post), sr_pre=sr1, se_pre_iid=se1, se_pre_hac=h1,
                       sr_post=sr2, se_post_iid=se2, se_post_hac=h2, diff=sr2 - sr1,
                       diff_ci95=[sr2 - sr1 - 1.96 * math.sqrt(h1**2 + h2**2), sr2 - sr1 + 1.96 * math.sqrt(h1**2 + h2**2)],
                       z=z, p_one_sided_decay=0.5 * math.erfc(-z / math.sqrt(2)),
                       ratio=sr2 / sr1 if sr1 else None,
                       ratio_boot_ci95=np.nanpercentile(ratio, [2.5, 97.5]).tolist(),
                       diff_boot_ci95=np.percentile(b2 - b1, [2.5, 97.5]).tolist())
            res["factors"].append(rec)
            print(f, pub, f"pre {sr1:.2f}±{h1:.2f} (n={len(pre)})  post {sr2:.2f}±{h2:.2f} (n={len(post)})  diff {sr2-sr1:+.2f}  z={z:.2f}", flush=True)
    # live index: reported summary statistics only (returns not public)
    reported = [
        {"source": "López de Prado (2023), Causal Factor Investing (CUP Element)", "start": "2007-05-02", "end": "2022-12-02", "sr": 0.29, "t": 1.16},
        {"source": "López de Prado, Lipton & Zoonekynd (SSRN 4774522)", "start": "2007-05-02", "end": "2023-12-31", "sr": -0.08, "t": -0.33},
        {"source": "López de Prado, Lipton & Zoonekynd (2024, JPM)", "start": "2007-05-02", "end": "2024-07-19", "sr": 0.17, "t": 0.69}]
    for r in reported:
        y = (np.datetime64(r["end"]) - np.datetime64(r["start"])).astype(int) / 365.25
        r["years"] = y
        r["se_iid"] = math.sqrt((1 + 0.5 * r["sr"] ** 2) / y)
        r["se_implied_by_t"] = r["sr"] / r["t"]
        r["ci95_iid"] = [r["sr"] - 1.96 * r["se_iid"], r["sr"] + 1.96 * r["se_iid"]]
        r["ci_includes_0"] = r["ci95_iid"][0] <= 0 <= r["ci95_iid"][1]
        r["ci_includes_0.3"] = r["ci95_iid"][0] <= 0.3 <= r["ci95_iid"][1]
        print("live", r["end"], r["sr"], [round(v, 2) for v in r["ci95_iid"]], round(r["se_implied_by_t"], 3))
    res["live_index_reported"] = reported
    # power: two-sided alpha .05, iid normal approx, annual SR, 17 years
    yrs = 17.0
    res["power"] = {"years": yrs, "min_detectable_sr_80pct": (1.96 + 0.8416) / math.sqrt(yrs),
                    **{f"power_sr_{s}": 0.5 * math.erfc((1.96 - s * math.sqrt(yrs)) / math.sqrt(2)) for s in (0.17, 0.3, 0.5)},
                    "years_needed_sr0.3_80pct": ((1.96 + 0.8416) / 0.3) ** 2}
    print(res["power"])
    res["env"]["runtime_s"] = round(time.time() - t0, 1)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))

if __name__ == "__main__":
    main()
