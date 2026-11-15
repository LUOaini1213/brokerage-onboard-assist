"""Hand-built document bundles: each validator rule fires on the defect it is meant to catch and stays quiet on a
clean bundle. Amounts are worked out in the comments."""
import copy

import pytest

from boa.handling_note import draft_note
from boa.validator import corrective_action_route, readiness, validate_enrolment, validate_shipment

FX = {"USD": 1.30, "SGD": 1.0, "AUD": 0.86}
SGD_TO_AUD = 1.16
UEN = "209912345K"


def clean_import():
    # Invoice: 100 T-shirts x USD 5.00 = 500.00 and 50 pairs of shoes x USD 20.00 = 1,000.00; total USD 1,500.00.
    # FOB with actual freight USD 120 and insurance USD 6: CIF = 1,626.00 USD = SGD 2,113.80 at 1.30.
    return {
        "shipment": {"direction": "Import", "mode": "Sea", "loading_country": "CN",
                     "departure_at": "2026-05-01T10:00", "arrival_at": "2026-05-10T08:00",
                     "permit_submitted_at": "2026-05-08T09:00", "freight_on_file": 120.0, "insurance_on_file": 6.0,
                     "inland_costs_on_file": None, "preference_claimed": False, "bicon_check_recorded": None,
                     "consignee_abn_provided": None, "permit_party_uen": UEN, "permit_invoice_total": 1500.0,
                     "permit_declared_value_sgd": 2113.80},
        "customer": {"uen": UEN, "customs_account_active": True},
        "invoice": {"present": True, "invoice_no": "INV-1", "invoice_date": "2026-04-28", "seller_name": "Seller",
                    "buyer_name": "Buyer", "currency": "USD", "incoterm": "FOB", "invoice_total": 1500.0},
        "lines": [
            {"line_no": 1, "product_id": "P1", "description": "cotton T-shirts", "hs_code": "61091000",
             "quantity": 100, "unit": "PCE", "unit_price": 5.0, "line_value": 500.0, "origin_country": "CN",
             "packing_quantity": 100, "ca_licence_ref": ""},
            {"line_no": 2, "product_id": "P2", "description": "sports shoes", "hs_code": "64041100",
             "quantity": 50, "unit": "PCE", "unit_price": 20.0, "line_value": 1000.0, "origin_country": "CN",
             "packing_quantity": 50, "ca_licence_ref": ""}],
        "packing_list": {"present": True, "gross_weight_kg": 210.0},
        "transport_doc": {"present": True, "gross_weight_kg": 210.0},
        "co_present": False, "licences": {}, "product_origin": {"P1": "CN", "P2": "CN"},
    }


def run(b):
    return validate_shipment(b, FX, SGD_TO_AUD)


def non_info(findings):
    return [(f.check, f.reason_code, f.severity) for f in findings if f.severity != "INFO"]


def test_clean_bundle_is_ready_with_gst_estimate():
    f = run(clean_import())
    assert non_info(f) == []
    assert readiness(f) == (100, "Ready")
    gst = [x for x in f if x.check == "gst_estimate"]
    assert len(gst) == 1 and "SGD 190.24" in gst[0].message     # 9% x 2,113.80 = 190.242


def test_missing_incoterm_blocks_and_skips_value_check():
    b = clean_import()
    b["invoice"]["incoterm"] = ""
    assert non_info(run(b)) == [("incoterm_present", "INVOICE_DATA", "BLOCKING")]
    assert readiness(run(b)) == (75, "Not ready")


def test_freight_and_insurance_not_added_is_caught():
    b = clean_import()
    b["shipment"]["permit_declared_value_sgd"] = 1950.0            # 1,500 x 1.30: FOB declared as CIF
    assert non_info(run(b)) == [("cif_consistency", "VALUE_CIF", "BLOCKING")]


def test_value_within_tolerance_passes():
    b = clean_import()
    b["shipment"]["permit_declared_value_sgd"] = round(2113.80 * 1.004, 2)   # 0.4% < 0.5% tolerance
    assert non_info(run(b)) == []
    b["shipment"]["permit_declared_value_sgd"] = round(2113.80 * 1.006, 2)   # 0.6% > 0.5%
    assert non_info(run(b)) == [("cif_consistency", "VALUE_CIF", "BLOCKING")]


def test_flat_rate_used_when_charges_unknown():
    b = clean_import()
    b["shipment"]["freight_on_file"] = b["shipment"]["insurance_on_file"] = None
    b["shipment"]["permit_declared_value_sgd"] = 2252.25   # 1,500 x 1.155 = 1,732.50 USD x 1.30
    assert non_info(run(b)) == []


