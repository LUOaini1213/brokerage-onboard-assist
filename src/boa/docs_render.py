"""Generated documentation: docs/assumptions.md (from config) and docs/kpi_definitions.md (from the TMDL)."""
import json

from pbitest.tmdl import parse_folder

from .kpis import MEASURES
from .paths import POWERBI


def assumptions_markdown(raw):
    lines = ["# Assumptions of the synthetic data generator", "",
             "Generated from `config/synth_assumptions.json` by `scripts/build_all.py`; edit that file, not this one.",
             "", raw["_about"], "",
             "| Parameter | Label | Value | Meaning |", "|---|---|---|---|"]
    for key, entry in raw.items():
        if key.startswith("_"):
            continue
        value = json.dumps(entry["value"], ensure_ascii=False)
        if len(value) > 160:
            value = value[:157] + "..."
        value = value.replace("|", "\\|")
        lines.append(f"| `{key}` | {entry['label']} | `{value}` | {entry['about']} |")
    lines += ["", "Full values (including the long lists truncated above) are in the JSON file.", ""]
    return "\n".join(lines)


def kpi_markdown(values):
    """values: {measure name: value in the empty filter context, from boa.kpis}."""
    model = parse_folder(POWERBI / "BrokerageOnboard.SemanticModel" / "definition")
    lines = ["# DAX measures", "",
             "Generated from the TMDL files in `powerbi/BrokerageOnboard.SemanticModel/definition/tables` by "
             "`scripts/build_all.py`. Each measure has an independent pandas implementation in `src/boa/kpis.py`; "
             "`tests/test_measures.py` evaluates the DAX text below with the evaluator in `pbitest/dax.py` and compares "
             "it with the pandas value in many filter contexts, and `tests/test_kpis.py` checks the pandas functions "
             "against values worked out by hand. The DAX has not been run by the Analysis Services engine yet: the "
             "report has not been opened in Power BI Desktop.", "",
             "'Value (all data)' is the pandas result with no filter, on the SYNTHETIC data; it is what a card with no "
             "slicer selection should show once the report is rendered.", ""]
    for tname, t in model.tables.items():
        if not t.measures:
            continue
        lines += [f"## {tname}", ""]
        for m in t.measures.values():
            v = values.get(m.name)
            shown = "BLANK" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v))
            lines += [f"### {m.name}", "", m.description, "", "```dax", m.expression, "```", "",
                      f"- Format: `{m.format_string}`; Python: `boa.kpis.{MEASURES[m.name].__name__}`; "
                      f"value (all data): {shown}", ""]
    return "\n".join(lines)
