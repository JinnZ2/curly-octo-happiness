#!/usr/bin/env python3
"""SKETCH (not results): audit the hypothesis engine's stage-4 oracle on its own data.

For every open gap in data/gap_registry.json that points at a claim in
data/claim_tree.json, this script

  1. lists the findings the claim was recorded as tested against
     (claim.tested_against -> findings_log.jsonl hashes),
  2. re-runs the engine's own `corroboration()` on each of them against the
     *current* corpus IDF, and
  3. records, per verdict, the shared tokens, the polarity markers that fired,
     and structural flags:
        same_title   - the "independent" source has the claim's own title
                       (one paper indexed under two URLs/sources)
        template_tok - a shared token comes from the claim template
                       ("On topic ..., <title> reports: ...") not the abstract
        title_tok    - a shared token occurs only in the claim's *title*
        verdict_drift- recomputed verdict differs from the stored count

It does NOT judge whether any paper agrees with any other. It produces an
annotation sheet (CSV) for EXP-ENG-01, where humans label stance, and, if a
labels file is supplied, computes agreement between the oracle and humans.

Read-only: imports scripts/hypothesis_engine.py and never writes to data/ or
hypotheses/. Stdlib only. Offline.

Usage:
  python experiments/sketches/oracle_audit.py                 # summary to stdout
  python experiments/sketches/oracle_audit.py --sheet out.csv # annotation sheet
  python experiments/sketches/oracle_audit.py --labels labels.csv
      labels.csv columns: pair_id,human  (human in {+1,-1,0})
"""
import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_TOKENS = {"report", "topic"}


def load_engine():
    spec = importlib.util.spec_from_file_location(
        "hypothesis_engine", ROOT / "scripts" / "hypothesis_engine.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hypothesis_engine"] = mod
    spec.loader.exec_module(mod)
    return mod


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def norm(s):
    return " ".join((s or "").lower().split())


def audit(data_dir: Path):
    he = load_engine()
    rows = read_jsonl(data_dir / "findings_log.jsonl")
    by_hash = {r.get("hash"): r for r in rows}
    idf = he.idf_map([r.get("abstract", "") or "" for r in rows])
    claims = {c["id"]: c for c in
              json.loads((data_dir / "claim_tree.json").read_text())["claims"]}
    reg = json.loads((data_dir / "gap_registry.json").read_text())["gaps"]

    out = []
    for key, g in sorted(reg.items(), key=lambda kv: kv[1]["id"]):
        if not g.get("standing", True):
            continue
        kind, _, cid = key.partition(":")
        c = claims.get(cid)
        if c is None:
            continue  # escape/hidden gaps are not stage-4 claims
        topic = c["scope"]["topic"]
        title, _body = he.split_claim_text(c["text"])
        for h in c.get("tested_against", []):
            r = by_hash.get(h)
            if r is None:
                out.append({"gap": g["id"], "pair_id": f"{g['id']}:{h[:10]}",
                            "other_title": "<hash not in findings log>",
                            "verdict_now": "", "flags": "missing_finding"})
                continue
            abstract = r.get("abstract", "") or ""
            v = he.corroboration(c["text"], abstract, idf=idf, topic=topic)
            shared = he.shared_subject(c["text"], abstract, topic)
            rel = [s for s in he._sentences(abstract) if he._tokens(s) & shared]
            ctx = " ".join(rel).lower()
            pos = [m for m in he.CORROBORATION_MARKERS if m in ctx]
            neg = [m for m in he.CONTRADICTION_MARKERS if m in ctx]
            title_only = shared & he._tokens(title) - he._tokens(_body)
            flags = []
            if norm(r.get("title")) == norm(title):
                flags.append("same_title")
            if shared & TEMPLATE_TOKENS:
                flags.append("template_tok")
            if title_only:
                flags.append("title_tok")
            if v == 0:
                flags.append("verdict_now_zero")
            out.append({
                "gap": g["id"], "pair_id": f"{g['id']}:{h[:10]}",
                "claim_title": title[:100], "other_title": r.get("title", "")[:100],
                "other_url": r.get("url", ""), "verdict_now": v,
                "shared": " ".join(sorted(shared)), "pos_markers": " ".join(pos),
                "neg_markers": " ".join(neg), "context": ctx[:400],
                "flags": " ".join(flags),
            })
    return out


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--sheet", help="write annotation CSV here")
    ap.add_argument("--labels", help="CSV with pair_id,human to score against")
    args = ap.parse_args(argv)
    rows = audit(Path(args.data_dir))

    flags = Counter(f for r in rows for f in r["flags"].split())
    gaps = {r["gap"] for r in rows}
    print(f"# oracle audit (sketch output, not a finding): {len(rows)} recorded "
          f"verdict pairs across {len(gaps)} claim-backed open gaps")
    for f, n in flags.most_common():
        print(f"  {f:18s} {n}")
    if args.sheet:
        cols = ["pair_id", "gap", "claim_title", "other_title", "other_url",
                "verdict_now", "shared", "pos_markers", "neg_markers",
                "context", "flags", "human"]
        with open(args.sheet, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({**r, "human": ""})
        print(f"wrote {args.sheet}")
    if args.labels:
        lab = {}
        with open(args.labels, encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                if rec.get("human", "").strip():
                    lab[rec["pair_id"]] = int(rec["human"])
        pairs = [(int(r["verdict_now"]), lab[r["pair_id"]]) for r in rows
                 if r["pair_id"] in lab and r["verdict_now"] != ""]
        a, b = zip(*pairs) if pairs else ((), ())
        print(f"labelled pairs: {len(pairs)}  kappa(oracle, human) = "
              f"{cohen_kappa(list(a), list(b)):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
