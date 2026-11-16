# Microsoft Lists

Three lists on the owner's OneDrive personal site (`<onedrive-site-url>`), filled from the SYNTHETIC seed CSVs in
[seed/](seed). The machine-readable version of this page is [lists_schema.json](lists_schema.json);
`tests/test_power_platform.py` checks that it matches the seed files.

How they were made: the lists were first created with "Create list > From CSV". That importer gave the columns
internal names such as `field_1` and made the Choice columns multi-select, so the lists were rebuilt through the
SharePoint REST API with internal column names equal to the CSV headers and single-select Choice columns.

Naming: each list's first column is SharePoint's built-in **Title** column renamed (to CustomerName, ShipmentRef or
ActionTitle). Renaming changes only the display name, so its **internal name stays `Title`**: use `Title` in
Power Automate filter queries and the display name in Power Fx. Every other column was created with an internal name
equal to its column name (no spaces), so both tools use the same name.

The lists are joined by the text key `AccountNo` rather than by Lookup columns: a CSV import creates plain columns,
and text-key filters are delegable (see [app.md](app.md)). Index `AccountNo` in BA_Shipments and BA_ActionLog
(List settings > Indexed columns) so the filters stay fast if the lists grow.

## BA_Customers (24 seed rows)

| Column | Internal name | SharePoint type | Values / note |
|---|---|---|---|
| CustomerName | Title | Single line of text | renamed Title; fictional names |
| AccountNo | AccountNo | Single line of text | key, e.g. DEMO-C001 |
| TradeLane | TradeLane | Choice | CN-SG, SG-MY, US-SG, SG-AU, DE-SG |
| Commodity | Commodity | Choice | Electronics, Auto parts, Cosmetics, Food supplements, Machinery, Apparel |
| ImporterUEN | ImporterUEN | Single line of text | placeholders UEN-DEMO-nnn |
| InvoiceReady | InvoiceReady | Yes/No | |
| PackingListReady | PackingListReady | Yes/No | |
| PermitNeeded | PermitNeeded | Yes/No | |
| PermitReady | PermitReady | Yes/No | Yes when no permit is needed |
| CoORequested | CoORequested | Yes/No | customer wants FTA preference |
| ReadinessScore | ReadinessScore | Number (0 decimals) | 25 per check: invoice, packing list, permit, UEN present |
| EnrolmentStatus | EnrolmentStatus | Choice | Requested, Docs pending, Validated, Active |
| HandlingNotes | HandlingNotes | Multiple lines of text (plain) | |
| RequestedOn | RequestedOn | Date and Time (date only) | |
| AccountExec | AccountExec | Single line of text | role codes AE-01 to AE-06 |

## BA_Shipments (42 seed rows)

| Column | Internal name | SharePoint type | Values / note |
|---|---|---|---|
| ShipmentRef | Title | Single line of text | renamed Title, e.g. DEMO-S0021 |
| AccountNo | AccountNo | Single line of text | matches BA_Customers |
| ShipmentSeq | ShipmentSeq | Number (0 decimals) | 1, 2 or 3 |
| HSCode | HSCode | Single line of text | text, keeps the dot (8471.30) |
| DeclaredValueSGD | DeclaredValueSGD | Number | |
| Incoterm | Incoterm | Choice | EXW, FCA, FOB, CIF, DAP, DDP |
| Status | Status | Choice | Booked, In transit, Held, Released (Booked is not in the seed) |
| HoldReason | HoldReason | Choice | None, Invoice missing, HS code query, Permit missing, Valuation query, Consignee details, CoO missing |
| HeldOn | HeldOn | Date and Time (date only) | |
| ReleasedOn | ReleasedOn | Date and Time (date only) | |

## BA_ActionLog (26 seed rows)

| Column | Internal name | SharePoint type | Values / note |
|---|---|---|---|
| ActionTitle | Title | Single line of text | renamed Title |
| AccountNo | AccountNo | Single line of text | |
| ShipmentRef | ShipmentRef | Single line of text | blank for account-level actions |
| ActionType | ActionType | Choice | Hold follow-up, Welcome call, Document request, Enrolment check (the last two are not in the seed; add them for the app) |
| LoggedOn | LoggedOn | Date and Time (date only) | |
| Outcome | Outcome | Multiple lines of text (plain) | |
| LoggedBy | LoggedBy | Single line of text | role or "Flow", no person names |

## Notes

- The CSVs hold `Yes`/`No` for the Yes/No columns and ISO dates (`2026-10-06`) for the date columns.
- The choice lists above include a few values the seed does not use; the column types and choice values written
  here are the intended ones and were not read back from the live lists into this repository.
- Row counts stay far below the Power Apps data row limit (500 by default), so the non-delegable formulas noted in
  [app.md](app.md) still see every row.
- The live lists differ from the seed by the test rows listed in [README.md](README.md).
