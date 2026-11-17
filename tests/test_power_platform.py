"""The Power Platform design folder: seed files unchanged and reproducible, schema in step with the seed, the
readiness rule the flow uses matches the seed, the DESIGN label is present, and no real address is written down."""
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from boa.io import sha256_lf

ROOT = Path(__file__).resolve().parents[1]
PP = ROOT / "power-platform"
SEED = PP / "seed"
# SHA-256 (LF line endings) of the seed files as handed over from the Microsoft 365 build
PINNED = {
    "BA_Customers.csv": "d1fd77e64cd8996d01e260a941b75b4c2411e471a887da3f6a26cdb63c1546d1",
    "BA_Shipments.csv": "70de353bd3d35c186645288fc672b53ef0b2f762d4e2ff1f70a64261ce670818",
    "BA_ActionLog.csv": "3b83b9f15b077f1c55e3e6006190d1b5a35c386dd24fc77f5bfa5ea4b29a8c18",
    "make_seed.py": "ae0101b348860f6c2844bcfe1ef3d9c98b969bd91af263585487bfb4cd05a507",
}


def rows(name):
    with open(SEED / f"{name}.csv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def schema():
    return json.loads((PP / "lists_schema.json").read_text(encoding="utf-8"))


def test_seed_files_are_unchanged():
    for name, digest in PINNED.items():
        assert sha256_lf(SEED / name) == digest, name


def test_seed_script_reproduces_the_csvs(tmp_path):
    shutil.copy(SEED / "make_seed.py", tmp_path / "make_seed.py")
    subprocess.run([sys.executable, str(tmp_path / "make_seed.py")], check=True, capture_output=True)
    for name in ("BA_Customers.csv", "BA_Shipments.csv", "BA_ActionLog.csv"):
        assert (tmp_path / name).read_bytes().replace(b"\r\n", b"\n") == (SEED / name).read_bytes().replace(b"\r\n", b"\n")


def test_seed_sizes_stay_below_delegation_limits():
    counts = {lst["name"]: len(rows(lst["name"])) for lst in schema()["lists"]}
    assert counts == {"BA_Customers": 24, "BA_Shipments": 42, "BA_ActionLog": 26}
    assert max(counts.values()) <= 300


def test_schema_matches_seed_columns_and_choices():
    for lst in schema()["lists"]:
        data = rows(lst["name"])
        assert [c["name"] for c in lst["columns"]] == list(data[0].keys()), lst["name"]
        assert lst["columns"][0]["internal"] == "Title"
        for c in lst["columns"][1:]:
            assert c["internal"] == c["name"] and " " not in c["internal"]
        for c in lst["columns"]:
            values = {r[c["name"]] for r in data}
            if c["type"] == "Choice":
                assert values <= set(c["choices"]), (lst["name"], c["name"], values - set(c["choices"]))
            elif c["type"] == "Yes/No":
                assert values <= {"Yes", "No"}, c["name"]
            elif c["type"] == "Number":
                assert all(re.fullmatch(r"\d+", v) for v in values), c["name"]
            elif c["type"] == "Date and Time":
                assert all(v == "" or re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in values), c["name"]
    names = {lst["name"]: lst for lst in schema()["lists"]}
    # every shipment and action belongs to a seeded customer; shipments are the first three
    accounts = {r["AccountNo"] for r in rows("BA_Customers")}
    assert {r["AccountNo"] for r in rows("BA_Shipments")} <= accounts
    assert {r["AccountNo"] for r in rows("BA_ActionLog")} <= accounts
    assert {r["ShipmentSeq"] for r in rows("BA_Shipments")} <= {"1", "2", "3"}
    assert names["BA_Shipments"]["columns"][2]["name"] == "ShipmentSeq"


def test_flow1_score_rule_matches_the_seed():
    """Flow 1 and the app score 25 points per check; the seed's ReadinessScore and status follow the same rule."""
    for r in rows("BA_Customers"):
        checks = [r["InvoiceReady"] == "Yes", r["PackingListReady"] == "Yes",
                  r["PermitReady"] == "Yes" or r["PermitNeeded"] == "No", r["ImporterUEN"].strip() != ""]
        score = 25 * sum(checks)
        assert int(r["ReadinessScore"]) == score, r["AccountNo"]
        expected = "Validated" if score == 100 else ("Docs pending" if score >= 50 else "Requested")
        assert r["EnrolmentStatus"] == expected or (expected == "Validated" and r["EnrolmentStatus"] == "Active")


def test_held_seed_shipments_have_one_follow_up_each():
    held = {r["ShipmentRef"] for r in rows("BA_Shipments") if r["HoldReason"] != "None"}
    follow = [r["ShipmentRef"] for r in rows("BA_ActionLog") if r["ActionType"] == "Hold follow-up"]
    assert sorted(follow) == sorted(held)


def test_status_wording_and_no_real_addresses():
    text = {p.name: p.read_text(encoding="utf-8") for p in PP.glob("*.md")}
    readme = text["README.md"]
    # the status is "built and tested", with what is missing said plainly
    assert "built and tested" in readme and "not shared with other users" in readme
    assert "Package exports" in readme and "DEMO-C025" in readme and "DEMO-S0041" in readme
    for name in ("flow1_enrolment_readiness.md", "flow2_first_three_hold_alert.md", "app.md"):
        assert "Built and tested" in text[name] and "(export" in text[name], name
    assert "not a listing of the built app" in text["app.md"]
    everything = "\n".join(text.values()) + (PP / "lists_schema.json").read_text(encoding="utf-8")
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", everything), "an email address is written in power-platform/"
    assert not re.search(r"https://[\w-]+(-my)?\.sharepoint\.com", everything), "a tenant URL is written down"
    assert "<owner-email>" in everything and "<onedrive-site-url>" in everything


def test_screenshots_exist_and_are_linked():
    shots = sorted(p.name for p in (PP / "screenshots").glob("*.png"))
    assert shots == ["app_first_three_shipments.png", "flow1_enrolment_check_run.png", "flow2_hold_alert_run.png"]
    readme = (PP / "README.md").read_text(encoding="utf-8")
    for name in shots:
        assert f"screenshots/{name}" in readme
        assert (PP / "screenshots" / name).read_bytes()[1:4] == b"PNG"


def test_flow1_documented_test_case_follows_the_score_rule():
    """DEMO-C025 in the build test: invoice yes, packing list no, permit needed and not ready, no UEN -> 25."""
    checks = [True, False, (not True) or False, False]
    assert 100 * sum(checks) // 4 == 25
    text = (PP / "flow1_enrolment_readiness.md").read_text(encoding="utf-8")
    assert "score 25" in text and "Docs pending" in text


def test_only_standard_connectors_in_the_build_sheets():
    for name in ("flow1_enrolment_readiness.md", "flow2_first_three_hold_alert.md"):
        steps = [ln for ln in (PP / name).read_text(encoding="utf-8").splitlines() if re.match(r"^\d+\. \*\*", ln)]
        assert len(steps) >= 4
        for ln in steps:
            assert not re.search(r"HTTP|Dataverse|AI Builder|SQL", ln), ln


# ---------------------------------------------------------------------------------------------------------------
# package exports (power-platform/export): archives open, hold no account identifier, and match the extracted sources
EXPORT = PP / "export"
PACKAGES = ("BrokerageOnboardAssist_App.zip", "BA_EnrolmentReadinessCheck.zip", "BA_FirstThreeShipmentsHoldAlert.zip")


def _members(data, prefix=""):
    """Every file in a zip archive, descending into nested archives (the .msapp is a zip inside the app package)."""
    import io
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(data))
    assert z.testzip() is None
    for info in z.infolist():
        b = z.read(info)
        if b[:2] == b"PK":
            yield from _members(b, prefix + info.filename + " > ")
        else:
            yield prefix + info.filename, b


