"""Hand-worked customs-value and tax arithmetic (rules SG-IMP-07 to SG-IMP-12, AU-01, AU-03, AU-04)."""
import pytest

from boa import valuation as V


def test_cif_and_cip_are_taken_as_invoiced():
    assert V.sg_cif(10_000, "CIF").amount == 10_000
    assert V.sg_cif(10_000, "CIP", freight=500, insurance=20).amount == 10_000


def test_fob_with_actual_charges():
    # 10,000 + 800 freight + 50 insurance
    assert V.sg_cif(10_000, "FOB", freight=800, insurance=50, export_country="CN").amount == 10_850


@pytest.mark.parametrize("country,expected", [("CN", 11_550), ("US", 12_450), ("DE", 11_900), ("MY", 10_500),
                                              ("VN", 10_950)])
def test_fob_flat_rates_when_charges_unknown(country, expected):
    # SG-IMP-08: FOB x (1 + rate); China 15.5%, USA 24.5%, Europe 19%, Peninsular Malaysia 5%, Vietnam 9.5%
    v = V.sg_cif(10_000, "FOB", export_country=country)
    assert v.amount == pytest.approx(expected) and v.problem is None


def test_fob_flat_rate_needs_a_listed_country_and_both_charges_unknown():
    assert V.sg_cif(10_000, "FOB", export_country="BR").problem == "charges_unknown"
    assert V.sg_cif(10_000, "FOB", freight=800, export_country="CN").problem == "charges_unknown"  # insurance unknown


def test_fca_and_fas_have_no_flat_rate():
    assert V.sg_cif(10_000, "FCA", export_country="CN").problem == "charges_unknown"
    assert V.sg_cif(10_000, "FCA", freight=600, insurance=30).amount == 10_630


def test_cfr_insurance_flat_one_percent():
    assert V.sg_cif(10_000, "CFR").amount == 10_100            # SG-IMP-09, base = CFR value (assumption)
    assert V.sg_cif(10_000, "CFR", insurance=25).amount == 10_025
    assert V.sg_cif(10_000, "CPT").problem == "charges_unknown"  # flat insurance only stated for CFR


def test_exw_needs_inland_freight_and_insurance():
    assert V.sg_cif(10_000, "EXW", freight=800, insurance=50, inland=200).amount == 11_050
    assert V.sg_cif(10_000, "EXW", freight=800, insurance=50).problem == "charges_unknown"


def test_other_charges_are_added():
    assert V.sg_cif(10_000, "CIF", other=300).amount == 10_300   # e.g. a selling commission


def test_d_terms_and_missing_incoterm():
    assert V.sg_cif(10_000, "DAP").amount == 10_000
    ddp = V.sg_cif(10_000, "DDP")
    assert ddp.amount == 10_000 and ddp.problem == "ddp_breakdown"
    assert V.sg_cif(10_000, "").problem == "incoterm_missing"
    assert V.sg_cif(10_000, "C&F").problem == "incoterm_unknown"


def test_singapore_gst():
    assert V.SG_GST_RATE == 0.09
    assert V.sg_gst(11_550) == 1039.5                  # 9% x CIF
    assert V.sg_gst(1_000, duty_sgd=200) == 108.0      # 9% x (CIF + duty)


def test_fob_value_for_exports_and_australia():
    assert V.fob_value(10_000, "FOB").amount == 10_000
    assert V.fob_value(10_000, "CIF", freight=700, insurance=40).amount == 9_260
    assert V.fob_value(10_000, "CFR", freight=700).amount == 9_300
    assert V.fob_value(10_000, "EXW", inland=150).amount == 10_150
    assert V.fob_value(10_000, "CIF", freight=700).problem == "charges_unknown"
    assert V.fob_value(10_000, "DDP", freight=700, insurance=40).problem == "ddp_breakdown"


def test_australian_gst_on_voti():
    # AU-04: VoTI = customs value 10,000 + T&I 900 + duty 500 = 11,400; GST 10% = 1,140
    voti = V.au_voti(10_000, 900, duty_aud=500)
    assert voti == 11_400 and V.au_gst(voti) == 1140.0


@pytest.mark.parametrize("value,permit,alcohol,expected", [
    (1000.01, False, False, "Import Declaration (N10)"),
    (1000.0, False, False, "Self-Assessed Clearance"),     # AUD 1,000 or less: SAC
    (800, True, False, "long-format SAC"),
    (800, False, True, "tobacco or alcohol"),
])
def test_australian_declaration_type(value, permit, alcohol, expected):
    assert expected in V.au_declaration_type(value, permit, alcohol)
