"""Customs value and import-tax arithmetic.

Singapore (rules SG-IMP-07 to SG-IMP-12): customs value on a CIF basis; what has to be added to the invoice price
depends on its Incoterm; flat freight-and-insurance rates for FOB quotes and a flat 1% insurance for CFR quotes
apply only when the actual charges are unknown; GST = 9% x (customs value + duty).

Australia (rules AU-01, AU-03, AU-04): customs value on an FOB basis; GST = 10% of the value of the taxable
importation (customs value + international transport and insurance + duty); Import Declaration above AUD 1,000.

Amounts are in the invoice currency unless a function says otherwise. Results are rounded to cents.
"""
from dataclasses import dataclass

from .rules import sg_flat_rates

INCOTERMS_2020 = ("EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP")
SG_GST_RATE = 0.09          # SG-IMP-12
CFR_FLAT_INSURANCE = 0.01   # SG-IMP-09 (base: CFR value, an assumption)
AU_GST_RATE = 0.10          # AU-04
AU_N10_THRESHOLD_AUD = 1000.0  # AU-01


@dataclass(frozen=True)
class Value:
    amount: float | None     # None when the value cannot be computed from the documents
    method: str
    problem: str | None = None   # incoterm_missing | incoterm_unknown | charges_unknown | ddp_breakdown
    note: str = ""


def _known(*xs):
    return all(x is not None for x in xs)


def sg_cif(invoice_total, incoterm, freight=None, insurance=None, inland=None, other=0.0, export_country=None):
    """Singapore customs value (CIF) in the invoice currency. freight/insurance/inland are None when unknown."""
    if not incoterm:
        return Value(None, "", "incoterm_missing", "invoice states no Incoterm, so the additions to CIF are unknown")
    term = incoterm.upper()
    if term not in INCOTERMS_2020:
        return Value(None, "", "incoterm_unknown", f"{incoterm!r} is not an Incoterms 2020 rule")
    base = invoice_total + (other or 0.0)
    if term in ("CIF", "CIP"):
        return Value(round(base, 2), "as invoiced (CIF/CIP)")
    if term == "DDP":
        return Value(round(base, 2), "as invoiced (DDP)", "ddp_breakdown",
                     "a DDP price can include Singapore duty and GST paid by the seller; ask for the breakdown")
    if term in ("DAP", "DPU"):
        return Value(round(base, 2), "as invoiced (D-term)")
    if term in ("CFR", "CPT"):
        if insurance is not None:
            return Value(round(base + insurance, 2), "+ actual insurance")
        if term == "CFR":
            return Value(round(base + CFR_FLAT_INSURANCE * invoice_total, 2), "+ flat 1% insurance (SG-IMP-09)")
        return Value(None, "", "charges_unknown", "CPT invoice without the insurance amount; no flat rate applies")
    if term in ("FCA", "FAS", "FOB"):
        if _known(freight, insurance):
            return Value(round(base + freight + insurance, 2), "+ actual freight and insurance")
        if term == "FOB" and freight is None and insurance is None:
            rate = sg_flat_rates().get(export_country)
            if rate is not None:
                return Value(round(base + rate * invoice_total, 2),
                             f"+ flat {rate * 100:g}% freight and insurance for {export_country} (SG-IMP-08)")
            return Value(None, "", "charges_unknown",
                         f"FOB invoice without freight and insurance; no flat rate is published for {export_country}")
        return Value(None, "", "charges_unknown", f"{term} invoice without the actual freight and insurance")
    # EXW: inland transport and export handling, freight and insurance are all added (no flat rate applies)
    if _known(inland, freight, insurance):
        return Value(round(base + inland + freight + insurance, 2), "+ inland costs, freight and insurance")
    return Value(None, "", "charges_unknown", "EXW invoice: inland costs, freight and insurance are all needed")


def sg_gst(customs_value_sgd, duty_sgd=0.0, rate=SG_GST_RATE):
    """SG-IMP-11: GST = rate x (customs value + duties payable)."""
    return round(rate * (customs_value_sgd + duty_sgd), 2)


def fob_value(invoice_total, incoterm, freight=None, insurance=None, inland=None):
    """FOB-basis value in the invoice currency, used for the Singapore export permit (item value on FOB terms)
    and the Australian customs value (AU-03): international freight and insurance are taken out of C- and D-term
    prices; an EXW price needs the costs up to the place of export added."""
    if not incoterm:
        return Value(None, "", "incoterm_missing", "invoice states no Incoterm")
    term = incoterm.upper()
    if term not in INCOTERMS_2020:
        return Value(None, "", "incoterm_unknown", f"{incoterm!r} is not an Incoterms 2020 rule")
    if term in ("FCA", "FAS", "FOB"):
        return Value(round(invoice_total, 2), "as invoiced (F-term)")
    if term == "EXW":
        if inland is not None:
            return Value(round(invoice_total + inland, 2), "+ costs to the place of export")
        return Value(None, "", "charges_unknown", "EXW invoice without the costs to the place of export")
    if term in ("CFR", "CPT"):
        if freight is not None:
            return Value(round(invoice_total - freight, 2), "- international freight")
        return Value(None, "", "charges_unknown", f"{term} invoice without the freight amount shown separately")
    # CIF, CIP and D-terms
    if _known(freight, insurance):
        v = Value(round(invoice_total - freight - insurance, 2), "- international freight and insurance")
        if term == "DDP":
            return Value(v.amount, v.method, "ddp_breakdown",
                         "a DDP price can include Australian duty and GST; ask for the breakdown")
        return v
    return Value(None, "", "charges_unknown", f"{term} invoice without freight and insurance shown separately")


def au_voti(customs_value_aud, transport_insurance_aud, duty_aud=0.0, wet_aud=0.0):
    """AU-04: value of the taxable importation."""
    return round(customs_value_aud + transport_insurance_aud + duty_aud + wet_aud, 2)


def au_gst(voti_aud, rate=AU_GST_RATE):
    return round(rate * voti_aud, 2)


def au_declaration_type(value_aud, needs_permit=False, tobacco_or_alcohol=False):
    """AU-01 for air and sea cargo."""
    if value_aud > AU_N10_THRESHOLD_AUD:
        return "Import Declaration (N10), import processing charge payable"
    if needs_permit:
        return "Import Declaration (N10) or long-format SAC (permit needed)"
    if tobacco_or_alcohol:
        return "SAC declaration with duty and GST (tobacco or alcohol)"
    return "Self-Assessed Clearance (SAC) declaration"