def test_exports_open_and_hold_no_account_identifier():
    import re
    # a university account id (letter + 7 digits), a real e-mail domain, a real SharePoint tenant, a personal name
    bad = re.compile(rb"(?<![0-9a-fA-F-])[eE]\d{7}(?![0-9a-fA-F-])|@u\.nus\.edu|nus\.edu|nusu|(?<!contoso)(?<!contoso-my)\.sharepoint\.com|Wenjie", re.I)
    for name in PACKAGES:
        found = [(m, bad.findall(b)[:3]) for m, b in _members((EXPORT / name).read_bytes()) if bad.search(b)]
        assert not found, (name, found)


def test_extracted_sources_match_the_packages():
    import json
    app = dict(_members((EXPORT / PACKAGES[0]).read_bytes()))
    for short in ("App.pa.yaml", "MainScreen1.pa.yaml", "ShipmentsScreen.pa.yaml"):
        packed = next(b for m, b in app.items() if m.endswith("Src/" + short))
        assert packed.decode("utf-8-sig").replace("\r\n", "\n") == (EXPORT / "src" / short).read_text(encoding="utf-8")
    for pkg, short in ((PACKAGES[1], "flow1_definition.json"), (PACKAGES[2], "flow2_definition.json")):
        packed = next(b for m, b in _members((EXPORT / pkg).read_bytes()) if m.endswith("definition.json"))
        assert json.loads(packed.decode("utf-8-sig")) == json.loads((EXPORT / "src" / short).read_text(encoding="utf-8"))


def test_exported_app_and_flows_are_the_ones_described():
    ship = (EXPORT / "src" / "ShipmentsScreen.pa.yaml").read_text(encoding="utf-8")
    for needle in ("ShipGallery", "ActionTypeCombo", "LogActionButton", "Patch(", "BA_ActionLog", "SortByColumns"):
        assert needle in ship, needle
    assert "ShipmentsNavButton" in (EXPORT / "src" / "MainScreen1.pa.yaml").read_text(encoding="utf-8")
    f1 = (EXPORT / "src" / "flow1_definition.json").read_text(encoding="utf-8")
    f2 = (EXPORT / "src" / "flow2_definition.json").read_text(encoding="utf-8")
    assert "ReadinessScore" in f1 and "Docs pending" in f1 and "Validated" in f1
    assert "HeldOn" in f2 and "Hold follow-up" in f2 and "ShipmentSeq" in f2
