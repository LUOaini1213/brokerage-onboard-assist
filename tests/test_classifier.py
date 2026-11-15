"""Hold-note classifier: split hygiene, hand-worked metrics, determinism, and the committed metrics."""
import csv
import json

import pytest

from boa import classifier as clf
from boa.data import read_tables
from boa.note_templates import HELD_OUT_TEMPLATES
from boa.paths import RESULTS, SYNTHETIC


@pytest.fixture(scope="module")
def holds():
    return read_tables(SYNTHETIC)["holds"]


def test_split_is_disjoint_and_template_held_out(holds):
    train, seen, held = clf.split(holds)
    ids = [set(h["hold_id"] for h in part) for part in (train, seen, held)]
    assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])
    assert sum(len(i) for i in ids) == len(holds)
    assert {clf.template_index(h["note_template"]) for h in held} == set(HELD_OUT_TEMPLATES)
    assert not {clf.template_index(h["note_template"]) for h in train + seen} & set(HELD_OUT_TEMPLATES)
    # no held-out note is a verbatim copy of a training note
    assert not {h["note"] for h in held} & {h["note"] for h in train}
    # the seen-template test set is a stratified quarter of each reason
    for code in {h["reason_code"] for h in train + seen}:
        n_seen = sum(h["reason_code"] == code for h in seen)
        n_all = n_seen + sum(h["reason_code"] == code for h in train)
        assert n_seen == int(round(0.25 * n_all)), code


def test_metrics_hand_worked():
    e = clf.evaluate(["A", "A", "B", "B"], ["A", "B", "B", "B"], ["A", "B"])
    assert e["accuracy"] == 0.75
    assert e["per_class"]["A"] == {"precision": 1.0, "recall": 0.5, "f1": pytest.approx(2 / 3), "support": 2}
    assert e["per_class"]["B"]["precision"] == pytest.approx(2 / 3) and e["per_class"]["B"]["f1"] == pytest.approx(0.8)
    assert e["macro_f1"] == pytest.approx((2 / 3 + 0.8) / 2)
    assert e["confusion"] == [[1, 1], [0, 2]]


def test_bootstrap_interval_brackets_the_estimate():
    y = ["A"] * 30 + ["B"] * 30
    p = ["A"] * 25 + ["B"] * 5 + ["B"] * 28 + ["A"] * 2
    ci = clf.bootstrap_ci(y, p, ["A", "B"], n_boot=300)
    acc = clf.evaluate(y, p, ["A", "B"])["accuracy"]
    assert 0 <= ci["accuracy_95ci"][0] <= acc <= ci["accuracy_95ci"][1] <= 1
    assert ci == clf.bootstrap_ci(y, p, ["A", "B"], n_boot=300)     # seeded


@pytest.mark.parametrize("text,label", [
    ("BICON conditions require supporting documents not supplied.", "BIOSECURITY"),
    ("HSA approval missing, goods held pending licence.", "CA_APPROVAL"),
    ("Permit applied after arrival. Customs hold until permit approval.", "PERMIT_TIMING"),
    ("Importer UEN on permit does not match customer record.", "PARTY_UEN"),
    ("Tariff code 94054000 rejected by system as invalid.", "HS_INVALID"),
    ("Classification query - product literature requested.", "HS_QUERY"),
    ("Valuation query: FOB terms, freight/insurance missing.", "VALUE_CIF"),
    ("Preference claimed but no certificate of origin provided.", "ORIGIN_DOCS"),
    ("Quantity on packing list (98) differs from invoice (100).", "DOC_MISMATCH"),
    ("Commercial invoice incomplete: invoice date missing.", "INVOICE_DATA"),
    ("Random examination by Customs; no discrepancy found.", "INSPECTION"),
])
def test_keyword_baseline(text, label):
    assert clf.keyword_predict(text) == label


def test_training_is_deterministic(holds):
    train, seen, _ = clf.split(holds)
    texts = [h["note"] for h in seen]
    assert list(clf.fit(train).predict(texts)) == list(clf.fit(train).predict(texts))


def test_committed_metrics_match_committed_predictions(holds):
    m = json.loads((RESULTS / "classifier" / "metrics.json").read_text(encoding="utf-8"))
    with open(RESULTS / "classifier" / "predictions.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    train, seen, held = clf.split(holds)
    assert (m["n_train"], m["n_test_seen"], m["n_test_heldout"]) == (len(train), len(seen), len(held))
    for split_name, n in (("seen", len(seen)), ("heldout", len(held))):
        part = [r for r in rows if r["split"] == split_name]
        assert len(part) == n
        acc = sum(r["true"] == r["tfidf_logreg"] for r in part) / n
        kw = sum(r["true"] == r["keyword_rules"] for r in part) / n
        assert acc == pytest.approx(m[split_name]["tfidf_logreg"]["accuracy"], abs=1e-6)
        assert kw == pytest.approx(m[split_name]["keyword_rules"]["accuracy"], abs=1e-6)
    folds = m["leave_one_template_out"]["folds"]
    assert [f["template_index"] for f in folds] == list(range(8)) and sum(f["n"] for f in folds) == len(holds)
