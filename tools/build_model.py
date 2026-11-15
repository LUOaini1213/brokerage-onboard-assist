"""Write the semantic model (powerbi/BrokerageOnboard.SemanticModel) as TMDL from the compact spec below.

Same layout and conventions as the author's sg-transport-powerbi project (definition.pbism 4.2, TMDL with tabs,
one file per table, a DataFolder parameter, CSV partitions through Csv.Document). The files are committed; this
script is how they were produced, and tests/test_model.py checks that re-running it reproduces them byte for byte.
Edit the spec here, not the TMDL, until the model has been opened and saved in Power BI Desktop once.

    python tools/build_model.py
"""
import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi" / "BrokerageOnboard.SemanticModel"
NS = uuid.UUID("6f1c2b0e-1d55-4f0a-9a5e-0b7e7c3f4a21")
M_TYPE = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type date",
          "boolean": "type logical"}
BOOL_FMT = '"""TRUE"";""TRUE"";""FALSE"""'


def col(name, data_type, hidden=False, key=False, fmt=None, sort_by=None, doc=None):
    return {"name": name, "type": data_type, "hidden": hidden, "key": key, "fmt": fmt, "sort_by": sort_by, "doc": doc}


def msr(name, expression, fmt, doc):
    return {"name": name, "expr": expression.strip("\n"), "fmt": fmt, "doc": doc}


