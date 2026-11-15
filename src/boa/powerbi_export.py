"""Shape the SYNTHETIC tables into the star schema the Power BI model loads (powerbi/data/*.csv)."""
from datetime import date, timedelta
from pathlib import Path

from .io import write_csv
from .rules import hold_reasons

STAGES = [(1, "Submitted"), (2, "Documents received"), (3, "Validated"), (4, "Profile created"),
          (5, "First shipment released"), (6, "Three shipments released")]
DATE_RANGE = (date(2026, 3, 1), date(2026, 11, 30))

COLUMNS = {
    "dim_date.csv": ["Date", "Year", "MonthNumber", "MonthName", "YearMonth", "IsoWeekday", "DayName"],
    "dim_customer.csv": ["CustomerId", "CustomerName", "Segment", "PrimaryLaneId", "TradeDirection", "CommodityGroup"],
    "dim_lane.csv": ["LaneId", "LaneName", "Origin", "Destination", "Mode", "Direction"],
    "dim_reason.csv": ["ReasonCode", "ReasonLabel", "Category", "DetectableBeforeLodgement"],
    "dim_stage.csv": ["StageOrder", "Stage"],
    "fact_enrolment_stage.csv": ["EnrolmentId", "CustomerId", "StageOrder", "ReachedDate", "DaysFromSubmission"],
    "fact_shipment.csv": ["ShipmentId", "CustomerId", "ShipmentSeq", "LaneId", "ArrivalDate", "ClearanceHours",
                          "WasHeld", "HoldCount", "ReadinessScore", "ReadinessBand"],
    "fact_hold.csv": ["HoldId", "ShipmentId", "CustomerId", "LaneId", "ReasonCode", "HoldDate", "HoursToRelease",
                      "Note"],
    "fact_action.csv": ["ActionId", "CustomerId", "ShipmentId", "HoldId", "Source", "ReasonCode", "ActionType",
                        "RuleRef", "OwnerRole", "OpenedDate", "DueDate", "ClosedDate", "Status", "DaysToClose",
                        "IsOverdue"],
}


def export(t, readiness, lanes, as_of, out_dir):
    """t: synthetic tables (typed); readiness: {shipment_id: (score, band)}; lanes: config lanes; as_of: date."""
    out_dir = Path(out_dir)
    days = []
    d = DATE_RANGE[0]
    while d <= DATE_RANGE[1]:
        days.append({"Date": d.isoformat(), "Year": d.year, "MonthNumber": d.month, "MonthName": d.strftime("%b"),
                     "YearMonth": f"{d.year}-{d.month:02d}", "IsoWeekday": d.isoweekday(), "DayName": d.strftime("%a")})
        d += timedelta(days=1)
    write_csv(out_dir / "dim_date.csv", days, COLUMNS["dim_date.csv"])
    write_csv(out_dir / "dim_customer.csv", [
        {"CustomerId": c["customer_id"], "CustomerName": c["customer_name"], "Segment": c["segment"],
         "PrimaryLaneId": c["primary_lane_id"], "TradeDirection": c["trade_direction"],
         "CommodityGroup": c["commodity_group"]} for c in t["customers"]], COLUMNS["dim_customer.csv"])
    write_csv(out_dir / "dim_lane.csv", [
        {"LaneId": ln["lane_id"], "LaneName": f"{ln['origin']}-{ln['destination']} {ln['mode']}",
         "Origin": ln["origin"], "Destination": ln["destination"], "Mode": ln["mode"], "Direction": ln["direction"]}
        for ln in lanes], COLUMNS["dim_lane.csv"])
    write_csv(out_dir / "dim_reason.csv", [
        {"ReasonCode": code, "ReasonLabel": r["label"], "Category": r["category"],
         "DetectableBeforeLodgement": r["detectable_before_lodgement"]} for code, r in hold_reasons().items()],
        COLUMNS["dim_reason.csv"])
    write_csv(out_dir / "dim_stage.csv", [{"StageOrder": o, "Stage": s} for o, s in STAGES], COLUMNS["dim_stage.csv"])

    stage_rows = []
    keys = [None, "documents_received_date", "validated_date", "profile_created_date",
            "first_shipment_released_date", "third_shipment_released_date"]
    for e in t["enrolments"]:
        sub = date.fromisoformat(e["submitted_date"])
        for (order, _), key in zip(STAGES, keys):
            value = e["submitted_date"] if key is None else e[key]
            if not value:
                break
            stage_rows.append({"EnrolmentId": e["enrolment_id"], "CustomerId": e["customer_id"], "StageOrder": order,
                               "ReachedDate": value, "DaysFromSubmission": (date.fromisoformat(value) - sub).days})
    write_csv(out_dir / "fact_enrolment_stage.csv", stage_rows, COLUMNS["fact_enrolment_stage.csv"])
    write_csv(out_dir / "fact_shipment.csv", [
        {"ShipmentId": s["shipment_id"], "CustomerId": s["customer_id"], "ShipmentSeq": s["shipment_seq"],
         "LaneId": s["lane_id"], "ArrivalDate": s["arrival_at"][:10], "ClearanceHours": s["clearance_hours"],
         "WasHeld": s["held"], "HoldCount": s["hold_count"], "ReadinessScore": readiness[s["shipment_id"]][0],
         "ReadinessBand": readiness[s["shipment_id"]][1]} for s in t["shipments"]], COLUMNS["fact_shipment.csv"])
    write_csv(out_dir / "fact_hold.csv", [
        {"HoldId": h["hold_id"], "ShipmentId": h["shipment_id"], "CustomerId": h["customer_id"],
         "LaneId": h["lane_id"], "ReasonCode": h["reason_code"], "HoldDate": h["hold_start"][:10],
         "HoursToRelease": h["hours_to_release"], "Note": h["note"]} for h in t["holds"]], COLUMNS["fact_hold.csv"])
    actions = []
    for a in t["actions"]:
        opened, due = date.fromisoformat(a["opened_date"]), date.fromisoformat(a["due_date"])
        closed = date.fromisoformat(a["closed_date"]) if a["closed_date"] else None
        overdue = (closed > due) if closed else (as_of > due)
        actions.append({"ActionId": a["action_id"], "CustomerId": a["customer_id"], "ShipmentId": a["shipment_id"],
                        "HoldId": a["hold_id"], "Source": a["source"], "ReasonCode": a["reason_code"],
                        "ActionType": a["action_type"], "RuleRef": a["rule_ref"], "OwnerRole": a["owner_role"],
                        "OpenedDate": a["opened_date"], "DueDate": a["due_date"], "ClosedDate": a["closed_date"],
                        "Status": a["status"], "DaysToClose": (closed - opened).days if closed else None,
                        "IsOverdue": overdue})
    write_csv(out_dir / "fact_action.csv", actions, COLUMNS["fact_action.csv"])
