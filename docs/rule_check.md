# Rule check: second pass over every rule

The rulebook (`rules/rulebook.json`, rendered in [rulebook.md](rulebook.md)) was written on 2026-11-15 while reading
each cited page. Later the same day every rule was checked again, in a separate pass, against its source.

## How the second pass was done

- **Singapore, OECD and ABS sources (35 rules and the flat-rate table).** A separate agent session, which had only
  the rule texts, `rules/sources.json` and the URLs, re-fetched every page (PDFs through `pdftotext`) and was told to
  mark a rule *confirmed* only if every factual claim in its requirement text was supported. Its verdicts are below.
- **Australian Border Force and DAFF pages (10 rules).** These sites refuse automated fetches (HTTP 403, or a time-out
  for DAFF), so the separate session could not read them. They were re-read in a browser, in a separate pass, by the
  session that wrote the rules, searching each page for every claim. This part of the check is therefore not
  independent of the first pass. ABS paragraph references for AU-03 were checked by the separate session.
- Evidence is paraphrased here; the pages are the authority, and the access date is the one in `rules/sources.json`.

Outcome: 30 rules confirmed as written, 14 partly confirmed and none contradicted. Of the
partly confirmed ones, 13 were corrected (a claim the source did not support, a missing case, or a
source locator) and one, SG-IMP-24, had already been marked *not verified* and was kept so. The corrections
changed two pieces of code as well: the UEN pattern now accepts the foreign-company formats (`src/boa/uen.py`), and
the corrective-action route now follows the cancellation window and the audit case of SG-IMP-26
(`src/boa/validator.py`).

"Status after check" is the status recorded in `rules/rulebook.json`. A rule can be confirmed by the second pass and
still be *partially verified*, when the rule is confirmed but the check this project builds on it adds an assumption
(a tolerance, a base, an HS mapping).

