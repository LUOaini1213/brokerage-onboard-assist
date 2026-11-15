"""Templates for the SYNTHETIC free-text hold notes.

Eight templates per reason code. Templates 0-5 are the 'seen' phrasings; templates 6 and 7 are written with
different vocabulary (no codes or document names that appear in 0-5 where avoidable) and are used only for the
template-held-out test set, so the classifier is also scored on phrasings it never saw in training.
"""

HELD_OUT_TEMPLATES = (6, 7)

TEMPLATES = {
    "PERMIT_TIMING": [
        "Cargo {event} before permit approval. Permit submitted {hours}h after {event}, cargo held pending permit.",
        "No valid TradeNet permit at time of {event} for {ref}; declarant lodged permit late.",
        "Permit applied after {event}. Customs hold until permit approval.",
        "Hold: permit not obtained before {event}. Late lodgement by {hours} hrs.",
        "Shipment {ref} held - permit missing at {event}, applied for afterwards.",
        "Permit approval came after {event}; goods could not be released.",
        "Goods moved while the declaration was still unfiled; release waited on the declaration being approved.",
        "Late filing: the customs declaration went in {hours} hours after the scheduled {event}.",
    ],
    "PARTY_UEN": [
        "Importer UEN on permit {uen} does not match customer record. Permit to be amended.",
        "Customs account of importer not activated - permit rejected, hold until activation.",
        "Wrong importer name/UEN declared on permit for {ref}.",
        "UEN missing on declaration, importer cannot be identified.",
        "Hold: importer details mismatch between permit and customer profile (UEN {uen}).",
        "Permit held as importer UEN {uen} not recognised for this account.",
        "The company registration number on the declaration belongs to a different entity; party identity to be confirmed.",
        "Entity identifier not matched to the trader who owns the goods; trader to confirm its registration.",
    ],
    "HS_INVALID": [
        "HS code {hs} not valid in current tariff (STCCED 2022). Correct code required.",
        "Permit item HS {hs} rejected: code does not exist.",
        "Invalid HS code declared ({hs}), looks like an outdated HS 2017 code.",
        "HS code format wrong on line {line}: {hs}.",
        "Hold - HS code {hs} not found, declarant to re-classify.",
        "Tariff code {hs} rejected by system as invalid.",
        "Commodity number on the declaration is obsolete since the 2022 nomenclature change; needs the current subheading.",
        "Classification number {hs} is not a live entry in the schedule; a current number must be supplied.",
    ],
    "HS_QUERY": [
        "Customs query on classification: goods described as {desc} declared under {hs}; officer suggests {hs_alt}.",
        "Classification query - product literature requested for {desc}.",
        "HS {hs} questioned, may fall under heading {hs_alt4}. Pending technical specs.",
        "Officer disputes tariff classification of {desc}; datasheet requested.",
        "Hold for classification review: HS {hs} vs description {desc}.",
        "Customs requests catalogue/specs to confirm HS code for {desc}.",
        "Examining officer believes the goods belong in a different heading than declared; awaiting brochure from supplier.",
        "Nature of the {desc} unclear from the paperwork, so the declared subheading is being reviewed.",
    ],
    "VALUE_CIF": [
        "Declared value SGD {decl} lower than CIF SGD {calc}; freight and insurance not added ({term} invoice).",
        "Valuation query: {term} terms, freight/insurance missing from customs value.",
        "Customs value mismatch: permit SGD {decl} vs invoice SGD {calc}.",
        "Value queried - insurance not included for {term} shipment.",
        "Hold: undervaluation suspected, declared {decl} vs calculated {calc}.",
        "CIF value incorrect, freight charges omitted. Permit amendment needed.",
        "The amount declared is below what the goods cost delivered; shipping and cover charges were left out.",
        "Officer asked for the carriage bill because the declared worth looks too low against the price paid.",
    ],
    "INVOICE_DATA": [
        "Commercial invoice incomplete: {field} missing.",
        "Invoice {inv} lacks {field}; supplier to reissue.",
        "Hold: invoice does not show {field}.",
        "Missing {field} on commercial invoice, cannot verify declaration.",
        "Invoice provided is a proforma without {field}.",
        "Commercial invoice missing {field}, corrected invoice requested from shipper.",
        "Seller's bill is missing key particulars ({field}), so the entry cannot be checked against it.",
        "Paperwork from the supplier omits {field}; a reissued bill has been asked for.",
    ],
    "CA_APPROVAL": [
        "Controlled item: {ca} licence not provided for {desc}.",
        "{ca} approval missing, goods held pending licence.",
        "Hold by competent authority {ca} - no import licence/permit for controlled goods.",
        "{lic} not on file; {ca} requires licence before import.",
        "Permit rejected by {ca}: licence number missing in CA licence field.",
        "Goods under {ca} control, approval not obtained.",
        "The regulating agency for these goods has not cleared the consignment; registration reference absent.",
        "Release blocked until the agency that oversees {desc} issues its approval.",
    ],
    "ORIGIN_DOCS": [
        "Preference claimed but no certificate of origin provided.",
        "CO missing for FTA preference; duty payable at general rate.",
        "Country of origin declared as {pol} (port of loading) but goods made in {country}.",
        "Origin query: certificate of origin required for preferential treatment.",
        "Hold - origin documents incomplete, Form D / CO not received.",
        "Declared origin {pol} not supported, supplier docs show {country}.",
        "Reduced tariff was requested but the proof that the goods qualify was not supplied.",
        "Where the goods were manufactured does not match the declaration; supplier to confirm provenance.",
    ],
    "DOC_MISMATCH": [
        "Quantity on packing list ({q2}) differs from invoice ({q1}).",
        "Gross weight on BL/AWB {w2} kg vs packing list {w1} kg.",
        "Packing list missing for {ref}, cannot reconcile quantities.",
        "Discrepancy between invoice and packing list quantities.",
        "AWB/BL weight does not match declaration; documents to be reconciled.",
        "Hold: number of packages and weights inconsistent across documents.",
        "Counts on the carton list and the bill disagree, so the declared quantity cannot be confirmed.",
        "The carrier's document shows a different mass ({w2} kg) from the shipper's list ({w1} kg).",
    ],
    "INSPECTION": [
        "Selected for inspection, documents in order.",
        "Random examination by Customs; no discrepancy found.",
        "Physical inspection required - container scanned.",
        "Cargo selected for check, released after examination.",
        "Hold for inspection, awaiting officer availability.",
        "Routine inspection, no issue with documents.",
        "Consignment picked for a physical look by officers; nothing irregular in what was filed.",
        "Goods opened and examined at the checkpoint before being let go.",
    ],
    "BIOSECURITY": [
        "Biosecurity hold: BICON import conditions not met for {desc}.",
        "Referred to DAFF, treatment certificate required.",
        "Biosecurity inspection - import permit missing.",
        "Hold by biosecurity: fumigation certificate not provided.",
        "DAFF directed goods for inspection, packaging declaration missing.",
        "BICON conditions require supporting documents not supplied.",
        "Australian agriculture officers stopped the goods pending evidence of treatment of the timber packing.",
        "Quarantine authority wants a clean certificate before the produce can enter.",
    ],
}

