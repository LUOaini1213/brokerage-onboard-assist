"""Compare what Microsoft's TOM library read from the TMDL files with what pbitest.tmdl reads.

tools/check_tmdl.ps1 (PowerShell 7, Microsoft.AnalysisServices 19.117.0) deserializes the TMDL folder, runs
Model.Validate() and writes checks/tom_model.json, which is committed. If the TMDL changes without TOM being
re-run, or the two readers disagree on a table, column type, measure text or relationship, this test fails.
"""
import json
from pathlib import Path

SUMMARY = Path(__file__).resolve().parents[1] / "checks" / "tom_model.json"
TOM_TYPES = {"String": "string", "Int64": "int64", "Double": "double", "DateTime": "dateTime", "Boolean": "boolean"}


def tom():
    return json.loads(SUMMARY.read_text(encoding="utf-8-sig"))


def test_same_tables_columns_and_types(model):
    t_all = tom()
    assert set(t_all["tables"]) == set(model.meta.tables)
    for name, t in t_all["tables"].items():
        mine = model.meta.tables[name]
        assert (t["dataCategory"] or "") == mine.data_category
        assert list(t["columns"]) == list(mine.columns)
        for cname, c in t["columns"].items():
            assert TOM_TYPES[c["dataType"]] == mine.columns[cname].data_type, f"{name}[{cname}]"
            assert c["sourceColumn"] == mine.columns[cname].source_column
            assert c["isKey"] == mine.columns[cname].is_key
            assert c["isHidden"] == mine.columns[cname].is_hidden


def test_same_measure_text(model):
    for name, t in tom()["tables"].items():
        mine = model.meta.tables[name].measures
        assert list(t["measures"]) == list(mine)
        for mname, m in t["measures"].items():
            assert m["expression"].replace("\r\n", "\n").strip() == mine[mname].expression.strip(), mname
            assert m["formatString"] == mine[mname].format_string, mname


def test_same_partitions_and_relationships(model):
    t_all = tom()
    for name, t in t_all["tables"].items():
        assert len(t["partitionSources"]) == 1
        assert t["partitionSources"][0].replace("\r\n", "\n").strip() == model.meta.tables[name].partition_source.strip()
    rels = {(r["from"], r["to"]) for r in t_all["relationships"]}
    assert rels == {(f"{r.from_table}.{r.from_column}", f"{r.to_table}.{r.to_column}") for r in model.relationships}
    for r in t_all["relationships"]:
        assert (r["fromCardinality"], r["toCardinality"], r["crossFilteringBehavior"], r["isActive"]) == \
            ("Many", "One", "OneDirection", True)
    assert t_all["compatibilityLevel"] >= 1600 and t_all["tomVersion"] == "19.117.0"
