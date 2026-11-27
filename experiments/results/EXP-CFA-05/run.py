#!/usr/bin/env python3
"""EXP-CFA-05 run: HaluEval detector replication + shortcut ablation.

Data: RUCAIBox/HaluEval data/*.json (public). Pass the directory holding
qa_data.json, dialogue_data.json, summarization_data.json, general_data.json.
Needs numpy, scipy, scikit-learn. Seeds fixed (SEEDS below).
"""
import json, re, sys, time, platform
from pathlib import Path
import numpy as np
import scipy.sparse as sp
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/halueval")
OUT = Path(__file__).resolve().parent / "raw"
SEEDS = [0, 1, 2, 3, 4]
PAIRED_SEED = 100
N_BOOT = 1000
TOK = re.compile(r"[a-z0-9]+")

def load():
    ex = []  # dict(domain, item, ctx, query, answer, y)
    for name, dom, c, q, r, h in [
        ("qa_data.json", "qa", "knowledge", "question", "right_answer", "hallucinated_answer"),
        ("dialogue_data.json", "dialogue", "knowledge", "dialogue_history", "right_response", "hallucinated_response"),
        ("summarization_data.json", "summarization", "document", None, "right_summary", "hallucinated_summary")]:
        for i, line in enumerate(open(DATA / name, encoding="utf-8")):
            d = json.loads(line)
            base = dict(domain=dom, item=f"{dom}:{i}", ctx=d[c], query=d[q] if q else "")
            ex.append({**base, "answer": d[r], "y": 0})
            ex.append({**base, "answer": d[h], "y": 1})
    for i, line in enumerate(open(DATA / "general_data.json", encoding="utf-8")):
        d = json.loads(line)
        ex.append(dict(domain="general", item=f"general:{i}", ctx="", query=d["user_query"],
                       answer=d["chatgpt_response"], y=int(d["hallucination"] == "yes")))
    return ex

def toks(s):
    return TOK.findall((s or "").lower())

def hand_features(e):
    a, c, q = toks(e["answer"]), toks(e["ctx"]), toks(e["query"])
    A, C, Q = set(a), set(c), set(q)
    nA = max(len(A), 1)
    nums = {t for t in A if t.isdigit()}
    length = [len(e["answer"]), len(a), len(c), len(q), len(a) / (len(c) + 1)]
    overlap = [len(A & C) / nA, len(A & Q) / nA, len(A & C) / max(len(C), 1),
               len(A - C - Q) / nA, len(nums - C - Q), len(A & C) / max(len(A | C), 1)]
    return length, overlap   # 5 + 6 = 11 features (definitions ours; source unlisted)

def splits(ex, seed, paired):
    rng = np.random.default_rng(seed)
    n = len(ex)
    if paired:
        items = sorted({e["item"] for e in ex})
        perm = rng.permutation(len(items))
        part = {items[j]: (0 if k < 0.6 * len(items) else 1 if k < 0.8 * len(items) else 2)
                for k, j in enumerate(perm)}
        lab = np.array([part[e["item"]] for e in ex])
    else:
        perm = rng.permutation(n)
        lab = np.empty(n, int)
        lab[perm[: int(0.6 * n)]] = 0
        lab[perm[int(0.6 * n): int(0.8 * n)]] = 1
        lab[perm[int(0.8 * n):]] = 2
    return lab

def ece(p, y, bins=15):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    tot = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            tot += m.mean() * abs(p[m].mean() - y[m].mean())
    return tot

def ece_null(p, rng, reps=200, bins=15):
    """Consistency resampling: ECE of a perfectly calibrated model with these p."""
    return np.array([ece(p, (rng.random(len(p)) < p).astype(int), bins) for _ in range(reps)])

def cluster_boot_auc(y, s, groups, rng, reps=N_BOOT):
    ug, inv = np.unique(groups, return_inverse=True)
    members = [[] for _ in ug]
    for i, g in enumerate(inv):
        members[g].append(i)
    members = [np.array(m) for m in members]
    out = []
    for _ in range(reps):
        pick = rng.integers(0, len(ug), len(ug))
        idx = np.concatenate([members[k] for k in pick])
        if len(np.unique(y[idx])) < 2:
            continue
        out.append(roc_auc_score(y[idx], s[idx]))
    return np.percentile(out, [2.5, 97.5]).tolist()