| Rule | Checked by | Second-pass verdict | What the source supports (paraphrase) | Discrepancy found | Action | Status after check |
|---|---|---|---|---|---|---|
| SG-IMP-01 | separate session | partly confirmed | Overview: permit obtained before import; permit page: submitted through TradeNet | First version said an unused or used permit is itself a listed error; those are headings for how to correct a wrong permit | Sentence rewritten | verified |
| SG-IMP-02 | separate session | partly confirmed | Register for a UEN, activate the Customs account before any permit application; a declaring agent may apply | Page says ACRA "or the relevant" UEN agency | Added | verified |
| SG-IMP-03 | separate session | partly confirmed | OECD sheet: ROB, ROC and other-entity patterns and the meaning of each part | Foreign-company formats F000NNNNNC / FDDDNNNNNC were omitted | Added to the rule and to `uen.py` (test cases added) | partially verified |
| SG-IMP-04 | separate session | confirmed | Wrong importer name and UEN, wrong importer, and the UEN "do not" rule | none (errors sit in the MES and In-Payment sub-lists) | Note added | verified |
| SG-IMP-05 | separate session | partly confirmed | STCCED validity (Module 5 field 36); STCCED 2022 is the schedule; AHTN 8-digit, HS 2022 changes | The page does not say STCCED 2022 is built on AHTN | Reworded; the link is marked as this project's reading | partially verified |
| SG-IMP-06 | separate session | confirmed | Module 5 fields 37 and 8 | none | none | verified |
| SG-IMP-07 | separate session | confirmed | CIF basis, incidental charges, EXW example, value errors and offences | none | none | partially verified |
| SG-IMP-08 | separate session | confirmed | FOB condition, all six regions and rates | none | none | partially verified |
| SG-IMP-09 | separate session | confirmed | CFR condition, 1%, zero if no insurance bought | none (base of the 1% not stated, as already noted) | none | partially verified |
| SG-IMP-10 | separate session | confirmed | Weekly average MAS rates; preceding week (Module 5) | none | none | verified |
| SG-IMP-11 | separate session | confirmed | GST on all imports; formula with and without duty | none | none | verified |
| SG-IMP-12 | separate session | confirmed | Current rate 9%; 8% in 2023 | none | none | verified |
| SG-IMP-13 | separate session | confirmed | The four dutiable categories | none | none | partially verified |
| SG-IMP-14 | separate session | confirmed | CA authorisation before import; HS/CA Product Code Checker; ruling route | none | none | partially verified |
| SG-IMP-15 | separate session | partly confirmed | All 14 authorities | SFA names salted/preserved and processed egg products, not eggs; the page uses only "GEW" and "PABs" | Reworded to the page; expansions marked as this project's reading | partially verified |
| SG-IMP-16 | separate session | confirmed | HSA Table 1; products not currently controlled; product codes | none | none | verified |
| SG-IMP-17 | separate session | partly confirmed | SFA categories and requirements | Licence, per-consignment permit and veterinary certificate are stated for meat only; egg products need approved establishments and a health certificate | Rewritten | verified |
| SG-IMP-18 | separate session | confirmed | Declaration to IMDA, dealer's licence, prior approval for some equipment, publications | none | none | verified |
| SG-IMP-19 | separate session | confirmed | Hazardous substances, ODS/HFC, Basel permit, radiation licences, permit before arrival | none | none | verified |
| SG-IMP-20 | separate session | partly confirmed | Prohibited list | Drugs item is limited to the 4th Schedule of the Misuse of Drugs Regulations | Corrected | partially verified |
| SG-IMP-21 | separate session | confirmed | Module 5 field 18; "do not" declare the loading country as origin | none | none | verified |
| SG-IMP-22 | separate session | confirmed | Proof of origin, PRF indicator, 1 week, 1 year | none | none | verified |
| SG-IMP-23 | separate session | partly confirmed | Module 5 fields 35, 43, 50, 87, 90 | Field 87 excludes freight, insurance and other *taxable* charges shown separately | Corrected | partially verified |
| SG-IMP-24 | separate session | partly confirmed | What each Incoterm needs added; FOB and CFR conditions | The conclusion is not stated by any page; field 90 covers only ad valorem dutiable goods | Kept as a derived rule; note extended | not verified |
| SG-IMP-25 | separate session | confirmed | Supporting documents to the declaring agent; failure to produce documents; 5 years | none | none | partially verified |
| SG-IMP-26 | separate session | partly confirmed | Amend while valid; cancel and re-apply for non-amendable fields | Voluntary disclosure applies where a permit cannot be cancelled: used, expired more than 1 calendar day, or requested for audit | Rule and `corrective_action_route` corrected (tests added) | verified |
| SG-IMP-27 | separate session | confirmed | Disclosure complete and before any Customs check; exclusions | none | none | verified |
| SG-IMP-28 | separate session | partly confirmed | Module 5 fields 85 and 37 | The guide does not say the figures come from the packing list and BL/AWB, nor that they must agree | Reworded as this project's assumption | not verified |
| SG-EXP-01 | separate session | confirmed | Before export; post-departure exceptions; quoted offence | none | none | verified |
| SG-EXP-02 | separate session | confirmed | Permit, invoice, BL/AWB; S$1,000 air exemption and its limits | none | none | verified |
| SG-EXP-03 | separate session | confirmed | Individual permit 5 working days before export | none | none | verified |
| SG-EXP-04 | separate session | confirmed | Origin criteria for declaring Singapore; "do not" and common errors | none | none | verified |
| SG-EXP-05 | separate session | partly confirmed | Exporter normally the invoicing party; UEN rule | Third party must be involved in exporting; consolidator case is for customers without a UEN | Added | verified |
| SG-EXP-06 | separate session | confirmed | Offence wording | none | none | partially verified |
| AU-01 | browser, same session | confirmed | N10 above AUD 1,000 for home consumption, charges incl. import processing charge before release; SAC at AUD 1,000 or less by air or sea; permit goods need N10 or long SAC; tobacco and alcohol regardless of value | none | none | verified |
| AU-02 | browser, same session | confirmed | BL/AWB, invoices, evidence of identity, permits; keep documents five years | none | none | verified |
| AU-03 | separate session (ABS) and browser (ABF) | partly confirmed | ABF: transaction value is the method most applied, price paid or payable with adjustments, relationship condition; ABS: FOB valuation excluding international freight and insurance | ABS paragraph numbers were 3.13, 3.16 and 3.18, not 3.14 | Source locator corrected | verified |
| AU-04 | browser, same session | confirmed | GST 10% of VoTI = customs value + T&I not already in it + duty + WET | none | none | verified |
| AU-05 | browser, same session | confirmed | Supply the ABN when entering goods; ABN and GST registration for credits and deferral; owner codes for importers without an ABN | none | none | verified |
| AU-06 | browser, same session | confirmed | Customs Tariff Act 1995, self-assessment, penalties, Tariff Advice | none | none | partially verified |
| AU-07 | browser, same session | partly confirmed | BICON outcomes; permits in 20 / 40 business days | Page says *most* permits are issued in those times | Wording corrected | partially verified |
| AU-08 | browser, same session | confirmed | No import licence; permits regardless of value; permission and proof for prohibited and restricted goods | none | none | verified |
| AU-09 | browser, same session | confirmed | Do not enter preference without evidence of origin; origin country still entered; SFTA and AANZ codes | The page sentence appears to omit a word | Note added | verified |
| AU-10 | browser, same session | confirmed | Trade description in English with country of origin; unlabelled goods may be seized | none | none | verified |
| Flat-rate table | separate session | confirmed | All six region strings and rates match the page | none (the country-code column is this project's mapping) | none | n/a |
