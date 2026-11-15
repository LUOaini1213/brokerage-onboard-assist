"""Repository paths. Every script resolves files relative to the repository root, never the working directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "rules"
CONFIG = ROOT / "config"
DATA = ROOT / "data"
REFERENCE = DATA / "reference"
SYNTHETIC = DATA / "synthetic"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
DOCS = ROOT / "docs"
POWERBI = ROOT / "powerbi"
POWERBI_DATA = POWERBI / "data"
