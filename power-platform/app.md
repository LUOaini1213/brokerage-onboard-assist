# Canvas app "Brokerage Onboard Assist"

**Built and tested** in the owner's Microsoft 365 account; not shared with other users (see
[README.md](README.md)). The app's package export is in [export/](export), and the exact formulas of the built app
can be read in [export/src/ShipmentsScreen.pa.yaml](export/src/ShipmentsScreen.pa.yaml) and
[export/src/MainScreen1.pa.yaml](export/src/MainScreen1.pa.yaml).

## The app as built

Data source: the three lists in [lists.md](lists.md) through the standard SharePoint connector.

- **Screen 1** was generated from BA_Customers ("Create an app" from the list): a searchable list of customers and a
  profile form that includes the handling notes. The header was renamed. A "First 3 shipments" button is shown only
  for customers whose EnrolmentStatus is Validated or Active.
- **Screen 2, "First three shipments"**, was added as pasted YAML:
  - the selected customer's shipments, sorted by ShipmentSeq, with Held rows highlighted and the hold reason and
    dates shown;
  - an action form: an ActionType combo box filled from `Choices`, an outcome text box and a button that Patches a
    row into BA_ActionLog with LoggedBy "App";
  - the customer's action log below the form.
- Test: in preview, one action row was written to BA_ActionLog
  ([screenshot](screenshots/app_first_three_shipments.png)).

## Reference formulas (design sheet)

The rest of this page is the design sheet written before the build: Power Fx for this data model on a SharePoint data
source, with delegation notes. It is **not a listing of the built app**. The built app covers the queue with search,
the profile form, the first-three-shipments gallery with hold highlighting, the action form and the action history
in two screens instead of the four below, and writes LoggedBy "App" where the sheet says "Agent". The status
drop-down, the score preview and checklist gallery, the Save button that recomputes the score, and the portfolio
hold-rate label are in this sheet only and were not built.

In Power Fx a renamed Title column is used by its display name (CustomerName, ShipmentRef, ActionTitle); choice
columns are records, so compare `.Value`.

## 1. scrQueue: enrolment queue

| Control | Property | Formula |
|---|---|---|
| drpStatus | Items | `["All", "Requested", "Docs pending", "Validated", "Active"]` |
| txtSearch | (text input) | |
| galQueue | Items | see below (D) |
| galQueue | OnSelect | `Navigate(scrProfile, ScreenTransition.None, {locCustomer: ThisItem})` |
| lblScore (in gallery) | Text | `Text(ThisItem.ReadinessScore) & " / 100"` |
| icoScore (in gallery) | Color | `If(ThisItem.ReadinessScore = 100, Color.Green, ThisItem.ReadinessScore >= 50, Color.DarkOrange, Color.Red)` |
| lblPending | Text | `CountRows(Filter(BA_Customers, EnrolmentStatus.Value = "Docs pending")) & " waiting for documents"` (ND) |

```powerfx
// galQueue.Items
SortByColumns(
    Filter(
        BA_Customers,
        (drpStatus.Selected.Value = "All" || EnrolmentStatus.Value = drpStatus.Selected.Value)
            && StartsWith(CustomerName, txtSearch.Text)
    ),
    "RequestedOn",
    SortOrder.Descending
)
```

## 2. scrProfile: customer profile, checklist and handling notes

`frmCustomer` is an edit form on BA_Customers with `Item = locCustomer`. Rename the generated data-card controls so
the formulas below read: `tglInvoice`, `tglPacking`, `tglPermitNeeded`, `tglPermitReady`, `tglCoO` (Yes/No columns)
and `txtUEN` (ImporterUEN).

