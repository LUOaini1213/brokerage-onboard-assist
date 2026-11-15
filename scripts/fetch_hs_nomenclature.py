"""Fetch the public HS 2022 nomenclature file and derive the codes-only reference list (needs network).

Source: the `datasets/harmonized-system` data package on GitHub, pinned to one commit, whose datapackage.json
declares version 2022.0 and the ODC Public Domain Dedication and Licence (PDDL) 1.0, with UN Comtrade as the
upstream source. The HS nomenclature text itself is published by the World Customs Organization, which holds
copyright in it; to stay clear of that, this repository commits only the numeric 6-digit subheading codes (and
their chapter and heading numbers), not the descriptions. The raw download stays in data/reference/raw/, which is
git-ignored.

    python scripts/fetch_hs_nomenclature.py            # download, verify SHA-256, write the derived files
    python scripts/fetch_hs_nomenclature.py --offline  # rebuild the derived files from an existing raw copy

Everything else in the pipeline reads only the committed derived file (data/reference/hs2022_subheadings.csv).
"""
import argparse
import csv
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boa.io import write_csv, write_json  # noqa: E402

COMMIT = "b1be3f2531a85fb0ea17147b19c41d3641912e43"   # datasets/harmonized-system main, 2026-07-27
URL = f"https://raw.githubusercontent.com/datasets/harmonized-system/{COMMIT}/data/harmonized-system.csv"
SHA256 = "e77ee9e1cfd15a42d1fadeb2c0618d10f6b9ed9aec0e5d66826dc7ef9d3126a5"
RAW = ROOT / "data" / "reference" / "raw" / "harmonized-system.csv"
OUT = ROOT / "data" / "reference" / "hs2022_subheadings.csv"
META = ROOT / "data" / "reference" / "hs2022_provenance.json"
RETRIEVED = "2026-11-15"


def download():
    RAW.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "hs-reference-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"SHA-256 mismatch: got {digest}, expected {SHA256}")
    RAW.write_bytes(data)


def derive():
    data = RAW.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"raw file SHA-256 {digest} differs from the pinned {SHA256}")
    rows = list(csv.DictReader(data.decode("utf-8").splitlines()))
    total = [r for r in rows if r["hscode"] == "TOTAL"]
    if not total or "HS2022" not in total[0]["description"]:
        raise SystemExit("the file does not declare itself as HS2022")
    six = sorted(r["hscode"] for r in rows if r["level"] == "6")
    if not all(len(c) == 6 and c.isdigit() for c in six):
        raise SystemExit("unexpected 6-digit code format")
    # Chapter 99 is not part of the WCO nomenclature (UN Comtrade uses it for unspecified commodities).
    kept = [c for c in six if c[:2] != "99"]
    write_csv(OUT, [{"hs6": c, "chapter": c[:2], "heading": c[:4]} for c in kept], ["hs6", "chapter", "heading"])
    chapters = sorted({c[:2] for c in kept})
    write_json(META, {
        "label": "REAL (public reference data), codes only",
        "source_repository": "https://github.com/datasets/harmonized-system",
        "source_url": URL,
        "source_commit": COMMIT,
        "raw_sha256": SHA256,
        "retrieved": RETRIEVED,
        "hs_edition": "HS 2022 (the file's TOTAL row reads 'Total of all HS2022 commodities')",
        "licence_declared_by_source": "ODC-PDDL-1.0 (datapackage.json); data from UN Comtrade",
        "licence_note": ("The HS nomenclature is a World Customs Organization publication and the WCO holds "
                         "copyright in its text. Only the numeric 6-digit codes, with their chapter and heading "
                         "numbers, are redistributed here; descriptions are not."),
        "excluded": "chapter 99 codes (not WCO HS; UN Comtrade uses 99 for unspecified commodities)",
        "subheadings_in_source": len(six),
        "subheadings_kept": len(kept),
        "chapters_kept": len(chapters),
    })
    print(f"{len(kept)} HS 2022 subheadings in {len(chapters)} chapters -> {OUT.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use the existing raw download")
    a = ap.parse_args()
    if not a.offline or not RAW.exists():
        download()
    derive()


if __name__ == "__main__":
    main()
