#!/usr/bin/env python3
"""EXP-ENG-02 run: record integrity under dedupe x history x verdict-source.

Deterministic replay of the engine's own git history. Read-only: reads
historical blobs with `git show`, imports historical copies of
scripts/hypothesis_engine.py from a temp dir, never writes to data/ or
hypotheses/. Stdlib only.

Factors (pre-registered in experiments/engine-oracle.md):
  dedupe   : off | title | doi | arxiv   (one vote per paper, key varies)
  history  : post (since last reformulation, what the engine counts) | full
  verdict  : stored (replayed with the engine code + corpus IDF + claim text
             of the run in which the pair was first recorded) | now (current
             code, current IDF, current claim text)
Outcome: gap class under the engine's own classify_gap rule.
"""
import importlib.util, json, re, subprocess, sys, tempfile, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
HEAD = sys.argv[1] if len(sys.argv) > 1 else "HEAD"

def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], check=True,
                          capture_output=True, text=True).stdout

def show(sha, path):
    try:
        return git("show", f"{sha}:{path}")
    except subprocess.CalledProcessError:
        return None

_mods = {}
def engine_at(sha):
    blob = git("rev-parse", f"{sha}:scripts/hypothesis_engine.py").strip()
    if blob in _mods:
        return _mods[blob]
    d = Path(tempfile.mkdtemp())
    p = d / f"he_{blob[:8]}.py"
    p.write_text(show(sha, "scripts/hypothesis_engine.py"))
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(p.stem, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[p.stem] = m
    spec.loader.exec_module(m)
    _mods[blob] = m
    return m

def jl(text):
    return [json.loads(l) for l in (text or "").splitlines() if l.strip()]

SUFFIX = re.compile(r"\s*\(scope narrowed: restricted after failure #\d+\)\s*$")

def norm_title(t):
    return re.sub(r"[^a-z0-9 ]", "", " ".join((t or "").lower().split()))

def doi_key(url, title):
    m = re.search(r"(10\.\d{4,9}/[^\s?#]+)", url or "")
    if m:
        k = m.group(1).lower().rstrip("/")
        k = re.sub(r"_v\d+$", "", k)          # OSF/preprint version suffix
        return "doi:" + k
    return "title:" + norm_title(title)       # fallback, stated in results

def arxiv_key(url, title):
    m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", url or "")
    if m:
        return "arxiv:" + m.group(1)
    return "title:" + norm_title(title)       # fallback, stated in results

import inspect
def call_corr(he, text, other, idf, topic):
    """Call the corroboration() of that engine version with the args it took."""
    params = inspect.signature(he.corroboration).parameters
    kw = {}
    if "idf" in params:
        kw["idf"] = idf
    if "topic" in params:
        kw["topic"] = topic
    return he.corroboration(text, other, **kw)

def main():
    t0 = time.time()
    shas = git("log", "--reverse", "--format=%H", HEAD, "--",
               "data/claim_tree.json").split()
    cur = engine_at(HEAD)
    # pair -> first run info
    first = {}            # (cid, hash) -> dict(run_idx, sha, verdict_stored)
    reform_at = defaultdict(list)   # cid -> [run_idx of each reformulation]
    validation = []       # per (run, claim): reconstructed vs actual deltas
    prev = {}
    for i, sha in enumerate(shas):
        he = engine_at(sha)
        rows = jl(show(sha, "data/findings_log.jsonl"))
        by_hash = {r.get("hash"): r for r in rows}
        idf = he.idf_map([r.get("abstract", "") or "" for r in rows]) if hasattr(he, "idf_map") else None
        claims = {c["id"]: c for c in json.loads(show(sha, "data/claim_tree.json"))["claims"]}
        for cid, c in claims.items():
            p = prev.get(cid)
            old_keys = set(p["tested_against"]) if p else set()
            new_keys = [k for k in c["tested_against"] if k not in old_keys]
            reformed = p is not None and c["reformulation_count"] > p["reformulation_count"]
            if p is None and c["reformulation_count"] > 0:
                reformed = True
            if reformed:
                reform_at[cid].append(i)
            text = SUFFIX.sub("", c["text"]) if reformed else c["text"]
            pos = neg = 0
            for k in new_keys:
                r = by_hash.get(k)
                v = None
                if r is not None:
                    v = call_corr(he, text, r.get("abstract", "") or "",
                                  idf, c["scope"]["topic"])
                first[(cid, k)] = {"run": i, "sha": sha[:7], "stored": v}
                pos += v == 1; neg += v == -1
            if p is not None and not reformed:
                validation.append({
                    "run": i, "claim": cid, "new_pairs": len(new_keys),
                    "d_passed": c["passed"] - p["passed"], "rec_pos": pos,
                    "d_failed": c["failed"] - p["failed"], "rec_neg": neg})
            elif p is None and not reformed:
                validation.append({
                    "run": i, "claim": cid, "new_pairs": len(new_keys),
                    "d_passed": c["passed"], "rec_pos": pos,
                    "d_failed": c["failed"], "rec_neg": neg})
        prev = claims

    # current state
    rows = jl(show(HEAD, "data/findings_log.jsonl"))
    by_hash = {r.get("hash"): r for r in rows}
    idf_now = cur.idf_map([r.get("abstract", "") or "" for r in rows])
    claims = prev
    reg = json.loads(show(HEAD, "data/gap_registry.json"))["gaps"]
    open_gaps = {}
    for key, g in reg.items():
        if not g.get("standing", True):
            continue
        kind, _, cid = key.partition(":")
        if cid in claims:
            open_gaps[cid] = (g["id"], kind)
    cid_of_gap = {v[0]: k for k, v in open_gaps.items()}

    def paper_key(mode, url, title):
        if mode == "off":
            return None
        if mode == "title":
            return "title:" + norm_title(title)
        if mode == "doi":
            return doi_key(url, title)
        return arxiv_key(url, title)

    def claim_title(c):
        return cur.split_claim_text(c["text"])[0]

    pairs = []
    for cid, c in claims.items():
        last_reform = max(reform_at[cid]) if reform_at[cid] else -1
        for k in c["tested_against"]:
            r = by_hash.get(k, {})
            fi = first.get((cid, k), {})
            now = cur.corroboration(c["text"], r.get("abstract", "") or "",
                                    idf=idf_now, topic=c["scope"]["topic"]) if r else None
            pairs.append({
                "claim": cid, "gap": open_gaps.get(cid, ("", ""))[0], "hash": k,
                "other_title": r.get("title", ""), "other_url": r.get("url", ""),
                "first_run": fi.get("run"), "first_sha": fi.get("sha"),
                "post_reform": (fi.get("run", -1) > last_reform),
                "stored": fi.get("stored"), "now": now})

    def record(cid, mode, hist, verd):
        c = claims[cid]
        # claim-level merge: all current claims that are the same paper
        if mode == "off":
            members = [cid]
        else:
            me = paper_key(mode, c.get("source_url"), claim_title(c))
            members = [x for x, cx in claims.items()
                       if cx["scope"]["topic"] == c["scope"]["topic"] and
                       paper_key(mode, cx.get("source_url"), claim_title(cx)) == me]
        me_keys = {paper_key(m, claims[x].get("source_url"), claim_title(claims[x]))
                   for x in members for m in ([mode] if mode != "off" else [])}
        votes = {}
        n = 0
        for p in pairs:
            if p["claim"] not in members:
                continue
            if hist == "post" and not p["post_reform"]:
                continue
            v = p[verd]
            if v not in (1, -1):
                continue
            if mode == "off":
                votes[n] = v; n += 1
                continue
            pk = paper_key(mode, p["other_url"], p["other_title"])
            if pk in me_keys:
                continue          # a paper cannot testify about itself
            votes.setdefault(pk, []).append(v)
        if mode != "off":
            # one vote per paper: sign of the paper's net verdict; ties abstain
            votes = {k: (1 if sum(v) > 0 else -1) for k, v in votes.items() if sum(v) != 0}
        passed = sum(1 for v in votes.values() if v == 1)
        failed = sum(1 for v in votes.values() if v == -1)
        return passed, failed, members

    def classify(passed, failed):
        if passed + failed < cur.GAP_MIN_TESTS:
            return None
        beta = (1 + passed) / (2 + passed + failed)
        lo, hi = cur.GAP_SPLIT_BAND
        if passed and failed and lo <= beta <= hi:
            return "contested"
        if failed > passed:
            return "contradicted"
        return None

    cells = [(m, h, v) for m in ("off", "title", "doi", "arxiv")
             for h in ("post", "full") for v in ("stored", "now")]
    results = []
    for gid, cid in sorted(cid_of_gap.items()):
        c = claims[cid]
        row = {"gap": gid, "claim": cid, "registry_kind": open_gaps[cid][1],
               "engine_passed": c["passed"], "engine_failed": c["failed"]}
        for m, h, v in cells:
            p, f, mem = record(cid, m, h, v)
            row[f"{m}|{h}|{v}"] = {"passed": p, "failed": f, "class": classify(p, f),
                                   "merged_with": [open_gaps.get(x, ("(no gap)",))[0] for x in mem if x != cid]}
        results.append(row)

    # also: claims that are not open gaps but would become gaps
    newgaps = []
    for cid in claims:
        if cid in open_gaps:
            continue
        for m, h, v in cells:
            p, f, _ = record(cid, m, h, v)
            k = classify(p, f)
            if k:
                newgaps.append({"claim": cid, "cell": f"{m}|{h}|{v}", "class": k,
                                "passed": p, "failed": f})

    (OUT / "raw").mkdir(exist_ok=True)
    (OUT / "raw" / "pairs.json").write_text(json.dumps(pairs, indent=1))
    (OUT / "raw" / "cells.json").write_text(json.dumps(results, indent=1))
    (OUT / "raw" / "validation.json").write_text(json.dumps(validation, indent=1))
    (OUT / "raw" / "non_gap_claims_that_become_gaps.json").write_text(json.dumps(newgaps, indent=1))

    # summaries
    val_ok = sum(1 for x in validation if x["d_passed"] == x["rec_pos"] and x["d_failed"] == x["rec_neg"])
    val_with_pairs = [x for x in validation if x["new_pairs"]]
    val_ok_wp = sum(1 for x in val_with_pairs if x["d_passed"] == x["rec_pos"] and x["d_failed"] == x["rec_neg"])
    base = "off|post|stored"
    lines = [f"runs replayed: {len(shas)} ({shas[0][:7]}..{shas[-1][:7]})",
             f"pairs on current claims: {len(pairs)}; open claim-backed gaps: {len(results)}",
             f"reconstruction check (non-reformulated claim-runs): {val_ok}/{len(validation)} exact; "
             f"with >=1 new pair: {val_ok_wp}/{len(val_with_pairs)}",
             f"stored verdict missing (finding not in log at that run): {sum(p['stored'] is None for p in pairs)}"]
    eng = Counter()
    for r in results:
        b = r[base]
        eng["baseline==engine counts"] += (b["passed"], b["failed"]) == (r["engine_passed"], r["engine_failed"])
        eng["baseline class==registry kind"] += b["class"] == r["registry_kind"]
    lines.append(f"baseline cell {base}: counts match engine for {eng['baseline==engine counts']}/{len(results)}, "
                 f"class matches registry for {eng['baseline class==registry kind']}/{len(results)}")
    lines.append("")
    lines.append("cell -> gaps whose class differs from registry kind (of %d)" % len(results))
    for m, h, v in cells:
        k = f"{m}|{h}|{v}"
        ch = [r["gap"] for r in results if r[k]["class"] != r["registry_kind"]]
        lines.append(f"  {k:22s} {len(ch):3d}  " + " ".join(ch))
    lines.append(f"\nruntime_s: {time.time()-t0:.1f}")
    (OUT / "raw" / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
