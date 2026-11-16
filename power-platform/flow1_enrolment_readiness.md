# Flow 1: "BA - Enrolment readiness check"

**Built and tested** in the owner's Microsoft 365 account (see [README.md](README.md)). Automated cloud flow,
standard connectors only (SharePoint, Office 365 Outlook). The flow's package export is not in this repository; the
steps below are written from the build. Expressions use internal column names; `<onedrive-site-url>` stands for the
site address.

**What it does:** when a customer is added to BA_Customers, it scores four document checks (25 points each:
commercial invoice, packing list, permit ready or not needed, importer UEN present), writes the score and a status
back to the item, and, if anything is missing, emails the person who created the item.

## Steps as built

1. **Trigger** - SharePoint "When an item is created".
   - Site Address: `<onedrive-site-url>`; List Name: `BA_Customers`.
   - The trigger fires only on creation, so the "Update item" below does not start the flow again.

2. **Compose "ReadinessScore"** - the number of passed checks times 100, divided by 4:
   ```
   div(mul(add(add(add(
       if(InvoiceReady, 1, 0),
       if(PackingListReady, 1, 0)),
       if(or(not(PermitNeeded), PermitReady), 1, 0)),
       if(empty(ImporterUEN), 0, 1)), 100), 4)
   ```
   where each column name stands for the trigger output of that column, e.g. `triggerBody()?['InvoiceReady']`.

3. **Update item** (SharePoint, BA_Customers, the trigger's item)
   - ReadinessScore: the Compose output
   - EnrolmentStatus: `Validated` if the score equals 100, otherwise `Docs pending`

4. **Condition** - score is less than 100.
   - If true: **Send an email (V2)** (Office 365 Outlook) to the item's creator, listing the missing documents.
   - If false: no action.

## Test run

A customer DEMO-C025 was created with InvoiceReady = Yes, PackingListReady = No, PermitNeeded = Yes,
PermitReady = No and no ImporterUEN. Expected by the rule: 1 of 4 checks, score 25, status Docs pending. Result: the
run succeeded in 4 s, the item shows score 25 and status Docs pending, and the email was sent
([screenshot](screenshots/flow1_enrolment_check_run.png)). The creator is the owner, so the email went to the
owner's own mailbox.

## Notes and limits

- The score rule is the one the seed uses for its ReadinessScore column (`seed/make_seed.py`);
  `tests/test_power_platform.py` recomputes it for every seed row. The seed script additionally gives the status
  "Requested" to scores below 50; the flow as built uses only Validated and Docs pending. No seed row scores below 50.
- Only this one case was run. Not tested: a customer with all four checks passing (no email expected), and failure
  of the SharePoint or Outlook step.
- Not built: Try/Catch scopes with a failure notification, and re-scoring when a customer is edited later (the
  trigger covers creation only).
- It is a simplified stand-in for the 44-rule validator of the analytics part (`src/boa/validator.py`).
