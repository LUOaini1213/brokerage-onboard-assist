# DAX measures

Generated from the TMDL files in `powerbi/BrokerageOnboard.SemanticModel/definition/tables` by `scripts/build_all.py`. Each measure has an independent pandas implementation in `src/boa/kpis.py`; `tests/test_measures.py` evaluates the DAX text below with the evaluator in `pbitest/dax.py` and compares it with the pandas value in many filter contexts, and `tests/test_kpis.py` checks the pandas functions against values worked out by hand. The DAX has not been run by the Analysis Services engine yet: the report has not been opened in Power BI Desktop.

'Value (all data)' is the pandas result with no filter, on the SYNTHETIC data; it is what a card with no slicer selection should show once the report is rendered.

## FactAction

### Actions

Logged actions.

```dax
COUNTROWS(FactAction)
```

- Format: `#,##0`; Python: `boa.kpis.actions`; value (all data): 1267

### Open Actions

Actions not closed by the snapshot date (KEEPFILTERS: a Status slicer still applies).

```dax
CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Open"))
```

- Format: `#,##0`; Python: `boa.kpis.open_actions`; value (all data): 120

### Overdue Actions

Actions closed after their due date, or still open after it.

```dax
CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[IsOverdue] = TRUE()))
```

- Format: `#,##0`; Python: `boa.kpis.overdue_actions`; value (all data): 477

### Avg Days to Close

Mean days from opening to closing, closed actions only.

```dax
CALCULATE(AVERAGE(FactAction[DaysToClose]), KEEPFILTERS(FactAction[Status] = "Closed"))
```

- Format: `0.0`; Python: `boa.kpis.avg_days_to_close`; value (all data): 4.6251

### Closed On Time %

Share of closed actions closed by their due date.

```dax
DIVIDE(
	CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Closed"), KEEPFILTERS(FactAction[IsOverdue] = FALSE())),
	CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Closed")))
```

- Format: `0.0%`; Python: `boa.kpis.closed_on_time_rate`; value (all data): 0.6888

## FactEnrolmentStage

### Enrolments at Stage

Enrolment requests that reached the stage(s) in the filter context.

```dax
COUNTROWS(FactEnrolmentStage)
```

- Format: `#,##0`; Python: `boa.kpis.enrolments_at_stage`; value (all data): 4043

### Enrolments Submitted

Enrolment requests submitted (stage 1), whatever stage is selected.

```dax
CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = 1)
```

- Format: `#,##0`; Python: `boa.kpis.enrolments_submitted`; value (all data): 800

### Profiles Created

Customers whose profile and handling note were created (stage 4).

```dax
CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = 4)
```

- Format: `#,##0`; Python: `boa.kpis.profiles_created`; value (all data): 671

### Three Shipments Completed

Customers whose first three shipments were all released (stage 6).

```dax
CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = 6)
```

- Format: `#,##0`; Python: `boa.kpis.three_shipments_completed`; value (all data): 519

### Stage Conversion %

Share of submitted enrolments that reached the stage.

```dax
DIVIDE([Enrolments at Stage], [Enrolments Submitted])
```

- Format: `0.0%`; Python: `boa.kpis.stage_conversion`; value (all data): 5.0537

### Step Conversion %

Share of the previous stage that reached this stage; BLANK for the first stage or no single stage.

```dax
VAR s = SELECTEDVALUE(DimStage[StageOrder])
VAR prev = CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = s - 1)
RETURN IF(ISBLANK(s) || s = 1, BLANK(), DIVIDE([Enrolments at Stage], prev))
```

- Format: `0.0%`; Python: `boa.kpis.step_conversion`; value (all data): BLANK

### Median Days to Stage

Median days from submission to reaching the stage.

```dax
MEDIAN(FactEnrolmentStage[DaysFromSubmission])
```

- Format: `0.0`; Python: `boa.kpis.median_days_to_stage`; value (all data): 9.0000

## FactHold

### Holds

Hold events.

```dax
COUNTROWS(FactHold)
```

- Format: `#,##0`; Python: `boa.kpis.holds`; value (all data): 551

