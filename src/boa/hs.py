"""HS code format and validity checks (rules SG-IMP-05 and AU-06).

Validity is tested against the public HS 2022 6-digit list in data/reference/hs2022_subheadings.csv. Singapore
declares 8-digit AHTN codes (STCCED 2022) and Australia 8-digit tariff subheadings with a statistical code; the
national digits after the sixth are only format-checked, because the national code lists are not used here.
"""
import re
from functools import lru_cache

from .io import read_csv_rows
from .paths import REFERENCE

_DIGITS = re.compile(r"^\d+$")
NATIONAL_LENGTHS = {"SG": (8,), "AU": (8, 10)}


@lru_cache(maxsize=None)
def hs6_codes():
    return frozenset(r["hs6"] for r in read_csv_rows(REFERENCE / "hs2022_subheadings.csv"))


def normalise(code):
    """'8517.13.00' or '8517 13 00' -> '85171300'. Returns '' for None."""
    if code is None:
        return ""
    return re.sub(r"[.\s]", "", str(code))


def chapter(code):
    return normalise(code)[:2]


def check(code, jurisdiction="SG"):
    """Return a list of (problem, message); an empty list means the code passes.

    problem is 'missing', 'format' (not digits or wrong length for the jurisdiction) or 'hs6_unknown' (the first
    six digits are not an HS 2022 subheading, e.g. a code deleted in the 2022 edition)."""
    c = normalise(code)
    if not c:
        return [("missing", "no HS code")]
    lengths = NATIONAL_LENGTHS[jurisdiction]
    if not _DIGITS.match(c) or len(c) not in lengths:
        want = " or ".join(str(n) for n in lengths)
        return [("format", f"HS code {code!r} is not {want} digits")]
    if c[:6] not in hs6_codes():
        return [("hs6_unknown", f"HS code {c}: {c[:6]} is not an HS 2022 subheading")]
    return []


def is_valid(code, jurisdiction="SG"):
    return not check(code, jurisdiction)
