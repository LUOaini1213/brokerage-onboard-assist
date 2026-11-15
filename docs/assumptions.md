# Assumptions of the synthetic data generator

Generated from `config/synth_assumptions.json` by `scripts/build_all.py`; edit that file, not this one.

Every parameter of the SYNTHETIC data generator (src/boa/synth.py). None of these numbers is estimated from real customs or customer data: each is an ASSUMPTION chosen to give a plausible-looking demo, or ILLUSTRATIVE (a stand-in for a real-world quantity such as an exchange rate). docs/assumptions.md is generated from this file. Changing a value changes every result.

| Parameter | Label | Value | Meaning |
|---|---|---|---|
| `seed` | ASSUMPTION | `20261115` | Seed of numpy.random.default_rng for the whole generator. |
| `n_customers` | ASSUMPTION | `800` | Number of new customers whose enrolment requests are generated. |
| `enrolment_window` | ASSUMPTION | `["2026-03-02", "2026-08-28"]` | Enrolment requests are submitted on uniformly drawn weekdays in this window. |
| `as_of_date` | ASSUMPTION | `"2026-10-30"` | Snapshot date. Events after it are not generated; open actions are judged overdue against it. |
| `segment_mix` | ASSUMPTION | `{"SME": 0.6, "Mid-size": 0.3, "Large": 0.1}` | Share of customers by size segment. |
| `segment_defect_multiplier` | ASSUMPTION | `{"SME": 1.4, "Mid-size": 1.0, "Large": 0.6}` | Multiplier on every enrolment and document defect probability, by segment. |
| `segment_response_multiplier` | ASSUMPTION | `{"SME": 1.2, "Mid-size": 1.0, "Large": 0.85}` | Multiplier on hold release times (how fast the customer supplies what is missing). |
| `lanes` | ILLUSTRATIVE | `[{"lane_id": "CN-SG-SEA", "origin": "CN", "destination": "SG", "mode": "Sea", "direction": "Import", "weight": 0.24, "transit_days": [7, 12]}, {"lane_id": "C...` | Trade lanes (country pair and mode), their share of customers' primary lanes and a uniform transit-time range in days. Country codes are real ISO 3166 codes; the shares and transit times are invented. |
| `p_primary_lane` | ASSUMPTION | `0.8` | Probability that a shipment uses the customer's primary lane; otherwise another lane with the same direction is drawn by weight. |
| `commodities` | ILLUSTRATIVE | `[{"group": "Consumer electronics", "weight": 0.18, "hs6": ["851713", "847130", "852872", "851830", "850760", "851762"], "unit_price": [40, 900], "unit": "PCE...` | Commodity groups, their share of customers, the HS 2022 subheadings (real codes) a customer of that group trades, and invented unit-price (in the invoice currency) and weight ranges. National 7th-8th digits are drawn from national_suffixes. |
| `product_descriptions` | ILLUSTRATIVE | `{"851713": "smartphones", "847130": "laptop computers", "852872": "LED televisions", "851830": "headphones", "850760": "lithium-ion battery packs", "851762":...` | Plain-language product names used on synthetic invoices and in hold notes (this project's own wording, not the HS nomenclature text). |
| `national_suffixes` | ILLUSTRATIVE | `["00", "10", "90"]` | Two digits appended to an HS 6-digit code to make an 8-digit code. Invented: the STCCED national split is not used, so these may not be real AHTN codes. |
| `outdated_or_malformed_hs` | ILLUSTRATIVE | `["85171200", "94054000", "30022000", "8517130", "851713000"]` | Codes used for the hs_invalid defect: three HS 2017 subheadings that no longer exist in HS 2022 (8517.12, 9405.40, 3002.20) with two zeros appended, a 7-digit code and a 9-digit code. |
| `product_origin` | ASSUMPTION | `{"p_same_as_export_country": 0.85, "other_import_origins": ["TH", "VN", "MY", "IN", "KR", "ID"], "p_singapore_made_export": 0.4, "export_origins": ["CN", "MY...` | Country of manufacture on the product master: for imports usually the export country, otherwise one of other_import_origins; for exports from Singapore, Singapore-made with probability p_singapore_made_export, otherwise one of export_origins. |
| `p_licence_before_first_shipment` | ASSUMPTION | `0.5` | Probability that a licence missing at enrolment is obtained before the first shipment (otherwise it is obtained only after a CA_APPROVAL hold, when that hold's corrective action closes). |
| `shipment_cutoff_days_before_as_of` | ASSUMPTION | `14` | No shipment arrives later than this many days before the snapshot date, so almost every shipment is released by then. |
| `products_per_customer` | ASSUMPTION | `[2, 5]` | Uniform range of products (HS codes) on a customer's product list. |
| `lines_per_invoice` | ASSUMPTION | `[1, 4]` | Uniform range of invoice lines per shipment. |
| `quantity_per_line` | ASSUMPTION | `[10, 2000]` | Log-uniform range of the quantity on one invoice line. |
| `incoterm_mix` | ASSUMPTION | `{"FOB": 0.32, "CIF": 0.18, "EXW": 0.12, "FCA": 0.1, "CFR": 0.1, "DAP": 0.12, "DDP": 0.06}` | Incoterms 2020 rule on the commercial invoice. |
| `p_charges_known` | ASSUMPTION | `0.7` | Singapore imports only: probability that the actual freight and insurance (or, for CFR, the insurance) are on file when a flat rate could stand in for them (FOB from a country in the flat-rate table, or CFR). For every other term that needs charges they are always on file, and for exports to Australia freight and insurance are always shown. |
| `freight_share_of_value` | ASSUMPTION | `{"Sea": [0.03, 0.08], "Air": [0.06, 0.16], "Road": [0.01, 0.04]}` | Uniform range of actual freight as a share of the goods value, by mode. |
| `insurance_share_of_value` | ASSUMPTION | `[0.002, 0.006]` | Uniform range of actual insurance as a share of the goods value. |
| `inland_share_of_value` | ASSUMPTION | `[0.005, 0.02]` | Uniform range of inland transport and export handling (EXW) as a share of the goods value. |
| `currency_by_origin` | ASSUMPTION | `{"CN": ["USD", "CNY"], "US": ["USD"], "DE": ["EUR", "USD"], "JP": ["JPY", "USD"], "VN": ["USD"], "MY": ["MYR", "SGD"], "SG": ["SGD", "AUD", "USD"]}` | Invoice currency, drawn uniformly from the list for the export country. |
| `fx_to_sgd` | ILLUSTRATIVE | `{"SGD": 1.0, "USD": 1.3, "CNY": 0.18, "EUR": 1.45, "JPY": 0.0088, "MYR": 0.3, "AUD": 0.86}` | Fixed SGD per unit of currency. NOT the MAS weekly average rates that SG-IMP-10 requires; one fixed rate is used for the whole period. |
| `fx_sgd_to_aud` | ILLUSTRATIVE | `1.16` | Fixed AUD per SGD for the Australian value checks. |
| `p_preference_claimed` | ASSUMPTION | `{"SG_dutiable": 0.5, "AU_export": 0.45}` | Probability that FTA preference is claimed: on Singapore imports of dutiable lines (wine in this data), and on exports to Australia. |
| `funnel` | ASSUMPTION | `{"p_docs_received": 0.93, "days_to_docs": [1, 10], "p_fix_after_findings": 0.75, "days_to_fix": [3, 18], "days_to_validate": [1, 4], "p_profile": 0.97, "days...` | Onboarding funnel: probability of each step and uniform delays in days. An enrolment with blocking validator findings is fixed with probability p_fix_after_findings, otherwise it stalls at 'Documents received'. |
| `enrolment_defects` | ASSUMPTION | `{"uen_missing": 0.03, "uen_malformed": 0.04, "customs_account_inactive": 0.1, "sample_invoice_no_incoterm": 0.12, "product_hs_invalid": 0.05, "licence_missin...` | Probability of each defect in the enrolment bundle (before the segment multiplier). licence_missing_if_controlled applies per competent authority to customers whose products are screened as controlled. |
| `shipment_defects` | ASSUMPTION | `{"invoice_field_missing": 0.1, "incoterm_missing": 0.05, "charges_not_added": 0.1, "value_typo": 0.04, "hs_invalid": 0.025, "hs_misclassified": 0.05, "licenc...` | Probability of each latent defect on shipment 1 (before multipliers). licence_missing_if_controlled is the chance of a missing or wrong licence reference when the licence was obtained at enrolment; without a licence on file every screened line is a defect. |
| `sequence_multiplier` | ASSUMPTION | `[1.0, 0.8, 0.65]` | Multiplier on shipment defect probabilities for shipments 1, 2 and 3 (customers and suppliers learn the routine). |
| `recurrence_multiplier_after_action` | ASSUMPTION | `0.3` | Multiplier on a defect's probability in later shipments once a corrective action for a hold with that reason was closed before the shipment arrived. |
| `p_hold_given_defect` | ASSUMPTION | `{"PERMIT_TIMING": 0.9, "PARTY_UEN": 0.8, "HS_INVALID": 0.85, "HS_QUERY": 0.55, "VALUE_CIF": 0.5, "INVOICE_DATA": 0.45, "CA_APPROVAL": 0.9, "ORIGIN_DOCS": 0.6...` | Probability that a latent defect leads to a hold with that reason code. |
| `p_random_inspection` | ASSUMPTION | `0.02` | Probability of an INSPECTION hold on a shipment, independent of its documents. |
| `max_holds_per_shipment` | ASSUMPTION | `2` | At most this many holds are recorded per shipment (the two with the longest expected release time). |
| `release_hours` | ASSUMPTION | `{"PERMIT_TIMING": [6, 0.6], "PARTY_UEN": [10, 0.6], "HS_INVALID": [8, 0.5], "HS_QUERY": [30, 0.7], "VALUE_CIF": [16, 0.7], "INVOICE_DATA": [12, 0.6], "CA_APP...` | Hours from hold to release: lognormal with [median, sigma of log] per reason, before mode, destination and segment multipliers. |
| `release_mode_multiplier` | ASSUMPTION | `{"Air": 0.8, "Sea": 1.1, "Road": 0.7}` | Multiplier on release hours by mode. |
| `release_destination_multiplier` | ASSUMPTION | `{"SG": 1.0, "AU": 1.25}` | Multiplier on release hours by destination country. |
| `base_clearance_hours` | ASSUMPTION | `{"Air": [5, 0.5], "Sea": [22, 0.45], "Road": [2.5, 0.5]}` | Hours from arrival to release for a shipment without a hold: lognormal [median, sigma of log] by mode. |
| `hold_start_hours_after_arrival` | ASSUMPTION | `[0.5, 6]` | Uniform range of hours between arrival and the start of a hold. |
| `permit_hours_before_arrival` | ASSUMPTION | `[6, 96]` | Uniform range of hours by which the permit precedes arrival (import) or departure (export); a 'permit_late' defect instead puts it 1-30 hours after. |
| `action_types` | ASSUMPTION | `{"PERMIT_TIMING": ["Apply for permit before arrival", "Add permit timing to handling note"], "PARTY_UEN": ["Amend or re-apply permit with correct importer", ...` | Corrective actions logged for a hold of each reason: the first is always logged, the second with probability p_second_action. Wording follows rules/hold_reasons.csv. |
| `p_second_action` | ASSUMPTION | `0.6` | Probability that a hold also gets the second corrective action of its reason. |
| `action_owner_roles` | ASSUMPTION | `["Onboarding analyst", "Customs declarant", "Customer"]` | Roles an action can be assigned to (no person names); the first role owns every optional second action of a hold. |
| `action_owner_by_reason` | ASSUMPTION | `{"PERMIT_TIMING": "Customs declarant", "PARTY_UEN": "Customs declarant", "HS_INVALID": "Customs declarant", "HS_QUERY": "Customs declarant", "VALUE_CIF": "Cu...` | Owner role of the first corrective action of a hold, by reason; the optional second action is always owned by the onboarding analyst. |
| `action_sla_days` | ASSUMPTION | `4` | Calendar days from opening to the due date of every action. |
| `action_close_days` | ASSUMPTION | `[2.0, 0.8]` | Days from opening to closing: lognormal [median, sigma of log]. |
| `note_noise` | ASSUMPTION | `{"p_abbreviate": 0.35, "p_typo": 0.15, "p_reference": 0.5, "p_distractor": 0.12, "p_lowercase": 0.2}` | Free-text hold note noise: abbreviations (inv, pkg list, frt), one character swap, an appended reference, a sentence mentioning another document in passing, all-lowercase text. |

Full values (including the long lists truncated above) are in the JSON file.
