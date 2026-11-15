"""Rebuild every result from the committed inputs (config, rules, HS reference, cached LLM predictions), offline.

    python scripts/build_all.py

out_root defaults to the repository; tests/test_pipeline.py builds into a temporary folder and compares.
"""
import csv
from collections import Counter
from datetime import date
from pathlib import Path

from . import analytics as an
from . import classifier as clf
from . import kpis as K
from .data import enrolment_bundles, read_tables, shipment_bundles, write_tables
from .docs_render import assumptions_markdown, kpi_markdown
from .handling_note import draft_note
from .io import read_json, write_csv, write_json, write_text
from .paths import CONFIG, ROOT
from .powerbi_export import export as export_powerbi
from .rules import hold_reasons, render_markdown, rules
from .synth import generate, load_config
from .validator import readiness, validate_enrolment, validate_shipment

LLM_CACHE = ROOT / "results" / "classifier" / "llm_predictions.csv"
EXAMPLE_NOTES = 3


def _findings_rows(owner_key, owner_id, findings):
    return [{owner_key: owner_id, **f.as_dict()} for f in findings]


def build(out_root=ROOT, figures=True):
    out = Path(out_root)
    cfg = load_config()
    raw_cfg = read_json(CONFIG / "synth_assumptions.json")
    lanes = {ln["lane_id"]: ln for ln in cfg["lanes"]}
    as_of = date.fromisoformat(cfg["as_of_date"])

    # 1. synthetic data (written, then read back so every step uses exactly the committed CSV text)
    write_tables(generate(cfg), out / "data" / "synthetic")
    t = read_tables(out / "data" / "synthetic")

    # 2. validator: enrolments and shipments
    efind, erows = {}, []
    for eid, b in enrolment_bundles(t, lanes).items():
        f = validate_enrolment(b)
        efind[b["customer_id"]] = f
        score, band = readiness(f)
        erows.append({"enrolment_id": eid, "customer_id": b["customer_id"], "readiness_score": score, "band": band,
                      "blocking": sum(x.severity == "BLOCKING" for x in f),
                      "warnings": sum(x.severity == "WARNING" for x in f)})
    cols_f = ["check", "rule_id", "reason_code", "severity", "message", "line_no"]
    vdir = out / "results" / "validation"
    write_csv(vdir / "enrolment_readiness.csv", erows, list(erows[0]))
    write_csv(vdir / "enrolment_findings.csv",
              [r for e in t["enrolments"] for r in _findings_rows("enrolment_id", e["enrolment_id"],
                                                                   efind[e["customer_id"]])],
              ["enrolment_id"] + cols_f)
    sfind, srows, ready = {}, [], {}
    for sid, b in shipment_bundles(t).items():
        f = validate_shipment(b, cfg["fx_to_sgd"], cfg["fx_sgd_to_aud"])
        sfind[sid] = f
        ready[sid] = readiness(f)
        srows.append({"shipment_id": sid, "customer_id": b["shipment"]["customer_id"],
                      "shipment_seq": b["shipment"]["shipment_seq"], "readiness_score": ready[sid][0],
                      "band": ready[sid][1], "blocking": sum(x.severity == "BLOCKING" for x in f),
                      "warnings": sum(x.severity == "WARNING" for x in f), "held": b["shipment"]["held"]})
    write_csv(vdir / "shipment_readiness.csv", srows, list(srows[0]))
    write_csv(vdir / "shipment_findings.csv",
              [r for sid, f in sfind.items() for r in _findings_rows("shipment_id", sid, f)], ["shipment_id"] + cols_f)

    # 3. handling notes (one per customer with a profile; three written out as examples)
    customers = {c["customer_id"]: c for c in t["customers"]}
    products = {}
    for p in t["products"]:
        products.setdefault(p["customer_id"], []).append(p)
    licences = {}
    for x in t["licences"]:
        licences.setdefault(x["customer_id"], {}).setdefault(x["authority"], x["licence_ref"])
    notes = []
    for e in t["enrolments"]:
        if not e["profile_created_date"]:
            continue
        cid = e["customer_id"]
        notes.append({"customer_id": cid, "note": draft_note(customers[cid], products[cid], lanes, efind[cid],
                                                             licences.get(cid, {}))})
    write_csv(vdir / "handling_notes.csv", notes, ["customer_id", "note"])
    picks = _example_customers(t, efind, lanes)
    for old in (out / "docs" / "examples").glob("handling_note_*.md"):
        old.unlink()
    for cid in picks:
        note = next(n["note"] for n in notes if n["customer_id"] == cid)
        write_text(out / "docs" / "examples" / f"handling_note_{cid}.md", note)

    # 4. root-cause analytics
    adir = out / "results" / "analytics"
    labels = {k: v["label"] for k, v in hold_reasons().items()}
    holds, shipments = t["holds"], t["shipments"]
    par = an.pareto(holds, labels)
    write_csv(adir / "pareto.csv", par, list(par[0]))
    rel_r = an.time_to_release(holds, ["reason_code"])
    rel_l = an.time_to_release(holds, ["lane_id"])
    rel_rl = an.time_to_release(holds, ["reason_code", "lane_id"], min_n=5)
    write_csv(adir / "release_by_reason.csv", rel_r, list(rel_r[0]))
    write_csv(adir / "release_by_lane.csv", rel_l, list(rel_l[0]))
    write_csv(adir / "release_by_reason_lane.csv", rel_rl, list(rel_rl[0]))
    for s in shipments:
        s["band"] = ready[s["shipment_id"]][1]
    rates = {k: an.hold_rates(shipments, k) for k in ("shipment_seq", "lane_id", "band")}
    for k, rows_ in rates.items():
        write_csv(adir / f"hold_rate_by_{k}.csv", rows_, list(rows_[0]))
    clr = an.clearance_by_lane(shipments)
    write_csv(adir / "clearance_by_lane.csv", clr, list(clr[0]))
    det = an.detection(holds, sfind)
    write_csv(adir / "readiness_detection_by_reason.csv", det, list(det[0]))
    prec = an.blocking_precision(shipments, sfind)

    # 5. classifier
    cl = _classifier(holds, out)

    # 6. Power BI model data and the Python KPIs on it
    pdir = out / "powerbi" / "data"
    export_powerbi(t, ready, cfg["lanes"], as_of, pdir)
    frames = K.load_frames(pdir)
    totals = {name: K.value(name, frames) for name in K.MEASURES}
    write_json(out / "results" / "kpis.json", totals)
    write_csv(out / "results" / "powerbi_expected_values.csv", _expected_visual_values(frames),
              ["page", "visual", "category", "measure", "value"])

    # 7. generated docs
    write_text(out / "docs" / "rulebook.md", render_markdown())
    write_text(out / "docs" / "assumptions.md", assumptions_markdown(raw_cfg))
    write_text(out / "docs" / "kpi_definitions.md", kpi_markdown(totals))

    # 8. summary (README numbers come from here)
    status = Counter(r["status"] for r in rules())
    vital = an.vital_few(par)
    summary = {
        "data_label": "SYNTHETIC",
        "rules": {"total": len(rules()), "SG": sum(r["jurisdiction"] == "SG" for r in rules()),
                  "AU": sum(r["jurisdiction"] == "AU" for r in rules()), **dict(status)},
        "counts": {"customers": len(t["customers"]), "enrolments": len(t["enrolments"]),
                   "shipments": len(shipments), "holds": len(holds), "actions": len(t["actions"])},
        "funnel": {name: totals[name] for name in ("Enrolments Submitted", "Profiles Created",
                                                   "Three Shipments Completed")},
        "first3": {"hold_rate": totals["First-3 Hold Rate %"], "customers_with_hold_rate": totals["Customers With a Hold %"],
                   "by_seq": {str(r["shipment_seq"]): r["hold_rate"] for r in rates["shipment_seq"]}},
        "pareto": {"top": par[0]["reason_code"], "top_share": par[0]["share"], "vital_few": vital,
                   "vital_few_share": par[len(vital) - 1]["cumulative_share"]},
        "release": {"median_hours_all": totals["Median Hours to Release"],
                    "slowest_reason": max(rel_r, key=lambda r: r["median_hours"])["reason_code"],
                    "slowest_median": max(r["median_hours"] for r in rel_r),
                    "fastest_reason": min(rel_r, key=lambda r: r["median_hours"])["reason_code"],
                    "fastest_median": min(r["median_hours"] for r in rel_r)},
        "clearance": {"median_hours_all": totals["Median Clearance Hours"],
                      "slowest_lane": max(clr, key=lambda r: r["median_hours"])["lane_id"],
                      "slowest_lane_median": max(r["median_hours"] for r in clr),
                      "fastest_lane": min(clr, key=lambda r: r["median_hours"])["lane_id"],
                      "fastest_lane_median": min(r["median_hours"] for r in clr)},
        "readiness": {"detected_same_reason": det[-1]["same_reason_rate"], "detected_any_blocking":
                      det[-1]["any_blocking_rate"], **prec,
                      "bands": dict(Counter(v[1] for v in ready.values()))},
        "actions": {"open": totals["Open Actions"], "overdue": totals["Overdue Actions"],
                    "closed_on_time": totals["Closed On Time %"], "avg_days_to_close": totals["Avg Days to Close"]},
        "classifier": cl,
    }
    write_json(out / "results" / "summary.json", summary)
    if figures:
        from .figures import draw_all
        draw_all(out, frames, par, rel_r, clr, rates, cl)
    return summary


