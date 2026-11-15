# Flow 1: "Enrolment readiness check"

DESIGN — build in progress (trigger, score and update item reported built; email and error handling not yet).
Automated cloud flow, standard connectors only (SharePoint, Office 365 Outlook).

**What it does:** when a customer is added to BA_Customers, it scores the four document checks (25 points each:
commercial invoice, packing list, permit or licence if needed, importer UEN present), sets EnrolmentStatus from the
score, writes both back to the item and emails the owner a summary with what is missing.

The score is the same rule as the app's `lblScore` ([app.md](app.md)) and as the `ReadinessScore` column of the
seed (`seed/make_seed.py`): 100 -> Validated, 50 to 75 -> Docs pending, below 50 -> Requested. It is a simplified
stand-in for the 44-rule validator of the analytics part.

## Build sheet

1. **Trigger** - SharePoint "When an item is created".
   - Site Address: `<onedrive-site-url>` (choose "Enter custom value" if the personal site is not listed)
   - List Name: `BA_Customers`
   - Because the trigger fires only on creation, the "Update item" below cannot re-trigger the flow.

2. **Scope "Try"** - put steps 3 to 6 inside it.

3. **Compose "Score"** - Inputs (expression):
   ```
   add(add(add(
       if(equals(triggerBody()?['InvoiceReady'], true), 25, 0),
       if(equals(triggerBody()?['PackingListReady'], true), 25, 0)),
       if(or(equals(triggerBody()?['PermitReady'], true), equals(triggerBody()?['PermitNeeded'], false)), 25, 0)),
       if(empty(trim(coalesce(triggerBody()?['ImporterUEN'], ''))), 0, 25))
   ```

4. **Compose "Status"** - Inputs (expression):
   ```
   if(equals(outputs('Score'), 100), 'Validated', if(greaterOrEquals(outputs('Score'), 50), 'Docs pending', 'Requested'))
   ```

5. **Compose "Missing"** - Inputs (expression):
   ```
   concat(
       if(equals(triggerBody()?['InvoiceReady'], true), '', 'Commercial invoice not received. '),
       if(equals(triggerBody()?['PackingListReady'], true), '', 'Packing list not received. '),
       if(or(equals(triggerBody()?['PermitReady'], true), equals(triggerBody()?['PermitNeeded'], false)), '', 'Permit or licence not ready (controlled goods). '),
       if(empty(trim(coalesce(triggerBody()?['ImporterUEN'], ''))), 'Importer UEN missing. ', ''),
       if(equals(triggerBody()?['CoORequested'], true), 'Customer wants FTA preference: certificate of origin needed. ', ''))
   ```

6. **Update item** (SharePoint)
   - Site Address `<onedrive-site-url>`, List Name `BA_Customers`
   - Id: `triggerBody()?['ID']`
   - CustomerName (the renamed Title, required by the action): `triggerBody()?['Title']`
   - ReadinessScore: `outputs('Score')`
   - EnrolmentStatus Value: `outputs('Status')`
   - Retry policy: leave the default (exponential).

7. **Send an email (V2)** (Office 365 Outlook) - inside "Try", after Update item
   - To: `<owner-email>` (the owner only)
   - Subject: `[Onboarding] @{triggerBody()?['Title']} (@{triggerBody()?['AccountNo']}): @{outputs('Status')}, score @{outputs('Score')}`
   - Body: `Lane @{triggerBody()?['TradeLane']?['Value']}, commodity @{triggerBody()?['Commodity']?['Value']}. Missing: @{outputs('Missing')}`

8. **Scope "Catch"** - after "Try"; Settings > Run after: "has failed" and "has timed out" only.
   - **Send an email (V2)** to `<owner-email>`, subject `[Onboarding] readiness check failed for @{triggerBody()?['AccountNo']}`,
     body `Run @{workflow()?['run']?['name']} of flow @{workflow()?['name']} failed; see the flow's run history.`

## Test (build-order step 3 in [README.md](README.md))

Create an item with InvoiceReady = No, PackingListReady = Yes, PermitNeeded = No, PermitReady = Yes and a UEN:
expect ReadinessScore 75, EnrolmentStatus "Docs pending", one email whose body lists "Commercial invoice not
received". Then create one with everything ready: expect 100 and "Validated".

## Notes

- Yes/No columns arrive in the trigger output as `true`/`false`; choice columns as records with a `Value` field.
- Customers that are later edited in the app get their score from the app's Save button, not from this flow
  (the trigger only covers creation).