def test_unknown_charges_without_flat_rate_block():
    b = clean_import()
    b["shipment"]["freight_on_file"] = b["shipment"]["insurance_on_file"] = None
    b["shipment"]["loading_country"] = "BR"   # no published flat rate
    assert non_info(run(b)) == [("cif_consistency", "VALUE_CIF", "BLOCKING")]


def test_permit_total_differs_from_invoice():
    b = clean_import()
    b["shipment"]["permit_invoice_total"] = 1400.0
    assert ("invoice_vs_permit_total", "VALUE_CIF", "BLOCKING") in non_info(run(b))


def test_invoice_arithmetic():
    b = clean_import()
    b["lines"][0]["line_value"] = 520.0        # 100 x 5.00 = 500, and the total no longer matches the lines
    got = non_info(run(b))
    assert ("invoice_arithmetic", "INVOICE_DATA", "WARNING") in got
    assert ("invoice_arithmetic", "INVOICE_DATA", "BLOCKING") in got


@pytest.mark.parametrize("field,severity", [("invoice_no", "BLOCKING"), ("invoice_date", "BLOCKING"),
                                            ("currency", "BLOCKING"), ("seller_name", "WARNING"),
                                            ("buyer_name", "WARNING")])
def test_invoice_header_fields(field, severity):
    b = clean_import()
    b["invoice"][field] = ""
    assert ("invoice_fields_complete", "INVOICE_DATA", severity) in non_info(run(b))


@pytest.mark.parametrize("field", ["description", "unit_price", "origin_country"])
def test_invoice_line_fields(field):
    b = clean_import()
    b["lines"][1][field] = None if field == "unit_price" else ""
    got = [f for f in run(b) if f.check == "invoice_fields_complete"]
    assert len(got) == 1 and got[0].line_no == 2 and got[0].severity == "BLOCKING"


def test_outdated_hs_code_blocks():
    b = clean_import()
    b["lines"][0]["hs_code"] = "94054000"   # HS 2017 subheading 9405.40, split in HS 2022
    assert non_info(run(b)) == [("hs_format_and_hs6", "HS_INVALID", "BLOCKING")]
    b["lines"][0]["hs_code"] = "85171200"   # deleted 8517.12 is still screened under IMDA heading 8517
    assert sorted(non_info(run(b))) == [("ca_screening", "CA_APPROVAL", "BLOCKING"),
                                        ("hs_format_and_hs6", "HS_INVALID", "BLOCKING")]


def test_controlled_goods_need_licence_on_file_and_quoted():
    b = clean_import()
    b["lines"][0]["hs_code"] = "85171300"   # smartphones: IMDA
    assert non_info(run(b)) == [("ca_screening", "CA_APPROVAL", "BLOCKING")]
    b["licences"] = {"IMDA": "2026-01-15"}
    assert non_info(run(b)) == [("ca_screening", "CA_APPROVAL", "BLOCKING")]   # on file but not quoted
    b["lines"][0]["ca_licence_ref"] = "LIC-1"
    assert non_info(run(b)) == []
    b["licences"] = {"IMDA": "2026-05-09"}   # obtained after the permit was submitted
    assert non_info(run(b)) == [("ca_screening", "CA_APPROVAL", "BLOCKING")]


def test_pharma_flagged_cosmetics_not():
    b = clean_import()
    b["lines"][0]["hs_code"] = "30049000"   # medicaments: HSA licence (SG-IMP-16)
    assert non_info(run(b)) == [("ca_screening", "CA_APPROVAL", "BLOCKING")]
    b["lines"][0]["hs_code"] = "33049900"   # cosmetics: not subject to HSA import licensing
    assert non_info(run(b)) == []


def test_prohibited_and_dutiable_screening():
    b = clean_import()
    b["lines"][0]["hs_code"] = "85434000"   # e-cigarettes
    assert ("prohibited_screening", "CA_APPROVAL", "BLOCKING") in non_info(run(b))
    b["lines"][0]["hs_code"] = "22042100"   # wine: dutiable (INFO) and SFA processed food (no licence -> blocking)
    f = run(b)
    assert any(x.check == "dutiable_screening" and x.severity == "INFO" for x in f)
    assert ("ca_screening", "CA_APPROVAL", "BLOCKING") in non_info(f)


def test_permit_after_arrival_blocks():
    b = clean_import()
    b["shipment"]["permit_submitted_at"] = "2026-05-10T09:00"   # one hour after arrival
    assert non_info(run(b)) == [("permit_before_arrival", "PERMIT_TIMING", "BLOCKING")]