def _example_customers(t, efind, lanes):
    """Three customers with a profile: an import with controlled goods, an export to Australia, and one with open
    enrolment items. Deterministic: the first match of each kind by customer id."""
    with_profile = [e["customer_id"] for e in t["enrolments"] if e["profile_created_date"]]
    cust = {c["customer_id"]: c for c in t["customers"]}
    picks = []
    ctl = next(c for c in with_profile if lanes[cust[c]["primary_lane_id"]]["direction"] == "Import" and any(
        f.check == "ca_screening" for f in efind[c]))
    exp = next(c for c in with_profile if lanes[cust[c]["primary_lane_id"]]["direction"] == "Export")
    picks += [ctl, exp]
    opn = next(c for c in with_profile if c not in picks and any(f.severity != "INFO" for f in efind[c]))
    picks.append(opn)
    return picks


def _classifier(holds, out):
    train, test_seen, test_held = clf.split(holds)
    model = clf.fit(train)
    labels = sorted(hold_reasons())
    rows, result = [], {"n_train": len(train), "n_test_seen": len(test_seen), "n_test_heldout": len(test_held),
                        "labels": labels}
    majority = clf.majority_label(train)
    for split_name, test in (("seen", test_seen), ("heldout", test_held)):
        texts = [h["note"] for h in test]
        y = [h["reason_code"] for h in test]
        pred = list(model.predict(texts))
        kw = [clf.keyword_predict(x) for x in texts]
        res = {"tfidf_logreg": clf.evaluate(y, pred, labels), "keyword_rules": clf.evaluate(y, kw, labels),
               "majority": clf.evaluate(y, [majority] * len(y), labels)}
        res["tfidf_logreg"].update(clf.bootstrap_ci(y, pred, labels))
        res["keyword_rules"].update(clf.bootstrap_ci(y, kw, labels))
        result[split_name] = res
        for h, p, k in zip(test, pred, kw):
            rows.append({"hold_id": h["hold_id"], "split": split_name, "note_template": h["note_template"],
                         "true": h["reason_code"], "tfidf_logreg": p, "keyword_rules": k})
    # leave-one-template-index-out: train on notes of 7 template indices, test on the 8th
    folds = []
    pooled_t, pooled_p = [], []
    for k in range(8):
        tr = [h for h in holds if clf.template_index(h["note_template"]) != k]
        te = [h for h in holds if clf.template_index(h["note_template"]) == k]
        m = clf.fit(tr)
        p = list(m.predict([h["note"] for h in te]))
        y = [h["reason_code"] for h in te]
        e = clf.evaluate(y, p, labels)
        folds.append({"template_index": k, "n": e["n"], "accuracy": e["accuracy"], "macro_f1": e["macro_f1"]})
        pooled_t += y
        pooled_p += p
    pooled = clf.evaluate(pooled_t, pooled_p, labels)
    result["leave_one_template_out"] = {"folds": folds, "pooled_accuracy": pooled["accuracy"],
                                        "pooled_macro_f1": pooled["macro_f1"]}
    result["llm"] = _llm_metrics(rows, labels)
    write_csv(out / "results" / "classifier" / "predictions.csv", rows,
              ["hold_id", "split", "note_template", "true", "tfidf_logreg", "keyword_rules"])
    write_json(out / "results" / "classifier" / "metrics.json", result)
    return {k: result[k] for k in ("n_train", "n_test_seen", "n_test_heldout")} | {
        "seen_accuracy": result["seen"]["tfidf_logreg"]["accuracy"],
        "seen_macro_f1": result["seen"]["tfidf_logreg"]["macro_f1"],
        "heldout_accuracy": result["heldout"]["tfidf_logreg"]["accuracy"],
        "heldout_macro_f1": result["heldout"]["tfidf_logreg"]["macro_f1"],
        "heldout_accuracy_95ci": result["heldout"]["tfidf_logreg"]["accuracy_95ci"],
        "heldout_keyword_accuracy": result["heldout"]["keyword_rules"]["accuracy"],
        "heldout_majority_accuracy": result["heldout"]["majority"]["accuracy"],
        "loto_accuracy": result["leave_one_template_out"]["pooled_accuracy"],
        "loto_macro_f1": result["leave_one_template_out"]["pooled_macro_f1"],
        "llm": {k: v for k, v in result["llm"].items() if k != "per_split_detail"},
    }


