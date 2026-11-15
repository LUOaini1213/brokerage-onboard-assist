"""The PBIR report: folder layout, references into the semantic model and the generator (structure follows the
author's sg-transport-powerbi project)."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PBIP = ROOT / "powerbi"
REPORT = PBIP / "BrokerageOnboard.Report"
DEF = REPORT / "definition"
NAME = re.compile(r"^[\w-]+$")

sys.path.insert(0, str(ROOT / "tools"))
import build_report  # noqa: E402


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def visuals():
    for f in sorted(DEF.glob("pages/*/visuals/*/visual.json")):
        yield f, load(f)


def fields(obj):
    """Every Column/Measure reference (Entity, Property, kind) anywhere in a PBIR document."""
    if isinstance(obj, dict):
        for kind in ("Column", "Measure"):
            v = obj.get(kind)
            if isinstance(v, dict) and "Property" in v and "Entity" in v.get("Expression", {}).get("SourceRef", {}):
                yield v["Expression"]["SourceRef"]["Entity"], v["Property"], kind
        for v in obj.values():
            yield from fields(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from fields(v)


def test_generator_reproduces_committed_files(tmp_path):
    build_report.build(tmp_path / "definition")
    made = {p.relative_to(tmp_path / "definition").as_posix(): p.read_bytes()
            for p in (tmp_path / "definition").rglob("*") if p.is_file()}
    committed = {p.relative_to(DEF).as_posix(): p.read_bytes() for p in DEF.rglob("*") if p.is_file()}
    assert made == committed, "run python tools/build_report.py"
    build_report.build_project_files(tmp_path)
    for rel in ("BrokerageOnboard.pbip", "BrokerageOnboard.Report/definition.pbir", "BrokerageOnboard.Report/.platform"):
        assert (tmp_path / rel).read_bytes() == (PBIP / rel).read_bytes(), rel


def test_project_files_point_at_each_other():
    pbip = load(PBIP / "BrokerageOnboard.pbip")
    assert [a["report"]["path"] for a in pbip["artifacts"]] == ["BrokerageOnboard.Report"]
    pbir = load(REPORT / "definition.pbir")
    target = (REPORT / pbir["datasetReference"]["byPath"]["path"]).resolve()
    assert target == (PBIP / "BrokerageOnboard.SemanticModel").resolve()
    assert (target / "definition.pbism").exists() and (target / "definition" / "model.tmdl").exists()
    report = load(DEF / "report.json")
    base = report["themeCollection"]["baseTheme"]["name"]
    items = {i["name"]: i["path"] for pkg in report["resourcePackages"] for i in pkg["items"]}
    assert (REPORT / "StaticResources" / "SharedResources" / items[base]).exists()
    ids = {load(p)["config"]["logicalId"] for p in PBIP.glob("*/.platform")}
    assert len(ids) == 2


def test_pages_and_names():
    meta = load(DEF / "pages" / "pages.json")
    folders = sorted(p.name for p in (DEF / "pages").iterdir() if p.is_dir())
    assert sorted(meta["pageOrder"]) == folders and meta["activePageName"] in folders
    assert meta["pageOrder"] == ["onboarding", "first_three", "hold_reasons", "clearance", "action_log"]
    for folder in folders:
        page = load(DEF / "pages" / folder / "page.json")
        assert page["name"] == folder and NAME.match(folder) and page["displayOption"] == "FitToPage"
        names = set()
        for f in (DEF / "pages" / folder).glob("visuals/*/visual.json"):
            v = load(f)
            assert v["name"] == f.parent.name and NAME.match(v["name"])
            pos = v["position"]
            assert pos["x"] >= 0 and pos["y"] >= 0
            assert pos["x"] + pos["width"] <= page["width"] and pos["y"] + pos["height"] <= page["height"]
            names.add(v["name"])
        assert len(names) >= 4
        for i in page.get("visualInteractions", []):
            assert i["source"] in names and i["target"] in names


def test_every_field_exists_in_the_model(model):
    seen = 0
    for f, v in visuals():
        for entity, prop, kind in fields(v):
            t = model.meta.tables.get(entity)
            assert t is not None, f"{f}: unknown table {entity}"
            if kind == "Measure":
                assert prop in t.measures, f"{f}: {entity} has no measure [{prop}]"
            else:
                assert prop in t.columns, f"{f}: {entity} has no column [{prop}]"
                assert not t.columns[prop].is_hidden, f"{f}: {entity}[{prop}] is hidden"
            seen += 1
        for role in v.get("visual", {}).get("query", {}).get("queryState", {}).values():
            for p in role["projections"]:
                (entity, prop, _), = list(fields(p["field"]))
                assert p["queryRef"] == f"{entity}.{prop}"
    assert seen > 60


def test_every_model_measure_is_on_a_page(model):
    used = {prop for _, v in visuals() for _, prop, kind in fields(v) if kind == "Measure"}
    assert used == set(model.measures)


def test_required_visuals_exist():
    types = {v["name"]: v["visual"]["visualType"] for _, v in visuals()}
    assert types["onb_funnel"] == "funnel"
    assert types["hr_pareto"] == "lineClusteredColumnComboChart"
    assert types["al_table"] == "tableEx" and types["cl_by_lane"] == "clusteredBarChart"


@pytest.mark.parametrize("vtype,roles", [("cardVisual", {"Data"}), ("slicer", {"Values"}), ("tableEx", {"Values"}),
                                         ("clusteredBarChart", {"Category", "Y"}),
                                         ("clusteredColumnChart", {"Category", "Y"}), ("funnel", {"Category", "Y"}),
                                         ("lineClusteredColumnComboChart", {"Category", "Y", "Y2"})])
def test_visual_roles(vtype, roles):
    found = 0
    for _, v in visuals():
        if v["visual"]["visualType"] == vtype:
            assert set(v["visual"]["query"]["queryState"]) == roles
            found += 1
    assert found


def test_report_says_data_are_synthetic():
    headers = [v for _, v in visuals() if v["visual"]["visualType"] == "textbox"]
    assert len(headers) == 5
    for v in headers:
        assert "SYNTHETIC" in json.dumps(v)
