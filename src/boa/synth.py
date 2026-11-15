"""SYNTHETIC data generator: customers, enrolment requests, documents, each customer's first three shipments,
holds with reason codes, free-text hold notes, release times and the action log.

Nothing here comes from a real company, customer or shipment. Every probability, range and distribution is read
from config/synth_assumptions.json, where each one is labelled ASSUMPTION or ILLUSTRATIVE (docs/assumptions.md is
generated from it). The generator does not call the validator: holds are driven by *latent* defects (recorded in
shipment_defects.csv), so the validator can be scored against them.

Important consequence for every result built on this data: the hold-reason mix, release times and the effect of
corrective actions are whatever the assumptions say. The analytics recover the assumptions; they are a test of the
pipeline, not evidence about real customs holds.
"""
import math
from datetime import date, datetime, timedelta

import numpy as np

from .io import read_json
from .note_templates import ABBREVIATIONS, DISTRACTORS, REFERENCES, TEMPLATES
from .paths import CONFIG
from .rules import au_biosecurity_chapters, sg_flat_rates, sg_screening
from .valuation import fob_value, sg_cif

LABEL = "SYNTHETIC"
DEFECT_REASON = {
    "invoice_field_missing": "INVOICE_DATA", "incoterm_missing": "INVOICE_DATA",
    "charges_not_added": "VALUE_CIF", "value_typo": "VALUE_CIF",
    "hs_invalid": "HS_INVALID", "hs_misclassified": "HS_QUERY",
    "licence_missing": "CA_APPROVAL",
    "co_missing": "ORIGIN_DOCS", "origin_as_loading_country": "ORIGIN_DOCS",
    "quantity_mismatch": "DOC_MISMATCH", "weight_mismatch": "DOC_MISMATCH",
    "packing_list_missing": "DOC_MISMATCH", "transport_doc_missing": "DOC_MISMATCH",
    "permit_late": "PERMIT_TIMING", "importer_uen_mismatch": "PARTY_UEN",
    "au_bicon_not_checked": "BIOSECURITY",
    "au_abn_missing": None,   # readiness warning only; never causes a hold in this data
}
CONFIG_KEY = {"licence_missing": "licence_missing_if_controlled", "co_missing": "co_missing_if_preference",
              "au_bicon_not_checked": "au_bicon_not_checked_if_screened"}
INVOICE_FIELDS = ["invoice number", "invoice date", "currency", "goods description", "unit price",
                  "country of origin"]
# Rule cited on the corrective action of a hold, by reason (import lane, export lane).
ACTION_RULE = {"PERMIT_TIMING": ("SG-IMP-01", "SG-EXP-01"), "PARTY_UEN": ("SG-IMP-04", "SG-EXP-05"),
               "HS_INVALID": ("SG-IMP-05", "SG-IMP-05"), "HS_QUERY": ("SG-IMP-05", "AU-06"),
               "VALUE_CIF": ("SG-IMP-07", "AU-03"), "INVOICE_DATA": ("SG-IMP-23", "SG-IMP-23"),
               "CA_APPROVAL": ("SG-IMP-14", "AU-08"), "ORIGIN_DOCS": ("SG-IMP-22", "AU-09"),
               "DOC_MISMATCH": ("SG-IMP-28", "AU-02"), "INSPECTION": ("", "AU-10"),
               "BIOSECURITY": ("AU-07", "AU-07")}
CHECK_LETTERS = "ABCDEFGHJKLMNPRSTUWXYZ"


class Config:
    """Read-only view of config/synth_assumptions.json that fails loudly on an undocumented parameter."""

    def __init__(self, raw):
        self.raw = raw

    def __getitem__(self, key):
        if key not in self.raw:
            raise KeyError(f"assumption {key!r} is not in config/synth_assumptions.json")
        entry = self.raw[key]
        if not isinstance(entry, dict) or "value" not in entry or not entry.get("about"):
            raise KeyError(f"assumption {key!r} has no value/about")
        return entry["value"]


def load_config(path=None):
    return Config(read_json(path or CONFIG / "synth_assumptions.json"))


def _ts(x):
    return x.strftime("%Y-%m-%dT%H:%M")


def _d(x):
    return x.isoformat() if x else ""


