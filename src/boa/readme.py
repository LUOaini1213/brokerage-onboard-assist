"""README.md is rendered from README.template.md; every number in it comes from the results files.

Placeholders look like {{key}}. scripts/build_all.py calls update_readme(); tests/test_readme.py renders the
template again from the committed results and fails if README.md differs, so a number cannot be typed by hand or go
stale.
"""
import re

from .io import read_json, write_text
from .paths import DOCS, RESULTS, ROOT

TEMPLATE = ROOT / "README.template.md"
README = ROOT / "README.md"
PLACEHOLDER = re.compile(r"\{\{([a-z0-9_]+)\}\}")


def pct(x, nd=1):
    return f"{100 * x:.{nd}f}%"


def numbers(summary, metrics, mutation):
    s, c = summary, summary["classifier"]
    r, f = s["readiness"], s["funnel"]
    held = metrics["heldout"]
    loto = metrics["leave_one_template_out"]["folds"]
    worst = min(loto, key=lambda x: x["accuracy"])
    n = {
        "rules_total": str(s["rules"]["total"]), "rules_sg": str(s["rules"]["SG"]), "rules_au": str(s["rules"]["AU"]),
        "rules_verified": str(s["rules"].get("verified", 0)),
        "rules_partial": str(s["rules"].get("partially verified", 0)),
        "rules_unverified": str(s["rules"].get("not verified", 0)),
        "n_customers": f"{s['counts']['customers']:,}", "n_shipments": f"{s['counts']['shipments']:,}",
        "n_holds": f"{s['counts']['holds']:,}", "n_actions": f"{s['counts']['actions']:,}",
        "funnel_submitted": f"{f['Enrolments Submitted']:,}", "funnel_profiles": f"{f['Profiles Created']:,}",
        "funnel_three": f"{f['Three Shipments Completed']:,}",
        "funnel_profiles_pct": pct(f["Profiles Created"] / f["Enrolments Submitted"]),
        "funnel_three_pct": pct(f["Three Shipments Completed"] / f["Enrolments Submitted"]),
        "hold_rate": pct(s["first3"]["hold_rate"]),
        "hold_rate_1": pct(s["first3"]["by_seq"]["1"]), "hold_rate_2": pct(s["first3"]["by_seq"]["2"]),
        "hold_rate_3": pct(s["first3"]["by_seq"]["3"]),
        "customers_with_hold": pct(s["first3"]["customers_with_hold_rate"]),
        "pareto_top": s["pareto"]["top"], "pareto_top_share": pct(s["pareto"]["top_share"]),
        "pareto_vital_n": str(len(s["pareto"]["vital_few"])), "pareto_vital_share": pct(s["pareto"]["vital_few_share"]),
        "release_median": f"{s['release']['median_hours_all']:.1f}",
        "release_slowest": s["release"]["slowest_reason"], "release_slowest_h": f"{s['release']['slowest_median']:.1f}",
        "release_fastest": s["release"]["fastest_reason"], "release_fastest_h": f"{s['release']['fastest_median']:.1f}",
        "clearance_median": f"{s['clearance']['median_hours_all']:.1f}",
        "clearance_slowest": s["clearance"]["slowest_lane"],
        "clearance_slowest_h": f"{s['clearance']['slowest_lane_median']:.1f}",
        "clearance_fastest": s["clearance"]["fastest_lane"],
        "clearance_fastest_h": f"{s['clearance']['fastest_lane_median']:.1f}",
        "detect_same": pct(r["detected_same_reason"]), "detect_any": pct(r["detected_any_blocking"]),
        "flagged_n": f"{r['flagged_shipments']:,}", "flagged_rate": pct(r["flagged_hold_rate"]),
        "unflagged_n": f"{r['unflagged_shipments']:,}", "unflagged_rate": pct(r["unflagged_hold_rate"]),
        "band_ready": f"{r['bands'].get('Ready', 0):,}", "band_attention": f"{r['bands'].get('Needs attention', 0):,}",
        "band_not_ready": f"{r['bands'].get('Not ready', 0):,}",
        "actions_open": f"{s['actions']['open']:,}", "actions_overdue": f"{s['actions']['overdue']:,}",
        "actions_on_time": pct(s["actions"]["closed_on_time"]),
        "actions_days": f"{s['actions']['avg_days_to_close']:.1f}",
        "clf_train": str(c["n_train"]), "clf_seen_n": str(c["n_test_seen"]), "clf_held_n": str(c["n_test_heldout"]),
        "clf_seen_acc": pct(c["seen_accuracy"]), "clf_held_acc": pct(c["heldout_accuracy"]),
        "clf_held_ci": f"{pct(c['heldout_accuracy_95ci'][0])} to {pct(c['heldout_accuracy_95ci'][1])}",
        "clf_held_f1": f"{c['heldout_macro_f1']:.2f}",
        "clf_seen_kw": pct(metrics["seen"]["keyword_rules"]["accuracy"]),
        "clf_held_kw": pct(held["keyword_rules"]["accuracy"]),
        "clf_seen_major": pct(metrics["seen"]["majority"]["accuracy"]),
        "clf_held_major": pct(held["majority"]["accuracy"]),
        "clf_loto_acc": pct(c["loto_accuracy"]), "clf_loto_f1": f"{c['loto_macro_f1']:.2f}",
        "clf_loto_worst": pct(worst["accuracy"]), "clf_loto_worst_k": str(worst["template_index"]),
        "llm_rows": llm_rows(c["llm"]), "llm_sentence": llm_sentence(c["llm"], c),
        "mutation": (f"{mutation['killed']} of {mutation['total']}" if mutation else "not run yet"),
    }
    n.update(rule_check_counts())
    return n