| Control | Property | Formula |
|---|---|---|
| lblScore | Text | see below: 25 points per check, the same rule as flow 1 |
| lblStatusPreview | Text | `With({s: Value(lblScore.Text)}, If(s = 100, "Validated", s >= 50, "Docs pending", "Requested"))` |
| lblUENWarn | Visible | `!IsBlank(txtUEN.Text) && !IsMatch(txtUEN.Text, "^(\d{8}[A-Z]\|\d{9}[A-Z]\|F(000\| {3})\d{5}[A-Z]\|[ST]\d{2}[A-Z]{2}\d{4}[A-Z])$")` (optional; the seed's placeholder UENs all fail it) |
| galChecklist | Items | see below |
| btnSave | OnSelect | see below |
| btnShipments | OnSelect | `Navigate(scrShipments, ScreenTransition.None, {locCustomer: locCustomer})` |

```powerfx
// lblScore.Text
25 * (
    If(tglInvoice.Value, 1, 0)
    + If(tglPacking.Value, 1, 0)
    + If(tglPermitReady.Value || !tglPermitNeeded.Value, 1, 0)
    + If(IsBlank(Trim(txtUEN.Text)), 0, 1)
)

// galChecklist.Items: what each check stands for in the rulebook (docs/rulebook.md)
Table(
    {Check: "Commercial invoice with number, date, currency, Incoterm and line values", Rule: "SG-IMP-23, SG-IMP-24", Done: tglInvoice.Value},
    {Check: "Packing list that agrees with the invoice and the BL/AWB", Rule: "SG-IMP-28", Done: tglPacking.Value},
    {Check: "Competent-authority licence or permit, if the goods are controlled", Rule: "SG-IMP-14", Done: tglPermitReady.Value || !tglPermitNeeded.Value},
    {Check: "Importer UEN on file and Customs account activated", Rule: "SG-IMP-02, SG-IMP-03", Done: !IsBlank(Trim(txtUEN.Text))},
    {Check: "Certificate of origin before any FTA preference claim", Rule: "SG-IMP-22, AU-09", Done: !tglCoO.Value}
)

// btnSave.OnSelect: write the form, the score and the status; never downgrade an Active customer
Patch(
    BA_Customers,
    locCustomer,
    frmCustomer.Updates,
    {
        ReadinessScore: Value(lblScore.Text),
        EnrolmentStatus: {Value: If(locCustomer.EnrolmentStatus.Value = "Active", "Active", lblStatusPreview.Text)}
    }
);
Notify("Customer saved", NotificationType.Success)
```

## 3. scrShipments: first three shipments

| Control | Property | Formula |
|---|---|---|
| galShips | Items | see below (D) |
| galShips | TemplateFill | `If(ThisItem.Status.Value = "Held", RGBA(253, 231, 233, 1), RGBA(0, 0, 0, 0))` (hold highlighting) |
| lblHold (in gallery) | Text | `If(ThisItem.Status.Value = "Held", "Held: " & ThisItem.HoldReason.Value & " since " & Text(ThisItem.HeldOn, "yyyy-mm-dd"), ThisItem.Status.Value)` |
| lblSummary | Text | `CountRows(Filter(galShips.AllItems, Status.Value = "Held")) & " of " & CountRows(galShips.AllItems) & " first-three shipments on hold"` (local: at most 3 rows) |
| galPortfolio | Items | `Filter(BA_Shipments, Status.Value = "Held" && ShipmentSeq <= 3)` (D) |
| lblHoldRate | Text | `Text(CountRows(Filter(BA_Shipments, ShipmentSeq <= 3 && Status.Value = "Held")) / CountRows(Filter(BA_Shipments, ShipmentSeq <= 3)), "0%")` (ND) |
| btnLog | OnSelect | `Navigate(scrLogAction, ScreenTransition.None, {locCustomer: locCustomer, locShipment: galShips.Selected})` |

```powerfx
// galShips.Items
SortByColumns(
    Filter(BA_Shipments, AccountNo = locCustomer.AccountNo && ShipmentSeq <= 3),
    "ShipmentSeq",
    SortOrder.Ascending
)
```

## 4. scrLogAction: log an action

| Control | Property | Formula |
|---|---|---|
| drpActionType | Items | `["Hold follow-up", "Document request", "Welcome call", "Enrolment check"]` |
| txtOutcome | (multi-line text input) | |
| btnSubmit | OnSelect | see below |
| galHistory | Items | `SortByColumns(Filter(BA_ActionLog, AccountNo = locCustomer.AccountNo), "LoggedOn", SortOrder.Descending)` (D) |

```powerfx
// btnSubmit.OnSelect
Patch(
    BA_ActionLog,
    Defaults(BA_ActionLog),
    {
        ActionTitle: drpActionType.Selected.Value & " " & Coalesce(locShipment.ShipmentRef, locCustomer.AccountNo),
        AccountNo: locCustomer.AccountNo,
        ShipmentRef: Coalesce(locShipment.ShipmentRef, ""),
        ActionType: {Value: drpActionType.Selected.Value},
        LoggedOn: Today(),
        Outcome: txtOutcome.Text,
        LoggedBy: "Agent"
    }
);
Notify("Action logged", NotificationType.Success);
Back()
```

## Delegation

(D) = delegable to SharePoint, (ND) = not delegable. Based on Microsoft Learn, "Connect to SharePoint from a canvas app",
section "Power Apps delegable functions and operations for SharePoint"
(<https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/connections/connection-sharepoint-online>, accessed
2026-11-15): `Filter` and `=` delegate for every column type, comparisons such as `<=` for Number and DateTime but not
Text or Yes/No, `StartsWith` for Text, `Sort`/`SortByColumns` for Number, Text, Yes/No and DateTime (not for Choice),
And/Or delegate and Not does not. Choice columns delegate through their `.Value` subfield. `CountRows` does not appear
in that table, so it is treated as not delegable.

| Formula | Delegable? | Why it is safe |
|---|---|---|
| galQueue.Items | D (Choice `.Value` =, StartsWith on Title text, Or, SortByColumns on a date) | If Studio still shows a warning, the list has 24 rows |
| lblPending, lblHoldRate (CountRows) | ND | Power Apps fetches up to the app's data row limit (500 by default, adjustable up to 10,000 in Settings) and counts locally; the lists have 24, 42 and 26 rows and the seed design keeps every list at 300 rows or fewer, so the counts include every row |
| galShips.Items, galPortfolio.Items, galHistory.Items | D (= on text, <= on a number, And, sort on a number or date) | |
| lblSummary | local | counts items already loaded in the gallery (3 at most) |
| lblScore, lblStatusPreview, lblUENWarn, galChecklist | local | read control values only, no data source |

Not used on purpose: `Not(...)` and `IsBlank(column)` inside `Filter` (neither delegates; `column = Blank()` is the
delegable alternative), and sorting by a Choice column.