def test_party_checks():
    b = clean_import()
    b["shipment"]["permit_party_uen"] = "209912346K"
    assert non_info(run(b)) == [("importer_matches_profile", "PARTY_UEN", "BLOCKING")]
    b = clean_import()
    b["customer"]["customs_account_active"] = False
    assert non_info(run(b)) == [("customs_account_active", "PARTY_UEN", "BLOCKING")]


def test_origin_checks():
    b = clean_import()
    b["product_origin"]["P2"] = "VN"         # made in Vietnam, declared as China (the loading country)
    assert non_info(run(b)) == [("origin_consistency", "ORIGIN_DOCS", "BLOCKING")]
    b = clean_import()
    b["shipment"]["preference_claimed"] = True
    assert non_info(run(b)) == [("preference_proof", "ORIGIN_DOCS", "BLOCKING")]
    b["co_present"] = True
    assert non_info(run(b)) == []


def test_quantities_weights_and_documents():
    b = clean_import()
    b["lines"][0]["packing_quantity"] = 98
    assert non_info(run(b)) == [("quantity_weight_consistency", "DOC_MISMATCH", "WARNING")]
    b = clean_import()
    b["transport_doc"]["gross_weight_kg"] = 213.0   # 1.4% apart: inside the 2% tolerance
    assert non_info(run(b)) == []
    b["transport_doc"]["gross_weight_kg"] = 216.5   # 3.0% apart
    assert non_info(run(b)) == [("quantity_weight_consistency", "DOC_MISMATCH", "WARNING")]
    b = clean_import()
    b["packing_list"]["present"] = False
    assert non_info(run(b)) == [("docs_present", "DOC_MISMATCH", "WARNING")]
    b = clean_import()
    b["transport_doc"]["present"] = False
    assert non_info(run(b)) == [("docs_present", "DOC_MISMATCH", "BLOCKING")]


def test_readiness_score_arithmetic():
    b = clean_import()
    b["invoice"]["incoterm"] = ""                     # blocking
    b["shipment"]["permit_party_uen"] = "209912346K"  # blocking
    b["lines"][0]["packing_quantity"] = 98            # warning
    assert readiness(run(b)) == (100 - 25 - 25 - 8, "Not ready")
    b2 = clean_import()
    b2["packing_list"]["present"] = False
    assert readiness(run(b2)) == (92, "Needs attention")


def export_to_au():
    # CIF Sydney invoice USD 2,000 with freight 150 and insurance 10 shown: FOB = 1,840 USD = SGD 2,392.00.
    b = clean_import()
    b["shipment"].update({"direction": "Export", "loading_country": "SG", "permit_submitted_at": "2026-04-30T09:00",
                          "freight_on_file": 150.0, "insurance_on_file": 10.0, "permit_invoice_total": 2000.0,
                          "permit_declared_value_sgd": 2392.0, "bicon_check_recorded": True,
                          "consignee_abn_provided": True})
    b["invoice"].update({"incoterm": "CIF", "invoice_total": 2000.0})
    b["lines"] = [{"line_no": 1, "product_id": "P1", "description": "sweet biscuits", "hs_code": "19053100",
                   "quantity": 400, "unit": "KGM", "unit_price": 5.0, "line_value": 2000.0, "origin_country": "SG",
                   "packing_quantity": 400, "ca_licence_ref": ""}]
    b["product_origin"] = {"P1": "SG"}
    return b


def test_export_to_australia():
    f = run(export_to_au())
    assert non_info(f) == []                                 # SG import controls are not applied to exports
    info = {x.check: x.message for x in f if x.severity == "INFO"}
    # FOB SGD 2,392.00 x 1.16 = AUD 2,774.72 (> 1,000: N10); T&I = 160 USD x 1.30 x 1.16 = AUD 241.28;
    # VoTI = 3,016.00; GST = 301.60
    assert "Import Declaration (N10)" in info["au_declaration_type"] and "2,774.72" in info["au_declaration_type"]
    assert "VoTI AUD 3,016.00" in info["au_voti_gst"] and "GST AUD 301.60" in info["au_voti_gst"]


