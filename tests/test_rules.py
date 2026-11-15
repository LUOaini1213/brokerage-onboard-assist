"""The rulebook's structure: every rule cites a registered official source with an access date, carries a status,
links to known hold reasons and validator checks, and docs/rulebook.md is current."""
import csv
import re

from boa import rules as R
from boa.paths import DOCS, RULES

ALLOWED_TOPICS = {"permit", "party", "classification", "valuation", "tax", "controlled_goods", "origin",
                  "documents", "amendment", "biosecurity", "labelling"}
VALIDATOR_CHECKS = {"permit_before_arrival", "permit_before_departure", "customs_account_active",
                    "uen_present_and_format", "importer_matches_profile", "hs_format_and_hs6", "cif_consistency",
                    "invoice_fields_complete", "gst_estimate", "dutiable_screening", "ca_screening",
                    "prohibited_screening", "origin_consistency", "preference_proof", "incoterm_present",
                    "docs_present", "corrective_action_route", "quantity_weight_consistency", "au_declaration_type",
                    "au_voti_gst", "au_abn_quoted", "au_biosecurity_screening"}


def test_every_rule_is_complete():
    ids = [r["id"] for r in R.rules()]
    assert len(ids) == len(set(ids))
    for r in R.rules():
        assert re.fullmatch(r"(SG-(IMP|EXP)|AU)-\d\d", r["id"]), r["id"]
        assert r["jurisdiction"] == r["id"][:2]
        assert r["flow"] in ("import", "export", "both")
        assert r["topic"] in ALLOWED_TOPICS, r["id"]
        assert r["status"] in R.STATUSES, r["id"]
        assert r["title"] and len(r["requirement"]) > 40 and r["readiness_check"], r["id"]
        assert r["sources"], f"{r['id']} cites no source"
        if r["status"] != "verified":
            assert r["status_note"], f"{r['id']} is {r['status']} but does not say why"
        if r["automated_check"] is not None:
            assert r["automated_check"] in VALIDATOR_CHECKS, r["id"]


def test_sources_are_official_and_dated():
    official = ("customs.gov.sg", "isomer-user-content.by.gov.sg", "iras.gov.sg", "abf.gov.au", "abs.gov.au",
                "agriculture.gov.au", "oecd.org")
    for sid, s in R.sources().items():
        assert s["url"].startswith("https://") and any(d in s["url"] for d in official), sid
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["accessed"]), sid
        assert s["publisher"] and s["title"] and s["read_with"], sid
    used = {src["id"] for r in R.rules() for src in r["sources"]}
    assert used <= set(R.sources()), used - set(R.sources())
    assert set(R.sources()) <= used, "a registered source is not cited by any rule"


def test_hold_reasons_link_to_rules():
    ids = {r["id"] for r in R.rules()}
    reasons = R.hold_reasons()
    assert len(reasons) == 11
    for code, h in reasons.items():
        assert set(h["rule_ids"]) <= ids, code
        assert h["detectable_before_lodgement"] in ("yes", "no", "partly")
    for r in R.rules():
        assert set(r["hold_reasons"]) <= set(reasons), r["id"]


def test_second_destination_is_smaller_and_both_sg_flows_covered():
    sg = [r for r in R.rules() if r["jurisdiction"] == "SG"]
    au = [r for r in R.rules() if r["jurisdiction"] == "AU"]
    assert 5 <= len(au) < len(sg)
    assert any(r["flow"] == "export" for r in sg) and any(r["flow"] == "import" for r in sg)


def test_screening_tables_point_at_rules():
    ids = {r["id"] for r in R.rules()}
    for s in R.sg_screening():
        assert s.rule_id in ids and s.kind in ("controlled", "dutiable", "prohibited") and s.hs_prefix.isdigit()
    # cosmetics are deliberately not screened (SG-IMP-16: not subject to HSA licensing before import)
    assert not [s for s in R.sg_screening() if s.hs_prefix.startswith("33")]
    with open(RULES / "au_biosecurity_screening.csv", encoding="utf-8", newline="") as fh:
        assert all(r["rule_id"] == "AU-07" for r in csv.DictReader(fh))


def test_flat_rates_table():
    rates = R.sg_flat_rates()
    assert rates["US"] == 0.245 and rates["CN"] == 0.155 and rates["DE"] == 0.19 and rates["MY"] == 0.05
    assert rates["VN"] == 0.095 and rates["JP"] == 0.19
    assert "BN" not in rates   # not in the published table


def test_rulebook_markdown_is_current():
    text = R.render_markdown()
    expected = text if text.endswith("\n") else text + "\n"
    assert (DOCS / "rulebook.md").read_text(encoding="utf-8") == expected, "run python scripts/build_all.py"


def test_rule_check_log_covers_every_rule_with_its_final_status():
    rows = {}
    for line in (DOCS / "rule_check.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and re.fullmatch(r"(SG-(IMP|EXP)|AU)-\d\d", cells[0]):
            rows[cells[0]] = cells
    assert set(rows) == {r["id"] for r in R.rules()}
    for r in R.rules():
        verdict, final = rows[r["id"]][2], rows[r["id"]][6]
        assert verdict in ("confirmed", "partly confirmed", "contradicted"), r["id"]
        assert final == r["status"], f"{r['id']}: rule_check.md says {final}, rulebook says {r['status']}"
