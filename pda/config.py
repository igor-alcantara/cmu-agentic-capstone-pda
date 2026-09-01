"""Run configuration: caps, beam parameters, model, paths. Reads .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    api_key: str = ""
    model: str = "claude-sonnet-5"
    mock: bool = False
    # Budget caps. Hitting any of them yields a labeled partial plan.
    max_tool_calls: int = 40
    max_total_tokens: int = 120_000
    max_wall_seconds: float = 300.0
    max_gathering_retries: int = 1
    # Tree of Thought parameters (checkpoint 4.1).
    beam_width: int = 2
    branching_factor: int = 3
    depth: int = 3
    # Retrieval (checkpoint 3.1).
    retrieval_top_k: int = 8
    retrieval_keep_min: int = 4
    retrieval_keep_max: int = 6
    similarity_floor: float = 0.02  # coarse floor only, never the primary gate
    stale_snapshot_days: int = 45
    # Paths.
    db_path: Path = field(default_factory=lambda: ROOT / "data" / "pda.db")
    role_docs_dir: Path = field(default_factory=lambda: ROOT / "data" / "role_docs")
    catalog_path: Path = field(default_factory=lambda: ROOT / "data" / "resource_catalog.json")
    memory_dir: Path = field(default_factory=lambda: ROOT / "data" / "memory")
    outbox_dir: Path = field(default_factory=lambda: ROOT / "outbox")
    runs_dir: Path = field(default_factory=lambda: ROOT / "runs")


def load_settings(mock: bool | None = None) -> Settings:
    _load_dotenv(ROOT / ".env")
    s = Settings()
    s.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    s.model = os.environ.get("PDA_MODEL", s.model) or s.model
    env_mock = os.environ.get("PDA_MOCK", "0") == "1"
    s.mock = env_mock if mock is None else mock
    return s
