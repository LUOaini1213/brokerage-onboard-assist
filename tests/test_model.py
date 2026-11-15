"""Structure of the semantic model (TMDL) and of the CSV extracts it loads."""
import re
import sys
from pathlib import Path

import pandas as pd

from pbitest.model import DATA, DEFINITION

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_model  # noqa: E402

M_TYPES = {"type text": "string", "Int64.Type": "int64", "type number": "double", "type date": "dateTime",
           "type logical": "boolean"}
TABLES = {"DimDate", "DimCustomer", "DimLane", "DimReason", "DimStage", "FactEnrolmentStage", "FactShipment",
          "FactHold", "FactAction"}


def test_generator_reproduces_committed_tmdl(tmp_path):
    out = tmp_path / "BrokerageOnboard.SemanticModel"
    build_model.build(out)
    committed = DEFINITION.parent
    made = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    have = {p.relative_to(committed).as_posix(): p.read_bytes() for p in committed.rglob("*") if p.is_file()}
    assert made == have, "run python tools/build_model.py"


def test_tmdl_uses_tabs():
    for f in DEFINITION.rglob("*.tmdl"):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            assert not line.startswith(" "), f"{f.name}:{n} indented with spaces"


def test_model_lists_every_table_file():
    refs = re.findall(r"^ref table (\S+)", (DEFINITION / "model.tmdl").read_text(encoding="utf-8"), re.M)
    files = sorted(p.stem for p in (DEFINITION / "tables").glob("*.tmdl"))
    assert sorted(refs) == files


def test_star_schema_shape(model):
    assert set(model.meta.tables) == TABLES
    rels = {(r.from_table, r.from_column, r.to_table, r.to_column) for r in model.relationships}
    assert rels == {
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
    }
    # the same relationships drive the independent pandas implementation
    from boa.kpis import RELS
    assert rels == {(f, fk, d, pk) for f, dims in RELS.items() for d, (fk, pk) in dims.items()}
    assert model.date_tables == {"DimDate": "Date"}


def test_csv_matches_declared_columns(model):
    for name, t in model.meta.tables.items():
        header = list(pd.read_csv(DATA / t.csv_file, nrows=0).columns)
        assert header == [c.source_column for c in t.columns.values()], name
        pairs = re.findall(r'\{"([A-Za-z0-9_]+)",\s*(type text|Int64\.Type|type number|type date|type logical)\}',
                           t.partition_source)
        assert dict(pairs) == {c.source_column: next(k for k, v in M_TYPES.items() if v == c.data_type)
                               for c in t.columns.values()}, name
        assert "DataFolder" in t.partition_source


def test_one_side_keys_unique_and_no_orphans(model):
    for r in model.relationships:
        one = model.frames[r.to_table][r.to_column]
        many = model.frames[r.from_table][r.from_column]
        assert one.notna().all() and one.is_unique, f"{r.to_table}[{r.to_column}] is not a unique key"
        assert many.notna().all(), f"{r.from_table}[{r.from_column}] has nulls"
        orphans = set(many) - set(one)
        assert not orphans, f"{r.from_table}[{r.from_column}] values missing from {r.to_table}: {sorted(orphans)[:5]}"


def test_fact_grains_and_values(model):
    f = model.frames
    assert not f["FactEnrolmentStage"].duplicated(["EnrolmentId", "StageOrder"]).any()
    assert f["FactShipment"].ShipmentId.is_unique and f["FactHold"].HoldId.is_unique and f["FactAction"].ActionId.is_unique
    assert set(f["FactShipment"].ShipmentSeq) == {1, 2, 3}
    assert (f["FactShipment"].ClearanceHours > 0).all() and f["FactShipment"].ReadinessScore.between(0, 100).all()
    held = f["FactHold"].groupby("ShipmentId").size()
    ship = f["FactShipment"].set_index("ShipmentId")
    assert (ship.loc[held.index, "WasHeld"]).all() and (ship.loc[held.index, "HoldCount"] == held).all()
    a = f["FactAction"]
    assert set(a.Status) == {"Open", "Closed"}
    assert a.loc[a.Status == "Closed", "DaysToClose"].notna().all() and a.loc[a.Status == "Open", "DaysToClose"].isna().all()


def test_date_table(model):
    d = model.frames["DimDate"]
    days = pd.to_datetime(pd.Series(d.Date))
    assert (days.diff().dropna() == pd.Timedelta(days=1)).all()
    for t, c in (("FactEnrolmentStage", "ReachedDate"), ("FactShipment", "ArrivalDate"), ("FactHold", "HoldDate"),
                 ("FactAction", "OpenedDate")):
        assert set(model.frames[t][c]) <= set(d.Date), c


def test_measures_are_unique_documented_and_formatted(model):
    measures = [m for t in model.meta.tables.values() for m in t.measures.values()]
    names = [m.name for m in measures]
    assert len(names) == len(set(names)) == 26
    columns = {c for t in model.meta.tables.values() for c in t.columns}
    assert not set(names) & columns, "a measure has the name of a column"
    for m in measures:
        assert m.format_string and m.description, m.name


def test_extracts_are_synthetic_and_small():
    total = sum(p.stat().st_size for p in Path(DATA).glob("*.csv"))
    assert total < 3_000_000
    customers = pd.read_csv(DATA / "dim_customer.csv")
    assert customers.CustomerName.str.startswith("Synthetic Customer ").all()
    assert not any(k in c.lower() for c in customers.columns for k in ("uen", "email", "phone", "address"))