def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    ex = load()
    y = np.array([e["y"] for e in ex])
    dom = np.array([e["domain"] for e in ex])
    groups = np.array([e["item"] for e in ex])
    L, O = zip(*[hand_features(e) for e in ex])
    L, O = np.array(L, float), np.array(O, float)
    full_text = [f"{e['ctx']} {e['query']} {e['answer']}" for e in ex]
    ans_text = [e["answer"] for e in ex]
    env = dict(python=platform.python_version(), numpy=np.__version__,
               sklearn=sklearn.__version__, cpu=platform.processor() or platform.machine(),
               n_examples=len(ex), per_domain={d: int((dom == d).sum()) for d in np.unique(dom)},
               hallucinated_rate={d: float(y[dom == d].mean()) for d in np.unique(dom)})
    print(json.dumps(env))
    results = []
    split_list = [("random", s, False) for s in SEEDS] + [("paired", PAIRED_SEED, True)]
    for kind, seed, paired in split_list:
        lab = splits(ex, seed, paired)
        tr, va, te = lab == 0, lab == 1, lab == 2
        rng = np.random.default_rng(seed + 1000)
        def scaled(M):
            mu, sd = M[tr].mean(0), M[tr].std(0) + 1e-9
            return sp.csr_matrix((M - mu) / sd)
        vec_full = TfidfVectorizer(max_features=30000, ngram_range=(1, 1), sublinear_tf=True)
        vec_full.fit([full_text[i] for i in np.where(tr)[0]])
        X_full_t = vec_full.transform(full_text)
        vec_ans = TfidfVectorizer(max_features=30000, ngram_range=(1, 1), sublinear_tf=True)
        vec_ans.fit([ans_text[i] for i in np.where(tr)[0]])
        X_ans_t = vec_ans.transform(ans_text)
        Ls, Os = scaled(L), scaled(O)
        Lans = scaled(L[:, :2])   # answer chars, answer tokens only
        feats = {
            "full": sp.hstack([X_full_t, Ls, Os]).tocsr(),
            "answer_only": sp.hstack([X_ans_t, Lans]).tocsr(),
            "length_only": Ls,
            "overlap_only": Os,
        }
        ytr = y.copy()
        variants = list(feats.items()) + [("shuffled_labels", feats["full"])]
        for name, X in variants:
            yfit = y.copy()
            if name == "shuffled_labels":
                yfit = y.copy()
                yfit[tr] = rng.permutation(y[tr])
            clf = LinearSVC(C=1.0, max_iter=5000, random_state=seed)
            clf.fit(X[tr], yfit[tr])
            s = clf.decision_function(X)
            # domain-conditional Platt scaling on validation
            p = np.zeros(len(y))
            for d in np.unique(dom):
                m_va, m_d = va & (dom == d), dom == d
                lr = LogisticRegression(C=1e6, max_iter=1000)
                lr.fit(s[m_va].reshape(-1, 1), yfit[m_va])
                p[m_d] = lr.predict_proba(s[m_d].reshape(-1, 1))[:, 1]
            # global sigmoid baseline (raw score) for comparison with source
            p_raw = 1 / (1 + np.exp(-s))
            rec = dict(split=kind, seed=seed, model=name, n_test=int(te.sum()))
            yt = y[te]
            rec["auroc"] = float(roc_auc_score(yt, s[te]))
            rec["auroc_ci"] = cluster_boot_auc(yt, s[te], groups[te], rng, reps=N_BOOT if name in ("full", "answer_only") else 200)
            rec["ece15"] = float(ece(p[te], yt))
            rec["ece15_raw_sigmoid"] = float(ece(p_raw[te], yt))
            if name in ("full", "answer_only"):
                nul = ece_null(p[te], rng)
                rec["ece15_null_95"] = float(np.percentile(nul, 95))
            rec["per_domain"] = {}
            for d in np.unique(dom):
                m = te & (dom == d)
                r = dict(n=int(m.sum()), auroc=float(roc_auc_score(y[m], s[m])),
                         ece15=float(ece(p[m], y[m])))
                if name in ("full", "answer_only"):
                    r["auroc_ci"] = cluster_boot_auc(y[m], s[m], groups[m], rng, reps=500)
                rec["per_domain"][d] = r
            results.append(rec)
            print(kind, seed, name, f"auroc={rec['auroc']:.3f}", f"ece={rec['ece15']:.4f}",
                  {d: round(v['auroc'], 3) for d, v in rec['per_domain'].items()}, flush=True)
    env["runtime_s"] = round(time.time() - t0, 1)
    (OUT / "results.json").write_text(json.dumps({"env": env, "results": results}, indent=1))
    print("runtime_s", env["runtime_s"])

if __name__ == "__main__":
    main()
