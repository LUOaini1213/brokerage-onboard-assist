"""Rebuild every result from committed inputs, offline: synthetic data, validator output, analytics, classifier
metrics (LLM metrics from the cached predictions), Power BI data, KPIs, figures, generated docs and README numbers.

    python scripts/build_all.py              # everything, into the repository
    python scripts/build_all.py --no-figures # skip the matplotlib figures
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from boa.pipeline import build  # noqa: E402
from boa.readme import update_readme  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    summary = build(ROOT, figures=not a.no_figures)
    update_readme(summary)
    c = summary["counts"]
    print(f"{c['customers']} customers, {c['shipments']} shipments, {c['holds']} holds, {c['actions']} actions (SYNTHETIC)")


if __name__ == "__main__":
    main()
