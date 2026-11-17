"""Document-readiness checks for enrolments and shipments, a readiness score and the corrective-action route.

Each check cites the rulebook rule it implements (rules/rulebook.json). The validator only reads what a broker
would have before lodging: the customer profile, product list, licences on file, the commercial invoice and its
lines, packing list, transport document, certificate of origin and the draft permit fields. It never reads the
generator's latent-defect table (shipment_defects_truth.csv), which is used only to score it.

Severity: BLOCKING = the permit should not be lodged as is; WARNING = lodge only after a look; INFO = fact for the
handling note. Readiness score = 100 - 25 per blocking finding - 8 per warning, floored at 0; the weights are an
assumption of this project, not a customs rule.
"""
from dataclasses import asdict, dataclass

from . import hs as hsmod
from .rules import au_biosecurity_chapters, sg_screening
from .uen import uen_type
from .valuation import (au_declaration_type, au_gst, au_voti, fob_value, sg_cif, sg_gst)

WEIGHTS = {"BLOCKING": 25, "WARNING": 8, "INFO": 0}
VALUE_TOLERANCE = 0.005      # SG-IMP-07 assumption: 0.5% of the computed value ...
VALUE_MIN_SGD = 1.0          # ... but never less than SGD 1
WEIGHT_TOLERANCE = 0.02      # SG-IMP-28 assumption
AMOUNT_TOLERANCE = 0.005     # invoice arithmetic (line value vs quantity x price, total vs lines)


@dataclass(frozen=True)
class Finding:
    check: str
    rule_id: str
    reason_code: str
    severity: str
    message: str
    line_no: int | None = None

    def as_dict(self):
        return asdict(self)


def readiness(findings):
    """(score 0-100, band) for a list of findings."""
    score = max(0, 100 - sum(WEIGHTS[f.severity] for f in findings))
    if any(f.severity == "BLOCKING" for f in findings):
        band = "Not ready"
    elif any(f.severity == "WARNING" for f in findings):
        band = "Needs attention"
    else:
        band = "Ready"
    return score, band


def _blank(x):
    return x is None or (isinstance(x, float) and x != x) or (isinstance(x, str) and not x.strip())


def _close(a, b, rel, floor):
    return abs(a - b) <= max(rel * max(abs(a), abs(b)), floor) + 1e-9   # a one-cent gap is not exactly 0.01 in floats


def screens_for(hs_code, kinds=("controlled", "dutiable", "prohibited")):
    code = hsmod.normalise(hs_code)
    return [s for s in sg_screening() if s.kind in kinds and code.startswith(s.hs_prefix)]


# ---------------------------------------------------------------------------------------------- enrolment

def validate_enrolment(e):
    """e: dict with uen_submitted, customs_account_active_at_submission, sample_invoice_states_incoterm,
    licences_provided (set of authorities), direction ('Import'/'Export'), documents_received (bool),
    products: list of dicts with product_id, hs_code_submitted, description."""
    out = []
    if not e["documents_received"]:
        return [Finding("docs_present", "SG-IMP-25", "DOC_MISMATCH", "BLOCKING",
                        "enrolment documents (business profile, product list, sample invoice) not received")]
    uen = e["uen_submitted"]
    if _blank(uen):
        out.append(Finding("uen_present_and_format", "SG-IMP-03", "PARTY_UEN", "BLOCKING", "UEN missing"))
    elif uen_type(uen) is None:
        out.append(Finding("uen_present_and_format", "SG-IMP-03", "PARTY_UEN", "BLOCKING",
                           f"UEN {uen!r} matches none of the UEN formats"))
    if not e["customs_account_active_at_submission"]:
        out.append(Finding("customs_account_active", "SG-IMP-02", "PARTY_UEN", "BLOCKING",
                           "Customs account not activated; no permit can be submitted until it is"))
    for p in e["products"]:
        for problem, msg in hsmod.check(p["hs_code_submitted"], "SG"):
            out.append(Finding("hs_format_and_hs6", "SG-IMP-05", "HS_INVALID", "BLOCKING",
                               f"product {p['product_id']}: {msg}"))
        if e["direction"] == "Import":
            for s in screens_for(p["hs_code_submitted"], ("controlled",)):
                if s.authority not in e["licences_provided"]:
                    out.append(Finding("ca_screening", s.rule_id, "CA_APPROVAL", "WARNING",
                                       f"product {p['product_id']} ({p['description']}): {s.authority} "
                                       f"({s.scope}); ask for {s.licence_to_ask_for} before the first shipment"))
            for s in screens_for(p["hs_code_submitted"], ("prohibited",)):
                out.append(Finding("prohibited_screening", s.rule_id, "CA_APPROVAL", "BLOCKING",
                                   f"product {p['product_id']}: {s.scope} - prohibited import"))
    if not e["sample_invoice_states_incoterm"]:
        out.append(Finding("incoterm_present", "SG-IMP-24", "INVOICE_DATA", "WARNING",
                           "sample invoice states no Incoterm; ask the supplier to state one on every invoice"))
    return _dedupe(out)


