"""Classify free-text hold notes into reason codes: TF-IDF + logistic regression, with two transparent baselines.

The notes are SYNTHETIC: they are generated from templates (src/boa/note_templates.py) with noise. Two test sets:
- 'seen-template test': a stratified 25% of the notes written from templates 0-5 (the training templates), so
  test notes share phrasings with training notes; this score is optimistic;
- 'held-out-template test': every note written from templates 6 and 7, whose wording the model never saw.
The model is trained once, on the other 75% of the seen-template notes, and scored on both.
"""
import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.pipeline import FeatureUnion, Pipeline

from .note_templates import HELD_OUT_TEMPLATES

SEED = 7
TEST_SHARE_SEEN = 0.25

# Keyword baseline: first matching rule wins (order matters); written by hand from the reason definitions.
KEYWORDS = [
    ("BIOSECURITY", r"biosecurity|bicon|daff|fumigat|quarantine"),
    ("CA_APPROVAL", r"licen[cs]e|competent authority|\b(hsa|sfa|imda|nea|nparks|spf|scdf|lta|moh|bca|gra|cnb)\b"),
    ("PERMIT_TIMING", r"permit (submitted|applied|approval came|not obtained|missing at)|late lodg|lodged permit late"),
    ("PARTY_UEN", r"\buen\b|importer (name|details)|customs account"),
    ("HS_INVALID", r"(hs|tariff) code .*(not valid|invalid|rejected|not found|format)|code does not exist"),
    ("HS_QUERY", r"classification|datasheet|specs|literature|catalogue"),
    ("VALUE_CIF", r"valu|cif|undervalu|freight|insurance"),
    ("ORIGIN_DOCS", r"origin|\bco\b|form d|preference"),
    ("INSPECTION", r"inspect|examin|scanned|selected"),
    ("DOC_MISMATCH", r"packing list|weight|quantit|bl\b|awb|discrepan|packages"),
    ("INVOICE_DATA", r"invoice|proforma"),
]


def keyword_predict(text):
    t = text.lower()
    for label, pat in KEYWORDS:
        if re.search(pat, t):
            return label
    return "INSPECTION"


def template_index(note_template):
    return int(note_template.rsplit("-", 1)[1])


def split(holds, seed=SEED):
    """Return (train, test_seen, test_heldout) lists of holds. Stratified by reason within seen-template notes."""
    seen = [h for h in holds if template_index(h["note_template"]) not in HELD_OUT_TEMPLATES]
    held_out = [h for h in holds if template_index(h["note_template"]) in HELD_OUT_TEMPLATES]
    rng = np.random.default_rng(seed)
    train, test = [], []
    for code in sorted({h["reason_code"] for h in seen}):
        group = [h for h in seen if h["reason_code"] == code]
        order = rng.permutation(len(group))
        n_test = int(round(TEST_SHARE_SEEN * len(group)))
        test += [group[i] for i in order[:n_test]]
        train += [group[i] for i in order[n_test:]]
    key = lambda h: h["hold_id"]  # noqa: E731
    return sorted(train, key=key), sorted(test, key=key), sorted(held_out, key=key)


def build_model():
    features = FeatureUnion([
        ("word", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
        ("char", TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=2)),
    ])
    clf = LogisticRegression(C=10.0, max_iter=5000, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])


def fit(train):
    model = build_model()
    model.fit([h["note"] for h in train], [h["reason_code"] for h in train])
    return model


def evaluate(y_true, y_pred, labels):
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    present = [lab for lab in labels if lab in set(y_true)]
    return {
        "n": len(y_true),
        "accuracy": float(np.mean(np.asarray(y_true) == np.asarray(y_pred))),
        "macro_f1": float(f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)),
        "per_class": {lab: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])}
                      for i, lab in enumerate(labels)},
        "confusion": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": list(labels),
    }


def bootstrap_ci(y_true, y_pred, labels, n_boot=1000, seed=SEED):
    """95% percentile bootstrap intervals of accuracy and macro-F1 (resampling test notes)."""
    rng = np.random.default_rng(seed)
    yt, yp = np.asarray(y_true), np.asarray(y_pred)
    acc, mf1 = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, len(yt), len(yt))
        t, q = yt[idx], yp[idx]
        acc.append(float(np.mean(t == q)))
        present = [lab for lab in labels if lab in set(t)]
        mf1.append(float(f1_score(t, q, labels=present, average="macro", zero_division=0)))
    pct = lambda xs: [float(np.percentile(xs, 2.5)), float(np.percentile(xs, 97.5))]  # noqa: E731
    return {"accuracy_95ci": pct(acc), "macro_f1_95ci": pct(mf1)}


def majority_label(train):
    return Counter(h["reason_code"] for h in train).most_common(1)[0][0]