def rule_check_counts():
    """Verdict counts read from the table in docs/rule_check.md."""
    counts = {"confirmed": 0, "partly confirmed": 0, "contradicted": 0}
    for line in (DOCS / "rule_check.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0].startswith(("SG-", "AU-")):
            counts[cells[2]] += 1
    return {"rulecheck_confirmed": str(counts["confirmed"]), "rulecheck_partly": str(counts["partly confirmed"]),
            "rulecheck_contradicted": "none" if counts["contradicted"] == 0 else str(counts["contradicted"])}


def _llm_done(llm, split):
    return isinstance(llm.get(split), dict) and "accuracy" in llm[split]


def llm_rows(llm):
    if llm.get("status") != "cached":
        return "| Local LLM (zero-shot) | not run | not run |"
    cells = []
    for split in ("seen", "heldout"):
        if _llm_done(llm, split):
            e = llm[split]
            cells.append(f"{pct(e['accuracy'])} ({pct(e['accuracy_95ci'][0])} to {pct(e['accuracy_95ci'][1])})")
        else:
            cells.append("not complete")
    return f"| Local LLM, {llm['model']} through Ollama {llm['ollama_version']}, zero-shot | {cells[0]} | {cells[1]} |"


def llm_sentence(llm, c):
    if llm.get("status") != "cached" or not _llm_done(llm, "heldout"):
        return ("The optional local-LLM comparison (`scripts/run_llm_baseline.py`) has not been run to completion, "
                "so no LLM result is reported.")
    e = llm["heldout"]
    diff = e["accuracy"] - c["heldout_accuracy"]
    lo, hi = e["accuracy_95ci"]
    clo, chi = c["heldout_accuracy_95ci"]
    if lo > chi:
        verdict = "higher than the TF-IDF model's, and the two bootstrap intervals do not overlap"
    elif hi < clo:
        verdict = "lower than the TF-IDF model's, and the two bootstrap intervals do not overlap"
    else:
        verdict = ("higher" if diff > 0 else "lower") + " than the TF-IDF model's, but the bootstrap intervals overlap"
    return (f"On the held-out-template notes the zero-shot local LLM ({llm['model']}, no training notes, answer "
            f"constrained to the 11 codes) reaches {pct(e['accuracy'])} accuracy and macro-F1 {e['macro_f1']:.2f}, "
            f"{verdict}. It returned {e['invalid_outputs']} invalid answers and took a median of "
            f"{e['median_seconds']:.1f} s per note on a laptop GPU while other jobs were running (the linear model's "
            f"prediction time was not measured). This is one run with one prompt and one small model, on clean "
            f"synthetic notes whose templates and reason descriptions were written by the same author: it shows "
            f"that here the LLM depends less on the wording of the templates, not how either method would do on "
            f"real notes.")


def render(template, nums):
    def sub(m):
        key = m.group(1)
        if key not in nums:
            raise KeyError(f"README placeholder {{{{{key}}}}} has no generated value")
        return nums[key]
    return PLACEHOLDER.sub(sub, template)


def current():
    summary = read_json(RESULTS / "summary.json")
    metrics = read_json(RESULTS / "classifier" / "metrics.json")
    mpath = RESULTS / "mutation_report.json"
    mutation = read_json(mpath) if mpath.exists() else None
    return render(TEMPLATE.read_text(encoding="utf-8"), numbers(summary, metrics, mutation))


def update_readme(_summary=None):
    write_text(README, current())
