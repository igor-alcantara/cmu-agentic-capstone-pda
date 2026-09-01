from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


@pytest.fixture(scope="session", autouse=True)
def synthetic_data() -> Path:
    """Build the synthetic data once per session if any piece is missing."""
    needed = [DATA / "pda.db", DATA / "resource_catalog.json", DATA / "role_docs"]
    if not all(p.exists() for p in needed):
        subprocess.run([sys.executable, str(DATA / "build_synthetic.py"), "--seed", "42"], check=True)
    return DATA
