# Power Apps and Power Automate part

**Status: DESIGN — build in progress, not complete and not verified end to end.** This folder is the design and
build sheet for the owner's Microsoft 365 build. Build log as reported on 2026-11-15: the three lists below exist in
the owner's account; a canvas app has an enrolment screen and a first-three-shipments screen with an action form,
saved and tried once in preview; flow 1 is partly built (trigger, readiness score, update item); flow 2 is not
started. Screenshots and exports will be added when the build is finished and checked. Nothing in this folder has been
run by this repository's tests except the seed data checks in `tests/test_power_platform.py`.

## Constraints of the target licence

- Licence: Power Apps for Office 365 (seeded with Microsoft 365), Power Automate in the same default environment.
- Data: three **Microsoft Lists** on the owner's OneDrive personal site (`<onedrive-site-url>`), reached through the
  standard **SharePoint** connector. No Dataverse.
- Connectors: standard only — SharePoint and Office 365 Outlook. No premium connectors (no HTTP, SQL Server,
  AI Builder or custom connectors).
- Email goes only to the owner (`<owner-email>`); no external recipients.
- Placeholders such as `<onedrive-site-url>` and `<owner-email>` stand for real values that are never written into
  this repository.

## Files

| File | What it is |
|---|---|
| [lists.md](lists.md) and [lists_schema.json](lists_schema.json) | The three lists: columns, SharePoint types, internal names, choice values |
| [seed/](seed) | SYNTHETIC seed rows (24 customers, 42 shipments, 26 actions) and the script that made them (`make_seed.py`, fixed seed 20261115), used with "Create list > From CSV" |
| [app.md](app.md) | Canvas app "Brokerage Onboard Assist": screens, Power Fx formulas and delegation notes |
| [flow1_enrolment_readiness.md](flow1_enrolment_readiness.md) | Build sheet: when a customer is created, score its documents, set its status, email the owner |
| [flow2_first_three_hold_alert.md](flow2_first_three_hold_alert.md) | Build sheet: when one of a customer's first three shipments is held, log an action and email the owner |

## How this part relates to the rest of the repository

The analytics in `src/`, `results/` and `powerbi/` use a larger SYNTHETIC dataset (800 customers) and a richer
readiness check with 44 cited rules. This Power Platform part is a small working prototype of the same process for
day-to-day use: an enrolment queue, a customer profile with a document checklist and handling notes, monitoring of
the first three shipments, and an action log. Its readiness score is deliberately simpler (four document checks,
25 points each) so that it can be computed inside a standard-connector flow without code.

Known differences between the demo seed and the rulebook, kept as they are because the lists are already built:

- The seed marks **Cosmetics** as `PermitNeeded = Yes` (a demo assumption in `make_seed.py`). The rulebook's
  SG-IMP-16 says cosmetic products are currently not subject to HSA licensing before importation, and the analytics
  validator does not flag HS chapter 33.
- Seed UENs are placeholders (`UEN-DEMO-nnn`) and do not match the UEN formats of SG-IMP-03, so the app only checks
  that a UEN is present; the optional format check in [app.md](app.md) would flag every seed row.

## Build order and checks

1. Create the three lists from the seed CSVs ([lists.md](lists.md)); check column types and choice values against
   `lists_schema.json`.
2. Build the app ([app.md](app.md)); in preview, open a customer, change a checklist box, save, and confirm the score
   and status update in the list.
3. Build flow 1; add a test customer with `InvoiceReady = No` and everything else ready: expect score 75, status
   "Docs pending" and one email to the owner.
4. Build flow 2; set a shipment with `ShipmentSeq = 1` to "Held": expect one new BA_ActionLog row and one email;
   edit the same shipment again: expect no second row.
5. Export the app (.msapp) and the flows (.zip) and add screenshots here; then change the status line above.