TABLES = [
    {"name": "DimDate", "csv": "dim_date.csv", "category": "Time",
     "doc": "Every day from 1 March to 30 November 2026. Marked as the date table.",
     "columns": [col("Date", "dateTime", key=True, fmt="yyyy-mm-dd"), col("Year", "int64", fmt="0"),
                 col("MonthNumber", "int64", hidden=True, fmt="0"), col("MonthName", "string", sort_by="MonthNumber"),
                 col("YearMonth", "string", doc="Calendar month as text, e.g. 2026-05."),
                 col("IsoWeekday", "int64", hidden=True, fmt="0"), col("DayName", "string", sort_by="IsoWeekday")],
     "measures": []},
    {"name": "DimCustomer", "csv": "dim_customer.csv",
     "doc": "SYNTHETIC new customers (fictional names and UENs; see config/synth_assumptions.json).",
     "columns": [col("CustomerId", "string", key=True), col("CustomerName", "string"), col("Segment", "string"),
                 col("PrimaryLaneId", "string"), col("TradeDirection", "string"), col("CommodityGroup", "string")],
     "measures": []},
    {"name": "DimLane", "csv": "dim_lane.csv",
     "doc": "Trade lanes: country pair and transport mode (ILLUSTRATIVE).",
     "columns": [col("LaneId", "string", key=True), col("LaneName", "string"), col("Origin", "string"),
                 col("Destination", "string"), col("Mode", "string"), col("Direction", "string")],
     "measures": []},
    {"name": "DimReason", "csv": "dim_reason.csv",
     "doc": "Hold reason codes of the rulebook (rules/hold_reasons.csv).",
     "columns": [col("ReasonCode", "string", key=True), col("ReasonLabel", "string"), col("Category", "string"),
                 col("DetectableBeforeLodgement", "string")],
     "measures": []},
    {"name": "DimStage", "csv": "dim_stage.csv",
     "doc": "Onboarding funnel stages, in order.",
     "columns": [col("StageOrder", "int64", key=True, fmt="0"), col("Stage", "string", sort_by="StageOrder")],
     "measures": []},
    {"name": "FactEnrolmentStage", "csv": "fact_enrolment_stage.csv",
     "doc": "One row per SYNTHETIC enrolment request and funnel stage it reached, with the date reached.",
     "columns": [col("EnrolmentId", "string"), col("CustomerId", "string", hidden=True),
                 col("StageOrder", "int64", hidden=True, fmt="0"),
                 col("ReachedDate", "dateTime", hidden=True, fmt="yyyy-mm-dd"),
                 col("DaysFromSubmission", "int64", hidden=True, fmt="0")],
     "measures": [
         msr("Enrolments at Stage", "COUNTROWS(FactEnrolmentStage)", "#,##0",
             "Enrolment requests that reached the stage(s) in the filter context."),
         msr("Enrolments Submitted",
             "CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = 1)", "#,##0",
             "Enrolment requests submitted (stage 1), whatever stage is selected."),
         msr("Profiles Created",
             "CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = 4)", "#,##0",
             "Customers whose profile and handling note were created (stage 4)."),
         msr("Three Shipments Completed",
             "CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = 6)", "#,##0",
             "Customers whose first three shipments were all released (stage 6)."),
         msr("Stage Conversion %", "DIVIDE([Enrolments at Stage], [Enrolments Submitted])", "0.0%",
             "Share of submitted enrolments that reached the stage."),
         msr("Step Conversion %", """
VAR s = SELECTEDVALUE(DimStage[StageOrder])
VAR prev = CALCULATE([Enrolments at Stage], REMOVEFILTERS(DimStage), DimStage[StageOrder] = s - 1)
RETURN IF(ISBLANK(s) || s = 1, BLANK(), DIVIDE([Enrolments at Stage], prev))
""", "0.0%", "Share of the previous stage that reached this stage; BLANK for the first stage or no single stage."),
         msr("Median Days to Stage", "MEDIAN(FactEnrolmentStage[DaysFromSubmission])", "0.0",
             "Median days from submission to reaching the stage."),
     ]},
    {"name": "FactShipment", "csv": "fact_shipment.csv",
     "doc": "Each SYNTHETIC customer's first three shipments, with clearance hours, hold flag and readiness score.",
     "columns": [col("ShipmentId", "string"), col("CustomerId", "string", hidden=True),
                 col("ShipmentSeq", "int64", fmt="0", doc="1, 2 or 3: position among the customer's first three shipments."),
                 col("LaneId", "string", hidden=True), col("ArrivalDate", "dateTime", hidden=True, fmt="yyyy-mm-dd"),
                 col("ClearanceHours", "double", hidden=True, fmt="0.0"),
                 col("WasHeld", "boolean", fmt=BOOL_FMT), col("HoldCount", "int64", hidden=True, fmt="0"),
                 col("ReadinessScore", "int64", hidden=True, fmt="0"),
                 col("ReadinessBand", "string", doc="Ready, Needs attention or Not ready, from the readiness check.")],
     "measures": [
         msr("First-3 Shipments", "COUNTROWS(FactShipment)", "#,##0", "Shipments among customers' first three."),
         msr("Held Shipments", "CALCULATE(COUNTROWS(FactShipment), KEEPFILTERS(FactShipment[WasHeld] = TRUE()))",
             "#,##0", "First-three shipments with at least one hold (KEEPFILTERS: a slicer on WasHeld still applies)."),
         msr("First-3 Hold Rate %", "DIVIDE([Held Shipments], [First-3 Shipments])", "0.0%",
             "Share of first-three shipments with at least one hold."),
         msr("Customers Shipping", "DISTINCTCOUNT(FactShipment[CustomerId])", "#,##0",
             "Customers with at least one shipment in the filter context."),
         msr("Customers With a Hold",
             "CALCULATE(DISTINCTCOUNT(FactShipment[CustomerId]), KEEPFILTERS(FactShipment[WasHeld] = TRUE()))", "#,##0",
             "Customers with at least one held shipment among their first three."),
         msr("Customers With a Hold %", "DIVIDE([Customers With a Hold], [Customers Shipping])", "0.0%",
             "Share of shipping customers with at least one held first-three shipment."),
         msr("Median Clearance Hours", "MEDIAN(FactShipment[ClearanceHours])", "0.0",
             "Median hours from presentation to release, including time on hold."),
         msr("P90 Clearance Hours", "PERCENTILE.INC(FactShipment[ClearanceHours], 0.9)", "0.0",
             "90th percentile of clearance hours."),
         msr("Avg Readiness Score", "AVERAGE(FactShipment[ReadinessScore])", "0.0",
             "Mean readiness score (0-100) from the pre-lodgement check."),
     ]},
    {"name": "FactHold", "csv": "fact_hold.csv",
     "doc": "SYNTHETIC holds on first-three shipments: reason code, hold date, hours to release and the free-text note.",
     "columns": [col("HoldId", "string"), col("ShipmentId", "string"), col("CustomerId", "string", hidden=True),
                 col("LaneId", "string", hidden=True), col("ReasonCode", "string", hidden=True),
                 col("HoldDate", "dateTime", hidden=True, fmt="yyyy-mm-dd"),
                 col("HoursToRelease", "double", hidden=True, fmt="0.0"), col("Note", "string")],
     "measures": [
         msr("Holds", "COUNTROWS(FactHold)", "#,##0", "Hold events."),
         msr("Hold Share %", "DIVIDE([Holds], CALCULATE([Holds], REMOVEFILTERS(DimReason)))", "0.0%",
             "Share of all holds (any reason) in the other filters."),
         msr("Hold Pareto Cumulative %", """
VAR curCode = SELECTEDVALUE(DimReason[ReasonCode])
VAR cur = [Holds]
VAR total = CALCULATE([Holds], REMOVEFILTERS(DimReason))
VAR cum = SUMX(FILTER(ALL(DimReason), VAR n = [Holds] RETURN n > cur || (n = cur && DimReason[ReasonCode] <= curCode)), [Holds])
RETURN IF(ISBLANK(curCode) || ISBLANK(cur), BLANK(), DIVIDE(cum, total))
""", "0.0%", "Cumulative share of holds up to this reason, reasons ordered by holds (descending) then code."),
         msr("Median Hours to Release", "MEDIAN(FactHold[HoursToRelease])", "0.0",
             "Median hours from hold to release (open holds excluded)."),
         msr("P90 Hours to Release", "PERCENTILE.INC(FactHold[HoursToRelease], 0.9)", "0.0",
             "90th percentile of hours from hold to release."),
     ]},
    {"name": "FactAction", "csv": "fact_action.csv",
     "doc": "SYNTHETIC action log: corrective actions for holds and enrolment findings, with due and closing dates.",
     "columns": [col("ActionId", "string"), col("CustomerId", "string", hidden=True), col("ShipmentId", "string"),
                 col("HoldId", "string"), col("Source", "string"), col("ReasonCode", "string", hidden=True),
                 col("ActionType", "string"), col("RuleRef", "string"), col("OwnerRole", "string"),
                 col("OpenedDate", "dateTime", fmt="yyyy-mm-dd"), col("DueDate", "dateTime", fmt="yyyy-mm-dd"),
                 col("ClosedDate", "dateTime", fmt="yyyy-mm-dd"), col("Status", "string"),
                 col("DaysToClose", "int64", hidden=True, fmt="0"), col("IsOverdue", "boolean", fmt=BOOL_FMT)],
     "measures": [
         msr("Actions", "COUNTROWS(FactAction)", "#,##0", "Logged actions."),
         msr("Open Actions", 'CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Open"))', "#,##0",
             "Actions not closed by the snapshot date (KEEPFILTERS: a Status slicer still applies)."),
         msr("Overdue Actions", "CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[IsOverdue] = TRUE()))",
             "#,##0", "Actions closed after their due date, or still open after it."),
         msr("Avg Days to Close",
             'CALCULATE(AVERAGE(FactAction[DaysToClose]), KEEPFILTERS(FactAction[Status] = "Closed"))', "0.0",
             "Mean days from opening to closing, closed actions only."),
         msr("Closed On Time %", """
DIVIDE(
	CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Closed"), KEEPFILTERS(FactAction[IsOverdue] = FALSE())),
	CALCULATE(COUNTROWS(FactAction), KEEPFILTERS(FactAction[Status] = "Closed")))
""", "0.0%", "Share of closed actions closed by their due date."),
     ]},
]

