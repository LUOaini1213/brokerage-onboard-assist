"""Hand-worked HS code and UEN format checks."""
import json

import pytest

from boa import hs
from boa.paths import REFERENCE
from boa.uen import is_valid_format, uen_type


def test_reference_file_is_hs2022_codes_only():
    meta = json.loads((REFERENCE / "hs2022_provenance.json").read_text(encoding="utf-8"))
    assert meta["subheadings_kept"] == len(hs.hs6_codes()) == 5612
    assert meta["chapters_kept"] == 96 and "HS2022" in meta["hs_edition"].replace(" ", "")
    header = (REFERENCE / "hs2022_subheadings.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == "hs6,chapter,heading"          # no descriptions are redistributed
    assert not any(c.startswith("77") or c.startswith("99") for c in hs.hs6_codes())


@pytest.mark.parametrize("code,problem", [
    ("85171300", None),          # smartphones: subheading 8517.13 was created in HS 2022
    ("8517.13.00", None),        # dots are ignored
    ("85171200", "hs6_unknown"),  # 8517.12 existed in HS 2017 and was deleted in HS 2022
    ("94054000", "hs6_unknown"),  # 9405.40 was split in HS 2022
    ("8517130", "format"),        # 7 digits
    ("851713000", "format"),      # 9 digits
    ("8517I300", "format"),       # letter I instead of digit 1
    ("", "missing"),
    (None, "missing"),
    ("77000000", "hs6_unknown"),  # chapter 77 is reserved
])
def test_sg_hs_check(code, problem):
    got = hs.check(code, "SG")
    assert (got[0][0] if got else None) == problem


def test_au_accepts_ten_digits_with_statistical_code():
    assert hs.is_valid("8517130010", "AU") and hs.is_valid("85171300", "AU")
    assert not hs.is_valid("8517130010", "SG")


@pytest.mark.parametrize("uen,kind", [
    ("53012345D", "business"),          # NNNNNNNNC
    ("200912345K", "local company"),    # YYYYNNNNNC
    ("T09LL0001B", "other entity"),     # TYYPQNNNNC (LL = limited liability partnership)
    ("S98SS0123A", "other entity"),     # SYYPQNNNNC
    ("F00012345A", "foreign company"),  # F000NNNNNC
    ("F   12345A", "foreign company"),  # FDDDNNNNNC, D = space
    ("F0012345A", None),                # one character short
    ("200912345", None),                # check letter missing
    ("200912345k", None),               # lower-case check letter
    (" 200912345K", None),              # leading space (not allowed)
    ("T09LL001B", None),                # one digit short
    ("", None),
    (None, None),
])
def test_uen_formats(uen, kind):
    assert uen_type(uen) == kind
    assert is_valid_format(uen) == (kind is not None)
