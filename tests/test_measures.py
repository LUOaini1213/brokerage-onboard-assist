"""Each DAX measure, as written in the TMDL files, against the independent pandas implementation (boa.kpis), on the
committed SYNTHETIC Power BI data, in many filter contexts: no filter, single dimension members, combinations, and
contexts that leave nothing visible, so that a measure that only matches on the grand total still fails."""
import pytest

from boa import kpis as K
from conftest import close, to_dax_filters

SEGMENTS = ["SME", "Mid-size", "Large"]
STAGES = ["Submitted", "Documents received", "Validated", "Profile created", "First shipment released",
          "Three shipments released"]
LANES = ["CN-SG Sea", "CN-SG Air", "US-SG Air", "DE-SG Air", "JP-SG Sea", "VN-SG Sea", "MY-SG Road", "SG-AU Sea",
         "SG-AU Air"]
REASONS = ["Invoice incomplete", "Competent-authority approval missing", "Customs value query",
           "Documents do not agree", "Classification query", "Origin documents", "Inspection without document defect",
           "Permit not obtained in time", "HS code not valid", "Importer UEN or account issue",
           "Biosecurity referral (Australia)"]
MONTHS = ["2026-04", "2026-06", "2026-09"]

FUNNEL = ([{}] + [{"DimStage.Stage": {s}} for s in STAGES]
          + [{"DimCustomer.Segment": {g}} for g in SEGMENTS]
          + [{"DimStage.Stage": {s}, "DimCustomer.Segment": {"SME"}} for s in STAGES[1:4]]
          + [{"DimStage.Stage": {"Validated", "Profile created"}}]
          + [{"DimCustomer.TradeDirection": {"Export"}, "DimStage.Stage": {"Three shipments released"}}]
          + [{"DimDate.YearMonth": {m}} for m in MONTHS]
          + [{"DimCustomer.CommodityGroup": {"Chemicals"}, "DimStage.Stage": {"Validated"}}])
SHIPMENTS = ([{}] + [{"DimLane.LaneName": {ln}} for ln in LANES]
             + [{"FactShipment.ShipmentSeq": {k}} for k in (1, 2, 3)]
             + [{"DimLane.Mode": {m}} for m in ("Air", "Sea", "Road")]
             + [{"DimCustomer.Segment": {g}} for g in SEGMENTS]
             + [{"FactShipment.ReadinessBand": {b}} for b in ("Ready", "Needs attention", "Not ready")]
             + [{"DimLane.Direction": {"Export"}, "FactShipment.ShipmentSeq": {1}},
                {"DimDate.YearMonth": {"2026-07"}, "DimLane.Mode": {"Sea"}},
                {"DimLane.LaneName": {"SG-AU Air"}, "DimCustomer.Segment": {"Large"}},
                {"DimLane.LaneName": {"MY-SG Road"}, "FactShipment.WasHeld": {True}},
                {"DimDate.YearMonth": {"2026-03"}}])
HOLDS = ([{}] + [{"DimReason.ReasonLabel": {r}} for r in REASONS]
         + [{"DimReason.ReasonLabel": {r}, "DimLane.Direction": {"Export"}} for r in REASONS[:6]]
         + [{"DimReason.ReasonLabel": {r}, "DimLane.Mode": {"Air"}} for r in REASONS[:4]]
         + [{"DimLane.LaneName": {ln}} for ln in LANES[:5]]
         + [{"DimReason.Category": {"Documents"}}, {"DimReason.Category": {"Classification"}},
            {"DimReason.ReasonLabel": {REASONS[0], REASONS[1]}},
            {"DimCustomer.Segment": {"SME"}, "DimReason.ReasonLabel": {REASONS[2]}},
            {"DimDate.YearMonth": {"2026-08"}, "DimReason.ReasonLabel": {REASONS[3]}},
            {"DimLane.LaneName": {"SG-AU Sea"}, "DimReason.ReasonLabel": {"Biosecurity referral (Australia)"}},
            {"DimLane.LaneName": {"MY-SG Road"}, "DimReason.ReasonLabel": {"Biosecurity referral (Australia)"}}])
ACTIONS = ([{}, {"FactAction.Status": {"Open"}}, {"FactAction.Status": {"Closed"}},
            {"FactAction.Source": {"Enrolment"}}, {"FactAction.Source": {"Hold"}}]
           + [{"FactAction.OwnerRole": {r}} for r in ("Customer", "Customs declarant", "Onboarding analyst")]
           + [{"DimReason.ReasonLabel": {r}} for r in REASONS[:5]]
           + [{"DimCustomer.Segment": {"SME"}, "FactAction.Status": {"Closed"}},
              {"DimDate.YearMonth": {"2026-06"}}, {"FactAction.IsOverdue": {True}}])

GROUPS = {
    "funnel": (["Enrolments at Stage", "Enrolments Submitted", "Profiles Created", "Three Shipments Completed",
                "Stage Conversion %", "Step Conversion %", "Median Days to Stage"], FUNNEL),
    "shipments": (["First-3 Shipments", "Held Shipments", "First-3 Hold Rate %", "Customers Shipping",
                   "Customers With a Hold", "Customers With a Hold %", "Median Clearance Hours",
                   "P90 Clearance Hours", "Avg Readiness Score"], SHIPMENTS),
    "holds": (["Holds", "Hold Share %", "Hold Pareto Cumulative %", "Median Hours to Release",
               "P90 Hours to Release"], HOLDS),
    "actions": (["Actions", "Open Actions", "Overdue Actions", "Avg Days to Close", "Closed On Time %"], ACTIONS),
}
CASES = [(m, i, ctx) for measures, contexts in GROUPS.values() for m in measures for i, ctx in enumerate(contexts)]


def test_every_model_measure_has_a_pandas_twin_and_is_tested(model):
    assert set(model.measures) == set(K.MEASURES)
    assert {m for m, _, _ in CASES} == set(model.measures)


def test_contexts_use_real_members(frames):
    for _, contexts in GROUPS.values():
        for ctx in contexts:
            for key, vals in ctx.items():
                table, col = key.split(".", 1)
                assert set(vals) <= set(frames[table][col]), key


@pytest.mark.parametrize("measure,i,ctx", CASES, ids=[f"{m}-{i}" for m, i, _ in CASES])
def test_measure_matches_pandas(dax, model, frames, measure, i, ctx):
    got = dax.measure(measure, to_dax_filters(model, ctx))
    want = K.value(measure, frames, ctx)
    assert close(got, want), f"{measure} in {ctx}: DAX {got!r}, pandas {want!r}"


def test_contexts_are_not_trivial(dax, model):
    """Most contexts must give a value and the values must differ, so equality is not a coincidence."""
    for measures, contexts in GROUPS.values():
        for m in measures:
            vals = [dax.measure(m, to_dax_filters(model, c)) for c in contexts]
            non_blank = [v for v in vals if v is not None]
            assert len(non_blank) >= len(vals) // 3, m
            assert len({round(v, 9) for v in non_blank}) >= 3, m