RELATIONSHIPS = [
    ("FactEnrolmentStage", "StageOrder", "DimStage", "StageOrder"),
    ("FactEnrolmentStage", "CustomerId", "DimCustomer", "CustomerId"),
    ("FactEnrolmentStage", "ReachedDate", "DimDate", "Date"),
    ("FactShipment", "CustomerId", "DimCustomer", "CustomerId"),
    ("FactShipment", "LaneId", "DimLane", "LaneId"),
    ("FactShipment", "ArrivalDate", "DimDate", "Date"),
    ("FactHold", "ReasonCode", "DimReason", "ReasonCode"),
    ("FactHold", "LaneId", "DimLane", "LaneId"),
    ("FactHold", "CustomerId", "DimCustomer", "CustomerId"),
    ("FactHold", "HoldDate", "DimDate", "Date"),
    ("FactAction", "ReasonCode", "DimReason", "ReasonCode"),
    ("FactAction", "CustomerId", "DimCustomer", "CustomerId"),
    ("FactAction", "OpenedDate", "DimDate", "Date"),
]

DATA_FOLDER_DEFAULT = "https://raw.githubusercontent.com/LUOaini1213/brokerage-onboard-assist/main/powerbi/data/"


def q(name):
    return "'" + name.replace("'", "''") + "'"


