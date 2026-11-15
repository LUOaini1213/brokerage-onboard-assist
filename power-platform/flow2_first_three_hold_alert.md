# Flow 2: "First-three-shipment hold alert"

DESIGN — not started (see [README.md](README.md)). Automated cloud flow, standard connectors only (SharePoint,
Office 365 Outlook).

**What it does:** when a shipment in BA_Shipments is Held and is one of the customer's first three shipments
(ShipmentSeq 1 to 3), it adds one "Hold follow-up" row to BA_ActionLog and emails the owner. It writes only to
BA_ActionLog, so it cannot re-trigger itself; a duplicate check keeps it to one row per held shipment when the
shipment is edited again.

## Build sheet

1. **Trigger** - SharePoint "When an item is created or modified".
   - Site Address: `<onedrive-site-url>`; List Name: `BA_Shipments`
   - Settings > Trigger conditions (one line; the flow only starts for held first-three shipments):
     ```
     @and(equals(triggerBody()?['Status']?['Value'], 'Held'), lessOrEquals(int(triggerBody()?['ShipmentSeq']), 3))
     ```

2. **Scope "Try"** - put steps 3 to 7 inside it.

3. **Get items** (SharePoint) "Existing action"
   - List Name: `BA_ActionLog`
   - Filter Query: `ShipmentRef eq '@{triggerBody()?['Title']}' and ActionType eq 'Hold follow-up'`
   - Top Count: `1`

4. **Condition** "No action logged yet": `length(body('Existing_action')?['value'])` is equal to `0`.
   - If no: do nothing (an action already exists for this shipment).
   - If yes: steps 5 to 7.

5. **Create item** (SharePoint) - List Name `BA_ActionLog`
   - ActionTitle (renamed Title): `Hold follow-up @{triggerBody()?['Title']}`
   - AccountNo: `triggerBody()?['AccountNo']`
   - ShipmentRef: `triggerBody()?['Title']`
   - ActionType Value: `Hold follow-up`
   - LoggedOn: `formatDateTime(utcNow(), 'yyyy-MM-dd')`
   - Outcome: `Reason: @{triggerBody()?['HoldReason']?['Value']}. Logged automatically; follow up with the customer.`
   - LoggedBy: `Flow`

6. **Get items** (SharePoint) "Customer" - List Name `BA_Customers`; Filter Query
   `AccountNo eq '@{triggerBody()?['AccountNo']}'`; Top Count `1`.

7. **Send an email (V2)** (Office 365 Outlook)
   - To: `<owner-email>` (the owner only)
   - Subject: `[First 3] Hold on shipment @{triggerBody()?['ShipmentSeq']} of 3 for @{triggerBody()?['AccountNo']}: @{triggerBody()?['HoldReason']?['Value']}`
   - Body: `@{first(body('Customer')?['value'])?['Title']} - shipment @{triggerBody()?['Title']}, HS @{triggerBody()?['HSCode']}, @{triggerBody()?['Incoterm']?['Value']}, held on @{triggerBody()?['HeldOn']}. Handling notes: @{first(body('Customer')?['value'])?['HandlingNotes']}`

8. **Scope "Catch"** - after "Try"; Run after "has failed" and "has timed out".
   - **Send an email (V2)** to `<owner-email>`: subject `[First 3] hold alert failed for @{triggerBody()?['Title']}`,
     body `Run @{workflow()?['run']?['name']} failed; see the flow's run history.`

## Test (build-order step 4 in [README.md](README.md))

Set a shipment with ShipmentSeq = 1 to Status "Held", HoldReason "Invoice missing": expect one new BA_ActionLog row
(ActionType "Hold follow-up", LoggedBy "Flow") and one email. Edit the same shipment again: the trigger fires but the
condition finds the existing row, so no second row or email. Set a shipment with ShipmentSeq = 3 to "Released": the
trigger condition stops the run.

## Notes

- Filter queries use internal names: the renamed Title column is `Title`.
- The seed already contains a "Hold follow-up" row for every held seed shipment, so for seed data the condition is
  false until a new shipment is set to Held.
