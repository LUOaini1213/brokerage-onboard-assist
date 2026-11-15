"""Load the rulebook (rules/*.json, rules/*.csv) and render docs/rulebook.md from it."""
from dataclasses import dataclass
from functools import lru_cache

from .io import read_csv_rows, read_json
from .paths import RULES

STATUSES = ("verified", "partially verified", "not verified")


@lru_cache(maxsize=None)
def rulebook():
    return read_json(RULES / "rulebook.json")


@lru_cache(maxsize=None)
def sources():
    return {s["id"]: s for s in read_json(RULES / "sources.json")["sources"]}


def rules():
    return rulebook()["rules"]


def rule(rule_id):
    for r in rules():
        if r["id"] == rule_id:
            return r
    raise KeyError(rule_id)


@lru_cache(maxsize=None)
def hold_reasons():
    rows = read_csv_rows(RULES / "hold_reasons.csv")
    for r in rows:
        r["rule_ids"] = r["rule_ids"].split(";")
    return {r["reason_code"]: r for r in rows}


@dataclass(frozen=True)
class Screen:
    hs_prefix: str
    authority: str
    kind: str          # controlled | dutiable | prohibited
    scope: str
    licence_to_ask_for: str
    rule_id: str


@lru_cache(maxsize=None)
def sg_screening():
    return tuple(Screen(r["hs_prefix"], r["authority"], r["kind"], r["scope"], r["licence_to_ask_for"], r["rule_id"])
                 for r in read_csv_rows(RULES / "sg_ca_screening.csv"))


@lru_cache(maxsize=None)
def sg_flat_rates():
    """{ISO country code: flat freight+insurance rate as a fraction of FOB} (SG-IMP-08)."""
    out = {}
    for r in read_csv_rows(RULES / "sg_flat_freight_insurance.csv"):
        for code in r["country_codes_mapped_here"].split(";"):
            out[code] = float(r["flat_rate_pct_of_fob"]) / 100.0
    return out


@lru_cache(maxsize=None)
def au_biosecurity_chapters():
    return frozenset(r["hs_chapter"] for r in read_csv_rows(RULES / "au_biosecurity_screening.csv"))


def render_markdown():
    """docs/rulebook.md, generated: do not edit by hand."""
    src = sources()
    lines = [
        "# Rulebook: customs-hold causes and document-readiness checks",
        "",
        "Generated from `rules/rulebook.json` and `rules/sources.json` by `scripts/build_all.py`; edit those files, "
        "not this one.",
        "",
        "Requirements are **paraphrased** from official public pages and were read on the access date shown. They "
        "are a study aid for a portfolio project, not customs or legal advice; check the live page before relying on "
        "any of them. The second, independent check of every rule is in [rule_check.md](rule_check.md).",
        "",
        "Status: **verified** = the requirement as written was found in the cited source; **partially verified** = "
        "the core requirement was found but a detail used here (a tolerance, a base, a mapping) was not; **not "
        "verified** = no cited source states it (a derived rule or common practice).",
        "",
    ]
    counts = {s: sum(r["status"] == s for r in rules()) for s in STATUSES}
    lines.append(f"{len(rules())} rules: " + ", ".join(f"{n} {s}" for s, n in counts.items()) + ".")
    lines.append("")
    lines += ["| Rule | Title | Hold reasons | Automated check | Status |", "|---|---|---|---|---|"]
    for r in rules():
        lines.append(f"| [{r['id']}](#{r['id'].lower()}) | {r['title']} | {', '.join(r['hold_reasons']) or '-'} | "
                     f"{r['automated_check'] or 'manual'} | {r['status']} |")
    lines.append("")
    sections = [("SG", "import", "Singapore imports"), ("SG", "both", "Singapore imports and exports"),
                ("SG", "export", "Singapore exports"), ("AU", "import", "Australia imports (second destination)")]
    for jur, flow, heading in sections:
        group = [r for r in rules() if r["jurisdiction"] == jur and r["flow"] == flow]
        if not group:
            continue
        lines += [f"## {heading}", ""]
        for r in group:
            lines += [f"### {r['id']}", "", f"**{r['title']}** ({r['topic']}; status: {r['status']})", "",
                      r["requirement"], "", f"- Readiness check: {r['readiness_check']}"]
            if r["corrective_action"]:
                lines.append(f"- Corrective action: {r['corrective_action']}")
            if r["assumptions"]:
                lines.append("- Assumptions: " + " ".join(r["assumptions"]))
            if r["status_note"]:
                lines.append(f"- Note: {r['status_note']}")
            for s in r["sources"]:
                meta = src[s["id"]]
                lines.append(f"- Source: {meta['publisher']}, [{meta['title']}]({meta['url']}) ({s['where']}); "
                             f"accessed {meta['accessed']}")
            lines.append("")
    lines += ["## Hold reason codes", "", "| Code | Label | Rules | Detectable before lodgement | Corrective action |",
              "|---|---|---|---|---|"]
    for code, h in hold_reasons().items():
        lines.append(f"| {code} | {h['label']} | {', '.join(h['rule_ids'])} | {h['detectable_before_lodgement']} | "
                     f"{h['corrective_action']} |")
    lines += ["", "## Screening tables", "",
              "- `rules/sg_ca_screening.csv`: HS prefixes mapped to Singapore competent authorities, dutiable "
              "categories and prohibited goods. The mapping is this project's **screening heuristic**: Singapore "
              "Customs decides control by HS and CA product code (HS/CA Product Code Checker), which is not used here. "
              "Chapter 33 (cosmetics) is deliberately absent (SG-IMP-16).",
              "- `rules/sg_flat_freight_insurance.csv`: the flat freight-and-insurance rates of SG-IMP-08, with the "
              "country codes this project maps to each published region.",
              "- `rules/au_biosecurity_screening.csv`: HS chapters for which a BICON check is suggested (AU-07); a "
              "screening heuristic.", ""]
    return "\n".join(lines)
