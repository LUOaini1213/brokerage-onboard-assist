"""Mutation check: plant one deliberate bug at a time and require the tests to fail.

"All tests pass" says little unless the tests can fail. Each mutant below changes one thing in a copy of the
repository (valuation, HS and UEN checks, validator rules, analytics, KPIs, the classifier's split and metrics, a
DAX measure, a relationship, the DAX evaluator, the generator, a rule table) and runs the test files meant to catch
it. A mutant that leaves those tests green has survived, and the check fails.

Two controls run first: the unmodified copy must pass, and a harmless edit (a changed comment) must survive, so a
broken runner cannot pass by failing everything.

The tests that only say "a committed file is out of date" (generator-reproduces-file and rebuild-equals-committed
tests) are never used to kill a mutant: they would catch any edit for a trivial reason.

    python mutation/mutate.py              # all mutants; writes results/mutation_report.json and mutation_report.md
    python mutation/mutate.py -k Dax       # only mutants whose id contains the text (no report written)
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY = ["src", "pbitest", "tests", "tools", "rules", "config", "data", "results", "powerbi", "docs", "power-platform",
        "checks", "pytest.ini", "README.md", "README.template.md"]
V, H, U, VAL, AN, K, C, S = ("src/boa/valuation.py", "src/boa/hs.py", "src/boa/uen.py", "src/boa/validator.py",
                             "src/boa/analytics.py", "src/boa/kpis.py", "src/boa/classifier.py", "src/boa/synth.py")
TABLES = "powerbi/BrokerageOnboard.SemanticModel/definition/tables/"
T_VALUATION = ["tests/test_valuation.py"]
T_HS = ["tests/test_hs_uen.py"]
T_VALIDATOR = ["tests/test_validator.py"]
T_ANALYTICS = ["tests/test_analytics.py"]
T_KPI = ["tests/test_kpis.py"]
T_DAX = ["tests/test_kpis.py", "tests/test_measures.py"]
T_ENGINE = ["tests/test_dax_engine.py"]
T_CLF = ["tests/test_classifier.py"]
T_SYNTH = ["tests/test_synth.py"]
T_RULES = ["tests/test_rules.py", "tests/test_valuation.py"]

# (id, file, old text, new text, tests that must fail, what the bug is)
MUTANTS = [
    # --- valuation and tax arithmetic
    ("Gst_rate_8pct", V, "SG_GST_RATE = 0.09", "SG_GST_RATE = 0.08", T_VALUATION, "Singapore GST at the 2023 rate"),
    ("Gst_ignores_duty", V, "return round(rate * (customs_value_sgd + duty_sgd), 2)",
     "return round(rate * customs_value_sgd, 2)", T_VALUATION, "GST base leaves out the duty"),
    ("Cif_fob_drops_insurance", V, 'return Value(round(base + freight + insurance, 2), "+ actual freight and insurance")',
     'return Value(round(base + freight, 2), "+ actual freight and insurance")', T_VALUATION,
     "FOB invoice: insurance not added to the CIF value"),
    ("Cif_flat_rate_for_fca", V, 'if term == "FOB" and freight is None and insurance is None:',
     'if term in ("FOB", "FCA") and freight is None and insurance is None:', T_VALUATION,
     "flat freight-and-insurance rate applied to FCA quotes (published for FOB only)"),
    ("Cif_cfr_flat_insurance_2pct", V, "CFR_FLAT_INSURANCE = 0.01", "CFR_FLAT_INSURANCE = 0.02", T_VALUATION,
     "flat CFR insurance doubled"),
    ("Fob_keeps_insurance_in_cif_price", V,
     'v = Value(round(invoice_total - freight - insurance, 2), "- international freight and insurance")',
     'v = Value(round(invoice_total - freight, 2), "- international freight and insurance")', T_VALUATION,
     "FOB value from a CIF price leaves the insurance in"),
    ("Au_voti_drops_transport", V, "return round(customs_value_aud + transport_insurance_aud + duty_aud + wet_aud, 2)",
     "return round(customs_value_aud + duty_aud + wet_aud, 2)", T_VALUATION,
     "Australian GST base without transport and insurance"),
    ("Au_n10_threshold_inclusive", V, "if value_aud > AU_N10_THRESHOLD_AUD:", "if value_aud >= AU_N10_THRESHOLD_AUD:",
     T_VALUATION, "Import Declaration required at exactly AUD 1,000 (rule: over 1,000)"),
    # --- HS and UEN
    ("Hs_checks_chapter_only", H, "if c[:6] not in hs6_codes():", "if c[:2] not in {x[:2] for x in hs6_codes()}:", T_HS,
     "HS validity tested at chapter level, so deleted subheadings pass"),
    ("Hs_accepts_7_digits", H, '"SG": (8,)', '"SG": (7, 8)', T_HS, "7-digit HS codes accepted for Singapore"),
    ("Uen_lowercase_check_letter", U, r'("local company", re.compile(r"^\d{9}[A-Z]$"))',
     r'("local company", re.compile(r"^\d{9}[A-Za-z]$"))', T_HS, "UEN with a lower-case check letter accepted"),
    # --- validator rules
    ("Score_blocking_weight", VAL, '"BLOCKING": 25', '"BLOCKING": 20', T_VALIDATOR, "readiness score weight changed"),
    ("Band_warning_reads_ready", VAL, '        band = "Needs attention"', '        band = "Ready"', T_VALIDATOR,
     "a shipment with warnings is reported Ready"),
    ("Permit_timing_reversed", VAL, 'if imp and s["permit_submitted_at"] >= s["arrival_at"]:',
     'if imp and s["permit_submitted_at"] <= s["arrival_at"]:', T_VALIDATOR,
     "permit-before-arrival check reversed"),
    ("Value_tolerance_5pct", VAL, "VALUE_TOLERANCE = 0.005", "VALUE_TOLERANCE = 0.05", T_VALIDATOR,
     "declared value may differ by 5% instead of 0.5%"),
    ("Weight_tolerance_5pct", VAL, "WEIGHT_TOLERANCE = 0.02", "WEIGHT_TOLERANCE = 0.05", T_VALIDATOR,
     "gross weights may differ by 5% instead of 2%"),
    ("Licence_date_ignored", VAL,
     'if sc.authority not in b["licences"] or b["licences"][sc.authority] > s["permit_submitted_at"][:10]:',
     'if sc.authority not in b["licences"]:', T_VALIDATOR, "a licence obtained after the permit counts as on file"),
    ("Licence_any_reference_accepted", VAL, 'elif not (refs & b["licence_refs"].get(sc.authority, set())):',
     "elif not refs:", T_VALIDATOR, "any quoted reference satisfies every authority of a line"),
    ("Origin_check_inverted", VAL, "if made and not _blank(declared) and declared != made:",
     "if made and not _blank(declared) and declared == made:", T_VALIDATOR, "origin mismatch check inverted"),
    ("Preference_needs_no_proof", VAL, 'if s["preference_claimed"] and not b["co_present"]:',
     'if s["preference_claimed"] and b["co_present"]:', T_VALIDATOR, "preference without proof of origin passes"),
    ("Sg_controls_applied_to_exports", VAL,
     "    if imp:\n        for ln in lines:\n            refs = set(",
     "    if True:\n        for ln in lines:\n            refs = set(", T_VALIDATOR,
     "Singapore import controls applied to exports"),
    ("Cancel_window_7_days", VAL, "if days_expired <= 1 else disclosure", "if days_expired <= 7 else disclosure",
     T_VALIDATOR, "expired permits treated as cancellable for a week (rule: 1 calendar day)"),
    # --- analytics
    ("Pareto_ascending", AN, "key=lambda kv: (-kv[1], kv[0])", "key=lambda kv: (kv[1], kv[0])", T_ANALYTICS,
     "Pareto sorted from the rarest reason"),
    ("Percentile_lower", AN, 'q * 100, method="linear")', 'q * 100, method="lower")', T_ANALYTICS,
     "percentiles without interpolation (differs from DAX)"),
    ("Vital_few_strict", AN, 'if r["cumulative_share"] >= threshold:', 'if r["cumulative_share"] > threshold:',
     T_ANALYTICS, "vital-few cut-off excludes a reason that lands exactly on the threshold"),
    ("Detection_ignores_warnings", AN, 'x.severity in ("BLOCKING", "WARNING")', 'x.severity in ("BLOCKING",)',
     T_ANALYTICS, "holds flagged only by a warning counted as not detected"),
    # --- KPIs in pandas
    ("Kpi_hold_rate_inverted", K, "return _divide(held_shipments(f, ctx), first3_shipments(f, ctx))",
     "return _divide(first3_shipments(f, ctx), held_shipments(f, ctx))", T_KPI, "hold rate numerator and denominator swapped"),
    ("Kpi_pareto_tie_break", K, "r.upper() <= code.upper()", "r.upper() < code.upper()", T_KPI,
     "Pareto cumulative share leaves out the reason itself when counts tie"),
    ("Kpi_step_conversion_vs_first_stage", K, "_at_stage(f, ctx, s - 1))", "_at_stage(f, ctx, 1))", T_KPI,
     "step conversion divides by the first stage instead of the previous one"),
    # --- classifier evaluation
    ("Clf_heldout_templates_leak", C,
     'seen = [h for h in holds if template_index(h["note_template"]) not in HELD_OUT_TEMPLATES]', "seen = list(holds)",
     T_CLF, "held-out-template notes leak into the training pool"),
    ("Clf_accuracy_is_error_rate", C, "float(np.mean(np.asarray(y_true) == np.asarray(y_pred)))",
     "float(np.mean(np.asarray(y_true) != np.asarray(y_pred)))", T_CLF, "accuracy computed as the error rate"),
    # --- DAX measures and relationships (the committed TMDL), caught by hand values and the pandas twin
    ("Dax_hold_rate_per_customer", TABLES + "FactShipment.tmdl", "DIVIDE([Held Shipments], [First-3 Shipments])",
     "DIVIDE([Held Shipments], [Customers Shipping])", T_DAX, "hold rate divided by customers instead of shipments"),
    ("Dax_median_is_average", TABLES + "FactShipment.tmdl", "MEDIAN(FactShipment[ClearanceHours])",
     "AVERAGE(FactShipment[ClearanceHours])", T_DAX, "median clearance hours computed as the mean"),
    ("Dax_open_actions_overrides_slicer", TABLES + "FactAction.tmdl",
     'CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Open"))',
     'CALCULATE(COUNTROWS(FactAction), FactAction[Status] = "Open")', T_DAX,
     "Open Actions ignores a Status slicer (KEEPFILTERS removed)"),
    ("Dax_pareto_ties_double_counted", TABLES + "FactHold.tmdl", "RETURN n > cur || (n = cur &&",
     "RETURN n >= cur || (n = cur &&", T_DAX, "Pareto cumulative share counts every tied reason"),
    ("Dax_stage_conversion_keeps_stage_filter", TABLES + "FactEnrolmentStage.tmdl",
     "measure 'Enrolments Submitted' = CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = 1)",
     "measure 'Enrolments Submitted' = CALCULATE([Enrolments at Stage], DimStage[StageOrder] = 1)", T_DAX,
     "Enrolments Submitted keeps the selected stage's filter, so conversion is blank or 100%"),
    ("Relationship_hold_lane_on_name", "powerbi/BrokerageOnboard.SemanticModel/definition/relationships.tmdl",
     "\tfromColumn: FactHold.LaneId\n\ttoColumn: DimLane.LaneId", "\tfromColumn: FactHold.LaneId\n\ttoColumn: DimLane.LaneName",
     ["tests/test_measures.py"], "holds joined to lanes on the wrong column"),
    # --- the DAX evaluator itself
    ("Engine_keepfilters_replaces", "pbitest/dax.py", "filters[key] = filters[key] & vals if key in filters else vals",
     "filters[key] = vals", T_ENGINE, "evaluator treats KEEPFILTERS like a plain filter"),
    ("Engine_no_context_transition", "pbitest/dax.py", "inner = self.transition(ctx, row) if row else ctx",
     "inner = ctx", T_ENGINE, "measure references inside an iterator ignore the current row"),
    # --- generator and rule table
    ("Synth_held_flag_always_false", S, '"held": bool(hold_rows)', '"held": False', T_SYNTH,
     "shipments never marked held although hold rows exist"),
    ("Synth_due_date_one_day_late", S, 'timedelta(days=self.c["action_sla_days"])),',
     'timedelta(days=self.c["action_sla_days"] + 1)),', T_SYNTH, "action due dates one day after the documented SLA"),
    ("Rule_table_china_flat_rate", "rules/sg_flat_freight_insurance.csv",
     '"China, Chinese Taipei, Korea, Sri Lanka, India and Pakistan",15.5,',
     '"China, Chinese Taipei, Korea, Sri Lanka, India and Pakistan",15,', T_RULES,
     "published flat rate for China mistyped"),
]

CONTROL = ("Control_comment_edit", VAL, "# --- permit timing (SG-IMP-01, SG-EXP-01)",
           "# --- permit timing (rules SG-IMP-01 and SG-EXP-01)", T_VALIDATOR, "harmless comment change")


def run_tests(base, tests):
    t = time.time()
    p = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", *tests],
                       cwd=base, capture_output=True, text=True)
    lines = p.stdout.strip().splitlines() or [""]
    failed = next((ln.split(" - ")[0].replace("FAILED ", "").replace("ERROR ", "") for ln in lines
                   if ln.startswith(("FAILED", "ERROR"))), "")
    return p.returncode, failed or lines[-1], time.time() - t


def apply(base, path, old, new):
    f = base / path
    text = f.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"mutant anchor found {text.count(old)} times in {path}: {old[:70]!r}")
    f.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return f, text


def write_reports(results):
    killed = sum(r["killed"] for r in results)
    report = {"killed": killed, "total": len(results), "controls": {"unmodified_copy_passes": True,
                                                                      "harmless_edit_survives": True},
              "results": results}
    out = ROOT / "results" / "mutation_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Mutation report", "",
             "Written by `python mutation/mutate.py`. Each mutant is one deliberate bug planted in a copy of the "
             "repository; it is *killed* when the listed tests fail. Controls: the unmodified copy passed, and a "
             "harmless comment edit survived.", "",
             f"**{killed} of {len(results)} mutants killed.**", ""]
    survivors = [r for r in results if not r["killed"]]
    if survivors:
        lines += ["Survivors: " + ", ".join(r["mutant"] for r in survivors), ""]
    else:
        lines += ["No survivors.", ""]
    lines += ["| Mutant | File | Planted bug | Tests run | Result | First failing test |", "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['mutant']} | `{r['file']}` | {r['bug']} | {', '.join(t.replace('tests/', '') for t in r['tests'])} | "
                     f"{'killed' if r['killed'] else 'SURVIVED'} | {r['summary'] if r['killed'] else ''} |")
    (ROOT / "mutation" / "mutation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", default="")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "repo"
        base.mkdir()
        for item in COPY:
            src = ROOT / item
            if src.is_dir():
                shutil.copytree(src, base / item, ignore=shutil.ignore_patterns("__pycache__", "raw"))
            elif src.exists():
                shutil.copy2(src, base / item)
        all_tests = sorted({t for m in MUTANTS for t in m[4]})
        code, last, secs = run_tests(base, all_tests)
        print(f"control  unmodified copy: {'pass' if code == 0 else 'FAIL'}  ({last}, {secs:.0f}s)", flush=True)
        if code != 0:
            raise SystemExit("the unmodified copy must pass before mutants mean anything")
        f, original = apply(base, *CONTROL[1:4])
        code, last, _ = run_tests(base, CONTROL[4])
        f.write_text(original, encoding="utf-8", newline="\n")
        print(f"control  harmless edit survives: {'yes' if code == 0 else 'NO'}  ({last})", flush=True)
        if code != 0:
            raise SystemExit("a harmless edit was reported as a failure; the runner is not trustworthy")
        results = []
        for mid, path, old, new, tests, bug in MUTANTS:
            if a.k and a.k not in mid:
                continue
            f, original = apply(base, path, old, new)
            try:
                code, last, secs = run_tests(base, tests)
            finally:
                f.write_text(original, encoding="utf-8", newline="\n")
            killed = code != 0
            results.append({"mutant": mid, "file": path, "bug": bug, "tests": tests, "killed": killed, "summary": last})
            print(f"{'killed  ' if killed else 'SURVIVED'} {mid:42s} {last}  ({secs:.0f}s)", flush=True)
    survived = [r["mutant"] for r in results if not r["killed"]]
    print(f"\n{len(results) - len(survived)}/{len(results)} mutants killed")
    if not a.k:
        write_reports(results)
    sys.exit(1 if survived else 0)


if __name__ == "__main__":
    main()
