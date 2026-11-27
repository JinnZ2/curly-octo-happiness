#!/usr/bin/env python3
"""EXP-CFA-05 supplement (added 2026-11-27 after the main run; post hoc).

run.py reports pooled AUROC on the raw SVM decision score. The detector in
the design outputs domain-conditional Platt probabilities, and Platt scaling
fitted per domain changes the *pooled* ranking (domains have different base
rates and score scales). This script refits the same `full` and `answer_only`
models with the same splits/seeds and reports pooled AUROC of the calibrated
probability p, plus raw-score AUROC to check it reproduces run.py.
"""
import json, sys, time
from pathlib import Path
import numpy as np, scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as R

def main():
    t0 = time.time()
    ex = R.load(); y = np.array([e["y"] for e in ex]); dom = np.array([e["domain"] for e in ex])
    L, O = zip(*[R.hand_features(e) for e in ex]); L, O = np.array(L, float), np.array(O, float)
    full_text = [f"{e['ctx']} {e['query']} {e['answer']}" for e in ex]; ans_text = [e["answer"] for e in ex]
    out = []
    for kind, seed, paired in [("random", s, False) for s in R.SEEDS] + [("paired", R.PAIRED_SEED, True)]:
        lab = R.splits(ex, seed, paired); tr, va, te = lab == 0, lab == 1, lab == 2
        def scaled(M):
            mu, sd = M[tr].mean(0), M[tr].std(0) + 1e-9
            return sp.csr_matrix((M - mu) / sd)
        vf = TfidfVectorizer(max_features=30000, sublinear_tf=True).fit([full_text[i] for i in np.where(tr)[0]])
        va_ = TfidfVectorizer(max_features=30000, sublinear_tf=True).fit([ans_text[i] for i in np.where(tr)[0]])
        feats = {"full": sp.hstack([vf.transform(full_text), scaled(L), scaled(O)]).tocsr(),
                 "answer_only": sp.hstack([va_.transform(ans_text), scaled(L[:, :2])]).tocsr()}
        for name, X in feats.items():
            s = LinearSVC(C=1.0, max_iter=5000, random_state=seed).fit(X[tr], y[tr]).decision_function(X)
            p = np.zeros(len(y))
            for d in np.unique(dom):
                m_va, m_d = va & (dom == d), dom == d
                p[m_d] = LogisticRegression(C=1e6, max_iter=1000).fit(s[m_va].reshape(-1, 1), y[m_va]).predict_proba(s[m_d].reshape(-1, 1))[:, 1]
            rec = dict(split=kind, seed=seed, model=name, auroc_raw=float(roc_auc_score(y[te], s[te])),
                       auroc_calibrated=float(roc_auc_score(y[te], p[te])),
                       auroc_calibrated_no_general=float(roc_auc_score(y[te & (dom != "general")], p[te & (dom != "general")])),
                       auroc_raw_no_general=float(roc_auc_score(y[te & (dom != "general")], s[te & (dom != "general")])))
            out.append(rec); print(json.dumps(rec), flush=True)
    (R.OUT / "calibrated_auroc.json").write_text(json.dumps({"runtime_s": round(time.time() - t0, 1), "results": out}, indent=1))

if __name__ == "__main__":
    main()
