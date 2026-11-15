"""Root-cause analytics: hand-worked Pareto, percentiles, hold rates and readiness detection."""
import csv

import pytest

from boa import analytics as an
from boa.paths import RESULTS
from boa.validator import Finding

LABELS = {"A": "Alpha", "B": "Beta", "C": "Gamma"}


def test_pareto_hand_worked():
    holds = [{"reason_code": c} for c in "AAABBC"]
    rows = an.pareto(holds, LABELS)
    assert [(r["reason_code"], r["holds"]) for r in rows] == [("A", 3), ("B", 2), ("C", 1)]
    assert [round(r["share"], 4) for r in rows] == [0.5, 0.3333, 0.1667]
    assert [round(r["cumulative_share"], 4) for r in rows] == [0.5, 0.8333, 1.0]
    assert an.vital_few(rows) == ["A", "B"]          # 83% reached at B
    assert an.vital_few(rows, 0.5) == ["A"]


def test_pareto_ties_are_ordered_by_code():
    rows = an.pareto([{"reason_code": c} for c in "BA"], LABELS)
    assert [r["reason_code"] for r in rows] == ["A", "B"] and rows[0]["cumulative_share"] == 0.5


def test_percentiles_are_linear_like_dax():
    assert an.percentile([1, 2, 3, 4], 0.5) == 2.5        # MEDIAN of an even count
    assert an.percentile([1, 2, 3, 4], 0.9) == pytest.approx(3.7)   # position 0.9 x 3 = 2.7 -> 3 + 0.7
    assert an.percentile([5], 0.9) == 5
    assert an.percentile([None, 2, None], 0.5) == 2
    assert an.percentile([None], 0.5) is None


def test_time_to_release_groups_and_ignores_open_holds():
    holds = [{"reason_code": "A", "lane_id": "L1", "hours_to_release": 10.0},
             {"reason_code": "A", "lane_id": "L2", "hours_to_release": 20.0},
             {"reason_code": "A", "lane_id": "L2", "hours_to_release": None},
             {"reason_code": "B", "lane_id": "L1", "hours_to_release": 4.0}]
    by_reason = an.time_to_release(holds, ["reason_code"])
    assert by_reason == [{"reason_code": "A", "holds": 2, "median_hours": 15.0, "p90_hours": 19.0, "mean_hours": 15.0},
                         {"reason_code": "B", "holds": 1, "median_hours": 4.0, "p90_hours": 4.0, "mean_hours": 4.0}]
    assert an.time_to_release(holds, ["reason_code", "lane_id"], min_n=2) == []


def test_hold_rates_and_clearance_by_lane():
    ships = [{"shipment_id": "s1", "lane_id": "L1", "shipment_seq": 1, "held": True, "clearance_hours": 30.0},
             {"shipment_id": "s2", "lane_id": "L1", "shipment_seq": 2, "held": False, "clearance_hours": 10.0},
             {"shipment_id": "s3", "lane_id": "L2", "shipment_seq": 1, "held": False, "clearance_hours": 5.0}]
    assert an.hold_rates(ships, "shipment_seq") == [
        {"shipment_seq": 1, "shipments": 2, "held": 1, "hold_rate": 0.5},
        {"shipment_seq": 2, "shipments": 1, "held": 0, "hold_rate": 0.0}]
    assert an.clearance_by_lane(ships) == [
        {"lane_id": "L1", "shipments": 2, "median_hours": 20.0, "p90_hours": 28.0, "hold_rate": 0.5},
        {"lane_id": "L2", "shipments": 1, "median_hours": 5.0, "p90_hours": 5.0, "hold_rate": 0.0}]


def test_detection_and_blocking_precision():
    f = {"s1": [Finding("c", "R", "VALUE_CIF", "BLOCKING", "m")],
         "s2": [Finding("c", "R", "DOC_MISMATCH", "WARNING", "m")],
         "s3": []}
    holds = [{"shipment_id": "s1", "reason_code": "VALUE_CIF"},     # flagged, same reason
             {"shipment_id": "s1", "reason_code": "HS_QUERY"},      # shipment flagged, other reason
             {"shipment_id": "s2", "reason_code": "DOC_MISMATCH"},  # warning counts as same-reason flag
             {"shipment_id": "s3", "reason_code": "INSPECTION"}]    # not flagged
    rows = {r["reason_code"]: r for r in an.detection(holds, f)}
    assert rows["VALUE_CIF"]["same_reason_flagged"] == 1 and rows["HS_QUERY"]["same_reason_flagged"] == 0
    assert rows["HS_QUERY"]["any_blocking_flagged"] == 1 and rows["DOC_MISMATCH"]["any_blocking_flagged"] == 0
    assert rows["ALL"]["holds"] == 4 and rows["ALL"]["same_reason_rate"] == 0.5 and rows["ALL"]["any_blocking_rate"] == 0.5
    ships = [{"shipment_id": "s1", "held": True}, {"shipment_id": "s2", "held": True},
             {"shipment_id": "s3", "held": False}]
    p = an.blocking_precision(ships, f)
    assert (p["flagged_shipments"], p["flagged_held"], p["unflagged_shipments"], p["unflagged_held"]) == (1, 1, 2, 1)
    assert p["flagged_hold_rate"] == 1.0 and p["unflagged_hold_rate"] == 0.5


def test_committed_pareto_is_consistent():
    with open(RESULTS / "analytics" / "pareto.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    counts = [int(r["holds"]) for r in rows]
    assert counts == sorted(counts, reverse=True)
    assert abs(float(rows[-1]["cumulative_share"]) - 1.0) < 1e-6
    with open(RESULTS.parent / "data" / "synthetic" / "holds.csv", encoding="utf-8", newline="") as fh:
        assert sum(counts) == sum(1 for _ in csv.DictReader(fh))
