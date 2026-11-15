"""Deterministic, LF-only file writing.

Every text file the pipeline writes goes through these helpers so that the bytes are identical on Windows and
Linux: UTF-8, newline="\n", fixed float formatting and stable column / key order.
"""
import csv
import hashlib
import json
from pathlib import Path


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _clean(obj):
    """Round floats so that last-digit platform differences cannot change the JSON text."""
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return round(obj, 6)
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if hasattr(obj, "item"):  # numpy scalar
        return _clean(obj.item())
    return obj


def write_json(path, obj):
    write_text(path, json.dumps(_clean(obj), indent=2, ensure_ascii=False, sort_keys=False))


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fmt(value):
    """CSV cell text: floats with up to 6 decimals, no trailing zeros; booleans as TRUE/FALSE; None as empty."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if hasattr(value, "item") and not isinstance(value, str):
        value = value.item()
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if value != value:
            return ""
        text = f"{round(value, 6):.6f}".rstrip("0").rstrip(".")
        return "0" if text in ("-0", "") else text
    return str(value)


def write_csv(path, rows, columns):
    """rows: iterable of dicts (or a pandas DataFrame). Columns are written in the given order."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(rows, "to_dict"):
        rows = rows.to_dict(orient="records")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([fmt(r.get(c)) for c in columns])


def read_csv_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256_lf(path):
    """SHA-256 of the file with CRLF normalised to LF, so a Windows checkout and a Linux checkout agree."""
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()