def _dedupe(findings):
    seen, out = set(), []
    for f in findings:
        key = (f.check, f.rule_id, f.message, f.line_no)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


# ---------------------------------------------------------------------------------------------- shipment

def validate_shipment(b, fx_to_sgd, fx_sgd_to_aud):
    """b: dict bundle with keys
       shipment: shipment fields (direction, mode, loading_country, arrival_at, departure_at, permit_submitted_at,
                 freight_on_file, insurance_on_file, inland_costs_on_file, preference_claimed, bicon_check_recorded,
                 consignee_abn_provided, permit_party_uen, permit_invoice_total, permit_declared_value_sgd)
       customer: uen, customs_account_active
       invoice: present, invoice_no, invoice_date, seller_name, buyer_name, currency, incoterm, invoice_total
       lines: list of invoice lines (line_no, description, hs_code, quantity, unit, unit_price, line_value,
              origin_country, packing_quantity, ca_licence_ref)
       packing_list: present, gross_weight_kg;  transport_doc: present, gross_weight_kg;  co_present: bool
       licences: {authority: obtained_date (ISO)} on file for the customer
       licence_refs: {authority: set of licence references on file}; a controlled line must quote one of them
       product_origin: {product_id: country of manufacture on the product master}
    fx_to_sgd: SGD per unit of currency; fx_sgd_to_aud: AUD per SGD (both ILLUSTRATIVE in this project)."""
    s, cust, inv, lines = b["shipment"], b["customer"], b["invoice"], b["lines"]
    imp = s["direction"] == "Import"
    out = []
    add = out.append

    # --- party (SG-IMP-02/03/04, SG-EXP-05)
    if _blank(cust["uen"]) or uen_type(cust["uen"]) is None:
        add(Finding("uen_present_and_format", "SG-IMP-03", "PARTY_UEN", "BLOCKING",
                    "customer UEN missing or not in a UEN format"))
    if not cust["customs_account_active"]:
        add(Finding("customs_account_active", "SG-IMP-02", "PARTY_UEN", "BLOCKING", "Customs account not activated"))
    if s["permit_party_uen"] != cust["uen"]:
        add(Finding("importer_matches_profile", "SG-IMP-04" if imp else "SG-EXP-05", "PARTY_UEN", "BLOCKING",
                    f"permit {'importer' if imp else 'exporter'} UEN {s['permit_party_uen']!r} differs from the "
                    f"customer's UEN {cust['uen']!r}"))

    # --- permit timing (SG-IMP-01, SG-EXP-01)
    if imp and s["permit_submitted_at"] >= s["arrival_at"]:
        add(Finding("permit_before_arrival", "SG-IMP-01", "PERMIT_TIMING", "BLOCKING",
                    f"permit submitted {s['permit_submitted_at']} is not before arrival {s['arrival_at']}"))
    if not imp and s["permit_submitted_at"] >= s["departure_at"]:
        add(Finding("permit_before_departure", "SG-EXP-01", "PERMIT_TIMING", "BLOCKING",
                    f"export permit submitted {s['permit_submitted_at']} is not before departure {s['departure_at']}"))

    # --- documents present (SG-IMP-25, SG-EXP-02, AU-02)
    if not inv["present"]:
        add(Finding("docs_present", "SG-IMP-25", "INVOICE_DATA", "BLOCKING", "commercial invoice not on file"))
    if not b["transport_doc"]["present"]:
        add(Finding("docs_present", "SG-IMP-25" if imp else "SG-EXP-02", "DOC_MISMATCH", "BLOCKING",
                    "bill of lading / air waybill / consignment note not on file"))
    if not b["packing_list"]["present"]:
        add(Finding("docs_present", "SG-IMP-25", "DOC_MISMATCH", "WARNING", "packing list not on file"))

    # --- invoice fields (SG-IMP-23, SG-IMP-10, SG-IMP-24)
    for field, label in (("invoice_no", "invoice number"), ("invoice_date", "invoice date"),
                         ("currency", "currency")):
        if _blank(inv.get(field)):
            add(Finding("invoice_fields_complete", "SG-IMP-10" if field == "currency" else "SG-IMP-23",
                        "INVOICE_DATA", "BLOCKING", f"invoice {label} missing"))
    for field, label in (("seller_name", "seller name"), ("buyer_name", "buyer name")):
        if _blank(inv.get(field)):
            add(Finding("invoice_fields_complete", "SG-IMP-23", "INVOICE_DATA", "WARNING", f"invoice {label} missing"))
    if _blank(inv.get("incoterm")):
        add(Finding("incoterm_present", "SG-IMP-24", "INVOICE_DATA", "BLOCKING",
                    "invoice states no Incoterm; the value cannot be built up to CIF/FOB without it"))
    for ln in lines:
        for field, label in (("description", "goods description"), ("unit_price", "unit price"),
                             ("quantity", "quantity"), ("line_value", "line value")):
            if _blank(ln.get(field)):
                add(Finding("invoice_fields_complete", "SG-IMP-23", "INVOICE_DATA", "BLOCKING",
                            f"line {ln['line_no']}: {label} missing", ln["line_no"]))
        if _blank(ln.get("origin_country")):
            add(Finding("invoice_fields_complete", "SG-IMP-21", "INVOICE_DATA", "BLOCKING",
                        f"line {ln['line_no']}: country of origin missing", ln["line_no"]))

    # --- invoice arithmetic and permit totals
    for ln in lines:
        if not _blank(ln.get("unit_price")) and not _blank(ln.get("quantity")) and not _blank(ln.get("line_value")):
            if not _close(ln["quantity"] * ln["unit_price"], ln["line_value"], AMOUNT_TOLERANCE, 0.01):
                add(Finding("invoice_arithmetic", "SG-IMP-23", "INVOICE_DATA", "WARNING",
                            f"line {ln['line_no']}: quantity x unit price differs from the line value", ln["line_no"]))
    line_sum = sum(ln["line_value"] for ln in lines if not _blank(ln.get("line_value")))
    if inv["present"] and not _close(line_sum, inv["invoice_total"], AMOUNT_TOLERANCE, 0.01):
        add(Finding("invoice_arithmetic", "SG-IMP-23", "INVOICE_DATA", "BLOCKING",
                    f"invoice total {inv['invoice_total']} differs from the sum of its lines {round(line_sum, 2)}"))
    if inv["present"] and not _close(s["permit_invoice_total"], inv["invoice_total"], AMOUNT_TOLERANCE, 0.01):
        add(Finding("invoice_vs_permit_total", "SG-IMP-07", "VALUE_CIF", "BLOCKING",
                    f"permit total invoice amount {s['permit_invoice_total']} differs from the invoice "
                    f"{inv['invoice_total']}"))

    # --- value (SG-IMP-07..11 for imports; FOB item value for exports, AU-03/AU-04)
    currency = inv.get("currency") or None
    rate = fx_to_sgd.get(currency) if currency else None
    term = inv.get("incoterm") or None
    if term and rate is not None:
        if imp:
            v = sg_cif(inv["invoice_total"], term, s["freight_on_file"], s["insurance_on_file"],
                       s["inland_costs_on_file"], 0.0, s["loading_country"])
            rule = "SG-IMP-07"
        else:
            v = fob_value(inv["invoice_total"], term, s["freight_on_file"], s["insurance_on_file"],
                          s["inland_costs_on_file"])
            rule = "AU-03"
        if v.amount is None:
            add(Finding("cif_consistency", "SG-IMP-08" if imp else rule, "VALUE_CIF", "BLOCKING", v.note))
        else:
            value_sgd = v.amount * rate
            if not _close(value_sgd, s["permit_declared_value_sgd"], VALUE_TOLERANCE, VALUE_MIN_SGD):
                kind = "CIF" if imp else "FOB"
                add(Finding("cif_consistency", rule, "VALUE_CIF", "BLOCKING",
                            f"declared value SGD {s['permit_declared_value_sgd']:,.2f} differs from the {kind} value "
                            f"SGD {value_sgd:,.2f} ({v.method})"))
            if v.problem == "ddp_breakdown":
                add(Finding("cif_consistency", rule, "VALUE_CIF", "WARNING", v.note))
            if imp:
                add(Finding("gst_estimate", "SG-IMP-11", "", "INFO",
                            f"estimated GST SGD {sg_gst(value_sgd):,.2f} (9% of CIF SGD {value_sgd:,.2f}, duty 0)"))
            else:
                fob_aud = value_sgd * fx_sgd_to_aud
                ti = ((s["freight_on_file"] or 0.0) + (s["insurance_on_file"] or 0.0)) * rate * fx_sgd_to_aud
                voti = au_voti(fob_aud, ti)
                needs_permit = any(ch in au_biosecurity_chapters() for ch in
                                   {hsmod.chapter(ln["hs_code"]) for ln in lines})
                alcohol = any(hsmod.normalise(ln["hs_code"]).startswith(("2203", "2204", "2205", "2206", "2208", "24"))
                              for ln in lines)
                add(Finding("au_declaration_type", "AU-01", "", "INFO",
                            f"AU: {au_declaration_type(fob_aud, needs_permit, alcohol)} (customs value AUD "
                            f"{fob_aud:,.2f})"))
                add(Finding("au_voti_gst", "AU-04", "", "INFO",
                            f"AU: VoTI AUD {voti:,.2f}, GST AUD {au_gst(voti):,.2f} (duty 0 assumed)"))

    # --- HS codes (SG-IMP-05, AU-06)
    for ln in lines:
        for problem, msg in hsmod.check(ln["hs_code"], "SG"):
            add(Finding("hs_format_and_hs6", "SG-IMP-05", "HS_INVALID", "BLOCKING", f"line {ln['line_no']}: {msg}",
                        ln["line_no"]))

    # --- controlled, prohibited, dutiable (SG imports only; SG-IMP-13..20)
    if imp:
        for ln in lines:
            refs = set(filter(None, (ln.get("ca_licence_ref") or "").split(";")))
            for sc in screens_for(ln["hs_code"], ("controlled",)):
                if sc.authority not in b["licences"] or b["licences"][sc.authority] > s["permit_submitted_at"][:10]:
                    add(Finding("ca_screening", sc.rule_id, "CA_APPROVAL", "BLOCKING",
                                f"line {ln['line_no']}: {sc.scope} - no {sc.authority} licence on file "
                                f"({sc.licence_to_ask_for})", ln["line_no"]))
                elif not (refs & b["licence_refs"].get(sc.authority, set())):
                    add(Finding("ca_screening", sc.rule_id, "CA_APPROVAL", "BLOCKING",
                                f"line {ln['line_no']}: {sc.authority} licence on file but not quoted on the permit "
                                f"line", ln["line_no"]))
            for sc in screens_for(ln["hs_code"], ("prohibited",)):
                add(Finding("prohibited_screening", sc.rule_id, "CA_APPROVAL", "BLOCKING",
                            f"line {ln['line_no']}: {sc.scope} - prohibited import", ln["line_no"]))
            for sc in screens_for(ln["hs_code"], ("dutiable",)):
                add(Finding("dutiable_screening", sc.rule_id, "", "INFO",
                            f"line {ln['line_no']}: {sc.scope} - duty rate and dutiable quantity needed", ln["line_no"]))

    # --- origin (SG-IMP-21, SG-IMP-22, SG-EXP-04, AU-09)
    for ln in lines:
        made = b["product_origin"].get(ln.get("product_id"))
        declared = ln.get("origin_country")
        if made and not _blank(declared) and declared != made:
            add(Finding("origin_consistency", "SG-IMP-21" if imp else "SG-EXP-04", "ORIGIN_DOCS", "BLOCKING",
                        f"line {ln['line_no']}: origin declared {declared} but the product master says {made}",
                        ln["line_no"]))
    if s["preference_claimed"] and not b["co_present"]:
        add(Finding("preference_proof", "SG-IMP-22" if imp else "AU-09", "ORIGIN_DOCS", "BLOCKING",
                    "FTA preference claimed but no certificate of origin or self-certification on file"))

    # --- quantities and weights (SG-IMP-28)
    for ln in lines:
        pq = ln.get("packing_quantity")
        if b["packing_list"]["present"] and not _blank(pq) and not _blank(ln.get("quantity")) and pq != ln["quantity"]:
            add(Finding("quantity_weight_consistency", "SG-IMP-28", "DOC_MISMATCH", "WARNING",
                        f"line {ln['line_no']}: packing list quantity {pq} vs invoice {ln['quantity']}", ln["line_no"]))
    pl, td = b["packing_list"], b["transport_doc"]
    if pl["present"] and td["present"] and not _close(pl["gross_weight_kg"], td["gross_weight_kg"], WEIGHT_TOLERANCE, 0):
        add(Finding("quantity_weight_consistency", "SG-IMP-28", "DOC_MISMATCH", "WARNING",
                    f"gross weight: packing list {pl['gross_weight_kg']} kg vs transport document "
                    f"{td['gross_weight_kg']} kg"))

    # --- Australia-specific (AU-05, AU-07)
    if not imp:
        if any(hsmod.chapter(ln["hs_code"]) in au_biosecurity_chapters() for ln in lines) and \
                not s["bicon_check_recorded"]:
            add(Finding("au_biosecurity_screening", "AU-07", "BIOSECURITY", "WARNING",
                        "AU: lines in a biosecurity-screened chapter and no BICON check recorded"))
        if not s["consignee_abn_provided"]:
            add(Finding("au_abn_quoted", "AU-05", "PARTY_UEN", "WARNING",
                        "AU: consignee ABN (or customs owner code) not provided"))
    return _dedupe(out)


# ---------------------------------------------------------------------------------------------- corrective action

def corrective_action_route(permit_state, field_amendable=True, days_expired=0):
    """SG-IMP-26 / SG-IMP-27: how a declaration error is corrected, given the permit's state.

    permit_state: 'valid' (approved, not yet used for clearance), 'used' (used for cargo clearance), 'expired'
    (days_expired calendar days ago) or 'audit' (Customs has requested it for audit or started a check)."""
    disclosure = "submit a voluntary disclosure (complete, before any Customs check)"
    if permit_state == "valid":
        return "amend the permit in TradeNet" if field_amendable else "cancel the permit and apply for a new one"
    if permit_state == "expired":
        # an expired permit cannot be amended; it can still be cancelled up to 1 calendar day after expiry
        return "cancel the permit and apply for a new one" if days_expired <= 1 else disclosure
    if permit_state == "used":
        return disclosure
    if permit_state == "audit":
        return "respond to the Customs check; a voluntary disclosure is no longer accepted once Customs has started"
    raise ValueError(f"unknown permit state {permit_state!r}")
