# Rulebook: customs-hold causes and document-readiness checks

Generated from `rules/rulebook.json` and `rules/sources.json` by `scripts/build_all.py`; edit those files, not this one.

Requirements are **paraphrased** from official public pages and were read on the access date shown. They are a study aid for a portfolio project, not customs or legal advice; check the live page before relying on any of them. The second, independent check of every rule is in [rule_check.md](rule_check.md).

Status: **verified** = the requirement as written was found in the cited source; **partially verified** = the core requirement was found but a detail used here (a tolerance, a base, a mapping) was not; **not verified** = no cited source states it (a derived rule or common practice).

44 rules: 28 verified, 14 partially verified, 2 not verified.

| Rule | Title | Hold reasons | Automated check | Status |
|---|---|---|---|---|
| [SG-IMP-01](#sg-imp-01) | Customs import permit before the goods are imported | PERMIT_TIMING | permit_before_arrival | verified |
| [SG-IMP-02](#sg-imp-02) | UEN from ACRA and an activated Customs account | PARTY_UEN | customs_account_active | verified |
| [SG-IMP-03](#sg-imp-03) | UEN format | PARTY_UEN | uen_present_and_format | partially verified |
| [SG-IMP-04](#sg-imp-04) | Correct importer name and UEN on the permit | PARTY_UEN | importer_matches_profile | verified |
| [SG-IMP-05](#sg-imp-05) | HS code valid in STCCED 2022 (8-digit AHTN, based on HS 2022) | HS_INVALID, HS_QUERY | hs_format_and_hs6 | partially verified |
| [SG-IMP-06](#sg-imp-06) | HS quantity and unit as prescribed in STCCED | DOC_MISMATCH | manual | verified |
| [SG-IMP-07](#sg-imp-07) | Customs value on a CIF basis, including incidental charges | VALUE_CIF | cif_consistency | partially verified |
| [SG-IMP-08](#sg-imp-08) | Flat freight-and-insurance rates for FOB imports with unknown charges | VALUE_CIF | cif_consistency | partially verified |
| [SG-IMP-09](#sg-imp-09) | Flat 1% insurance for CFR imports with unknown insurance | VALUE_CIF | cif_consistency | partially verified |
| [SG-IMP-10](#sg-imp-10) | Foreign-currency amounts converted at MAS weekly average rates | INVOICE_DATA | invoice_fields_complete | verified |
| [SG-IMP-11](#sg-imp-11) | GST on all imports: rate x (customs value + duties) | - | gst_estimate | verified |
| [SG-IMP-12](#sg-imp-12) | GST rate 9% | - | gst_estimate | verified |
| [SG-IMP-13](#sg-imp-13) | Dutiable goods: liquor, tobacco, motor vehicles, petroleum products | VALUE_CIF | dutiable_screening | partially verified |
| [SG-IMP-14](#sg-imp-14) | Controlled goods need competent-authority approval before import | CA_APPROVAL | ca_screening | partially verified |
| [SG-IMP-15](#sg-imp-15) | Competent authorities and what they control | CA_APPROVAL | ca_screening | partially verified |
| [SG-IMP-16](#sg-imp-16) | HSA: health products that need licensing or approval; cosmetics do not | CA_APPROVAL | ca_screening | verified |
| [SG-IMP-17](#sg-imp-17) | SFA: food imports need a licence or registration and a permit before arrival | CA_APPROVAL | ca_screening | verified |
| [SG-IMP-18](#sg-imp-18) | IMDA: telecommunication equipment is declared to IMDA | CA_APPROVAL | ca_screening | verified |
| [SG-IMP-19](#sg-imp-19) | NEA: hazardous substances, ODS/HFCs, radioactive materials, wastes | CA_APPROVAL | ca_screening | verified |
| [SG-IMP-20](#sg-imp-20) | Prohibited imports | CA_APPROVAL | prohibited_screening | partially verified |
| [SG-IMP-21](#sg-imp-21) | Country of origin is where goods were wholly obtained or substantially transformed | ORIGIN_DOCS | origin_consistency | verified |
| [SG-IMP-22](#sg-imp-22) | FTA preference on dutiable imports needs proof of origin | ORIGIN_DOCS | preference_proof | verified |
| [SG-IMP-23](#sg-imp-23) | Invoice data the permit needs | INVOICE_DATA | invoice_fields_complete | partially verified |
| [SG-IMP-24](#sg-imp-24) | Incoterm stated on the invoice | INVOICE_DATA, VALUE_CIF | incoterm_present | not verified |
| [SG-IMP-25](#sg-imp-25) | Supporting documents to the declaring agent; keep for 5 years | DOC_MISMATCH, INVOICE_DATA | docs_present | partially verified |
| [SG-IMP-26](#sg-imp-26) | Amend while valid; cancel and re-apply for non-amendable fields | VALUE_CIF, PARTY_UEN, HS_INVALID, HS_QUERY, ORIGIN_DOCS | corrective_action_route | verified |
| [SG-IMP-27](#sg-imp-27) | Voluntary disclosure of declaration errors | - | corrective_action_route | verified |
| [SG-IMP-28](#sg-imp-28) | Quantities and weights agree across invoice, packing list and transport document | DOC_MISMATCH | quantity_weight_consistency | not verified |
| [SG-EXP-01](#sg-exp-01) | Export permit before export | PERMIT_TIMING | permit_before_departure | verified |
| [SG-EXP-02](#sg-exp-02) | Export clearance documents; low-value air exemption | PERMIT_TIMING, DOC_MISMATCH | docs_present | verified |
| [SG-EXP-03](#sg-exp-03) | Strategic goods: individual permit 5 working days before export | PERMIT_TIMING | manual | verified |
| [SG-EXP-04](#sg-exp-04) | Singapore origin only when origin criteria are met | ORIGIN_DOCS | origin_consistency | verified |
| [SG-EXP-05](#sg-exp-05) | Exporter is normally the invoicing party | PARTY_UEN | importer_matches_profile | verified |
| [SG-EXP-06](#sg-exp-06) | Export documents within 14 days after departure | - | manual | partially verified |
| [AU-01](#au-01) | Declaration type by value: Import Declaration above AUD 1,000 | PERMIT_TIMING | au_declaration_type | verified |
| [AU-02](#au-02) | Documents for an Import Declaration; keep five years | DOC_MISMATCH, INVOICE_DATA | docs_present | verified |
| [AU-03](#au-03) | Customs value: transaction value on an FOB basis | VALUE_CIF | au_voti_gst | verified |
| [AU-04](#au-04) | GST 10% of the value of the taxable importation | - | au_voti_gst | verified |
| [AU-05](#au-05) | ABN on the import entry | PARTY_UEN | au_abn_quoted | verified |
| [AU-06](#au-06) | Self-assessed tariff classification under the Customs Tariff Act 1995 | HS_INVALID, HS_QUERY | hs_format_and_hs6 | partially verified |
| [AU-07](#au-07) | Biosecurity import conditions (BICON) | BIOSECURITY | au_biosecurity_screening | partially verified |
| [AU-08](#au-08) | Prohibited and restricted goods need permission | CA_APPROVAL | manual | verified |
| [AU-09](#au-09) | Claim FTA preference only with evidence of origin | ORIGIN_DOCS | preference_proof | verified |
| [AU-10](#au-10) | Trade description labels for certain goods | INSPECTION | manual | verified |

## Singapore imports

### SG-IMP-01

**Customs import permit before the goods are imported** (permit; status: verified)

The importer must obtain the relevant customs permit before the goods are imported into Singapore; the permit is submitted through TradeNet. The overview's 'common errors' section explains how a wrong permit is corrected depending on whether it has already been used for clearance.

- Readiness check: Permit application timestamp is earlier than the arrival date of the shipment.
- Corrective action: Apply for the permit before re-presenting the cargo; for later shipments the handling note asks for the permit before arrival. If goods were imported without a permit, the error can only be corrected through a voluntary disclosure (SG-IMP-27).
- Note: The timing comes from the overview and the TradeNet route from the permit page; neither page alone states both. The second-pass check found that the first version wrongly said an unused or used permit is itself listed as an error; corrected.
- Source: Singapore Customs, [Import Procedures Overview](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/import-procedures-overview/) (opening paragraph; 'Common errors' list); accessed 2026-11-15
- Source: Singapore Customs, [Obtain a Customs Import Permit](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/obtain-a-customs-import-permit/) (opening paragraph); accessed 2026-11-15

### SG-IMP-04

**Correct importer name and UEN on the permit** (party; status: verified)

Wrong importer name and UEN, and wrong importer, are listed as common permit errors. A UEN must not be used to import goods that do not belong to that entity, except when consolidating for customers without a UEN, in which case the consolidator remains responsible.

- Readiness check: Importer UEN and name on the draft permit equal the customer profile.
- Corrective action: Amend the importer fields while the permit is valid, or cancel and re-apply if the field is not amendable (SG-IMP-26); correct the customer master data.
- Note: The two errors appear in the overview's sub-lists for Major Exporter Scheme traders and for In-Payment permits.
- Source: Singapore Customs, [Import Procedures Overview](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/import-procedures-overview/) ('Do not' list; 'Common errors' list); accessed 2026-11-15

### SG-IMP-07

**Customs value on a CIF basis, including incidental charges** (valuation; status: partially verified)

Transaction value is the primary valuation method and is based on the CIF value. All charges incidental to the sale and delivery of the goods to Singapore are included, e.g. selling commissions, assists, packing, royalties and licence fees, freight and insurance; an EXW price additionally needs inland transport, port handling and export clearance costs. Wrong value is a common error and an incorrect value declaration an offence.

- Readiness check: CIF value computed from the invoice and the charges required by its Incoterm equals the value on the draft permit within tolerance.
- Corrective action: Recompute the CIF value and amend the permit while it is valid; if the permit has been used for clearance, submit a voluntary disclosure (SG-IMP-26, SG-IMP-27).
- Assumptions: Value tolerance 0.5% of the computed CIF value (minimum SGD 1).
- Note: Requirement verified. The comparison tolerance (0.5% of CIF, minimum SGD 1) is an assumption of this project.
- Source: Singapore Customs, [Establishing Customs Value and Methods](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/establishing-customs-value/establishing-customs-value-and-methods/) (transaction value; charges to include; EXW example); accessed 2026-11-15
- Source: Singapore Customs, [Import Procedures Overview](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/import-procedures-overview/) ('Do' list (include freight and insurance); 'Common errors' and 'Offences' lists); accessed 2026-11-15

### SG-IMP-08

**Flat freight-and-insurance rates for FOB imports with unknown charges** (valuation; status: partially verified)

When the transaction value is quoted FOB and the actual freight and insurance are not known or not available to the importer, flat rates of the FOB value may be used, by place of export: Africa, Canada and USA 24.5%; Europe 19%; Japan, Australia and New Zealand 19%; China, Chinese Taipei, Korea, Sri Lanka, India and Pakistan 15.5%; Myanmar, Thailand, Cambodia, Laos, Vietnam, Hong Kong, Philippines and Indonesia 9.5%; Peninsular Malaysia 5%.

- Readiness check: FOB invoice without actual charges: CIF = FOB x (1 + flat rate of the export country); other export countries need actual charges.
- Corrective action: Add the flat-rate amount, or obtain the freight and insurance invoices.
- Assumptions: The flat rate is applied regardless of mode (the page names no mode). Malaysian exports are assumed to leave from Peninsular Malaysia.
- Note: Rates and conditions verified; the page does not say whether the rates differ by transport mode. The country-to-region mapping in rules/sg_flat_freight_insurance.csv is this project's reading of the table (e.g. Germany as Europe).
- Source: Singapore Customs, [Flat Rates for Freight and Insurance](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/establishing-customs-value/flat-rates-for-freight-and-insurance/) (rate table and conditions); accessed 2026-11-15

### SG-IMP-09

**Flat 1% insurance for CFR imports with unknown insurance** (valuation; status: partially verified)

When the transaction value is quoted CFR and the actual insurance cost is unknown or unavailable, a flat insurance rate of 1% may be used to compute the customs value; if no insurance was bought, the insurance cost may be declared as zero.

- Readiness check: CFR invoice without an insurance amount: insurance = 1% of the CFR value unless the customer confirms no insurance was bought.
- Corrective action: Add the 1% insurance or a statement that no insurance was purchased.
- Assumptions: Base of the 1% = CFR invoice value.
- Note: Rate and conditions verified; the page does not state the base of the 1%. This project applies it to the CFR value.
- Source: Singapore Customs, [Flat Rate for Insurance](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/establishing-customs-value/flat-rate-for-insurance/) (whole page); accessed 2026-11-15

### SG-IMP-10

**Foreign-currency amounts converted at MAS weekly average rates** (valuation; status: verified)

Costs in foreign currency are converted to Singapore dollars at the prevailing weekly average MAS exchange rates; the permit-field guide says the rates of the preceding week are used for declarations made in the current week.

- Readiness check: Invoice currency is stated; the conversion uses the rate of the week before the declaration.
- Corrective action: Request an invoice that states its currency.
- Note: The synthetic data use fixed ILLUSTRATIVE exchange rates (config/synth_assumptions.json), not MAS rates.
- Source: Singapore Customs, [Establishing Customs Value and Methods](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/establishing-customs-value/establishing-customs-value-and-methods/) (currency conversion paragraph); accessed 2026-11-15
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Inward fields 32, 58, 87); accessed 2026-11-15

### SG-IMP-11

**GST on all imports: rate x (customs value + duties)** (tax; status: verified)

All goods imported into Singapore are subject to GST at the prevailing rate. For dutiable goods GST = rate x (customs value or last selling price + duties payable); for non-dutiable goods GST = rate x customs value (or last selling price).

- Readiness check: Estimated GST on the draft permit = 9% x (CIF value in SGD + duty).
- Corrective action: Recompute GST after any value correction.
- Note: Last selling price cases are not modelled.
- Source: Singapore Customs, [Goods and Services Tax](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/goods-and-services-tax-gst/) (formula paragraphs); accessed 2026-11-15

### SG-IMP-12

**GST rate 9%** (tax; status: verified)

The current GST rate in Singapore is 9%; IRAS's table of past rates shows 8% for 1 January to 31 December 2023.

- Readiness check: GST estimates use 9%.
- Source: Inland Revenue Authority of Singapore, [Current GST rates](https://www.iras.gov.sg/taxes/goods-services-tax-(gst)/basics-of-gst/current-gst-rates) (current rate statement; rate history table); accessed 2026-11-15

### SG-IMP-13

**Dutiable goods: liquor, tobacco, motor vehicles, petroleum products** (tax; status: partially verified)

Customs and excise duties apply to four categories: intoxicating liquors, tobacco products, motor vehicles, and petroleum products and biodiesel blends. Other goods are non-dutiable but GST may still apply.

- Readiness check: Lines in HS chapters/headings mapped to these categories are flagged 'dutiable: duty rate and quantity fields needed'.
- Corrective action: Declare duty rate and dutiable quantity; consider preference only with proof of origin (SG-IMP-22).
- Assumptions: Dutiable screening by HS heading, not by the exact STCCED duty column.
- Note: Categories verified. The HS mapping (2203-2208, 24, 2710, 8703) in rules/sg_ca_screening.csv is a screening heuristic of this project.
- Source: Singapore Customs, [Duties and Dutiable Goods Overview](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/duties-and-dutiable-goods/duties-and-dutiable-goods-overview/) (list of categories); accessed 2026-11-15

### SG-IMP-16

**HSA: health products that need licensing or approval; cosmetics do not** (controlled_goods; status: verified)

HSA licensing and/or approval before import applies to therapeutic products, medical devices, cell, tissue and gene therapy products, Chinese proprietary medicines, clinical-research products, controlled drugs and psychotropic substances, oral dental gums, poisons and active ingredients. Cosmetic products, health supplements, quasi-medicines and several traditional medicines are currently not subject to HSA licensing before importation. Declarations use an HSA product code and the licence details in the CA/SC code fields.

- Readiness check: Chapter 30 and medical-device headings require an HSA licence reference; chapter 33 (cosmetics) is not flagged.
- Corrective action: Ask for the HSA licence/approval and product code before the first shipment.
- Source: Singapore Customs, [Competent Authorities Requirements: Health Sciences Authority (HSA)](https://www.customs.gov.sg/doing-business/quick-links-for-traders/tradenet/competent-authorities-requirements-for-controlled-items/health-sciences-authority/) (Table 1; list of products not currently controlled; product code table); accessed 2026-11-15

### SG-IMP-17

**SFA: food imports need a licence or registration and a permit before arrival** (controlled_goods; status: verified)

SFA controls imports of fruit and vegetables (licence), livestock and animal products (permit in advance), meat (licence for meat and fish products, a permit for every consignment of meat product, veterinary health certificate), salted/preserved eggs and processed egg products (from SFA-approved establishments, with a health certificate), processed food and food appliances (registration), rice (licence) and fish (licence, permit per consignment, health certificates for some items). The customs permit must be obtained before the goods arrive.

- Readiness check: Food chapters require an SFA licence/registration reference; meat and seafood lines also need a health certificate on file.
- Corrective action: Ask for the SFA licence or registration number and the exporting country's health certificate.
- Assumptions: Health certificate requirement screened at chapters 02 and 03.
- Note: The second-pass check found that the first version applied the meat licence, permit and veterinary certificate to egg products as well; corrected. The health-certificate check is applied to chapters 02 and 03 only.
- Source: Singapore Customs, [Competent Authorities Requirements: Singapore Food Agency (SFA)](https://www.customs.gov.sg/doing-business/quick-links-for-traders/tradenet/competent-authorities-requirements-for-controlled-items/singapore-food-agency/) (sections by product type); accessed 2026-11-15

### SG-IMP-18

**IMDA: telecommunication equipment is declared to IMDA** (controlled_goods; status: verified)

All imported telecommunication equipment must be declared to IMDA through TradeNet before arrival; dealers need an IMDA telecommunication dealer's licence and enter the licence number, product code and equipment registration number; some equipment needs prior IMDA approval. Publications are also controlled.

- Readiness check: Headings 8517 and 8525-8529 require an IMDA dealer's licence reference (or an own-use declaration).
- Corrective action: Ask for the dealer's licence number and equipment registration numbers.
- Note: The heading list is this project's screening choice.
- Source: Singapore Customs, [Competent Authorities Requirements: Info-communications Media Development Authority (IMDA)](https://www.customs.gov.sg/doing-business/quick-links-for-traders/tradenet/competent-authorities-requirements-for-controlled-items/info-communications-media-development-authority/) (Telecommunication Equipment sections A and B; Publications); accessed 2026-11-15

### SG-IMP-19

**NEA: hazardous substances, ODS/HFCs, radioactive materials, wastes** (controlled_goods; status: verified)

NEA requires a hazardous substances licence for items containing EPMA-listed ingredients, an import licence for controlled ozone-depleting substances and HFCs, radiation licences for radioactive materials and irradiating apparatus, and a Basel permit for controlled hazardous waste; the customs permit is obtained before arrival.

- Readiness check: Chemical chapters (28, 29, 38) and heading 9022 require a licence reference or a statement that the substance is not controlled.
- Corrective action: Ask for the NEA licence number, or the safety data sheet showing the substance is not controlled.
- Note: Chapter-level screening over-flags: most chemicals in chapters 28, 29 and 38 are not NEA-controlled.
- Source: Singapore Customs, [Competent Authorities Requirements: National Environment Agency (NEA)](https://www.customs.gov.sg/doing-business/quick-links-for-traders/tradenet/competent-authorities-requirements-for-controlled-items/national-environment-agency/) (controls and licences sections); accessed 2026-11-15

### SG-IMP-20

**Prohibited imports** (controlled_goods; status: partially verified)

Goods that cannot be imported include chewing gum (other than HSA-approved oral dental and medicinal gum), rhinoceros horn and endangered wildlife products, certain telecommunication equipment such as jammers and scanning receivers, imitation tobacco products including e-cigarettes and vaporisers, other listed tobacco and nicotine products, and controlled drugs listed in the 4th Schedule of the Misuse of Drugs Regulations.

- Readiness check: Lines in heading 1704.10 (chewing gum) or subheading 8543.40 (e-cigarettes) are flagged 'prohibited: do not accept for import'.
- Corrective action: Do not lodge; inform the customer that the goods cannot be imported.
- Assumptions: Prohibited screening uses 170410 and 854340 only.
- Note: The list is verified; the two HS codes used for screening are this project's mapping.
- Source: Singapore Customs, [Controlled and Prohibited Goods for Imports](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/controlled-and-prohibited-goods-for-imports/) (prohibited goods list); accessed 2026-11-15

### SG-IMP-21

**Country of origin is where goods were wholly obtained or substantially transformed** (origin; status: verified)

The origin field is the country or region in which the goods were wholly obtained or substantially transformed, meeting the rules of origin of that place. Declaring the country of the port of loading as the origin when the goods originate elsewhere is on the 'do not' list.

- Readiness check: Every invoice line states a country of origin; if the origin equals the port-of-loading country while the certificate of origin or supplier declaration names another country, flag a mismatch.
- Corrective action: Ask the supplier to confirm origin; amend the permit.
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Inward fields, 18 country/region of origin); accessed 2026-11-15
- Source: Singapore Customs, [Import Procedures Overview](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/import-procedures-overview/) ('Do not' list); accessed 2026-11-15

### SG-IMP-22

**FTA preference on dutiable imports needs proof of origin** (origin; status: verified)

Lower or zero duty under an FTA applies to certain dutiable goods originating in a partner country. Proof of origin is a preferential certificate of origin, a self-certification, or an electronic reference (e.g. e-ATIGA Form D). With proof at import the permit uses preference indicator 'PRF'; the CO or self-certification, invoice and bill of lading go to Singapore Customs within 1 week of clearance. Without proof, full duty is paid and a refund may be requested within 1 year.

- Readiness check: If preference is claimed, a CO or self-certification is on file.
- Corrective action: Obtain the CO; if it is not available at import, pay the full duty, note the intention in Remarks and claim the refund within 1 year.
- Source: Singapore Customs, [Claiming Preferential Tariff Treatment for Dutiable Imports](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/claiming-preferential-tariff-treatment-for-dutiable-imports/) (proof of origin; declaring in TradeNet; time limits); accessed 2026-11-15

### SG-IMP-24

**Incoterm stated on the invoice** (documents; status: not verified)

Derived rule: what must be added to the invoice price to reach the CIF value depends on the delivery term (EXW needs inland and export costs; FOB needs freight and insurance; CFR needs insurance), and the flat rates apply only to FOB or CFR quotes. An invoice that does not state its Incoterm therefore cannot be valued without asking.

- Readiness check: Invoice states an Incoterms 2020 rule (and named place).
- Corrective action: Ask the supplier to state the Incoterm on the invoice.
- Note: No cited page states 'the invoice must show an Incoterm' as a requirement; the rule is inferred from the valuation pages. The permit's term-type field (Module 5 field 90) applies only to dutiable goods with ad valorem duty, so it does not support a general requirement either; the second-pass check agreed.
- Source: Singapore Customs, [Establishing Customs Value and Methods](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/establishing-customs-value/establishing-customs-value-and-methods/) (EXW example); accessed 2026-11-15
- Source: Singapore Customs, [Flat Rates for Freight and Insurance](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/establishing-customs-value/flat-rates-for-freight-and-insurance/) (conditions); accessed 2026-11-15
- Source: Singapore Customs, [Flat Rate for Insurance](https://www.customs.gov.sg/doing-business/valuation-duties-and-fees/establishing-customs-value/flat-rate-for-insurance/) (conditions); accessed 2026-11-15
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Inward field 90 (term type)); accessed 2026-11-15

### SG-IMP-25

**Supporting documents to the declaring agent; keep for 5 years** (documents; status: partially verified)

Provide full supporting documents (invoices, shipping documents, certificates of origin) to the declaring agent; failing to produce trade documents on request is an offence; supporting documents are kept for 5 years.

- Readiness check: Commercial invoice, packing list and bill of lading or air waybill are on file before the permit is drafted.
- Corrective action: Request the missing document; record the document checklist in the handling note.
- Assumptions: Packing list required by this project's checklist.
- Note: The page names invoices, shipping documents and certificates of origin; the packing list is common practice and is not named there.
- Source: Singapore Customs, [Import Procedures Overview](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/import-procedures-overview/) ('Do' list; 'Offences' list); accessed 2026-11-15

### SG-IMP-26

**Amend while valid; cancel and re-apply for non-amendable fields** (amendment; status: verified)

An approved permit can be amended in TradeNet while it is valid, any number of times, except non-amendable fields. Incorrect details in non-amendable fields are corrected by cancelling the valid permit and applying for a new one. A permit used for cargo clearance or expired cannot be amended; a permit used for cargo clearance, expired for more than 1 calendar day, or requested for audit by the Manifest Compliance Unit cannot be cancelled, and for such cases the page points to a voluntary disclosure.

- Readiness check: Corrective action chosen by permit state: valid -> amend (or cancel and re-apply for a non-amendable field); expired by at most 1 calendar day -> cancel and re-apply; used for clearance or expired longer -> voluntary disclosure; under a Customs check -> respond to the check, because a voluntary disclosure must come before any Customs check (SG-IMP-27).
- Corrective action: See readiness_check.
- Note: The second-pass check found that the first version treated every expired permit as needing a voluntary disclosure; the 1-calendar-day cancellation window and the audit case were added.
- Source: Singapore Customs, [Permit Amendment and Cancellation](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/permit-amendment-and-cancellation/) (Amendment; Cancellation; used permits); accessed 2026-11-15

## Singapore imports and exports

### SG-IMP-02

**UEN from ACRA and an activated Customs account** (party; status: verified)

An importer first registers with ACRA (or the relevant UEN issuance agency) to obtain a UEN and then activates a Customs account with Singapore Customs; the activation is needed before any import permit application can be submitted. A declaring agent may apply for permits on the importer's behalf.

- Readiness check: Customer profile has a UEN and the Customs account is recorded as activated before the first permit is drafted.
- Corrective action: Ask the customer to activate the Customs account (or confirm activation) before the first shipment; hold the enrolment at 'Documents received' until confirmed.
- Source: Singapore Customs, [Obtain a Customs Import Permit](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/obtain-a-customs-import-permit/) (UEN and Customs account section; Declaring Agent section); accessed 2026-11-15

### SG-IMP-03

**UEN format** (party; status: partially verified)

Entity UEN formats: businesses registered with ACRA NNNNNNNNC (9 characters); local companies YYYYNNNNNC (10 characters), with foreign companies listed under the same entry as F000NNNNNC or FDDDNNNNNC (D = a space); other entities TYYPQNNNNC or SYYPQNNNNC (10 characters). N is a digit, C a check letter, YYYY or TYY/SYY a year (T = 20, S = 19) and PQ an entity-type code.

- Readiness check: UEN on the enrolment form matches one of the three patterns.
- Corrective action: Request the UEN as shown on the ACRA business profile; do not draft permits until it is on file.
- Assumptions: Only the character pattern is validated; the check letter and the registration year are not.
- Note: Formats verified against the OECD TIN sheet that Singapore supplied; the agency page it links to (uen.gov.sg) returned HTTP 403, and the check-letter algorithm is not published there, so only the pattern is checked, not the check letter or whether the UEN exists. The second-pass check found that the first version omitted the foreign-company formats; they were added.
- Source: OECD (information supplied by Singapore), [Singapore - Information on Tax Identification Numbers (UEN structure, Section II)](https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Singapore-TIN.pdf) (Section II - TIN structure, entity ID types); accessed 2026-11-15

### SG-IMP-05

**HS code valid in STCCED 2022 (8-digit AHTN, based on HS 2022)** (classification; status: partially verified)

The permit HS code must be a valid code of the Singapore Trade Classification, Customs and Excise Duties (STCCED) publication, and Singapore's current schedule is STCCED 2022. Separately, the same page describes the ASEAN Harmonised Tariff Nomenclature (AHTN) as an 8-digit nomenclature used by all ASEAN member states, based on the WCO 6-digit HS, whose 2022 amendment incorporated the HS 2022 changes.

- Readiness check: HS code is 8 digits and its first 6 digits are an HS 2022 subheading.
- Corrective action: Correct the code in the product master and the permit (amend while valid). For doubtful cases use the HS/CA Product Code Checker or apply for a classification ruling (SG-IMP-14).
- Assumptions: Validity is tested at the 6-digit level only.
- Note: The requirement is verified. The page does not itself say that STCCED 2022 is built on AHTN 2022 (that link is this project's reading). The check uses only the public HS 2022 6-digit list: the national 7th-8th digits are not validated because the STCCED code list is not used here.
- Source: Singapore Customs, [Understanding HS Classification](https://www.customs.gov.sg/doing-business/business-resources/hs-classification-of-goods/understanding-hs-classification/) (HS and AHTN paragraphs); accessed 2026-11-15
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Inward fields, 36 HS code); accessed 2026-11-15

### SG-IMP-06

**HS quantity and unit as prescribed in STCCED** (classification; status: verified)

Each permit item carries a quantity and unit-of-quantity code as prescribed in STCCED; competent authorities may require their own product-code quantity and unit.

- Readiness check: Manual: unit on invoice and packing list can be converted to the STCCED unit of the HS code.
- Corrective action: Ask for a packing list that states the quantity in the prescribed unit.
- Note: Not automated: the STCCED unit table is not part of this repository.
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Inward fields, 37 HS quantity and unit; 8 CA/SC product code quantity and unit); accessed 2026-11-15

### SG-IMP-14

**Controlled goods need competent-authority approval before import** (controlled_goods; status: partially verified)

Controlled goods need authorisation from the relevant Competent Authority (advance notification, licence or certificate approval) before they may be imported. The HS/CA Product Code Checker shows whether an HS code is controlled and by which CA; uncertain classifications can be put to Singapore Customs for an official ruling.

- Readiness check: Lines whose HS prefix appears in the CA screening table need a CA licence or approval reference on file.
- Corrective action: Obtain the CA licence/approval, record its number in the handling note, then re-submit; confirm the CA product code with the HS/CA Product Code Checker.
- Assumptions: HS-prefix screening table rules/sg_ca_screening.csv.
- Note: Requirement verified. Screening by HS chapter/heading is this project's heuristic; the authoritative test is the HS/CA product code, which is not used here.
- Source: Singapore Customs, [Controlled and Prohibited Goods for Imports](https://www.customs.gov.sg/doing-business/import-operations/import-procedures/controlled-and-prohibited-goods-for-imports/) (controlled goods paragraph); accessed 2026-11-15
- Source: Singapore Customs, [Find my Harmonised System Code](https://www.customs.gov.sg/doing-business/business-resources/hs-classification-of-goods/find-my-harmonised-system-code/) (HS/CA Product Code Checker; 'Still unsure' section); accessed 2026-11-15

### SG-IMP-15

**Competent authorities and what they control** (controlled_goods; status: partially verified)

Singapore Customs lists 14 competent authorities for controlled items: BCA (sand and granite), CNB (controlled substances), Enterprise Singapore (rubber exports), GRA (fruit and jackpot machines), HSA (health products), IMDA (publications, telecommunication equipment), LTA (PABs and motorised PMDs), MOH (biological agents and toxins), NEA (wastes, hazardous substances and chemicals, ODS, HFCs, radioactive materials, irradiating apparatus), NParks (CITES specimens, plants, live animals, animal products, ornamental fish), SCDF (petroleum and flammable materials), Singapore Customs (regulated goods and sanctioned trade), SFA (fruit, vegetables, livestock, animal products, meat, salted/preserved eggs and processed egg products, processed food, rice, fish) and SPF (GEW-regulated items; amusement game machines).

- Readiness check: The CA named by the screening table is written into the handling note with the licence type to ask for.
- Note: The list is verified as written above. The expansions used elsewhere in this project, PAB = power-assisted bicycle and GEW = guns, explosives and weapons, are this project's reading; the page uses only the abbreviations. The first version also named eggs in general under SFA; corrected.
- Source: Singapore Customs, [Competent Authorities Requirements for Controlled Items](https://www.customs.gov.sg/doing-business/quick-links-for-traders/tradenet/competent-authorities-requirements-for-controlled-items/) (list of competent authorities); accessed 2026-11-15

### SG-IMP-23

**Invoice data the permit needs** (documents; status: partially verified)

The permit carries the commercial invoice number and date, the goods description as on the invoice, the total invoice amount with currency and exchange rate (excluding freight, insurance and other taxable charges when these are shown separately), item values on CIF terms for imports, and, for goods with ad valorem duty, the unit price with its currency and term type.

- Readiness check: Invoice has number, date, seller, buyer, currency, Incoterm, and for every line a description, quantity, unit, unit price, line value and origin.
- Corrective action: Request a corrected commercial invoice from the supplier; add the missing fields to the customer's invoice checklist in the handling note.
- Assumptions: Seller and buyer names are required by this project's checklist.
- Note: Invoice number and date, description, currency, total and item values are verified field requirements. Seller and buyer name on the invoice are common practice, not stated in the cited guide.
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Inward fields 35, 43, 50, 87, 90); accessed 2026-11-15

### SG-IMP-27

**Voluntary disclosure of declaration errors** (amendment; status: verified)

Traders are encouraged to disclose errors or omissions in their declarations through the Voluntary Disclosure Programme; the disclosure must be complete and made before Singapore Customs initiates checks, audits or investigations, and some situations are excluded.

- Readiness check: For holds found after clearance, the action log records a voluntary disclosure step.
- Corrective action: Prepare a complete disclosure with supporting documents before any Customs query.
- Source: Singapore Customs, [Voluntary Disclosure Programme](https://www.customs.gov.sg/doing-business/compliance/voluntary-disclosure-programme/) (description; conditions and exclusions); accessed 2026-11-15

### SG-IMP-28

**Quantities and weights agree across invoice, packing list and transport document** (documents; status: not verified)

The permit declares total gross weight (tonnes for sea, kilograms for air) and item quantities in the prescribed units. This project assumes these figures are taken from the packing list and the bill of lading or air waybill, so those documents must agree.

- Readiness check: Line quantities on invoice and packing list are equal; packing-list gross weight is within 2% of the transport document.
- Corrective action: Reconcile with the supplier and the forwarder; obtain corrected documents.
- Assumptions: Gross weight tolerance 2%.
- Note: The guide defines the weight and quantity fields; it does not state a cross-document tolerance. The 2% tolerance is an assumption.
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Inward fields 37 and 85); accessed 2026-11-15

## Singapore exports

### SG-EXP-01

**Export permit before export** (permit; status: verified)

Export permits are submitted before export (recommended before cargo lodgement with the port operator or air cargo handler); exceptions with post-departure deadlines exist for some bulk petroleum and chemicals and for steel bars. 'Submitting declarations only after export' is listed as a common offence.

- Readiness check: Export permit timestamp is earlier than the departure date.
- Corrective action: Apply for the export permit before lodging the cargo.
- Source: Singapore Customs, [Export Procedures Overview](https://www.customs.gov.sg/doing-business/export-operations/export-procedures/export-procedures-overview/) (timeline table; common offences); accessed 2026-11-15

### SG-EXP-02

**Export clearance documents; low-value air exemption** (documents; status: verified)

For clearance, the approved export permit and supporting documents such as commercial invoices and the bill of lading or air waybill are presented. A permit is not required for non-controlled, non-dutiable goods valued at S$1,000 or less exported by air; controlled goods and goods removed from licensed premises need a permit regardless of value.

- Readiness check: Export bundle has permit (unless exempt), invoice and BL/AWB.
- Corrective action: Request the missing document.
- Source: Singapore Customs, [Documentation for Clearance of Goods](https://www.customs.gov.sg/doing-business/export-operations/export-procedures/documentation-for-clearance-of-goods/) (containerised cargo; when no permit is needed); accessed 2026-11-15

### SG-EXP-03

**Strategic goods: individual permit 5 working days before export** (permit; status: verified)

For strategic goods under an Individual Permit of the Strategic Trade Scheme, the permit is submitted 5 working days before export.

- Readiness check: Manual: strategic goods are identified by the customer; not screened automatically.
- Corrective action: Plan the permit 5 working days ahead.
- Note: The synthetic data contain no strategic goods.
- Source: Singapore Customs, [Export Procedures Overview](https://www.customs.gov.sg/doing-business/export-operations/export-procedures/export-procedures-overview/) (timeline table); accessed 2026-11-15

### SG-EXP-04

**Singapore origin only when origin criteria are met** (origin; status: verified)

Singapore may be declared as the country of origin only if the goods meet the FTA rules of origin (for preference in the partner country) or Singapore's non-preferential rules of origin; declaring goods as Singapore-origin when they do not qualify is on the 'do not' list, and a wrong origin is a common error.

- Readiness check: Exports declared as SG origin have an origin basis recorded (FTA rule or non-preferential CO).
- Corrective action: Correct the origin; apply for a certificate of origin if preference is wanted.
- Source: Singapore Customs, [Guide to Customs' Procedures, Module 5: TradeNet Permit Applications - Important Permit Fields (footer: Last Updated July 2026; file name: Updated 18 Aug 2026)](https://isomer-user-content.by.gov.sg/174/a40a6521-10e3-4e86-8e70-c047937dee95/Module%205_Important%20Permit%20Fields%20(Updated%2018%20Aug%202026).pdf) (Outward fields, 15 country/region of origin); accessed 2026-11-15
- Source: Singapore Customs, [Export Procedures Overview](https://www.customs.gov.sg/doing-business/export-operations/export-procedures/export-procedures-overview/) ('Do not' list; common errors); accessed 2026-11-15

### SG-EXP-05

**Exporter is normally the invoicing party** (party; status: verified)

The exporter is usually the party issuing the commercial invoice to the overseas customer; a third party involved in exporting the goods may declare itself exporter when it acts on the invoicing party's behalf or consolidates for customers without a UEN. A UEN must not be used to export goods that do not belong to that entity unless it acts as exporter or consolidator.

- Readiness check: Exporter UEN on the permit equals the invoicing customer's UEN.
- Corrective action: Correct the exporter fields.
- Source: Singapore Customs, [Export Procedures Overview](https://www.customs.gov.sg/doing-business/export-operations/export-procedures/export-procedures-overview/) (exporter paragraph; 'Do not' list); accessed 2026-11-15

### SG-EXP-06

**Export documents within 14 days after departure** (documents; status: partially verified)

'Failing to submit export documents within 14 days after vessel or aircraft departure' is listed as a common offence.

- Readiness check: Manual reminder in the action log 14 days after departure.
- Note: The wording is on the page, but the page does not say which documents or to whom, so the rule is not automated.
- Source: Singapore Customs, [Export Procedures Overview](https://www.customs.gov.sg/doing-business/export-operations/export-procedures/export-procedures-overview/) (common offences list); accessed 2026-11-15

## Australia imports (second destination)

### AU-01

**Declaration type by value: Import Declaration above AUD 1,000** (permit; status: verified)

An Import Declaration (N10) is required when a consignment has a combined value over AUD 1,000 and is cleared into home consumption; duties, taxes and charges, including an import processing charge, are paid before release. Air and sea cargo of AUD 1,000 or less uses a Self-Assessed Clearance declaration; goods that need a permit use an N10 or a long-format SAC. Tobacco and alcohol bear duty and taxes regardless of value.

- Readiness check: For SG-to-AU shipments the expected declaration type is derived from the AUD value and the permit flag.
- Corrective action: Tell the consignee's broker which declaration type applies.
- Source: Australian Border Force, [Import declarations](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/import-declaration) (Import Declaration (N10); SAC Declaration sections); accessed 2026-11-15

### AU-02

**Documents for an Import Declaration; keep five years** (documents; status: verified)

Lodging an Import Declaration in person needs the bill of lading or air waybill, the commercial invoices, evidence of identity, permits or approvals and other relevant documents; all relevant documents are kept for five years after the declaration.

- Readiness check: SG-to-AU export bundle includes invoice, BL/AWB and any AU permit.
- Corrective action: Send the missing document to the consignee's broker.
- Source: Australian Border Force, [Import declarations](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/import-declaration) (lodging in person; final paragraph); accessed 2026-11-15

### AU-03

**Customs value: transaction value on an FOB basis** (valuation; status: verified)

The usual method (transaction value) is based on the price actually paid or payable, with adjustments, provided the buyer-seller relationship does not influence the price. Australia's customs value is an FOB valuation: it excludes international freight and insurance from the place of export.

- Readiness check: For SG-to-AU shipments the invoice value is converted to an FOB customs value: CIF/CIP/CFR/CPT/D-term invoices need the freight and insurance shown separately so they can be deducted.
- Corrective action: Ask the customer to show freight and insurance separately on the invoice.
- Note: FOB basis verified against the ABS methods publication; the ABF valuation fact sheet (PDF) could not be read here.
- Source: Australian Border Force, [Requirements to import goods](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/requirements) (Valuation); accessed 2026-11-15
- Source: Australian Bureau of Statistics, [International Merchandise Trade, Australia: Concepts, Sources and Methods, 2018 - Trade system, valuation and time of recording](https://www.abs.gov.au/statistics/detailed-methodology-information/concepts-sources-methods/international-merchandise-trade-australia-concepts-sources-and-methods/2018/trade-system-valuation-and-time-recording) (paragraphs 3.13, 3.16 and 3.18); accessed 2026-11-15

### AU-04

**GST 10% of the value of the taxable importation** (tax; status: verified)

GST on taxable importations is 10% of the value of the taxable importation: customs value + international transport and insurance (to the extent not already in the customs value) + customs duty + any wine equalisation tax.

- Readiness check: Estimated AU GST = 10% x (FOB customs value + T&I + duty) in AUD.
- Assumptions: Customs duty = 0 for all synthetic AU lines.
- Note: Duty is set to 0 in the synthetic data (tariff rates are not modelled).
- Source: Australian Border Force, [GST and other taxes when importing](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/cost-of-importing-goods/gst-and-other-taxes) ('How much GST do I have to pay?'); accessed 2026-11-15

### AU-05

**ABN on the import entry** (party; status: verified)

An importer that has an ABN supplies it when formally entering goods; an ABN and GST registration are needed to claim input tax credits or use GST deferral. Importers not entitled to an ABN are identified with customs owner codes.

- Readiness check: Consignee ABN (or owner code) recorded for SG-to-AU shipments.
- Corrective action: Ask the consignee for its ABN.
- Note: The synthetic data only record whether an ABN was provided, never an ABN number.
- Source: Australian Border Force, [Requirements to import goods](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/requirements) (The Australian Business Number); accessed 2026-11-15
- Source: Australian Border Force, [GST and other taxes when importing](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/cost-of-importing-goods/gst-and-other-taxes) (Departmental use of the ABN); accessed 2026-11-15

### AU-06

**Self-assessed tariff classification under the Customs Tariff Act 1995** (classification; status: partially verified)

Imported goods are classified under the Customs Tariff Act 1995; importers self-assess the classification (the Working Tariff is the online version), penalties may apply for incorrect or misleading information, and advance rulings are available through the Tariff Advice system.

- Readiness check: First 6 digits of the AU tariff code are a valid HS 2022 subheading.
- Corrective action: Correct the classification; use Tariff Advice for doubtful products.
- Note: The requirement is verified. Australia's national digits (8-digit tariff subheading plus statistical code) were not checked against an official page, so only the HS 6-digit prefix is validated.
- Source: Australian Border Force, [Requirements to import goods](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/requirements) (Tariff Classification); accessed 2026-11-15

### AU-07

**Biosecurity import conditions (BICON)** (biosecurity; status: partially verified)

Some goods are subject to biosecurity import conditions by law: some are not permitted, others need supporting documentation, treatment or a biosecurity import permit; BICON is used to find out which. Most permits are issued within 20 business days for standard (category 1) applications and within 40 for non-standard ones, after payment and a complete application.

- Readiness check: SG-to-AU lines in screened chapters (food, plants, animal products, wood, raw fibres) need a BICON check recorded in the handling note.
- Corrective action: Check BICON for the commodity and obtain the permit or treatment certificate it asks for before shipping.
- Assumptions: Biosecurity screening by HS chapter.
- Note: Requirement verified; the chapter screening list (rules/au_biosecurity_screening.csv) is this project's heuristic. It cannot see packaging such as timber pallets, nor timber goods classified outside the screened chapters (for example wooden furniture in chapter 94).
- Source: Department of Agriculture, Fisheries and Forestry (Australia), [Biosecurity Import Conditions system (BICON)](https://www.agriculture.gov.au/biosecurity-trade/import/online-services/bicon) (Importing into Australia; Biosecurity import permits); accessed 2026-11-15

### AU-08

**Prohibited and restricted goods need permission** (controlled_goods; status: verified)

No general import licence is needed, but some goods need permits regardless of value. For prohibited or restricted goods the importer must get permission from the relevant government department or agency and provide proof of it to the ABF.

- Readiness check: Manual: AU restrictions are not screened automatically; the handling note asks the consignee to confirm.
- Corrective action: Obtain the permission before shipping.
- Source: Australian Border Force, [Requirements to import goods](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/requirements) (Overview); accessed 2026-11-15
- Source: Australian Border Force, [Import declarations](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/import-declaration) (Prohibited and Restricted Goods); accessed 2026-11-15

### AU-09

**Claim FTA preference only with evidence of origin** (origin; status: verified)

Preferential tariff details should not be entered unless there is appropriate evidence that the goods meet the rules of origin, for example when the certificate or declaration of origin is not available; the origin country is still entered and the general rate applies. The Singapore-Australia FTA uses ICS preference scheme code SFTA and AANZFTA uses AANZ.

- Readiness check: If the customer asks for AU preference, a certificate or declaration of origin is on file.
- Corrective action: Obtain the origin document; otherwise the consignee declares the general rate.
- Note: On the ABF page the key sentence reads 'should not be input ... if appropriate evidence that the goods meet the rules of origin' and appears to omit a word; the next sentence (certificate or declaration of origin not available) supports the reading used here.
- Source: Australian Border Force, [Claiming Preference in the Integrated Cargo System](https://www.abf.gov.au/importing-exporting-and-manufacturing/fta/claiming-preference-in-ics) (Step five; Table 1); accessed 2026-11-15

### AU-10

**Trade description labels for certain goods** (labelling; status: verified)

Certain imported goods must carry a trade description in English that includes the country where they were made or produced (and a true description where required); goods that need a label but are not labelled may be seized.

- Readiness check: Manual: labelling is confirmed with the customer for consumer goods.
- Corrective action: Relabel before shipping.
- Source: Australian Border Force, [Requirements to import goods](https://www.abf.gov.au/importing-exporting-and-manufacturing/importing/how-to-import/requirements) (Commerce Trade Descriptions); accessed 2026-11-15

## Hold reason codes

| Code | Label | Rules | Detectable before lodgement | Corrective action |
|---|---|---|---|---|
| PERMIT_TIMING | Permit not obtained in time | SG-IMP-01, SG-EXP-01, SG-EXP-02, SG-EXP-03, AU-01 | yes | Apply for the permit before arrival or cargo lodgement; goods already imported without a permit need a voluntary disclosure |
| PARTY_UEN | Importer UEN or account issue | SG-IMP-02, SG-IMP-03, SG-IMP-04, SG-EXP-05, AU-05 | yes | Correct the importer fields (amend or cancel and re-apply) and the customer master data |
| HS_INVALID | HS code not valid | SG-IMP-05, AU-06 | yes | Correct the code in the product master and amend the permit |
| HS_QUERY | Classification query | SG-IMP-05, AU-06 | no | Provide product literature; consider a classification ruling; update the product master |
| VALUE_CIF | Customs value query | SG-IMP-07, SG-IMP-08, SG-IMP-09, SG-IMP-13, SG-IMP-24, AU-03 | yes | Recompute the CIF value and amend the permit; voluntary disclosure if the permit was already used |
| INVOICE_DATA | Invoice incomplete | SG-IMP-10, SG-IMP-23, SG-IMP-24, SG-IMP-25, AU-02 | yes | Request a corrected commercial invoice and add the field to the customer's invoice checklist |
| CA_APPROVAL | Competent-authority approval missing | SG-IMP-14, SG-IMP-15, SG-IMP-16, SG-IMP-17, SG-IMP-18, SG-IMP-19, SG-IMP-20, AU-08 | yes | Obtain the licence or approval and record its number in the handling note before re-submitting |
| ORIGIN_DOCS | Origin documents | SG-IMP-21, SG-IMP-22, SG-EXP-04, AU-09 | yes | Obtain the certificate of origin or pay the general rate and claim a refund; correct the origin field |
| DOC_MISMATCH | Documents do not agree | SG-IMP-06, SG-IMP-25, SG-IMP-28, SG-EXP-02, AU-02 | yes | Reconcile with supplier and forwarder and obtain corrected documents |
| INSPECTION | Inspection without document defect | AU-10 | no | Arrange the inspection; no document correction |
| BIOSECURITY | Biosecurity referral (Australia) | AU-07 | partly | Check BICON for the commodity and obtain the permit or treatment certificate |

## Screening tables

- `rules/sg_ca_screening.csv`: HS prefixes mapped to Singapore competent authorities, dutiable categories and prohibited goods. The mapping is this project's **screening heuristic**: Singapore Customs decides control by HS and CA product code (HS/CA Product Code Checker), which is not used here. Chapter 33 (cosmetics) is deliberately absent (SG-IMP-16).
- `rules/sg_flat_freight_insurance.csv`: the flat freight-and-insurance rates of SG-IMP-08, with the country codes this project maps to each published region.
- `rules/au_biosecurity_screening.csv`: HS chapters for which a BICON check is suggested (AU-07); a screening heuristic.
