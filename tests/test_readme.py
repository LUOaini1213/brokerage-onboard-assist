"""README.md is the template rendered with numbers from the committed results; nothing in it is typed by hand."""
import re
import sys
from pathlib import Path

import pytest

from boa import readme

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def test_readme_is_the_rendered_template():
    assert readme.README.read_text(encoding="utf-8") == readme.current(), "run python scripts/build_all.py"


def test_every_placeholder_has_a_value_and_none_is_left():
    template = readme.TEMPLATE.read_text(encoding="utf-8")
    keys = set(readme.PLACEHOLDER.findall(template))
    assert len(keys) >= 50
    assert "{{" not in readme.README.read_text(encoding="utf-8")
    with pytest.raises(KeyError):
        readme.render("{{no_such_number}}", {})


def test_template_has_no_hand_typed_results():
    """Outside placeholders the template may contain only fixed facts: rule parameters (9%, 10%, 0.5%, 2%, 80%),
    score weights and counts of things in the repository that other tests pin down."""
    template = readme.TEMPLATE.read_text(encoding="utf-8")
    body = readme.PLACEHOLDER.sub("", template)
    percents = set(re.findall(r"\d+(?:\.\d+)?%", body))
    assert percents <= {"9%", "10%", "0.5%", "2%", "80%", "95%"}, percents


def test_fixed_facts_in_the_readme_are_true(model):
    text = readme.README.read_text(encoding="utf-8")
    import validate_schemas
    assert f"all {len(validate_schemas.project_files(ROOT))} PBIP and PBIR files" in text
    assert f"{len(model.meta.tables)} tables".replace("9 tables", "nine tables") in text
    assert f"{len(model.measures)} measures" in text
    assert "**All customer, shipment, hold and action data in this repository are SYNTHETIC**" in text
    assert "not yet opened in Power BI Desktop" in text
    assert "no app or flow exports are in this" in text
    for rel in re.findall(r"\]\(((?!https?://)[^)#]+)\)", text):
        assert (ROOT / rel).exists(), f"README links to a missing file: {rel}"


def test_summary_numbers_appear_in_the_readme():
    s = readme.read_json(readme.RESULTS / "summary.json")
    text = readme.README.read_text(encoding="utf-8")
    assert f"{s['counts']['shipments']:,}, {readme.pct(s['first3']['hold_rate'])}" in text
    assert f"{s['counts']['holds']:,}; {s['pareto']['top']}" in text
    assert readme.pct(s["classifier"]["heldout_accuracy"]) in text
