"""Write the PBIR report definition (powerbi/BrokerageOnboard.Report) from the compact layout below.

Adapted from the author's sg-transport-powerbi project (tools/build_report.py): same schemas, theme and visual
conventions. The JSON files are committed; this script is how they were produced, and tests/test_report.py checks
that re-running it reproduces them byte for byte. Edit the layout here, not the JSON, until the report has been
opened and saved in Power BI Desktop once; after that, Desktop owns the files.

Visual roles follow published PBIR examples: cards use 'Data', tables and slicers 'Values', bar/column charts
and the funnel 'Category' + 'Y', and the line-and-column combo chart 'Category' + 'Y' (columns) + 'Y2' (line).

    python tools/build_report.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "powerbi" / "BrokerageOnboard.Report"
OUT = REPORT / "definition"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VISUAL_SCHEMA = f"{SCHEMA}/visualContainer/2.4.0/schema.json"
PAGE_SCHEMA = f"{SCHEMA}/page/2.0.0/schema.json"


def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def text(s):
    return lit("'" + s.replace("'", "''") + "'")


def field(kind, entity, prop):
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def col(entity, prop):
    return ("Column", entity, prop)


def msr(entity, prop):
    return ("Measure", entity, prop)


def projection(f, active=False):
    kind, entity, prop = f
    p = {"field": field(kind, entity, prop), "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if active:
        p["active"] = True
    return p


def container(name, x, y, w, h, z, visual):
    return {"$schema": VISUAL_SCHEMA, "name": name,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": visual}


def title_objects(title):
    return {"title": [{"properties": {"show": lit("true"), "text": text(title)}}]}


def sort_def(sort):
    kind, entity, prop = sort[0]
    return {"sort": [{"field": field(kind, entity, prop), "direction": sort[1]}], "isDefaultSort": False}


def chart(vtype, category, values, title, sort=None, line=None):
    roles = {"Category": {"projections": [projection(category, active=True)]},
             "Y": {"projections": [projection(v) for v in values]}}
    if line:
        roles["Y2"] = {"projections": [projection(v) for v in line]}
    v = {"visualType": vtype, "query": {"queryState": roles}, "visualContainerObjects": title_objects(title)}
    if sort:
        v["query"]["sortDefinition"] = sort_def(sort)
    return v


def card(values, title):
    return {"visualType": "cardVisual",
            "query": {"queryState": {"Data": {"projections": [projection(v) for v in values]}}},
            "visualContainerObjects": title_objects(title)}


def table(values, title, sort):
    return {"visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": [projection(v) for v in values]}},
                      "sortDefinition": sort_def(sort)},
            "visualContainerObjects": title_objects(title)}


def slicer(column, title):
    return {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [projection(column, True)]}}},
            "objects": {"data": [{"properties": {"mode": text("Dropdown")}}]},
            "visualContainerObjects": title_objects(title)}


def textbox(lines):
    paragraphs = []
    for i, line in enumerate(lines):
        style = {"fontWeight": "bold", "fontSize": "16pt"} if i == 0 else {"fontSize": "10pt"}
        paragraphs.append({"textRuns": [{"value": line, "textStyle": style}]})
    return {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]}}


E, S, H, A = "FactEnrolmentStage", "FactShipment", "FactHold", "FactAction"
ST, CU, LA, RE = "DimStage", "DimCustomer", "DimLane", "DimReason"
SYN = "All data are SYNTHETIC (generated; no real customers, shipments or holds)."

PAGES = [
    {
        "name": "onboarding", "displayName": "Onboarding funnel",
        "visuals": [
            ("onb_header", 20, 10, 860, 70, textbox([
                "Onboarding funnel", "Enrolment requests from submission to the third released shipment. " + SYN])),
            ("onb_segment_slicer", 900, 10, 360, 70, slicer(col(CU, "Segment"), "Customer segment")),
            ("onb_cards", 20, 90, 1240, 120, card([
                msr(E, "Enrolments Submitted"), msr(E, "Profiles Created"), msr(E, "Three Shipments Completed")],
                "Enrolments")),
            ("onb_funnel", 20, 220, 600, 480, chart(
                "funnel", col(ST, "Stage"), [msr(E, "Enrolments at Stage")], "Enrolments by stage reached",
                sort=(col(ST, "Stage"), "Ascending"))),
            ("onb_stage_table", 640, 220, 620, 480, table([
                col(ST, "Stage"), msr(E, "Enrolments at Stage"), msr(E, "Stage Conversion %"),
                msr(E, "Step Conversion %"), msr(E, "Median Days to Stage")],
                "Conversion and days from submission", sort=(col(ST, "Stage"), "Ascending"))),
        ],
    },
    {
        "name": "first_three", "displayName": "First three shipments",
        "visuals": [
            ("f3_header", 20, 10, 860, 70, textbox([
                "First three shipments of each new customer",
                "Hold rate by shipment number and lane; readiness score from the pre-lodgement check. " + SYN])),
            ("f3_mode_slicer", 900, 10, 360, 70, slicer(col(LA, "Mode"), "Transport mode")),
            ("f3_cards", 20, 90, 1240, 120, card([
                msr(S, "First-3 Shipments"), msr(S, "Held Shipments"), msr(S, "First-3 Hold Rate %"),
                msr(S, "Customers With a Hold %"), msr(S, "Avg Readiness Score")], "First-three shipments")),
            ("f3_by_seq", 20, 220, 400, 480, chart(
                "clusteredColumnChart", col(S, "ShipmentSeq"), [msr(S, "First-3 Hold Rate %")],
                "Hold rate by shipment number", sort=(col(S, "ShipmentSeq"), "Ascending"))),
            ("f3_by_lane", 440, 220, 400, 480, chart(
                "clusteredBarChart", col(LA, "LaneName"), [msr(S, "First-3 Hold Rate %")], "Hold rate by lane",
                sort=(msr(S, "First-3 Hold Rate %"), "Descending"))),
            ("f3_by_band", 860, 220, 400, 480, table([
                col(S, "ReadinessBand"), msr(S, "First-3 Shipments"), msr(S, "Held Shipments"),
                msr(S, "First-3 Hold Rate %"), msr(S, "Customers Shipping"), msr(S, "Customers With a Hold")],
                "Hold rate by readiness band", sort=(msr(S, "First-3 Shipments"), "Descending"))),
        ],
    },
    {
        "name": "hold_reasons", "displayName": "Hold reasons",
        "visuals": [
            ("hr_header", 20, 10, 860, 70, textbox([
                "Hold reasons (Pareto)",
                "Columns: holds by reason; line: cumulative share, reasons in descending order. " + SYN])),
            ("hr_direction_slicer", 900, 10, 360, 70, slicer(col(LA, "Direction"), "Direction")),
            ("hr_pareto", 20, 90, 760, 610, chart(
                "lineClusteredColumnComboChart", col(RE, "ReasonLabel"), [msr(H, "Holds")], "Hold reason Pareto",
                sort=(msr(H, "Holds"), "Descending"), line=[msr(H, "Hold Pareto Cumulative %")])),
            ("hr_table", 800, 90, 460, 610, table([
                col(RE, "ReasonLabel"), msr(H, "Holds"), msr(H, "Hold Share %"), msr(H, "Hold Pareto Cumulative %"),
                msr(H, "Median Hours to Release"), msr(H, "P90 Hours to Release")],
                "Holds and time to release by reason", sort=(msr(H, "Holds"), "Descending"))),
        ],
    },
    {
        "name": "clearance", "displayName": "Clearance lead time",
        "visuals": [
            ("cl_header", 20, 10, 1240, 70, textbox([
                "Clearance lead time by lane",
                "Hours from presentation to release, including time on hold; time to release by reason and lane. "
                + SYN])),
            ("cl_by_lane", 20, 90, 600, 300, chart(
                "clusteredBarChart", col(LA, "LaneName"), [msr(S, "Median Clearance Hours"), msr(S, "P90 Clearance Hours")],
                "Clearance hours by lane (median and P90)", sort=(msr(S, "Median Clearance Hours"), "Descending"))),
            ("cl_lane_table", 640, 90, 620, 300, table([
                col(LA, "LaneName"), msr(S, "First-3 Shipments"), msr(S, "First-3 Hold Rate %"),
                msr(S, "Median Clearance Hours"), msr(S, "P90 Clearance Hours")],
                "Lanes", sort=(msr(S, "Median Clearance Hours"), "Descending"))),
            ("cl_release_by_reason", 20, 400, 600, 300, chart(
                "clusteredBarChart", col(RE, "ReasonLabel"), [msr(H, "Median Hours to Release")],
                "Median hours to release by reason", sort=(msr(H, "Median Hours to Release"), "Descending"))),
            ("cl_reason_lane_table", 640, 400, 620, 300, table([
                col(LA, "LaneName"), col(RE, "ReasonLabel"), msr(H, "Holds"), msr(H, "Median Hours to Release")],
                "Time to release by lane and reason", sort=(msr(H, "Holds"), "Descending"))),
        ],
    },
    {
        "name": "action_log", "displayName": "Action log",
        "visuals": [
            ("al_header", 20, 10, 860, 70, textbox([
                "Action log", "Corrective actions for holds and enrolment findings; overdue = closed after, or "
                              "still open after, the due date. " + SYN])),
            ("al_status_slicer", 900, 10, 360, 70, slicer(col(A, "Status"), "Status")),
            ("al_cards", 20, 90, 1240, 110, card([
                msr(A, "Actions"), msr(A, "Open Actions"), msr(A, "Overdue Actions"), msr(A, "Avg Days to Close"),
                msr(A, "Closed On Time %")], "Actions")),
            ("al_by_owner", 20, 210, 360, 490, chart(
                "clusteredBarChart", col(A, "OwnerRole"), [msr(A, "Open Actions"), msr(A, "Overdue Actions")],
                "Open and overdue actions by owner", sort=(msr(A, "Overdue Actions"), "Descending"))),
            ("al_table", 400, 210, 860, 490, table([
                col(A, "ActionId"), col(CU, "CustomerName"), col(A, "ShipmentId"), col(RE, "ReasonLabel"),
                col(A, "ActionType"), col(A, "RuleRef"), col(A, "OwnerRole"), col(A, "OpenedDate"),
                col(A, "DueDate"), col(A, "ClosedDate"), col(A, "Status"), col(A, "IsOverdue")],
                "Action log", sort=(col(A, "OpenedDate"), "Descending"))),
        ],
    },
]

REPORT_JSON = {
    "$schema": f"{SCHEMA}/report/3.0.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU10",
                                      "reportVersionAtImport": {"visual": "1.8.97", "report": "2.0.97", "page": "1.3.97"},
                                      "type": "SharedResources"}},
    "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                          "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]}],
    "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True,
                 "allowChangeFilterTypes": True, "useEnhancedTooltips": True},
}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def build(out=OUT):
    if out.exists():
        shutil.rmtree(out)
    dump(out / "version.json", {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    dump(out / "report.json", REPORT_JSON)
    dump(out / "pages" / "pages.json", {"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                        "pageOrder": [p["name"] for p in PAGES], "activePageName": PAGES[0]["name"]})
    for p in PAGES:
        page = {"$schema": PAGE_SCHEMA, "name": p["name"], "displayName": p["displayName"],
                "displayOption": "FitToPage", "height": 720, "width": 1280}
        dump(out / "pages" / p["name"] / "page.json", page)
        for z, (name, x, y, w, h, visual) in enumerate(p["visuals"]):
            dump(out / "pages" / p["name"] / "visuals" / name / "visual.json",
                 container(name, x, y, w, h, z * 1000, visual))


def build_project_files(root=ROOT / "powerbi"):
    """The .pbip entry point and the report's definition.pbir and .platform (written once; static)."""
    import uuid
    ns = uuid.UUID("6f1c2b0e-1d55-4f0a-9a5e-0b7e7c3f4a21")
    dump(root / "BrokerageOnboard.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": "BrokerageOnboard.Report"}}],
        "settings": {"enableAutoRecovery": True}})
    dump(root / "BrokerageOnboard.Report" / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../BrokerageOnboard.SemanticModel"}}})
    dump(root / "BrokerageOnboard.Report" / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "BrokerageOnboard"},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(ns, "report"))}})


if __name__ == "__main__":
    build()
    build_project_files()
