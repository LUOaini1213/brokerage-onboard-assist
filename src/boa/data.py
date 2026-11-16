"""Write and read the SYNTHETIC tables (data/synthetic/*.csv) and assemble validator bundles from them."""
from collections import defaultdict
from pathlib import Path

from .io import read_csv_rows, write_csv
from .paths import SYNTHETIC
from .synth import FILE_NAMES, TABLE_COLUMNS

BOOL = {"customs_account_active", "customs_account_active_at_submission", "sample_invoice_states_incoterm", "present",
        "preference_claimed", "bicon_check_recorded", "consignee_abn_provided", "held"}
INT = {"shipment_seq", "line_no", "quantity", "packing_quantity", "hold_count"}
FLOAT = {"unit_price", "line_value", "invoice_total", "gross_weight_kg", "freight_on_file", "insurance_on_file",
         "inland_costs_on_file", "permit_invoice_total", "permit_declared_value_sgd", "clearance_hours",
         "hours_to_release"}


def write_tables(tables, folder=SYNTHETIC):
    for name, rows in tables.items():
        write_csv(Path(folder) / FILE_NAMES[name], rows, TABLE_COLUMNS[name])


def _convert(col, value):
    if col in BOOL:
        return {"TRUE": True, "FALSE": False, "": None}[value]
    if value == "":
        return None if (col in INT or col in FLOAT) else ""
    if col in INT:
        return int(value)
    if col in FLOAT:
        return float(value)
    return value


def read_tables(folder=SYNTHETIC):
    out = {}
    for name, fname in FILE_NAMES.items():
        rows = read_csv_rows(Path(folder) / fname)
        out[name] = [{k: _convert(k, v) for k, v in r.items()} for r in rows]
    return out


def enrolment_bundles(t, lanes):
    """{enrolment_id: bundle for validator.validate_enrolment}."""
    customers = {c["customer_id"]: c for c in t["customers"]}
    products = defaultdict(list)
    for p in t["products"]:
        products[p["customer_id"]].append(p)
    out = {}
    for e in t["enrolments"]:
        cust = customers[e["customer_id"]]
        out[e["enrolment_id"]] = {
            "enrolment_id": e["enrolment_id"], "customer_id": e["customer_id"],
            "documents_received": bool(e["documents_received_date"]),
            "uen_submitted": e["uen_submitted"],
            "customs_account_active_at_submission": e["customs_account_active_at_submission"],
            "sample_invoice_states_incoterm": e["sample_invoice_states_incoterm"],
            "licences_provided": set(filter(None, e["licences_provided_at_submission"].split(";"))),
            "direction": lanes[cust["primary_lane_id"]]["direction"],
            "products": products[e["customer_id"]]}
    return out


def shipment_bundles(t):
    """{shipment_id: bundle for validator.validate_shipment}."""
    customers = {c["customer_id"]: c for c in t["customers"]}
    lines = defaultdict(list)
    for ln in t["invoice_lines"]:
        lines[ln["shipment_id"]].append(ln)
    docs = defaultdict(dict)
    for d in t["documents"]:
        if d["scope"] == "shipment":
            docs[d["owner_id"]][d["doc_type"]] = d
    licences = defaultdict(dict)
    for x in t["licences"]:
        prev = licences[x["customer_id"]].get(x["authority"])
        if prev is None or x["obtained_date"] < prev:
            licences[x["customer_id"]][x["authority"]] = x["obtained_date"]
    origin = {p["product_id"]: p["origin_country"] for p in t["products"]}
    refs = defaultdict(lambda: defaultdict(set))
    for x in t["licences"]:
        refs[x["customer_id"]][x["authority"]].add(x["licence_ref"])
    out = {}
    for s in t["shipments"]:
        d = docs[s["shipment_id"]]
        transport = next(v for k, v in d.items() if k in ("Bill of lading", "Air waybill", "Truck consignment note"))
        out[s["shipment_id"]] = {
            "shipment": s, "customer": customers[s["customer_id"]], "invoice": d["Commercial invoice"],
            "lines": sorted(lines[s["shipment_id"]], key=lambda x: x["line_no"]),
            "packing_list": d["Packing list"], "transport_doc": transport,
            "co_present": d["Certificate of origin"]["present"], "licences": licences[s["customer_id"]],
            "licence_refs": refs[s["customer_id"]],
            "product_origin": origin}
    return out