def test_export_checks():
    b = export_to_au()
    b["shipment"]["bicon_check_recorded"] = False             # chapter 19 is biosecurity-screened
    b["shipment"]["consignee_abn_provided"] = False
    assert sorted(non_info(run(b))) == [("au_abn_quoted", "PARTY_UEN", "WARNING"),
                                        ("au_biosecurity_screening", "BIOSECURITY", "WARNING")]
    b = export_to_au()
    b["shipment"]["permit_submitted_at"] = "2026-05-01T11:00"   # after departure at 10:00
    assert non_info(run(b)) == [("permit_before_departure", "PERMIT_TIMING", "BLOCKING")]
    b = export_to_au()
    b["product_origin"]["P1"] = "CN"                         # declared Singapore origin, made in China
    assert non_info(run(b)) == [("origin_consistency", "ORIGIN_DOCS", "BLOCKING")]
    b = export_to_au()
    b["shipment"]["freight_on_file"] = None                  # CIF price, freight not shown: FOB unknown
    assert non_info(run(b)) == [("cif_consistency", "VALUE_CIF", "BLOCKING")]


def clean_enrolment():
    return {"documents_received": True, "uen_submitted": UEN, "customs_account_active_at_submission": True,
            "sample_invoice_states_incoterm": True, "licences_provided": set(), "direction": "Import",
            "products": [{"product_id": "P1", "hs_code_submitted": "61091000", "description": "cotton T-shirts"}]}


def test_enrolment_checks():
    assert validate_enrolment(clean_enrolment()) == []
    cases = [("uen_submitted", "", "uen_present_and_format", "BLOCKING"),
             ("uen_submitted", "2099123K", "uen_present_and_format", "BLOCKING"),
             ("customs_account_active_at_submission", False, "customs_account_active", "BLOCKING"),
             ("sample_invoice_states_incoterm", False, "incoterm_present", "WARNING")]
    for key, value, check, severity in cases:
        e = clean_enrolment()
        e[key] = value
        assert [(f.check, f.severity) for f in validate_enrolment(e)] == [(check, severity)], key
    e = clean_enrolment()
    e["products"][0]["hs_code_submitted"] = "94054000"
    assert [(f.check, f.severity) for f in validate_enrolment(e)] == [("hs_format_and_hs6", "BLOCKING")]
    e = clean_enrolment()
    e["products"][0]["hs_code_submitted"] = "30049000"
    assert [(f.check, f.severity) for f in validate_enrolment(e)] == [("ca_screening", "WARNING")]
    e["licences_provided"] = {"HSA"}
    assert validate_enrolment(e) == []
    e = clean_enrolment()
    e["documents_received"] = False
    assert [(f.check, f.severity) for f in validate_enrolment(e)] == [("docs_present", "BLOCKING")]


def test_corrective_action_route():
    assert corrective_action_route("valid") == "amend the permit in TradeNet"
    assert corrective_action_route("valid", field_amendable=False) == "cancel the permit and apply for a new one"
    assert "voluntary disclosure" in corrective_action_route("used")
    # SG-IMP-26: an expired permit can still be cancelled within 1 calendar day; later only a disclosure helps
    assert corrective_action_route("expired", days_expired=1) == "cancel the permit and apply for a new one"
    assert "voluntary disclosure" in corrective_action_route("expired", days_expired=2)
    # SG-IMP-27: a disclosure must come before any Customs check
    assert "no longer accepted" in corrective_action_route("audit")
    with pytest.raises(ValueError):
        corrective_action_route("draft")


def test_handling_note_mentions_flat_rate_controls_and_open_items():
    customer = {"customer_id": "SYN-C9999", "customer_name": "Synthetic Customer 9999", "segment": "SME",
                "uen": UEN, "customs_account_active": True, "primary_lane_id": "CN-SG-SEA",
                "commodity_group": "Consumer electronics"}
    lanes = {"CN-SG-SEA": {"lane_id": "CN-SG-SEA", "origin": "CN", "destination": "SG", "mode": "Sea",
                           "direction": "Import"}}
    products = [{"product_id": "P1", "description": "smartphones", "hs_code": "85171300", "origin_country": "CN"}]
    e = copy.deepcopy(clean_enrolment())
    e["products"] = [{"product_id": "P1", "hs_code_submitted": "85171300", "description": "smartphones"}]
    findings = validate_enrolment(e)
    note = draft_note(customer, products, lanes, findings, {})
    assert "SYNTHETIC" in note and "DRAFT" in note
    assert "15.5% of the FOB value (SG-IMP-08)" in note
    assert "IMDA approval needed" in note and "NOT on file" in note
    assert "[WARNING]" in note and "(SG-IMP-18)" in note
    note2 = draft_note(customer, products, lanes, [], {"IMDA": "SYN-IMDA-1"})
    assert "on file: SYN-IMDA-1" in note2 and "- none" in note2