ABBREVIATIONS = [("invoice", "inv"), ("packing list", "pkg list"), ("freight", "frt"), ("insurance", "ins"),
                 ("certificate of origin", "CO"), ("quantity", "qty"), ("shipment", "shpt"), ("permit", "pmt"),
                 ("declaration", "decl"), ("documents", "docs"), ("approval", "appr")]

REFERENCES = ["Ref {ref}.", "pls advise. ref {ref}", "- ops desk, {ref}", "Cust ref {ref}.", "FYI {ref}"]

# Sentences that mention another document or step in passing, so keywords alone do not give the label away.
# Each is paired with the reasons it would contradict; it is only added to notes of other reasons.
DISTRACTORS = [
    ("Invoice and packing list received.", {"INVOICE_DATA", "DOC_MISMATCH"}),
    ("Permit approved earlier today.", {"PERMIT_TIMING"}),
    ("HS codes checked by declarant.", {"HS_INVALID", "HS_QUERY"}),
    ("Certificate of origin on file.", {"ORIGIN_DOCS"}),
    ("Freight invoice attached.", {"VALUE_CIF"}),
    ("Customer contacted by phone.", set()),
    ("No inspection ordered.", {"INSPECTION"}),
    ("Licence copy attached for reference.", {"CA_APPROVAL"}),
]
