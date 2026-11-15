"""Small SYNTHETIC seed for the Power Platform demo (Microsoft Lists). Fictional customers only."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(20261115)
OUT = Path(__file__).parent
LANES = ["CN-SG", "SG-MY", "US-SG", "SG-AU", "DE-SG"]
COMMODITIES = {  # commodity -> (example HS heading, permit usually needed? ASSUMPTION for demo)
    "Electronics": ("8471.30", False),
    "Auto parts": ("8708.99", False),
    "Cosmetics": ("3304.99", True),
    "Food supplements": ("2106.90", True),
    "Machinery": ("8479.89", False),
    "Apparel": ("6109.10", False),
}
HOLD_REASONS = ["Invoice missing", "HS code query", "Permit missing", "Valuation query",
                "Consignee details", "CoO missing"]
INCOTERMS = ["EXW", "FCA", "FOB", "CIF", "DAP", "DDP"]
START = date(2026, 10, 1)


def d(x):
    return x.isoformat() if x else ""


customers, shipments, actions = [], [], []
for i in range(1, 25):
    acct = f"DEMO-C{i:03d}"
    com = rng.choice(list(COMMODITIES))
    hs, permit_needed = COMMODITIES[com]
    invoice = rng.random() > 0.1
    packing = rng.random() > 0.08
    permit_ready = (not permit_needed) or rng.random() > 0.3
    uen = f"UEN-DEMO-{i:03d}" if rng.random() > 0.08 else ""
    coo = rng.random() > 0.5
    checks = [invoice, packing, permit_ready, bool(uen)]
    score = round(100 * sum(checks) / len(checks))
    status = "Validated" if score == 100 else ("Docs pending" if score >= 50 else "Requested")
    if status == "Validated" and rng.random() > 0.4:
        status = "Active"
    req = START + timedelta(days=rng.randint(0, 30))
    notes = []
    if not invoice:
        notes.append("Commercial invoice not yet received.")
    if not packing:
        notes.append("Packing list outstanding.")
    if permit_needed and not permit_ready:
        notes.append("Controlled item: permit/licence to be confirmed before first shipment.")
    if not uen:
        notes.append("Importer UEN missing on enrolment form.")
    if coo:
        notes.append("Customer wants FTA preference: certificate of origin needed.")
    customers.append({
        "CustomerName": f"Demo Customer {i:03d}", "AccountNo": acct,
        "TradeLane": rng.choice(LANES), "Commodity": com, "ImporterUEN": uen,
        "InvoiceReady": "Yes" if invoice else "No", "PackingListReady": "Yes" if packing else "No",
        "PermitNeeded": "Yes" if permit_needed else "No", "PermitReady": "Yes" if permit_ready else "No",
        "CoORequested": "Yes" if coo else "No", "ReadinessScore": score, "EnrolmentStatus": status,
        "HandlingNotes": " ".join(notes) or "No open items.", "RequestedOn": d(req),
        "AccountExec": f"AE-{rng.randint(1, 6):02d}",
    })
    if status not in ("Validated", "Active"):
        continue
    for seq in (1, 2, 3):
        ref = f"DEMO-S{i:03d}{seq}"
        booked = req + timedelta(days=7 * seq + rng.randint(0, 3))
        p_hold = 0.35 if seq == 1 else 0.15
        held = rng.random() < p_hold
        reason = rng.choice(HOLD_REASONS) if held else "None"
        if held and permit_needed and rng.random() < 0.5:
            reason = "Permit missing"
        held_on = booked + timedelta(days=rng.randint(2, 5)) if held else None
        released = (held_on + timedelta(days=rng.randint(1, 4))) if held and rng.random() > 0.5 else None
        status_s = "Held" if held and not released else ("Released" if held or rng.random() > 0.3 else "In transit")
        shipments.append({
            "ShipmentRef": ref, "AccountNo": acct, "ShipmentSeq": seq, "HSCode": hs,
            "DeclaredValueSGD": rng.randint(8, 400) * 100, "Incoterm": rng.choice(INCOTERMS),
            "Status": status_s, "HoldReason": reason, "HeldOn": d(held_on), "ReleasedOn": d(released),
        })
        if held:
            actions.append({
                "ActionTitle": f"Hold follow-up {ref}", "AccountNo": acct, "ShipmentRef": ref,
                "ActionType": "Hold follow-up", "LoggedOn": d(held_on),
                "Outcome": f"Reason: {reason}. " + ("Released after documents corrected." if released
                                                   else "Waiting for customer documents."),
                "LoggedBy": "Agent",
            })
    actions.append({
        "ActionTitle": f"Welcome call {acct}", "AccountNo": acct, "ShipmentRef": "",
        "ActionType": "Welcome call", "LoggedOn": d(req + timedelta(days=2)),
        "Outcome": "Explained first-three-shipment monitoring and document checklist.", "LoggedBy": "Agent",
    })

for name, rows in [("BA_Customers", customers), ("BA_Shipments", shipments), ("BA_ActionLog", actions)]:
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(name, len(rows))