def table_tmdl(t):
    lines = [f"/// {t['doc']}", f"table {t['name']}"]
    if t.get("category"):
        lines.append(f"\tdataCategory: {t['category']}")
    lines.append("")
    for m in t["measures"]:
        lines.append(f"\t/// {m['doc']}")
        if "\n" in m["expr"]:
            lines.append(f"\tmeasure {q(m['name'])} =")
            for ln in m["expr"].split("\n"):
                lines.append("\t\t\t" + ln)
        else:
            lines.append(f"\tmeasure {q(m['name'])} = {m['expr']}")
        lines += [f"\t\tformatString: {m['fmt']}", ""]
    for c in t["columns"]:
        if c["doc"]:
            lines.append(f"\t/// {c['doc']}")
        lines += [f"\tcolumn {c['name']}", f"\t\tdataType: {c['type']}"]
        if c["hidden"]:
            lines.append("\t\tisHidden")
        if c["key"]:
            lines.append("\t\tisKey")
        if c["fmt"]:
            lines.append(f"\t\tformatString: {c['fmt']}")
        lines += ["\t\tsummarizeBy: none", f"\t\tsourceColumn: {c['name']}"]
        if c["sort_by"]:
            lines.append(f"\t\tsortByColumn: {c['sort_by']}")
        if c["type"] == "dateTime":
            lines += ["", "\t\tannotation UnderlyingDateTimeDataType = Date"]
        lines.append("")
    types = ", ".join('{"%s", %s}' % (c["name"], M_TYPE[c["type"]]) for c in t["columns"])
    lines += [
        f"\tpartition {t['name']} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t\tSource = Csv.Document(",
        f'\t\t\t\t\t\tif Text.StartsWith(DataFolder, "http") then Web.Contents(DataFolder & "{t["csv"]}") '
        f'else File.Contents(DataFolder & "{t["csv"]}"),',
        "\t\t\t\t\t\t[Delimiter = \",\", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]",
        "\t\t\t\t\t),",
        "\t\t\t\t\tPromoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'\t\t\t\t\tTyped = Table.TransformColumnTypes(Promoted, {{{types}}}, "en-US")',
        "\t\t\t\tin",
        "\t\t\t\t\tTyped",
        "",
        "\tannotation PBI_ResultType = Table",
        ""]
    return "\n".join(lines)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def dump(path, obj):
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def build(out=OUT):
    if out.exists():
        shutil.rmtree(out)
    dump(out / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": "BrokerageOnboard"},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(NS, "semantic-model"))}})
    dump(out / "definition.pbism", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})
    d = out / "definition"
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1601\n\n")
    order = json.dumps(["DataFolder"] + [t["name"] for t in TABLES])
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tdiscourageImplicitMeasures", "\tsourceQueryCulture: en-US", "\tdataAccessOptions",
             "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             "annotation __PBI_TimeIntelligenceEnabled = 0", "", f"annotation PBI_QueryOrder = {order}", ""]
    model += [f"ref table {t['name']}" for t in TABLES] + [""]
    write(d / "model.tmdl", "\n".join(model))
    write(d / "expressions.tmdl", "\n".join([
        "/// Folder or URL that holds the CSV extracts, ending with a slash. The default reads the files from the",
        "/// repository on GitHub once it is published; for a local clone set it to the powerbi\\data folder, e.g.",
        "/// C:\\src\\brokerage-onboard-assist\\powerbi\\data\\",
        f'expression DataFolder = "{DATA_FOLDER_DEFAULT}" meta [IsParameterQuery=true, Type="Text", '
        'IsParameterQueryRequired=true]', "", "\tannotation PBI_ResultType = Text", ""]))
    rel = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        rel += [f"relationship {uuid.uuid5(NS, f'{ft}.{fc}->{tt}.{tc}')}", f"\tfromColumn: {ft}.{fc}",
                f"\ttoColumn: {tt}.{tc}", ""]
    write(d / "relationships.tmdl", "\n".join(rel))
    for t in TABLES:
        write(d / "tables" / f"{t['name']}.tmdl", table_tmdl(t))


if __name__ == "__main__":
    build()