def _llm_metrics(rows, labels):
    """Metrics of the cached local-LLM predictions (scripts/run_llm_baseline.py), on the same test notes."""
    if not LLM_CACHE.exists():
        return {"status": "not run"}
    with open(LLM_CACHE, encoding="utf-8", newline="") as fh:
        cache = list(csv.DictReader(fh))
    by_id = {r["hold_id"]: r for r in cache}
    meta = {k: cache[0][k] for k in ("model", "ollama_version", "prompt_sha256")} if cache else {}
    out = {"status": "cached", **meta}
    for split_name in ("seen", "heldout"):
        test = [r for r in rows if r["split"] == split_name]
        missing = [r["hold_id"] for r in test if r["hold_id"] not in by_id]
        if missing:
            out[split_name] = {"status": f"cache misses {len(missing)} of {len(test)} test notes"}
            continue
        y = [r["true"] for r in test]
        p = [by_id[r["hold_id"]]["label"] for r in test]
        e = clf.evaluate(y, p, labels)
        e.update(clf.bootstrap_ci(y, p, labels))
        e["invalid_outputs"] = sum(by_id[r["hold_id"]]["label"] == "INVALID" for r in test)
        lat = sorted(float(by_id[r["hold_id"]]["seconds"]) for r in test)
        e["median_seconds"] = lat[len(lat) // 2]
        out[split_name] = {k: e[k] for k in ("n", "accuracy", "macro_f1", "accuracy_95ci", "macro_f1_95ci",
                                             "invalid_outputs", "median_seconds")}
    return out


def _expected_visual_values(frames):
    """What the main visuals should show once the report is rendered (pandas KPIs, SYNTHETIC data)."""
    rows = []

    def add(page, visual, category, measure, ctx):
        rows.append({"page": page, "visual": visual, "category": category, "measure": measure,
                     "value": K.value(measure, frames, ctx)})

    for m in ("Enrolments Submitted", "Profiles Created", "Three Shipments Completed"):
        add("onboarding", "onb_cards", "", m, {})
    for _, r in frames["DimStage"].iterrows():
        ctx = {"DimStage.Stage": {r["Stage"]}}
        for m in ("Enrolments at Stage", "Stage Conversion %", "Step Conversion %", "Median Days to Stage"):
            add("onboarding", "onb_stage_table", r["Stage"], m, ctx)
    for m in ("First-3 Shipments", "Held Shipments", "First-3 Hold Rate %", "Customers With a Hold %",
              "Avg Readiness Score"):
        add("first_three", "f3_cards", "", m, {})
    for seq in (1, 2, 3):
        add("first_three", "f3_by_seq", str(seq), "First-3 Hold Rate %", {"FactShipment.ShipmentSeq": {seq}})
    for _, r in frames["DimLane"].iterrows():
        add("first_three", "f3_by_lane", r["LaneName"], "First-3 Hold Rate %", {"DimLane.LaneName": {r["LaneName"]}})
        for m in ("Median Clearance Hours", "P90 Clearance Hours"):
            add("clearance", "cl_by_lane", r["LaneName"], m, {"DimLane.LaneName": {r["LaneName"]}})
    for _, r in frames["DimReason"].iterrows():
        ctx = {"DimReason.ReasonLabel": {r["ReasonLabel"]}}
        for m in ("Holds", "Hold Share %", "Hold Pareto Cumulative %", "Median Hours to Release",
                  "P90 Hours to Release"):
            add("hold_reasons", "hr_table", r["ReasonLabel"], m, ctx)
    for m in ("Actions", "Open Actions", "Overdue Actions", "Avg Days to Close", "Closed On Time %"):
        add("action_log", "al_cards", "", m, {})
    return rows
