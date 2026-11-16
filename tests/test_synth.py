"""The SYNTHETIC data generator: deterministic, labelled, internally consistent, and every parameter documented."""
from collections import Counter, defaultdict
from datetime import date, timedelta

import pytest

from boa import hs
from boa.data import read_tables, write_tables
from boa.docs_render import assumptions_markdown
from boa.io import read_json
from boa.note_templates import HELD_OUT_TEMPLATES, TEMPLATES
from boa.paths import CONFIG, DOCS, SYNTHETIC
from boa.rules import hold_reasons
from boa.synth import Config, generate, load_config


@pytest.fixture(scope="module")
def tables(tmp_path_factory):
    """Freshly generated tables, written and read back the way the pipeline does it, so the consistency checks
    below test the generator itself (tests/test_pipeline.py compares the committed files with a rebuild)."""
    folder = tmp_path_factory.mktemp("synth")
    write_tables(generate(), folder)
    return read_tables(folder)


def test_generation_is_deterministic_and_same_size_as_committed(tables):
    a, b = generate(), generate()
    assert a == b
    committed = read_tables(SYNTHETIC)
    assert {k: len(v) for k, v in committed.items()} == {k: len(v) for k, v in tables.items()}
    assert [h["note"] for h in committed["holds"]] == [h["note"] for h in tables["holds"]]


def test_every_row_is_labelled_synthetic(tables):
    for name, rows in tables.items():
        assert rows, name
        assert {r["data_label"] for r in rows} == {"SYNTHETIC"}, name
    assert all(c["customer_name"].startswith("Synthetic Customer ") for c in tables["customers"])
    # UENs are format-valid but use registration year 2099, which no real entity can have (or are defective)
    for c in tables["enrolments"]:
        assert c["uen_submitted"] == "" or c["uen_submitted"].startswith(("2099", "099"))


def test_every_parameter_is_documented_and_used():
    raw = read_json(CONFIG / "synth_assumptions.json")
    used = set()

    class Spy(Config):
        def __getitem__(self, key):
            used.add(key)
            return super().__getitem__(key)

    generate(Spy(raw))
    documented = {k for k in raw if not k.startswith("_")}
    used_by_pipeline = {"fx_sgd_to_aud"}   # read by the validator step of the pipeline, not by the generator
    assert used | used_by_pipeline == documented, f"unused: {documented - used - used_by_pipeline}"
    for k in documented:
        assert raw[k]["label"] in ("ASSUMPTION", "ILLUSTRATIVE") and len(raw[k]["about"]) > 20, k


def test_assumptions_doc_is_current():
    text = assumptions_markdown(read_json(CONFIG / "synth_assumptions.json"))
    expected = text if text.endswith("\n") else text + "\n"
    assert (DOCS / "assumptions.md").read_text(encoding="utf-8") == expected, "run python scripts/build_all.py"


def test_commodity_codes_are_real_hs2022_subheadings():
    cfg = load_config()
    for g in cfg["commodities"]:
        for h6 in g["hs6"]:
            assert h6 in hs.hs6_codes(), h6
            assert h6 in cfg["product_descriptions"], h6
    bad = cfg["outdated_or_malformed_hs"]
    assert all(not hs.is_valid(c, "SG") for c in bad)


def test_first_three_shipments(tables):
    by_customer = defaultdict(list)
    for s in tables["shipments"]:
        by_customer[s["customer_id"]].append(s)
    for cid, ships in by_customer.items():
        seqs = [s["shipment_seq"] for s in sorted(ships, key=lambda x: x["arrival_at"])]
        assert seqs == list(range(1, len(seqs) + 1)) and len(seqs) <= 3, cid
    for s in tables["shipments"]:
        assert s["departure_at"] < s["arrival_at"] and s["clearance_hours"] > 0


def test_funnel_dates_are_ordered(tables):
    keys = ["submitted_date", "documents_received_date", "validated_date", "profile_created_date",
            "first_shipment_released_date", "third_shipment_released_date"]
    as_of = date.fromisoformat(load_config()["as_of_date"])
    for e in tables["enrolments"]:
        reached = [e[k] for k in keys]
        filled = [d for d in reached if d]
        assert reached[:len(filled)] == filled, e["enrolment_id"]       # no stage skipped
        assert filled == sorted(filled) and date.fromisoformat(filled[-1]) <= as_of


def test_holds_agree_with_shipments(tables):
    ships = {s["shipment_id"]: s for s in tables["shipments"]}
    holds_per = Counter(h["shipment_id"] for h in tables["holds"])
    for sid, s in ships.items():
        assert s["hold_count"] == holds_per.get(sid, 0) and s["held"] == (holds_per.get(sid, 0) > 0)
    reasons = set(hold_reasons())
    for h in tables["holds"]:
        s = ships[h["shipment_id"]]
        assert h["reason_code"] in reasons and h["customer_id"] == s["customer_id"] and h["lane_id"] == s["lane_id"]
        start = s["departure_at"] if (h["reason_code"] == "PERMIT_TIMING" and s["direction"] == "Export") \
            else s["arrival_at"]
        assert h["hold_start"] >= start
        if h["hours_to_release"] is not None:
            assert h["released_at"] > h["hold_start"] and h["hours_to_release"] > 0
        assert h["note"].strip()
        code, idx = h["note_template"].rsplit("-", 1)
        assert code == h["reason_code"] and 0 <= int(idx) < len(TEMPLATES[code])
    assert max(holds_per.values()) <= load_config()["max_holds_per_shipment"]


def test_actions_are_consistent(tables):
    cfg = load_config()
    as_of = date.fromisoformat(cfg["as_of_date"])
    hold_ids = {h["hold_id"] for h in tables["holds"]}
    for a in tables["actions"]:
        opened, due = date.fromisoformat(a["opened_date"]), date.fromisoformat(a["due_date"])
        assert due == opened + timedelta(days=cfg["action_sla_days"])
        if a["status"] == "Closed":
            assert opened <= date.fromisoformat(a["closed_date"]) <= as_of
        else:
            assert a["status"] == "Open" and a["closed_date"] == ""
        assert (a["source"] == "Hold") == bool(a["hold_id"])
        if a["hold_id"]:
            assert a["hold_id"] in hold_ids
        assert a["owner_role"] in cfg["action_owner_roles"]
    assert {h["hold_id"] for h in tables["holds"]} <= {a["hold_id"] for a in tables["actions"]}


def test_note_templates_have_held_out_phrasings():
    assert set(TEMPLATES) == set(hold_reasons())
    for code, tpls in TEMPLATES.items():
        assert len(tpls) == 8 and all(i < len(tpls) for i in HELD_OUT_TEMPLATES), code
        assert len(set(tpls)) == 8, code


def test_defects_truth_table_matches_reasons(tables):
    allowed = set(hold_reasons()) | {""}
    for d in tables["shipment_defects"]:
        assert d["reason_code"] in allowed
    # a hold for a document reason always has a latent defect with that reason (INSPECTION is random)
    truth = defaultdict(set)
    for d in tables["shipment_defects"]:
        truth[d["shipment_id"]].add(d["reason_code"])
    for h in tables["holds"]:
        if h["reason_code"] != "INSPECTION":
            assert h["reason_code"] in truth[h["shipment_id"]], h["hold_id"]