### Hold Share %

Share of all holds (any reason) in the other filters.

```dax
DIVIDE([Holds], CALCULATE([Holds], REMOVEFILTERS(DimReason)))
```

- Format: `0.0%`; Python: `boa.kpis.hold_share`; value (all data): 1.0000

### Hold Pareto Cumulative %

Cumulative share of holds up to this reason, reasons ordered by holds (descending) then code.

```dax
VAR curCode = SELECTEDVALUE(DimReason[ReasonCode])
VAR cur = [Holds]
VAR total = CALCULATE([Holds], REMOVEFILTERS(DimReason))
VAR cum = SUMX(FILTER(ALL(DimReason), VAR n = [Holds] RETURN n > cur || (n = cur && DimReason[ReasonCode] <= curCode)), [Holds])
RETURN IF(ISBLANK(curCode) || ISBLANK(cur), BLANK(), DIVIDE(cum, total))
```

- Format: `0.0%`; Python: `boa.kpis.hold_pareto_cumulative`; value (all data): BLANK

### Median Hours to Release

Median hours from hold to release (open holds excluded).

```dax
MEDIAN(FactHold[HoursToRelease])
```

- Format: `0.0`; Python: `boa.kpis.median_hours_to_release`; value (all data): 19.2000

### P90 Hours to Release

90th percentile of hours from hold to release.

```dax
PERCENTILE.INC(FactHold[HoursToRelease], 0.9)
```

- Format: `0.0`; Python: `boa.kpis.p90_hours_to_release`; value (all data): 79.2000

## FactShipment

### First-3 Shipments

Shipments among customers' first three.

```dax
COUNTROWS(FactShipment)
```

- Format: `#,##0`; Python: `boa.kpis.first3_shipments`; value (all data): 1714

### Held Shipments

First-three shipments with at least one hold (KEEPFILTERS: a slicer on WasHeld still applies).

```dax
CALCULATE(COUNTROWS(FactShipment), KEEPFILTERS(FactShipment[WasHeld] = TRUE()))
```

- Format: `#,##0`; Python: `boa.kpis.held_shipments`; value (all data): 485

### First-3 Hold Rate %

Share of first-three shipments with at least one hold.

```dax
DIVIDE([Held Shipments], [First-3 Shipments])
```

- Format: `0.0%`; Python: `boa.kpis.first3_hold_rate`; value (all data): 0.2830

### Customers Shipping

Customers with at least one shipment in the filter context.

```dax
DISTINCTCOUNT(FactShipment[CustomerId])
```

- Format: `#,##0`; Python: `boa.kpis.customers_shipping`; value (all data): 623

### Customers With a Hold

Customers with at least one held shipment among their first three.

```dax
CALCULATE(DISTINCTCOUNT(FactShipment[CustomerId]), KEEPFILTERS(FactShipment[WasHeld] = TRUE()))
```

- Format: `#,##0`; Python: `boa.kpis.customers_with_hold`; value (all data): 371

### Customers With a Hold %

Share of shipping customers with at least one held first-three shipment.

```dax
DIVIDE([Customers With a Hold], [Customers Shipping])
```

- Format: `0.0%`; Python: `boa.kpis.customers_with_hold_rate`; value (all data): 0.5955

### Median Clearance Hours

Median hours from presentation to release, including time on hold.

```dax
MEDIAN(FactShipment[ClearanceHours])
```

- Format: `0.0`; Python: `boa.kpis.median_clearance_hours`; value (all data): 16.6000

### P90 Clearance Hours

90th percentile of clearance hours.

```dax
PERCENTILE.INC(FactShipment[ClearanceHours], 0.9)
```

- Format: `0.0`; Python: `boa.kpis.p90_clearance_hours`; value (all data): 54.3800

### Avg Readiness Score

Mean readiness score (0-100) from the pre-lodgement check.

```dax
AVERAGE(FactShipment[ReadinessScore])
```

- Format: `0.0`; Python: `boa.kpis.avg_readiness_score`; value (all data): 86.2952
