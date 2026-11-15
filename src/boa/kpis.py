"""The Power BI measures, implemented independently in pandas.

Each function mirrors one DAX measure of powerbi/BrokerageOnboard.SemanticModel (same name in MEASURES) and takes a
filter context {"Table.Column": set of allowed values}. Filters reach a fact table only through the star-schema
relationships below, the way single-direction many-to-one relationships propagate them in Power BI; a filter on a
table that is not related to the fact has no effect. BLANK is None.

This module does not read the TMDL files or use the DAX evaluator in pbitest/: tests/test_measures.py compares the
two, and tests/test_kpis.py checks these functions against values worked out by hand on a tiny fixture.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import POWERBI_DATA

RELS = {
    "FactEnrolmentStage": {"DimStage": ("StageOrder", "StageOrder"), "DimCustomer": ("CustomerId", "CustomerId"),
                           "DimDate": ("ReachedDate", "Date")},
    "FactShipment": {"DimCustomer": ("CustomerId", "CustomerId"), "DimLane": ("LaneId", "LaneId"),
                     "DimDate": ("ArrivalDate", "Date")},
    "FactHold": {"DimReason": ("ReasonCode", "ReasonCode"), "DimLane": ("LaneId", "LaneId"),
                 "DimCustomer": ("CustomerId", "CustomerId"), "DimDate": ("HoldDate", "Date")},
    "FactAction": {"DimReason": ("ReasonCode", "ReasonCode"), "DimCustomer": ("CustomerId", "CustomerId"),
                   "DimDate": ("OpenedDate", "Date")},
}
FILES = {"DimDate": "dim_date.csv", "DimCustomer": "dim_customer.csv", "DimLane": "dim_lane.csv",
         "DimReason": "dim_reason.csv", "DimStage": "dim_stage.csv", "FactEnrolmentStage": "fact_enrolment_stage.csv",
         "FactShipment": "fact_shipment.csv", "FactHold": "fact_hold.csv", "FactAction": "fact_action.csv"}
BOOLS = {"WasHeld", "IsOverdue"}
NUMS = {"StageOrder", "DaysFromSubmission", "ShipmentSeq", "ClearanceHours", "HoldCount", "ReadinessScore",
        "HoursToRelease", "DaysToClose", "Year", "MonthNumber", "IsoWeekday"}


def load_frames(folder=POWERBI_DATA):
    frames = {}
    for table, fname in FILES.items():
        df = pd.read_csv(Path(folder) / fname, dtype=str, keep_default_na=False)
        for c in df.columns:
            if c in BOOLS:
                df[c] = df[c].map({"TRUE": True, "FALSE": False})
            elif c in NUMS:
                df[c] = pd.to_numeric(df[c].replace("", np.nan))
        frames[table] = df
    return frames


def _split(ctx):
    out = {}
    for key, vals in (ctx or {}).items():
        table, col = key.split(".", 1)
        out.setdefault(table, {})[col] = set(vals)
    return out


def _dim_keys(frames, dim, filters, key_col):
    df = frames[dim]
    mask = np.ones(len(df), dtype=bool)
    for col, vals in filters.items():
        mask &= df[col].isin(list(vals)).to_numpy()
    return set(df.loc[mask, key_col])


def visible(frames, fact, ctx):
    """Rows of a fact table under the filter context."""
    by_table = _split(ctx)
    df = frames[fact]
    mask = np.ones(len(df), dtype=bool)
    for col, vals in by_table.get(fact, {}).items():
        mask &= df[col].isin(list(vals)).to_numpy()
    for dim, (fk, pk) in RELS[fact].items():
        if dim in by_table:
            mask &= df[fk].isin(list(_dim_keys(frames, dim, by_table[dim], pk))).to_numpy()
    return df[mask]


def without(ctx, table):
    return {k: v for k, v in (ctx or {}).items() if not k.startswith(table + ".")}


def selected(frames, ctx, table, col):
    """SELECTEDVALUE: the single value of a dimension column left by the filters on that dimension, else None."""
    filters = _split(ctx).get(table, {})
    df = frames[table]
    mask = np.ones(len(df), dtype=bool)
    for c, vals in filters.items():
        mask &= df[c].isin(list(vals)).to_numpy()
    vals = pd.unique(df.loc[mask, col])
    return vals[0].item() if len(vals) == 1 and hasattr(vals[0], "item") else (vals[0] if len(vals) == 1 else None)


def _count(df):
    return len(df) if len(df) else None


def _divide(a, b):
    if b is None or b == 0:
        return None
    if a is None:
        return None
    return a / b


def _median(series):
    s = series.dropna()
    return float(np.median(s.to_numpy(dtype=float))) if len(s) else None


def _p90(series):
    s = series.dropna()
    return float(np.percentile(s.to_numpy(dtype=float), 90, method="linear")) if len(s) else None


# ---------------------------------------------------------------- onboarding funnel

def enrolments_at_stage(f, ctx):
    return _count(visible(f, "FactEnrolmentStage", ctx))


def _at_stage(f, ctx, order):
    return enrolments_at_stage(f, {**without(ctx, "DimStage"), "DimStage.StageOrder": {order}})


def enrolments_submitted(f, ctx):
    return _at_stage(f, ctx, 1)


def profiles_created(f, ctx):
    return _at_stage(f, ctx, 4)


def three_shipments_completed(f, ctx):
    return _at_stage(f, ctx, 6)


def stage_conversion(f, ctx):
    return _divide(enrolments_at_stage(f, ctx), enrolments_submitted(f, ctx))


def step_conversion(f, ctx):
    s = selected(f, ctx, "DimStage", "StageOrder")
    if s is None or s == 1:
        return None
    return _divide(enrolments_at_stage(f, ctx), _at_stage(f, ctx, s - 1))


def median_days_to_stage(f, ctx):
    return _median(visible(f, "FactEnrolmentStage", ctx)["DaysFromSubmission"])


# ---------------------------------------------------------------- first three shipments

def first3_shipments(f, ctx):
    return _count(visible(f, "FactShipment", ctx))


def held_shipments(f, ctx):
    v = visible(f, "FactShipment", ctx)
    return _count(v[v["WasHeld"]])


def first3_hold_rate(f, ctx):
    return _divide(held_shipments(f, ctx), first3_shipments(f, ctx))


def customers_shipping(f, ctx):
    v = visible(f, "FactShipment", ctx)
    return v["CustomerId"].nunique() if len(v) else None


def customers_with_hold(f, ctx):
    v = visible(f, "FactShipment", ctx)
    v = v[v["WasHeld"]]
    return v["CustomerId"].nunique() if len(v) else None


def customers_with_hold_rate(f, ctx):
    return _divide(customers_with_hold(f, ctx), customers_shipping(f, ctx))


def median_clearance_hours(f, ctx):
    return _median(visible(f, "FactShipment", ctx)["ClearanceHours"])


def p90_clearance_hours(f, ctx):
    return _p90(visible(f, "FactShipment", ctx)["ClearanceHours"])


def avg_readiness_score(f, ctx):
    v = visible(f, "FactShipment", ctx)["ReadinessScore"].dropna()
    return float(v.mean()) if len(v) else None


# ---------------------------------------------------------------- holds

def holds(f, ctx):
    return _count(visible(f, "FactHold", ctx))


def hold_share(f, ctx):
    return _divide(holds(f, ctx), holds(f, without(ctx, "DimReason")))


def hold_pareto_cumulative(f, ctx):
    """Cumulative share of holds up to the selected reason, reasons ordered by hold count (descending) and then
    by reason code; BLANK when no single reason is selected or it has no holds."""
    code = selected(f, ctx, "DimReason", "ReasonCode")
    cur = holds(f, ctx)
    if code is None or cur is None:
        return None
    base = without(ctx, "DimReason")
    counts = {r: holds(f, {**base, "DimReason.ReasonCode": {r}}) or 0 for r in f["DimReason"]["ReasonCode"]}
    cum = sum(n for r, n in counts.items() if n > cur or (n == cur and r.upper() <= code.upper()))
    return _divide(cum if cum else None, holds(f, base))


def median_hours_to_release(f, ctx):
    return _median(visible(f, "FactHold", ctx)["HoursToRelease"])


def p90_hours_to_release(f, ctx):
    return _p90(visible(f, "FactHold", ctx)["HoursToRelease"])


# ---------------------------------------------------------------- action log

def actions(f, ctx):
    return _count(visible(f, "FactAction", ctx))


def open_actions(f, ctx):
    v = visible(f, "FactAction", ctx)
    return _count(v[v["Status"] == "Open"])


def overdue_actions(f, ctx):
    v = visible(f, "FactAction", ctx)
    return _count(v[v["IsOverdue"]])


def avg_days_to_close(f, ctx):
    v = visible(f, "FactAction", ctx)
    v = v[v["Status"] == "Closed"]["DaysToClose"].dropna()
    return float(v.mean()) if len(v) else None


def closed_on_time_rate(f, ctx):
    v = visible(f, "FactAction", ctx)
    closed = v[v["Status"] == "Closed"]
    return _divide(_count(closed[~closed["IsOverdue"]]), _count(closed))


MEASURES = {
    "Enrolments at Stage": enrolments_at_stage,
    "Enrolments Submitted": enrolments_submitted,
    "Profiles Created": profiles_created,
    "Three Shipments Completed": three_shipments_completed,
    "Stage Conversion %": stage_conversion,
    "Step Conversion %": step_conversion,
    "Median Days to Stage": median_days_to_stage,
    "First-3 Shipments": first3_shipments,
    "Held Shipments": held_shipments,
    "First-3 Hold Rate %": first3_hold_rate,
    "Customers Shipping": customers_shipping,
    "Customers With a Hold": customers_with_hold,
    "Customers With a Hold %": customers_with_hold_rate,
    "Median Clearance Hours": median_clearance_hours,
    "P90 Clearance Hours": p90_clearance_hours,
    "Avg Readiness Score": avg_readiness_score,
    "Holds": holds,
    "Hold Share %": hold_share,
    "Hold Pareto Cumulative %": hold_pareto_cumulative,
    "Median Hours to Release": median_hours_to_release,
    "P90 Hours to Release": p90_hours_to_release,
    "Actions": actions,
    "Open Actions": open_actions,
    "Overdue Actions": overdue_actions,
    "Avg Days to Close": avg_days_to_close,
    "Closed On Time %": closed_on_time_rate,
}


def value(name, frames, ctx=None):
    v = MEASURES[name](frames, ctx or {})
    return v.item() if hasattr(v, "item") else v
