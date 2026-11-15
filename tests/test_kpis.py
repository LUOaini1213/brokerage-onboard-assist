"""Every measure on a tiny hand-made model, worked out by hand. Both implementations are checked against the same
expected values: the pandas functions in boa.kpis and the measure DAX (from the committed TMDL) run by the
evaluator in pbitest/dax.py."""
import pytest

from boa import kpis as K
from boa.io import write_csv
from boa.powerbi_export import COLUMNS
from conftest import close, to_dax_filters
from pbitest.dax import Evaluator
from pbitest.model import DEFINITION, LoadedModel

STAGES = ["Submitted", "Documents received", "Validated", "Profile created", "First shipment released",
          "Three shipments released"]


def fixture_rows():
    days = [{"Date": f"2026-05-{d:02d}", "Year": 2026, "MonthNumber": 5, "MonthName": "May", "YearMonth": "2026-05",
             "IsoWeekday": 1, "DayName": "Mon"} for d in range(1, 32)]
    stage = []
    for eid, cid, days_to in (("E1", "C1", [0, 2, 5, 7, 30, 75]), ("E2", "C2", [0, 1, 3, 4]), ("E3", "C3", [0, 6])):
        for order, d in enumerate(days_to, 1):
            stage.append({"EnrolmentId": eid, "CustomerId": cid, "StageOrder": order,
                          "ReachedDate": f"2026-05-{1 + min(d, 30):02d}", "DaysFromSubmission": d})
    ship = [("S1", "C1", 1, "L1", "2026-05-03", 20.0, True, 1, 75, "Not ready"),
            ("S2", "C1", 2, "L1", "2026-05-10", 10.0, False, 0, 100, "Ready"),
            ("S3", "C1", 3, "L2", "2026-05-20", 30.0, True, 2, 50, "Not ready"),
            ("S4", "C2", 1, "L2", "2026-05-12", 4.0, False, 0, 92, "Needs attention")]
    holds = [("H1", "S1", "C1", "L1", "VALUE_CIF", "2026-05-03", 12.0, "n1"),
             ("H2", "S3", "C1", "L2", "VALUE_CIF", "2026-05-20", 30.0, "n2"),
             ("H3", "S3", "C1", "L2", "CA_APPROVAL", "2026-05-21", None, "n3")]      # still open: no hours
    acts = [("A1", "C1", "S1", "H1", "Hold", "VALUE_CIF", "t", "SG-IMP-07", "Customs declarant", "2026-05-03",
             "2026-05-07", "2026-05-05", "Closed", 2, False),
            ("A2", "C1", "S3", "H2", "Hold", "VALUE_CIF", "t", "SG-IMP-07", "Customs declarant", "2026-05-20",
             "2026-05-24", "2026-05-27", "Closed", 7, True),
            ("A3", "C1", "S3", "H3", "Hold", "CA_APPROVAL", "t", "SG-IMP-14", "Customer", "2026-05-21",
             "2026-05-25", "", "Open", None, True),
            ("A4", "C3", "", "", "Enrolment", "PARTY_UEN", "t", "SG-IMP-03", "Onboarding analyst", "2026-05-29",
             "2026-06-02", "", "Open", None, False)]
    return {
        "dim_date.csv": days,
        "dim_customer.csv": [{"CustomerId": c, "CustomerName": f"Synthetic {c}", "Segment": s, "PrimaryLaneId": "L1",
                              "TradeDirection": "Import", "CommodityGroup": "G"}
                             for c, s in (("C1", "SME"), ("C2", "Large"), ("C3", "SME"))],
        "dim_lane.csv": [{"LaneId": "L1", "LaneName": "CN-SG Sea", "Origin": "CN", "Destination": "SG", "Mode": "Sea",
                          "Direction": "Import"},
                         {"LaneId": "L2", "LaneName": "SG-AU Air", "Origin": "SG", "Destination": "AU", "Mode": "Air",
                          "Direction": "Export"}],
        "dim_reason.csv": [{"ReasonCode": c, "ReasonLabel": c.title(), "Category": cat, "DetectableBeforeLodgement": "yes"}
                           for c, cat in (("CA_APPROVAL", "Controlled goods"), ("INVOICE_DATA", "Documents"),
                                          ("PARTY_UEN", "Party data"), ("VALUE_CIF", "Valuation"))],
        "dim_stage.csv": [{"StageOrder": i, "Stage": s} for i, s in enumerate(STAGES, 1)],
        "fact_enrolment_stage.csv": stage,
        "fact_shipment.csv": [dict(zip(COLUMNS["fact_shipment.csv"], r)) for r in ship],
        "fact_hold.csv": [dict(zip(COLUMNS["fact_hold.csv"], r)) for r in holds],
        "fact_action.csv": [dict(zip(COLUMNS["fact_action.csv"], r)) for r in acts],
    }


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    folder = tmp_path_factory.mktemp("tiny")
    for fname, rows in fixture_rows().items():
        write_csv(folder / fname, rows, COLUMNS[fname])
    return folder


