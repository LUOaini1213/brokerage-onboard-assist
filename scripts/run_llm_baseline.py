"""Optional: classify the test hold notes with a local LLM through Ollama and cache the answers.

Needs a running Ollama server (http://127.0.0.1:11434) with the model pulled; it is not part of the offline build.
The cached answers (results/classifier/llm_predictions.csv) are committed, and scripts/build_all.py scores them on
exactly the same SYNTHETIC test notes as the TF-IDF model.

    python scripts/run_llm_baseline.py --model qwen3.5:4b

The answer is constrained to the 11 reason codes with Ollama's structured-output option (a JSON schema with an
enum), temperature 0 and a fixed seed. The prompt gives each code its one-line description from
rules/hold_reasons.csv and nothing else (no examples), so the model sees no training notes.
"""
import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from boa.classifier import split  # noqa: E402
from boa.data import read_tables  # noqa: E402
from boa.io import write_csv  # noqa: E402
from boa.rules import hold_reasons  # noqa: E402

OUT = ROOT / "results" / "classifier" / "llm_predictions.csv"
URL = "http://127.0.0.1:11434"


def system_prompt():
    lines = ["You classify free-text notes written when a customs shipment was put on hold.",
             "Choose the single reason code that best explains the hold. Codes:"]
    for code, h in hold_reasons().items():
        lines.append(f"- {code}: {h['label']}. {h['description']}.")
    lines.append('Answer with JSON {"code": "<one of the codes>"} and nothing else.')
    return "\n".join(lines)


def call(model, system, note, seed):
    codes = list(hold_reasons())
    body = {"model": model, "stream": False, "think": False, "keep_alive": "5m",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": f"Note: {note}"}],
            "format": {"type": "object", "properties": {"code": {"type": "string", "enum": codes}},
                       "required": ["code"]},
            "options": {"temperature": 0, "seed": seed, "num_predict": 32}}
    req = urllib.request.Request(f"{URL}/api/chat", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())["message"]["content"]


def parse(raw, codes):
    try:
        code = json.loads(raw).get("code", "")
    except (json.JSONDecodeError, AttributeError):
        code = ""
    return code if code in codes else "INVALID"


def loaded_models():
    with urllib.request.urlopen(f"{URL}/api/ps", timeout=10) as resp:
        return {m["name"] for m in json.loads(resp.read()).get("models", [])}


def unload(model):
    req = urllib.request.Request(f"{URL}/api/generate", data=json.dumps({"model": model, "keep_alive": 0}).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:4b")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=0, help="only the first N test notes (smoke test)")
    ap.add_argument("--fresh", action="store_true", help="ignore the existing cache")
    a = ap.parse_args()
    with urllib.request.urlopen(f"{URL}/api/version", timeout=10) as resp:
        version = json.loads(resp.read())["version"]
    holds = read_tables()["holds"]
    _, seen, held = split(holds)
    # held-out-template notes first: that is the comparison that matters if the run is interrupted
    tests = [("heldout", h) for h in held] + [("seen", h) for h in seen]
    if a.limit:
        tests = tests[:a.limit]
    system = system_prompt()
    digest = hashlib.sha256(system.encode()).hexdigest()
    codes = set(hold_reasons())
    # resume: keep cached answers made with the same model and prompt for notes whose text is unchanged
    rows = []
    if OUT.exists() and not a.fresh:
        with open(OUT, encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r["model"] == a.model and r["prompt_sha256"] == digest]
    notes = {h["hold_id"]: h["note"] for _, h in tests}
    rows = [r for r in rows if r["hold_id"] in notes and r["note_sha256"] == _sha(notes[r["hold_id"]])]
    done = {r["hold_id"] for r in rows}
    was_loaded = a.model in loaded_models()   # another program may be using the model: leave it loaded then
    try:
        for i, (split_name, h) in enumerate(tests, 1):
            if h["hold_id"] in done:
                continue
            t0 = time.time()
            raw = call(a.model, system, h["note"], a.seed)
            rows.append({"hold_id": h["hold_id"], "split": split_name, "label": parse(raw, codes),
                         "raw": raw.strip()[:120], "seconds": round(time.time() - t0, 2), "model": a.model,
                         "ollama_version": version, "prompt_sha256": digest, "note_sha256": _sha(h["note"])})
            if len(rows) % 10 == 0:
                save(rows)
                print(f"{len(rows)}/{len(tests)}", flush=True)
    finally:
        save(rows)
        if not was_loaded:
            unload(a.model)
    truth = {h["hold_id"]: h["reason_code"] for _, h in tests}
    ok = sum(r["label"] == truth[r["hold_id"]] for r in rows)
    print(f"{len(rows)} of {len(tests)} notes cached, {ok} correct, written to {OUT.relative_to(ROOT)}")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def save(rows):
    write_csv(OUT, sorted(rows, key=lambda r: r["hold_id"]),
              ["hold_id", "split", "label", "raw", "seconds", "model", "ollama_version", "prompt_sha256",
               "note_sha256"])


if __name__ == "__main__":
    main()