class Generator:
    def __init__(self, cfg):
        self.c = cfg
        self.rng = np.random.default_rng(cfg["seed"])
        self.lanes = cfg["lanes"]
        self.lane = {ln["lane_id"]: ln for ln in self.lanes}
        self.as_of = date.fromisoformat(cfg["as_of_date"])
        self.cutoff = self.as_of - timedelta(days=cfg["shipment_cutoff_days_before_as_of"])
        self.fx = cfg["fx_to_sgd"]
        self.desc = cfg["product_descriptions"]
        self.screens = [s for s in sg_screening() if s.kind == "controlled"]
        self.dutiable = [s for s in sg_screening() if s.kind == "dutiable"]
        self.bio = au_biosecurity_chapters()
        self.t = {k: [] for k in ("customers", "products", "licences", "enrolments", "documents", "invoice_lines",
                                  "shipments", "shipment_defects", "holds", "actions")}
        self.n_action = 0
        self.n_hold = 0

    # ------------------------------------------------------------------ random helpers
    def bern(self, p):
        return self.rng.random() < min(1.0, max(0.0, p))

    def u(self, lo, hi):
        return float(self.rng.uniform(lo, hi))

    def ri(self, lo, hi):
        return int(self.rng.integers(lo, hi + 1))

    def pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]

    def pick_weighted(self, items, weights):
        w = np.asarray(weights, dtype=float)
        return items[int(self.rng.choice(len(items), p=w / w.sum()))]

    def lognormal(self, median, sigma):
        return float(median * math.exp(sigma * self.rng.standard_normal()))

    # ------------------------------------------------------------------ ids and codes
    def new_uen(self):
        # Local-company pattern with registration year 2099: format-valid, but no real entity can have it.
        return f"2099{self.ri(0, 99999):05d}{self.pick(CHECK_LETTERS)}"

    def malformed_uen(self, good):
        return self.pick([good[:-1], good[:-1] + good[-1].lower(), good[1:], good[:-1] + "0"])

    def code8(self, hs6):
        return hs6 + self.pick(self.c["national_suffixes"])

    def screened_authorities(self, hs_code, direction):
        if direction != "Import":
            return []
        return sorted({s.authority for s in self.screens if hs_code.startswith(s.hs_prefix)})

    def is_dutiable(self, hs_code):
        return any(hs_code.startswith(s.hs_prefix) for s in self.dutiable)

    def action(self, customer_id, shipment_id, hold_id, reason, action_type, rule_ref, role, opened, closed, source):
        self.n_action += 1
        status = "Closed" if closed is not None and closed <= self.as_of else "Open"
        self.t["actions"].append({
            "data_label": LABEL, "action_id": f"SYN-A{self.n_action:05d}", "customer_id": customer_id,
            "shipment_id": shipment_id or "", "hold_id": hold_id or "", "source": source, "reason_code": reason,
            "action_type": action_type, "rule_ref": rule_ref, "owner_role": role, "opened_date": _d(opened),
            "due_date": _d(opened + timedelta(days=self.c["action_sla_days"])),
            "closed_date": _d(closed) if status == "Closed" else "", "status": status})
        return closed if status == "Closed" else None

    # ------------------------------------------------------------------ customers and enrolment
    def run(self):
        segs = list(self.c["segment_mix"])
        start, end = (date.fromisoformat(x) for x in self.c["enrolment_window"])
        weekdays = [start + timedelta(days=i) for i in range((end - start).days + 1)
                    if (start + timedelta(days=i)).weekday() < 5]
        for i in range(1, self.c["n_customers"] + 1):
            seg = self.pick_weighted(segs, [self.c["segment_mix"][s] for s in segs])
            lane = self.pick_weighted(self.lanes, [ln["weight"] for ln in self.lanes])
            group = self.pick_weighted(self.c["commodities"], [g["weight"] for g in self.c["commodities"]])
            self.customer(i, seg, lane, group, self.pick(weekdays))
        return self.t

    def customer(self, i, seg, lane, group, submitted):
        c, m = self.c, self.c["segment_defect_multiplier"][seg]
        cid = f"SYN-C{i:04d}"
        po = c["product_origin"]
        n_prod = min(self.ri(*c["products_per_customer"]), len(group["hs6"]))
        hs6s = [group["hs6"][j] for j in sorted(self.rng.choice(len(group["hs6"]), size=n_prod, replace=False))]
        products = []
        for k, h6 in enumerate(hs6s, 1):
            if lane["direction"] == "Import":
                origin = lane["origin"] if self.bern(po["p_same_as_export_country"]) else \
                    self.pick([x for x in po["other_import_origins"] if x != lane["origin"]])
            else:
                origin = "SG" if self.bern(po["p_singapore_made_export"]) else self.pick(po["export_origins"])
            products.append({"product_id": f"{cid}-P{k}", "hs_code": self.code8(h6), "origin_country": origin,
                             "description": self.desc[h6], "unit": group["unit"]})
        ed = c["enrolment_defects"]
        uen_missing = self.bern(ed["uen_missing"] * m)
        uen_malformed = not uen_missing and self.bern(ed["uen_malformed"] * m)
        account_inactive = self.bern(ed["customs_account_inactive"] * m)
        no_incoterm = self.bern(ed["sample_invoice_no_incoterm"] * m)
        hs_bad = self.bern(ed["product_hs_invalid"] * m)
        good_uen = self.new_uen()
        submitted_uen = "" if uen_missing else (self.malformed_uen(good_uen) if uen_malformed else good_uen)
        submitted_hs = [p["hs_code"] for p in products]
        if hs_bad:
            submitted_hs[self.ri(0, len(products) - 1)] = self.pick(c["outdated_or_malformed_hs"])
        authorities = sorted({a for p in products for a in self.screened_authorities(p["hs_code"], lane["direction"])})
        licence_at_enrolment = {a: not self.bern(ed["licence_missing_if_controlled"] * m) for a in authorities}

        f = c["funnel"]
        docs = self.bern(f["p_docs_received"])
        docs_date = submitted + timedelta(days=self.ri(*f["days_to_docs"])) if docs else None
        blocking = uen_missing or uen_malformed or account_inactive or hs_bad
        validated = profile = None
        fixed = False
        if docs_date and docs_date <= self.as_of:
            if blocking:
                fixed = self.bern(f["p_fix_after_findings"])
                if fixed:
                    validated = docs_date + timedelta(days=self.ri(*f["days_to_fix"]))
            else:
                validated = docs_date + timedelta(days=self.ri(*f["days_to_validate"]))
            if validated and validated > self.as_of:
                validated = None
            if validated and self.bern(f["p_profile"]):
                profile = validated + timedelta(days=self.ri(*f["days_to_profile"]))
                if profile > self.as_of:
                    profile = None
        else:
            docs_date = None
        # customer master after the fixes (what the profile holds); before profile it is what was submitted
        corrected = validated is not None
        uen = good_uen if corrected else submitted_uen
        active = True if corrected else not account_inactive
        self.t["customers"].append({
            "data_label": LABEL, "customer_id": cid, "customer_name": f"Synthetic Customer {i:04d}", "segment": seg,
            "uen": uen, "customs_account_active": active, "primary_lane_id": lane["lane_id"],
            "trade_direction": lane["direction"], "commodity_group": group["group"]})
        for p, sub in zip(products, submitted_hs):
            self.t["products"].append({"data_label": LABEL, "customer_id": cid, **p,
                                       "hs_code": p["hs_code"] if corrected else sub, "hs_code_submitted": sub})
        enrol_id = f"SYN-E{i:04d}"
        self.t["enrolments"].append({
            "data_label": LABEL, "enrolment_id": enrol_id, "customer_id": cid, "submitted_date": _d(submitted),
            "uen_submitted": submitted_uen, "customs_account_active_at_submission": not account_inactive,
            "sample_invoice_states_incoterm": not no_incoterm, "documents_received_date": _d(docs_date),
            "validated_date": _d(validated), "profile_created_date": _d(profile),
            "first_shipment_released_date": "", "third_shipment_released_date": ""})
        enrol = self.t["enrolments"][-1]
        self.t["documents"] += [
            {"data_label": LABEL, "doc_id": f"{enrol_id}-D1", "scope": "enrolment", "owner_id": enrol_id,
             "doc_type": "ACRA business profile", "present": bool(submitted_uen) and docs_date is not None},
            {"data_label": LABEL, "doc_id": f"{enrol_id}-D2", "scope": "enrolment", "owner_id": enrol_id,
             "doc_type": "Product list with HS codes", "present": docs_date is not None},
            {"data_label": LABEL, "doc_id": f"{enrol_id}-D3", "scope": "enrolment", "owner_id": enrol_id,
             "doc_type": "Sample commercial invoice", "present": docs_date is not None}]
        # enrolment actions for what the validator would flag
        lic_date = {}
        if docs_date:
            close = validated if fixed else None
            if uen_missing or uen_malformed:
                self.action(cid, None, None, "PARTY_UEN", "Request UEN as on ACRA business profile", "SG-IMP-03",
                            "Onboarding analyst", docs_date, close, "Enrolment")
            if account_inactive:
                self.action(cid, None, None, "PARTY_UEN", "Ask customer to activate Customs account", "SG-IMP-02",
                            "Customer", docs_date, close, "Enrolment")
            if hs_bad:
                self.action(cid, None, None, "HS_INVALID", "Correct HS code on product list", "SG-IMP-05",
                            "Onboarding analyst", docs_date, close, "Enrolment")
            if no_incoterm:
                self.action(cid, None, None, "INVOICE_DATA", "Add Incoterm to customer's invoice checklist",
                            "SG-IMP-24", "Onboarding analyst", docs_date, docs_date + timedelta(days=self.ri(0, 2)),
                            "Enrolment")
            for a, ok in licence_at_enrolment.items():
                if ok:
                    lic_date[a] = docs_date
                    continue
                lic_date[a] = None
                if corrected and self.bern(c["p_licence_before_first_shipment"]):
                    lic_date[a] = validated + timedelta(days=self.ri(1, 20))
                closed = self.action(cid, None, None, "CA_APPROVAL", f"Obtain {a} licence before first shipment",
                                     "SG-IMP-14", "Customer", docs_date, lic_date[a], "Enrolment")
                if closed is None:
                    lic_date[a] = None
            for a, d in lic_date.items():
                if d is not None:
                    self.record_licence(cid, a, d)
        enrol["licences_provided_at_submission"] = ";".join(a for a, ok in licence_at_enrolment.items()
                                                            if ok and docs_date)
        if profile and self.bern(f["p_ships"]):
            self.shipments(cid, i, seg, lane, products, profile, uen, enrol)

    def record_licence(self, cid, authority, obtained):
        n = sum(1 for x in self.t["licences"] if x["customer_id"] == cid) + 1
        self.t["licences"].append({"data_label": LABEL, "customer_id": cid, "authority": authority,
                                   "licence_ref": f"SYN-{authority.replace(' ', '')}-{cid[-4:]}{n}",
                                   "obtained_date": _d(obtained)})

    # ------------------------------------------------------------------ shipments
    def shipments(self, cid, i, seg, lane0, products, profile, uen, enrol):
        c, f = self.c, self.c["funnel"]
        arrival_day = profile + timedelta(days=self.ri(*f["days_to_first_shipment"]))
        learned = {}        # reason -> date its corrective action closed
        released_dates = []
        for seq in (1, 2, 3):
            if arrival_day > self.cutoff:
                break
            same_dir = [ln for ln in self.lanes if ln["direction"] == lane0["direction"]]
            lane = lane0 if self.bern(c["p_primary_lane"]) else \
                self.pick_weighted(same_dir, [ln["weight"] for ln in same_dir])
            arrival = datetime.combine(arrival_day, datetime.min.time()) + timedelta(minutes=self.ri(0, 24 * 60 - 1))
            transit = self.ri(*lane["transit_days"])
            departure = arrival - timedelta(days=transit, minutes=self.ri(0, 600))
            released = self.shipment(cid, i, seg, lane, products, uen, seq, arrival, departure, learned)
            released_dates.append(released)
            arrival_day = arrival_day + timedelta(days=self.ri(*f["days_between_shipments"]))
        if released_dates and released_dates[0] <= self.as_of:
            enrol["first_shipment_released_date"] = _d(released_dates[0])
        if len(released_dates) == 3 and released_dates[2] <= self.as_of:
            enrol["third_shipment_released_date"] = _d(released_dates[2])

    def shipment(self, cid, i, seg, lane, products, uen, seq, arrival, departure, learned):
        c = self.c
        sid = f"SYN-S{i:04d}-{seq}"
        m = c["segment_defect_multiplier"][seg] * c["sequence_multiplier"][seq - 1]
        sd = c["shipment_defects"]
        is_import = lane["direction"] == "Import"

        def p(name):
            reason = DEFECT_REASON[name]
            mult = c["recurrence_multiplier_after_action"] if reason in learned and learned[reason] <= arrival.date() \
                else 1.0
            return sd[CONFIG_KEY.get(name, name)] * m * mult

        term = self.pick_weighted(list(c["incoterm_mix"]), list(c["incoterm_mix"].values()))
        currency = self.pick(c["currency_by_origin"][lane["origin"]])
        group = next(g for g in c["commodities"] if any(pr["hs_code"][:6] in g["hs6"] for pr in products))
        n_lines = min(self.ri(*c["lines_per_invoice"]), len(products))
        chosen = [products[j] for j in sorted(self.rng.choice(len(products), size=n_lines, replace=False))]
        lines = []
        lo_q, hi_q = c["quantity_per_line"]
        for k, pr in enumerate(chosen, 1):
            qty = int(round(math.exp(self.u(math.log(lo_q), math.log(hi_q)))))
            price_usd = self.u(*group["unit_price"])
            price = round(price_usd * self.fx["USD"] / self.fx[currency], 2)
            kg = qty * self.u(*group["kg_per_unit"])
            lines.append({"line_no": k, "product_id": pr["product_id"], "description": pr["description"],
                          "hs_code": pr["hs_code"], "quantity": qty, "unit": pr["unit"], "unit_price": price,
                          "line_value": round(qty * price, 2), "origin_country": pr["origin_country"],
                          "packing_quantity": qty, "ca_licence_ref": "", "_kg": kg, "_true_hs": pr["hs_code"]})
        total = round(sum(ln["line_value"] for ln in lines), 2)
        freight = round(total * self.u(*c["freight_share_of_value"][lane["mode"]]), 2)
        insurance = round(total * self.u(*c["insurance_share_of_value"]), 2)
        inland = round(total * self.u(*c["inland_share_of_value"]), 2)
        loading = lane["origin"]
        flat = (term == "FOB" and loading in sg_flat_rates()) or term == "CFR"
        known = self.bern(c["p_charges_known"]) if (is_import and flat) else True
        f_on, i_on = (freight, insurance) if known else (None, None)
        if term == "CFR" and not known:
            f_on = freight       # CFR: freight is in the price; only the insurance is unknown
        in_on = inland if term == "EXW" else None

        defects = []

        def add(name, line=None, detail=""):
            defects.append({"defect": name, "line_no": line, "detail": detail})

        lead = timedelta(hours=self.u(*c["permit_hours_before_arrival"]))
        anchor = arrival if is_import else departure
        permit_at = anchor - lead
        if self.bern(p("permit_late")):
            permit_at = anchor + timedelta(hours=self.u(1, 30))
            add("permit_late", None, f"{(permit_at - anchor).total_seconds() / 3600:.1f}h late")
        # licences: a screened line needs a licence obtained before the permit is submitted
        for ln in lines:
            for a in self.screened_authorities(ln["hs_code"], lane["direction"]):
                have = [x for x in self.t["licences"] if x["customer_id"] == cid and x["authority"] == a
                        and x["obtained_date"] <= _d(permit_at.date())]
                if have and not self.bern(p("licence_missing")):
                    ln["ca_licence_ref"] = (ln["ca_licence_ref"] + ";" if ln["ca_licence_ref"] else "") + \
                        have[-1]["licence_ref"]
                else:
                    add("licence_missing", ln["line_no"], a)
        invoice_no = f"SYN-INV-{i:04d}{seq}{self.ri(100, 999)}"
        inv = {"invoice_no": invoice_no, "invoice_date": _d((departure - timedelta(days=self.ri(1, 5))).date()),
               "seller_name": (f"Synthetic Supplier {self.ri(1, 400):03d}" if is_import
                               else f"Synthetic Customer {i:04d}"),
               "buyer_name": (f"Synthetic Customer {i:04d}" if is_import
                              else f"Synthetic Consignee {self.ri(1, 400):03d}"),
               "currency": currency, "incoterm": term, "invoice_total": total}
        if self.bern(p("invoice_field_missing")):
            fld = self.pick(INVOICE_FIELDS)
            add("invoice_field_missing", None, fld)
            if fld == "invoice number":
                inv["invoice_no"] = ""
            elif fld == "invoice date":
                inv["invoice_date"] = ""
            elif fld == "currency":
                inv["currency"] = ""
            else:
                key = {"goods description": "description", "unit price": "unit_price",
                       "country of origin": "origin_country"}[fld]
                lines[self.ri(0, len(lines) - 1)][key] = "" if key != "unit_price" else None
        if self.bern(p("incoterm_missing")):
            inv["incoterm"] = ""
            add("incoterm_missing")
        if self.bern(p("hs_invalid")):
            k = self.ri(0, len(lines) - 1)
            lines[k]["hs_code"] = self.pick(c["outdated_or_malformed_hs"])
            add("hs_invalid", lines[k]["line_no"], lines[k]["hs_code"])
        if self.bern(p("hs_misclassified")):
            k = self.ri(0, len(lines) - 1)
            others = [h for g in c["commodities"] if g["group"] != group["group"] for h in g["hs6"]]
            lines[k]["hs_code"] = self.code8(self.pick(others))
            add("hs_misclassified", lines[k]["line_no"], lines[k]["hs_code"])
        if self.bern(p("origin_as_loading_country")):
            cand = [ln for ln in lines if ln["origin_country"] and ln["origin_country"] != loading]
            if cand:
                ln = self.pick(cand)
                add("origin_as_loading_country", ln["line_no"], f"{ln['origin_country']}->{loading}")
                ln["origin_country"] = loading
        dutiable = any(self.is_dutiable(ln["_true_hs"]) for ln in lines)
        if is_import:
            preference = dutiable and self.bern(c["p_preference_claimed"]["SG_dutiable"])
        else:
            preference = self.bern(c["p_preference_claimed"]["AU_export"])
        co = preference
        if preference and self.bern(p("co_missing")):
            co = False
            add("co_missing")
        if self.bern(p("quantity_mismatch")):
            k = self.ri(0, len(lines) - 1)
            delta = max(1, int(round(lines[k]["quantity"] * self.u(0.01, 0.1))))
            lines[k]["packing_quantity"] = lines[k]["quantity"] + self.pick([-delta, delta])
            add("quantity_mismatch", lines[k]["line_no"], f"{lines[k]['quantity']}->{lines[k]['packing_quantity']}")
        packing_kg = round(sum(ln["_kg"] for ln in lines) * 1.05, 1)
        transport_kg = packing_kg
        if self.bern(p("weight_mismatch")):
            transport_kg = round(packing_kg * (1 + self.pick([-1, 1]) * self.u(0.03, 0.12)), 1)
            add("weight_mismatch", None, f"{packing_kg}->{transport_kg}")
        packing_present = not self.bern(p("packing_list_missing"))
        if not packing_present:
            add("packing_list_missing")
            for ln in lines:
                ln["packing_quantity"] = None
        transport_present = not self.bern(p("transport_doc_missing"))
        if not transport_present:
            add("transport_doc_missing")
        permit_uen = uen
        if self.bern(p("importer_uen_mismatch")):
            permit_uen = uen[:5] + str((int(uen[5]) + 1) % 10) + uen[6:]
            add("importer_uen_mismatch", None, permit_uen)
        bicon = True
        abn = True
        if not is_import:
            if any(ln["_true_hs"][:2] in self.bio for ln in lines) and self.bern(p("au_bicon_not_checked")):
                bicon = False
                add("au_bicon_not_checked")
            if self.bern(p("au_abn_missing")):
                abn = False
                add("au_abn_missing")

        # the value the declarant puts on the permit
        permit_total = total
        if is_import:
            cif = sg_cif(total, term, f_on, i_on, in_on, 0.0, loading).amount
            if cif is None:          # cannot happen for a complete set of charges; keep the generator honest
                raise AssertionError(f"{sid}: CIF not computable with known charges ({term})")
            declared = cif
            needs_additions = term in ("EXW", "FCA", "FAS", "FOB", "CFR", "CPT")
            if needs_additions and self.bern(p("charges_not_added")):
                declared = total
                add("charges_not_added", None, f"{term}: declared {total} instead of {cif}")
        else:
            declared = fob_value(total, term, freight, insurance, inland).amount
        if self.bern(p("value_typo")):
            factor = 1 + self.pick([-1, 1]) * self.u(0.03, 0.15)
            permit_total = round(total * factor, 2)
            declared = declared * factor
            add("value_typo", None, f"x{factor:.3f}")
        declared_sgd = round(declared * self.fx[currency], 2)

        # holds
        reasons = sorted({DEFECT_REASON[d["defect"]] for d in defects if DEFECT_REASON[d["defect"]]})
        held = [r for r in reasons if self.bern(c["p_hold_given_defect"][r])]
        if self.bern(c["p_random_inspection"]):
            held.append("INSPECTION")
        rh = c["release_hours"]
        held = sorted(held, key=lambda r: (-rh[r][0], r))[: c["max_holds_per_shipment"]]
        dest = lane["destination"]
        mult = (c["release_mode_multiplier"][lane["mode"]] * c["release_destination_multiplier"][dest]
                * c["segment_response_multiplier"][seg])
        base_med, base_sig = c["base_clearance_hours"][lane["mode"]]
        clearance = self.lognormal(base_med, base_sig)
        start_offset = timedelta(hours=self.u(*c["hold_start_hours_after_arrival"]))
        t_next = None
        hold_rows = []
        for r in held:
            hours = self.lognormal(rh[r][0], rh[r][1]) * mult
            if t_next is None:
                begin = (departure if (r == "PERMIT_TIMING" and not is_import) else arrival) + start_offset
            else:
                begin = t_next + timedelta(hours=self.u(0, 2))
            end = begin + timedelta(hours=hours)
            t_next = end
            clearance += hours
            self.n_hold += 1
            hid = f"SYN-H{self.n_hold:05d}"
            note, tpl = self.note(r, sid, lines, inv, term, declared_sgd, total, currency, permit_uen, loading,
                                  is_import, transport_kg, packing_kg, permit_at, anchor, defects)
            open_hold = end.date() > self.as_of
            hold_rows.append({"data_label": LABEL, "hold_id": hid, "shipment_id": sid, "customer_id": cid,
                              "lane_id": lane["lane_id"], "reason_code": r, "hold_start": _ts(begin),
                              "released_at": "" if open_hold else _ts(end),
                              "hours_to_release": None if open_hold else round(hours, 1),
                              "note": note, "note_template": f"{r}-{tpl}"})
            # corrective actions
            types = c["action_types"][r]
            owner = c["action_owner_by_reason"][r]
            if owner not in c["action_owner_roles"]:
                raise ValueError(f"owner {owner!r} of {r} is not in action_owner_roles")
            rule_ref = ACTION_RULE[r][0 if is_import else 1]
            opened = begin.date()
            closed1 = opened + timedelta(days=math.ceil(self.lognormal(*c["action_close_days"])))
            closed1 = self.action(cid, sid, hid, r, types[0], rule_ref, owner, opened, closed1, "Hold")
            if len(types) > 1 and self.bern(c["p_second_action"]):
                closed2 = opened + timedelta(days=math.ceil(self.lognormal(*c["action_close_days"])))
                self.action(cid, sid, hid, r, types[1], rule_ref, c["action_owner_roles"][0], opened, closed2, "Hold")
            if closed1 is not None:
                learned.setdefault(r, closed1)
                if r == "CA_APPROVAL":
                    for d in defects:
                        if d["defect"] == "licence_missing":
                            have = [x for x in self.t["licences"] if x["customer_id"] == cid
                                    and x["authority"] == d["detail"]]
                            if not have:
                                self.record_licence(cid, d["detail"], closed1)
        released = arrival + timedelta(hours=clearance)
        self.t["holds"] += hold_rows

        # write the shipment, its documents and lines
        trans_kind = {"Sea": "Bill of lading", "Air": "Air waybill", "Road": "Truck consignment note"}[lane["mode"]]
        self.t["shipments"].append({
            "data_label": LABEL, "shipment_id": sid, "customer_id": cid, "shipment_seq": seq,
            "lane_id": lane["lane_id"], "direction": lane["direction"], "mode": lane["mode"],
            "origin_country": lane["origin"], "destination_country": dest, "loading_country": loading,
            "departure_at": _ts(departure), "arrival_at": _ts(arrival), "permit_submitted_at": _ts(permit_at),
            "freight_on_file": f_on if is_import else freight, "insurance_on_file": i_on if is_import else insurance,
            "inland_costs_on_file": in_on if is_import else inland,
            "preference_claimed": preference, "bicon_check_recorded": bicon if not is_import else None,
            "consignee_abn_provided": abn if not is_import else None,
            "permit_party_uen": permit_uen, "permit_invoice_total": permit_total,
            "permit_declared_value_sgd": declared_sgd, "released_at": _ts(released),
            "clearance_hours": round(clearance, 1), "held": bool(hold_rows), "hold_count": len(hold_rows)})
        base = {"data_label": LABEL, "scope": "shipment", "owner_id": sid}
        self.t["documents"] += [
            {**base, "doc_id": f"{sid}-INV", "doc_type": "Commercial invoice", "present": True,
             "invoice_no": inv["invoice_no"], "invoice_date": inv["invoice_date"], "seller_name": inv["seller_name"],
             "buyer_name": inv["buyer_name"], "currency": inv["currency"], "incoterm": inv["incoterm"],
             "invoice_total": total},
            {**base, "doc_id": f"{sid}-PL", "doc_type": "Packing list", "present": packing_present,
             "gross_weight_kg": packing_kg if packing_present else None},
            {**base, "doc_id": f"{sid}-TD", "doc_type": trans_kind, "present": transport_present,
             "gross_weight_kg": transport_kg if transport_present else None},
            {**base, "doc_id": f"{sid}-CO", "doc_type": "Certificate of origin", "present": bool(co)}]
        for ln in lines:
            self.t["invoice_lines"].append({"data_label": LABEL, "shipment_id": sid,
                                            **{k: v for k, v in ln.items() if not k.startswith("_")}})
        for d in defects:
            self.t["shipment_defects"].append({"data_label": LABEL, "shipment_id": sid, "defect": d["defect"],
                                               "reason_code": DEFECT_REASON[d["defect"]] or "",
                                               "line_no": d["line_no"], "detail": d["detail"]})
        return released.date()

    # ------------------------------------------------------------------ notes
    def note(self, reason, sid, lines, inv, term, declared_sgd, total, currency, uen, loading, is_import,
             tkg, pkg, permit_at, anchor, defects):
        nn = self.c["note_noise"]
        tpl = int(self.rng.integers(len(TEMPLATES[reason])))
        line = lines[self.ri(0, len(lines) - 1)]
        alt = self.code8(self.pick([h for g in self.c["commodities"] for h in g["hs6"] if h != line["hs_code"][:6]]))
        missing = next((d["detail"] for d in defects if d["defect"] == "invoice_field_missing"), None)
        if any(d["defect"] == "incoterm_missing" for d in defects) and (missing is None or self.bern(0.5)):
            missing = "Incoterm / terms of delivery"
        ca = next((d["detail"] for d in defects if d["defect"] == "licence_missing"), None) or "competent authority"
        origin_mismatch = next((d["detail"] for d in defects if d["defect"] == "origin_as_loading_country"), None)
        country = origin_mismatch.split("->")[0] if origin_mismatch else self.pick(["TH", "VN", "MY", "IN"])
        calc = round(declared_sgd * self.u(1.04, 1.25), 2)
        values = {
            "event": "arrival" if is_import else "departure", "ref": sid, "inv": inv["invoice_no"] or "(no number)",
            "hs": line["hs_code"], "hs_alt": alt, "hs_alt4": alt[:4], "desc": line["description"] or "the goods",
            "decl": f"{declared_sgd:,.2f}", "calc": f"{calc:,.2f}", "term": term, "field": missing or "invoice date",
            "ca": ca, "lic": f"{ca} licence", "country": country, "pol": loading, "q1": line["quantity"],
            "q2": line["packing_quantity"] if line["packing_quantity"] is not None else line["quantity"] + 5,
            "w1": f"{pkg:,.1f}", "w2": f"{tkg:,.1f}", "uen": uen or "(blank)", "line": line["line_no"],
            "hours": max(1, int(round(abs((permit_at - anchor).total_seconds()) / 3600)))}
        text = TEMPLATES[reason][tpl].format(**values)
        if self.bern(nn["p_distractor"]):
            options = [s for s, related in DISTRACTORS if reason not in related]
            text = text + " " + self.pick(options)
        if self.bern(nn["p_abbreviate"]):
            for full, short in ABBREVIATIONS:
                if full in text.lower() and self.bern(0.6):
                    idx = text.lower().find(full)
                    text = text[:idx] + short + text[idx + len(full):]
        if self.bern(nn["p_typo"]):
            words = [w for w in text.split(" ") if len(w) > 4 and w.isalpha()]
            if words:
                w = self.pick(words)
                k = self.ri(1, len(w) - 2)
                text = text.replace(w, w[:k] + w[k + 1] + w[k] + w[k + 2:], 1)
        if self.bern(nn["p_reference"]):
            text = text + " " + self.pick(REFERENCES).format(ref=sid)
        if self.bern(nn["p_lowercase"]):
            text = text.lower()
        return text, tpl