@pytest.fixture(scope="module")
def py(tiny):
    return K.load_frames(tiny)


@pytest.fixture(scope="module")
def tiny_dax(tiny):
    m = LoadedModel(DEFINITION, tiny)
    return m, Evaluator(m)


# (measure, filter context, value worked out by hand); None = BLANK
CASES = [
    # funnel: stage counts 3, 3, 2, 2, 1, 1
    ("Enrolments at Stage", {}, 12),
    ("Enrolments at Stage", {"DimStage.Stage": {"Validated"}}, 2),
    ("Enrolments Submitted", {}, 3),
    ("Enrolments Submitted", {"DimStage.Stage": {"Validated"}}, 3),          # REMOVEFILTERS(DimStage)
    ("Profiles Created", {}, 2),
    ("Profiles Created", {"DimCustomer.Segment": {"SME"}}, 1),               # only C1
    ("Three Shipments Completed", {}, 1),
    ("Stage Conversion %", {"DimStage.Stage": {"Validated"}}, 2 / 3),
    ("Stage Conversion %", {"DimStage.Stage": {"Three shipments released"}}, 1 / 3),
    ("Step Conversion %", {"DimStage.Stage": {"Validated"}}, 2 / 3),         # 2 of the 3 with documents
    ("Step Conversion %", {"DimStage.Stage": {"Profile created"}}, 1.0),
    ("Step Conversion %", {"DimStage.Stage": {"First shipment released"}}, 0.5),
    ("Step Conversion %", {"DimStage.Stage": {"Submitted"}}, None),
    ("Step Conversion %", {}, None),                                         # no single stage selected
    ("Median Days to Stage", {}, 3.5),       # 0,0,0,1,2,3,4,5,6,7,30,75 -> (3 + 4) / 2
    ("Median Days to Stage", {"DimStage.Stage": {"Profile created"}}, 5.5),  # 7 and 4
    ("Median Days to Stage", {"DimStage.Stage": {"Documents received"}}, 2.0),  # 2, 1, 6
    # first three shipments
    ("First-3 Shipments", {}, 4),
    ("Held Shipments", {}, 2),
    ("First-3 Hold Rate %", {}, 0.5),
    ("First-3 Hold Rate %", {"DimCustomer.Segment": {"SME"}}, 2 / 3),
    ("First-3 Hold Rate %", {"FactShipment.ShipmentSeq": {1}}, 0.5),
    ("First-3 Hold Rate %", {"DimLane.LaneName": {"SG-AU Air"}}, 0.5),
    ("Held Shipments", {"DimCustomer.Segment": {"Large"}}, None),
    ("Held Shipments", {"FactShipment.WasHeld": {False}}, None),              # KEEPFILTERS: slicer still applies
    ("Customers With a Hold", {"FactShipment.WasHeld": {False}}, None),
    ("Customers Shipping", {}, 2),
    ("Customers With a Hold", {}, 1),
    ("Customers With a Hold %", {}, 0.5),
    ("Median Clearance Hours", {}, 15.0),    # 4, 10, 20, 30
    ("P90 Clearance Hours", {}, 27.0),       # 20 + 0.7 x 10
    ("P90 Clearance Hours", {"DimLane.LaneName": {"SG-AU Air"}}, 27.4),     # 4 + 0.9 x 26
    ("Avg Readiness Score", {}, 79.25),      # (75 + 100 + 50 + 92) / 4
    # holds: VALUE_CIF 2, CA_APPROVAL 1 (open), others 0
    ("Holds", {}, 3),
    ("Hold Share %", {"DimReason.ReasonLabel": {"Value_Cif"}}, 2 / 3),
    ("Hold Share %", {"DimReason.ReasonLabel": {"Invoice_Data"}}, None),     # DIVIDE(BLANK, 3)
    ("Hold Pareto Cumulative %", {"DimReason.ReasonLabel": {"Value_Cif"}}, 2 / 3),
    ("Hold Pareto Cumulative %", {"DimReason.ReasonLabel": {"Ca_Approval"}}, 1.0),
    ("Hold Pareto Cumulative %", {"DimReason.ReasonLabel": {"Invoice_Data"}}, None),
    ("Hold Pareto Cumulative %", {}, None),
    # on the export lane both reasons have 1 hold: the tie is broken by code, CA_APPROVAL first
    ("Hold Pareto Cumulative %", {"DimReason.ReasonLabel": {"Ca_Approval"}, "DimLane.Direction": {"Export"}}, 0.5),
    ("Hold Pareto Cumulative %", {"DimReason.ReasonLabel": {"Value_Cif"}, "DimLane.Direction": {"Export"}}, 1.0),
    ("Hold Pareto Cumulative %", {"DimReason.Category": {"Valuation"}}, 2 / 3),
    ("Median Hours to Release", {}, 21.0),   # 12 and 30; the open hold has no hours
    ("P90 Hours to Release", {}, 28.2),      # 12 + 0.9 x 18
    ("Median Hours to Release", {"DimReason.ReasonLabel": {"Ca_Approval"}}, None),
    # action log
    ("Actions", {}, 4),
    ("Open Actions", {}, 2),
    ("Overdue Actions", {}, 2),
    ("Avg Days to Close", {}, 4.5),          # 2 and 7
    ("Closed On Time %", {}, 0.5),
    ("Open Actions", {"DimReason.ReasonLabel": {"Value_Cif"}}, None),
    ("Open Actions", {"FactAction.Status": {"Closed"}}, None),                # KEEPFILTERS: slicer still applies
    ("Avg Days to Close", {"FactAction.Status": {"Open"}}, None),
    ("Closed On Time %", {"FactAction.Status": {"Open"}}, None),
    ("Overdue Actions", {"FactAction.IsOverdue": {False}}, None),
    ("Overdue Actions", {"FactAction.OwnerRole": {"Customer"}}, 1),
    ("Actions", {"FactAction.Source": {"Enrolment"}}, 1),
    ("Closed On Time %", {"DimReason.ReasonLabel": {"Value_Cif"}}, 0.5),
]


def test_cases_cover_every_measure():
    assert {m for m, _, _ in CASES} == set(K.MEASURES)


@pytest.mark.parametrize("measure,ctx,expected", CASES, ids=[f"{m}-{i}" for i, (m, _, _) in enumerate(CASES)])
def test_pandas_matches_hand_value(py, measure, ctx, expected):
    assert close(K.value(measure, py, ctx), expected)


@pytest.mark.parametrize("measure,ctx,expected", CASES, ids=[f"{m}-{i}" for i, (m, _, _) in enumerate(CASES)])
def test_dax_matches_hand_value(tiny_dax, measure, ctx, expected):
    m, ev = tiny_dax
    assert close(ev.measure(measure, to_dax_filters(m, ctx)), expected)
