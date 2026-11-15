"""Draft customer handling note, built from the customer profile, the product list, the enrolment validation and
the rulebook. It is a DRAFT for an analyst to review; every instruction cites the rule it comes from."""
from . import hs as hsmod
from .rules import au_biosecurity_chapters, sg_flat_rates
from .validator import screens_for


def draft_note(customer, products, lanes, enrolment_findings, licences):
    """customer: customer row; products: product rows; lanes: {lane_id: lane dict} for the customer's lanes
    (primary first); enrolment_findings: validator findings of the enrolment; licences: {authority: ref}."""
    primary = lanes[customer["primary_lane_id"]]
    imp = primary["direction"] == "Import"
    lines = [
        f"# Customer handling note - {customer['customer_id']} (DRAFT)",
        "",
        "> Generated from SYNTHETIC data by brokerage-onboard-assist. Review before use; not customs advice.",
        "",
        "## Profile",
        f"- Customer: {customer['customer_name']} ({customer['segment']})",
        f"- UEN: {customer['uen'] or 'missing'}; Customs account active: "
        f"{'yes' if customer['customs_account_active'] else 'no'}",
        f"- Primary lane: {primary['lane_id']} ({primary['origin']} to {primary['destination']}, {primary['mode']}, "
        f"{primary['direction'].lower()})",
        f"- Commodity group: {customer['commodity_group']}",
        "",
        "## Products and HS codes",
        "",
        "| Product | Description | HS code | Origin | Controls (screening) |",
        "|---|---|---|---|---|",
    ]
    controls_needed = {}
    for p in products:
        ctl = []
        if imp:
            for s in screens_for(p["hs_code"]):
                ctl.append(f"{s.authority}: {s.scope} ({s.kind})")
                if s.kind == "controlled":
                    controls_needed.setdefault(s.authority, (s.licence_to_ask_for, s.rule_id))
        elif hsmod.chapter(p["hs_code"]) in au_biosecurity_chapters():
            ctl.append("AU: BICON check (AU-07)")
        lines.append(f"| {p['product_id']} | {p['description']} | {p['hs_code']} | {p['origin_country']} | "
                     f"{'; '.join(ctl) or '-'} |")
    lines += ["", "## Standing instructions"]
    if imp:
        lines.append("- Permit through TradeNet before the goods arrive; check the arrival date against the permit "
                     "date for every shipment (SG-IMP-01).")
        rate = sg_flat_rates().get(primary["origin"])
        flat = (f"if they are unknown, the flat rate for {primary['origin']} is {rate * 100:g}% of the FOB value "
                f"(SG-IMP-08)" if rate is not None else "no flat rate is published for this export country, so the "
                "actual charges are always needed")
        lines.append(f"- Customs value on a CIF basis (SG-IMP-07): for FOB invoices add freight and insurance; {flat}; "
                     "for CFR invoices without an insurance amount add 1% (SG-IMP-09); EXW invoices need inland "
                     "costs, freight and insurance.")
        lines.append("- GST 9% of (CIF value + duty) (SG-IMP-11, SG-IMP-12); convert foreign currency at the MAS "
                     "weekly average rate of the preceding week (SG-IMP-10).")
        lines.append("- Invoice checklist: invoice number and date, seller, buyer, currency, Incoterm with named "
                     "place, and per line description, quantity and unit, unit price, value and country of origin "
                     "(SG-IMP-23, SG-IMP-24).")
        lines.append("- Origin: the country where the goods were made, not the port-of-loading country (SG-IMP-21).")
    else:
        lines.append("- Export permit through TradeNet before departure / cargo lodgement (SG-EXP-01); the exporter "
                     "UEN is the invoicing customer's (SG-EXP-05).")
        lines.append("- Singapore origin only for goods that meet the rules of origin (SG-EXP-04).")
        lines.append("- Australia: customs value on an FOB basis, so C- and D-term invoices must show freight and "
                     "insurance separately (AU-03); GST 10% of customs value + transport and insurance + duty "
                     "(AU-04); Import Declaration above AUD 1,000 (AU-01).")
        lines.append("- Australia: ask the consignee for its ABN (AU-05); certificate or declaration of origin before "
                     "any preference claim under SAFTA or AANZFTA (AU-09).")
    for authority, (licence, rule_id) in sorted(controls_needed.items()):
        ref = licences.get(authority)
        status = f"on file: {ref}" if ref else "NOT on file - obtain before the first controlled shipment"
        lines.append(f"- {authority} approval needed for screened products: {licence} - {status} ({rule_id}).")
    lines += ["", "## Open items from enrolment validation"]
    open_items = [f for f in enrolment_findings if f.severity in ("BLOCKING", "WARNING")]
    if open_items:
        for f in open_items:
            lines.append(f"- [{f.severity}] {f.message} ({f.rule_id})")
    else:
        lines.append("- none")
    lines += ["", "## First-three-shipment monitoring",
              "- Run the readiness check on shipments 1 to 3 before lodgement; fix every BLOCKING finding first.",
              "- Any hold: record the reason code, root cause and corrective action in the action log, and update "
              "this note so the cause does not recur.", ""]
    return "\n".join(lines)
