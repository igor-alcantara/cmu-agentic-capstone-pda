"""Source verification: keep a resource only if its URL resolves to its title.

Failure removed: a fabricated or misattributed resource surviving into the
plan. A model that invents a resource will invent its URL too, so we do not
trust the claim. We fetch the URL (here: look it up in the catalog, which
stands in for the public web) and require the fetched title to match the
claimed title. Unverified claims are dropped and counted, never repaired.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pda.models import Resource


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


class Catalog:
    """The stand-in for live web search plus fetch."""

    def __init__(self, path: Path) -> None:
        self.entries: list[dict] = json.loads(Path(path).read_text(encoding="utf-8"))
        self.by_url = {e["url"]: e for e in self.entries}

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Keyword search over title, skills, and description. Returns raw entries."""
        terms = set(_norm(query).split())
        scored = []
        for e in self.entries:
            head = _norm(" ".join([e["title"], " ".join(e["skills"])]))
            body = _norm(e.get("description", ""))
            hits = sum(3 for t in terms if t in head) + sum(1 for t in terms if t in body)
            if hits:
                scored.append((hits, e["title"], e))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [e for _, _, e in scored[:limit]]

    def fetch(self, url: str) -> dict | None:
        return self.by_url.get(url)


def verify(claimed: list[Resource], catalog: Catalog) -> tuple[list[Resource], int]:
    kept: list[Resource] = []
    dropped = 0
    for r in claimed:
        fetched = catalog.fetch(r.url)
        if fetched is None or _norm(fetched["title"]) != _norm(r.title):
            dropped += 1
            continue
        kept.append(r.model_copy(update={"verified": True}))
    return kept, dropped
