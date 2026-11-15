"""Root-cause analytics on the SYNTHETIC holds: Pareto of hold reasons, time to release by reason and lane, hold
rates, and how many holds the readiness check would have flagged before lodgement.

Percentiles use linear interpolation between order statistics (numpy 'linear', the same definition as DAX
PERCENTILE.INC and MEDIAN), so the Power BI measures and these tables agree.
"""
from collections import Counter, defaultdict

import numpy as np


def percentile(values, q):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return float(np.percentile(np.asarray(vals, dtype=float), q * 100, method="linear"))


def pareto(holds, labels):
    """Rows sorted by count (descending) then code, with share and cumulative share of all holds."""
    counts = Counter(h["reason_code"] for h in holds)
    total = sum(counts.values())
    rows, cum = [], 0
    for rank, (code, n) in enumerate(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])), 1):
        cum += n
        rows.append({"rank": rank, "reason_code": code, "label": labels[code], "holds": n,
                     "share": n / total, "cumulative_share": cum / total})
    return rows


def vital_few(pareto_rows, threshold=0.8):
    """Reasons up to and including the first one at which the cumulative share reaches the threshold."""
    out = []
    for r in pareto_rows:
        out.append(r["reason_code"])
        if r["cumulative_share"] >= threshold:
            break
    return out


def time_to_release(holds, keys, min_n=1):
    groups = defaultdict(list)
    for h in holds:
        if h["hours_to_release"] is not None:
            groups[tuple(h[k] for k in keys)].append(h["hours_to_release"])
    rows = []
    for g, vals in sorted(groups.items()):
        if len(vals) < min_n:
            continue
        rows.append({**dict(zip(keys, g)), "holds": len(vals), "median_hours": percentile(vals, 0.5),
                     "p90_hours": percentile(vals, 0.9), "mean_hours": float(np.mean(vals))})
    return rows


def hold_rates(shipments, key):
    groups = defaultdict(lambda: [0, 0])
    for s in shipments:
        g = groups[s[key]]
        g[0] += 1
        g[1] += 1 if s["held"] else 0
    return [{key: k, "shipments": n, "held": h, "hold_rate": h / n} for k, (n, h) in sorted(groups.items())]


def clearance_by_lane(shipments):
    groups = defaultdict(list)
    held = defaultdict(int)
    for s in shipments:
        groups[s["lane_id"]].append(s["clearance_hours"])
        held[s["lane_id"]] += 1 if s["held"] else 0
    return [{"lane_id": k, "shipments": len(v), "median_hours": percentile(v, 0.5), "p90_hours": percentile(v, 0.9),
             "hold_rate": held[k] / len(v)} for k, v in sorted(groups.items())]


def detection(holds, findings_by_shipment):
    """For each hold: was the same reason flagged (BLOCKING or WARNING) before lodgement, and was the shipment
    flagged at all (any BLOCKING finding)? Returns per-reason rows and the overall row."""
    rows = defaultdict(lambda: {"holds": 0, "same_reason_flagged": 0, "any_blocking_flagged": 0})
    for h in holds:
        f = findings_by_shipment.get(h["shipment_id"], [])
        r = rows[h["reason_code"]]
        r["holds"] += 1
        r["same_reason_flagged"] += any(x.reason_code == h["reason_code"] and x.severity in ("BLOCKING", "WARNING")
                                        for x in f)
        r["any_blocking_flagged"] += any(x.severity == "BLOCKING" for x in f)
    out = []
    for code in sorted(rows):
        r = rows[code]
        out.append({"reason_code": code, **r, "same_reason_rate": r["same_reason_flagged"] / r["holds"],
                    "any_blocking_rate": r["any_blocking_flagged"] / r["holds"]})
    tot = {k: sum(r[k] for r in rows.values()) for k in ("holds", "same_reason_flagged", "any_blocking_flagged")}
    out.append({"reason_code": "ALL", **tot, "same_reason_rate": tot["same_reason_flagged"] / tot["holds"],
                "any_blocking_rate": tot["any_blocking_flagged"] / tot["holds"]})
    return out


def blocking_precision(shipments, findings_by_shipment):
    """Share of shipments with at least one BLOCKING finding that were held, and the hold rate of the others."""
    flagged = [s for s in shipments if any(x.severity == "BLOCKING" for x in findings_by_shipment[s["shipment_id"]])]
    clean = [s for s in shipments if not any(x.severity == "BLOCKING" for x in findings_by_shipment[s["shipment_id"]])]
    return {"flagged_shipments": len(flagged), "flagged_held": sum(s["held"] for s in flagged),
            "flagged_hold_rate": sum(s["held"] for s in flagged) / len(flagged) if flagged else None,
            "unflagged_shipments": len(clean), "unflagged_held": sum(s["held"] for s in clean),
            "unflagged_hold_rate": sum(s["held"] for s in clean) / len(clean) if clean else None}
