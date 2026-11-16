# Flow 2: "BA - First three shipments hold alert"

**Built and tested** in the owner's Microsoft 365 account (see [README.md](README.md)). Automated cloud flow,
standard connectors only (SharePoint, Office 365 Outlook). The flow's package export is not in this repository; the
steps below are written from the build. `<onedrive-site-url>` stands for the site address.

**What it does:** when a shipment in BA_Shipments becomes Held and is one of the customer's first three shipments
(ShipmentSeq 1 to 3), it stamps HeldOn, adds one "Hold follow-up" row to BA_ActionLog and emails the person who
modified the item.

## Steps as built

1. **Trigger** - SharePoint "When an item is created or modified".
   - Site Address: `<onedrive-site-url>`; List Name: `BA_Shipments`.
   - Trigger condition (the flow starts only for a held shipment whose HeldOn is still empty):
     ```
     @and(equals(Status, 'Held'), empty(HeldOn))
     ```
     where `Status` and `HeldOn` stand for the trigger outputs of those columns.

2. **Condition** - Status is Held **and** ShipmentSeq is less than or equal to 3 **and** HeldOn is empty.
   - If false: no action.
   - If true: steps 3 to 5.

3. **Update item** (SharePoint, BA_Shipments, the trigger's item) - HeldOn = `utcNow()`.

4. **Create item** (SharePoint, BA_ActionLog) - ActionType "Hold follow-up", LoggedBy "Flow", and an outcome text
   that contains the hold reason.

5. **Send an email (V2)** (Office 365 Outlook) to the person who modified the item.

## Why it does not loop

Step 3 modifies the same list item that triggered the flow, which would normally trigger it again. After step 3
HeldOn is no longer empty, so the trigger condition is false and no second run starts. The flow designer still shows
its static "possible loop" warning, because it does not evaluate the trigger condition.

## Test run

Shipment DEMO-S0041 (ShipmentSeq 1, status In transit) was set to Held with HoldReason "Permit missing". Result:
exactly one run (2 s); HeldOn was stamped, one row was added to BA_ActionLog and the email was sent
([screenshot](screenshots/flow2_hold_alert_run.png)). The modifier is the owner, so the email went to the owner's
own mailbox.

## Notes and limits

- Only this one case was run. Not tested: a held shipment with ShipmentSeq above 3 (the seed has none), a shipment
  that is released and later held again (HeldOn would already be filled, so no new alert), and failure of a step.
- A shipment created as Held with HeldOn already filled in, as in the seed rows, does not start the flow; the seed
  already contains a "Hold follow-up" row for each of its held shipments.
- Not built: Try/Catch scopes with a failure notification.
