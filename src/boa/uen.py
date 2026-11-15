"""Singapore UEN format check (rule SG-IMP-03).

Patterns from the OECD 'Singapore - Information on Tax Identification Numbers' sheet (source OECD-SG-TIN):
businesses (ROB) NNNNNNNNC, local companies (ROC) YYYYNNNNNC, foreign companies F000NNNNNC, other entities
TYYPQNNNNC or SYYPQNNNNC, where N is a digit and C a check letter. Only the pattern is checked: the check-letter
algorithm is not published in that source, and whether the UEN exists cannot be known offline.
"""
import re

PATTERNS = (
    ("business", re.compile(r"^\d{8}[A-Z]$")),
    ("local company", re.compile(r"^\d{9}[A-Z]$")),
    ("foreign company", re.compile(r"^F000\d{5}[A-Z]$")),
    ("other entity", re.compile(r"^[ST]\d{2}[A-Z]{2}\d{4}[A-Z]$")),
)


def uen_type(uen):
    """Entity type the UEN pattern matches, or None. Leading/trailing spaces are not accepted (the OECD sheet says
    the number must not have preceding spaces)."""
    if not uen:
        return None
    for name, pat in PATTERNS:
        if pat.match(uen):
            return name
    return None


def is_valid_format(uen):
    return uen_type(uen) is not None
