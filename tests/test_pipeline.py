"""Reproducibility: rebuild every result from the committed inputs into a temporary folder and compare with the
committed files. Text must match exactly; numbers in CSV and JSON may differ by 1e-6 relative (floating-point
libraries differ slightly between platforms)."""
import csv
import json
from pathlib import Path

import pytest

from boa.pipeline import build

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ["data/synthetic", "results/validation", "results/analytics", "powerbi/data", "docs/examples"]
FILES = ["results/kpis.json", "results/summary.json", "results/powerbi_expected_values.csv",
         "results/classifier/metrics.json", "results/classifier/predictions.csv", "docs/rulebook.md",
         "docs/assumptions.md", "docs/kpi_definitions.md"]
# inputs or separately produced files that the offline build reads or leaves alone
NOT_REBUILT = {"results/classifier/llm_predictions.csv", "results/mutation_report.json"}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _same_value(a, b):
    if a == b:
        return True
    fa, fb = _num(a), _num(b)
    return fa is not None and fb is not None and abs(fa - fb) <= 1e-6 * max(1.0, abs(fa), abs(fb))


def _same_json(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same_json(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same_json(x, y) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str) or isinstance(b, str):
        return a == b
    return _same_value(a, b)


def _compare(made, committed):
    if made.suffix == ".csv":
        with open(made, encoding="utf-8", newline="") as fa, open(committed, encoding="utf-8", newline="") as fb:
            ra, rb = list(csv.reader(fa)), list(csv.reader(fb))
        if len(ra) != len(rb):
            return f"{len(ra)} rows built, {len(rb)} committed"
        for i, (x, y) in enumerate(zip(ra, rb)):
            if len(x) != len(y) or not all(_same_value(p, q) for p, q in zip(x, y)):
                return f"row {i + 1}: built {x[:6]}, committed {y[:6]}"
        return None
    if made.suffix == ".json":
        a, b = (json.loads(p.read_text(encoding="utf-8")) for p in (made, committed))
        return None if _same_json(a, b) else "JSON values differ"
    a, b = (p.read_text(encoding="utf-8") for p in (made, committed))
    return None if a == b else "text differs"


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    out = tmp_path_factory.mktemp("rebuild")
    summary = build(out, figures=False)
    return out, summary


def _pairs(out):
    rels = list(FILES)
    for folder in FOLDERS:
        rels += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).glob("*") if p.is_file())
    return [(r, out / r, ROOT / r) for r in rels]


def test_rebuild_matches_committed_results(rebuilt):
    out, _ = rebuilt
    problems = []
    for rel, made, committed in _pairs(out):
        if not made.exists():
            problems.append(f"{rel}: not produced by the build")
        elif (why := _compare(made, committed)):
            problems.append(f"{rel}: {why}")
    assert not problems, "run python scripts/build_all.py\n" + "\n".join(problems)


def test_build_produces_nothing_that_is_not_committed(rebuilt):
    out, _ = rebuilt
    made = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    committed = {p.relative_to(ROOT).as_posix() for folder in ("data/synthetic", "results", "powerbi/data", "docs")
                 for p in (ROOT / folder).rglob("*") if p.is_file()}
    assert made <= committed, sorted(made - committed)
    expected = {r for r, _, _ in _pairs(out)}
    results = {r for r in committed if r.startswith(("results/", "data/synthetic/", "powerbi/data/"))}
    assert results - expected <= NOT_REBUILT, sorted(results - expected - NOT_REBUILT)


def test_committed_text_files_use_lf_only():
    bad = []
    for folder in ("data", "results", "powerbi", "docs", "rules", "config", "power-platform", "src", "tests", "tools",
                   "scripts", "pbitest", "checks", "mutation", ".github"):
        for p in (ROOT / folder).rglob("*"):
            if p.is_file() and p.suffix not in (".png", ".pyc") and "raw" not in p.parts and b"\r" in p.read_bytes():
                bad.append(p.relative_to(ROOT).as_posix())
    assert not bad, bad


def test_summary_headline_numbers_agree_with_tables(rebuilt):
    _, s = rebuilt
    with open(ROOT / "data" / "synthetic" / "shipments.csv", encoding="utf-8", newline="") as fh:
        ships = list(csv.DictReader(fh))
    held = sum(r["held"] == "TRUE" for r in ships)
    assert s["counts"]["shipments"] == len(ships)
    assert s["first3"]["hold_rate"] == pytest.approx(held / len(ships))
    with open(ROOT / "results" / "analytics" / "pareto.csv", encoding="utf-8", newline="") as fh:
        top = next(csv.DictReader(fh))
    assert s["pareto"]["top"] == top["reason_code"] and s["pareto"]["top_share"] == pytest.approx(float(top["share"]), abs=1e-6)