TABLE_COLUMNS = {
    "customers": ["data_label", "customer_id", "customer_name", "segment", "uen", "customs_account_active",
                  "primary_lane_id", "trade_direction", "commodity_group"],
    "products": ["data_label", "customer_id", "product_id", "description", "hs_code", "hs_code_submitted",
                 "origin_country", "unit"],
    "licences": ["data_label", "customer_id", "authority", "licence_ref", "obtained_date"],
    "enrolments": ["data_label", "enrolment_id", "customer_id", "submitted_date", "uen_submitted",
                   "customs_account_active_at_submission", "sample_invoice_states_incoterm",
                   "licences_provided_at_submission", "documents_received_date", "validated_date", "profile_created_date",
                   "first_shipment_released_date", "third_shipment_released_date"],
    "documents": ["data_label", "doc_id", "scope", "owner_id", "doc_type", "present", "invoice_no", "invoice_date",
                  "seller_name", "buyer_name", "currency", "incoterm", "invoice_total", "gross_weight_kg"],
    "invoice_lines": ["data_label", "shipment_id", "line_no", "product_id", "description", "hs_code", "quantity",
                      "unit", "unit_price", "line_value", "origin_country", "packing_quantity", "ca_licence_ref"],
    "shipments": ["data_label", "shipment_id", "customer_id", "shipment_seq", "lane_id", "direction", "mode",
                  "origin_country", "destination_country", "loading_country", "departure_at", "arrival_at",
                  "permit_submitted_at", "freight_on_file", "insurance_on_file", "inland_costs_on_file",
                  "preference_claimed", "bicon_check_recorded", "consignee_abn_provided", "permit_party_uen",
                  "permit_invoice_total", "permit_declared_value_sgd", "released_at", "clearance_hours", "held",
                  "hold_count"],
    "shipment_defects": ["data_label", "shipment_id", "defect", "reason_code", "line_no", "detail"],
    "holds": ["data_label", "hold_id", "shipment_id", "customer_id", "lane_id", "reason_code", "hold_start",
              "released_at", "hours_to_release", "note", "note_template"],
    "actions": ["data_label", "action_id", "customer_id", "shipment_id", "hold_id", "source", "reason_code",
                "action_type", "rule_ref", "owner_role", "opened_date", "due_date", "closed_date", "status"],
}
FILE_NAMES = {"customers": "customers.csv", "products": "products.csv", "licences": "licences.csv",
              "enrolments": "enrolment_requests.csv", "documents": "documents.csv",
              "invoice_lines": "invoice_lines.csv", "shipments": "shipments.csv",
              "shipment_defects": "shipment_defects_truth.csv", "holds": "holds.csv", "actions": "actions.csv"}


def generate(cfg=None):
    return Generator(cfg or load_config()).run()
