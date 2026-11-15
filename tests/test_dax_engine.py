"""The DAX evaluator's semantics on small hand-checked expressions over the tiny model of test_kpis.py."""
import pytest

from pbitest.dax import Context, DaxError, Evaluator, parse
from pbitest.model import DEFINITION, LoadedModel
from test_kpis import COLUMNS, fixture_rows, write_csv


@pytest.fixture(scope="module")
def ev(tmp_path_factory):
    folder = tmp_path_factory.mktemp("engine")
    for fname, rows in fixture_rows().items():
        write_csv(folder / fname, rows, COLUMNS[fname])
    return Evaluator(LoadedModel(DEFINITION, folder))


def run(ev, expr, filters=None):
    return ev.eval(parse(expr), Context(ev.model, filters or {}, ev._rows_cache), {}, None)


def test_filters_flow_from_dimension_to_fact(ev):
    assert run(ev, "COUNTROWS(FactShipment)") == 4
    assert run(ev, "COUNTROWS(FactShipment)", {("DimLane", "Mode"): {"Air"}}) == 2
    assert run(ev, "COUNTROWS(FactShipment)", {("DimLane", "Mode"): {"Rail"}}) is None   # no rows -> BLANK
    # single direction: a filter on the fact does not reach the dimension
    assert run(ev, "COUNTROWS(DimLane)", {("FactShipment", "ShipmentSeq"): {3}}) == 2


def test_calculate_replaces_and_removefilters_removes(ev):
    f = {("DimLane", "Mode"): {"Air"}}
    assert run(ev, 'CALCULATE(COUNTROWS(FactShipment), DimLane[Mode] = "Sea")', f) == 2        # replaces Air
    assert run(ev, "CALCULATE(COUNTROWS(FactShipment), REMOVEFILTERS(DimLane))", f) == 4
    assert run(ev, "CALCULATE(COUNTROWS(FactShipment), ALL(DimLane[Mode]))", f) == 4
    # removing another column of the same table leaves the Mode filter in place
    assert run(ev, "CALCULATE(COUNTROWS(FactShipment), REMOVEFILTERS(DimLane[LaneName]))", f) == 2


def test_keepfilters_intersects_instead_of_replacing(ev):
    f = {("FactAction", "Status"): {"Closed"}}
    assert run(ev, 'CALCULATE(COUNTROWS(FactAction), FactAction[Status] = "Open")', f) == 2        # replaced
    assert run(ev, 'CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Open"))', f) is None
    assert run(ev, 'CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Open"))') == 2


def test_blank_semantics(ev):
    assert run(ev, "BLANK() + BLANK()") is None
    assert run(ev, "BLANK() + 1") == 1
    assert run(ev, "BLANK() = 0") is True and run(ev, 'BLANK() = ""') is True
    assert run(ev, "BLANK() < 1") is True and run(ev, "BLANK() > 1") is False
    assert run(ev, "DIVIDE(1, BLANK())") is None and run(ev, "DIVIDE(1, 0, -1)") == -1
    assert run(ev, '"abc" = "ABC"') is True                       # text comparison is case-insensitive
    with pytest.raises(DaxError):
        run(ev, "1 / 0")


def test_aggregations(ev):
    assert run(ev, "MEDIAN(FactShipment[ClearanceHours])") == 15.0
    assert run(ev, "AVERAGE(FactShipment[ReadinessScore])") == 79.25
    assert run(ev, "DISTINCTCOUNT(FactShipment[CustomerId])") == 2
    assert run(ev, "MEDIAN(FactHold[HoursToRelease])") == 21.0              # the blank hours are ignored
    assert run(ev, "PERCENTILE.INC(FactShipment[ClearanceHours], 0.9)") == pytest.approx(27.0)
    assert run(ev, "MEDIAN(FactShipment[ClearanceHours])", {("DimLane", "Mode"): {"Rail"}}) is None


def test_selectedvalue(ev):
    assert run(ev, "SELECTEDVALUE(DimLane[Mode])") is None
    assert run(ev, "SELECTEDVALUE(DimLane[Mode], \"many\")") == "many"
    assert run(ev, "SELECTEDVALUE(DimLane[Mode])", {("DimLane", "LaneName"): {"SG-AU Air"}}) == "Air"


def test_filter_sumx_and_context_transition(ev):
    # SUMX over all lanes of a measure-like expression: context transition makes [x] see one lane at a time
    expr = "SUMX(ALL(DimLane), CALCULATE(COUNTROWS(FactShipment)))"
    assert run(ev, expr) == 4
    # FILTER keeps the lanes with two or more shipments (both have two)
    assert run(ev, "COUNTROWS(FILTER(ALL(DimLane), CALCULATE(COUNTROWS(FactShipment)) >= 2))") == 2
    # the row context replaces the outer filter on the same columns, but keeps other filters
    f = {("DimLane", "LaneName"): {"CN-SG Sea"}, ("DimCustomer", "Segment"): {"Large"}}
    assert run(ev, "SUMX(ALL(DimLane), CALCULATE(COUNTROWS(FactShipment)))", f) == 1   # only C2's air shipment
    # a measure reference inside a row context also triggers the transition
    assert run(ev, "SUMX(ALL(DimReason), [Holds])") == 3


def test_unsupported_functions_raise(ev):
    with pytest.raises(DaxError):
        run(ev, "COUNTX(FactShipment, FactShipment[ClearanceHours])")
    with pytest.raises(DaxError):
        run(ev, "FactShipment[ClearanceHours]")     # column without a row context
