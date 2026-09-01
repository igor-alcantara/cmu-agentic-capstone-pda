"""Resource Scout: search the external catalog, return typed resources only.

This agent is the one that reads untrusted text (catalog descriptions, which
stand in for fetched web pages). By construction it has no other capability:
no database, no drafting, no memory. And what it returns is a list of
``Resource`` records built from a fixed set of fields, so the description it
read has no path into any other agent's prompt. That, not a prompt rule, is
the prompt-injection guardrail.
"""
from __future__ import annotations

from pda.guardrails.query_builder import build_queries
from pda.guardrails.verifier import Catalog, verify
from pda.models import Gap, Resource


def to_resource(entry: dict) -> Resource:
    """Typed projection. Note the absence of ``description``."""
    return Resource(resource_id=entry["resource_id"], title=entry["title"], url=entry["url"],
                    provider=entry["provider"], skills=list(entry["skills"]),
                    hours=float(entry["hours"]), cost_usd=float(entry["cost_usd"]))


def scout(gaps: list[Gap], taxonomy: set[str], catalog: Catalog, per_query: int = 4
          ) -> tuple[list[Resource], int, list[str]]:
    """Return (verified resources, unverified dropped, queries used)."""
    queries = build_queries([g.skill for g in gaps], taxonomy)
    seen: dict[str, Resource] = {}
    for q in queries:
        for entry in catalog.search(q, limit=per_query):
            r = to_resource(entry)
            seen.setdefault(r.resource_id, r)
    gap_skills = {g.skill for g in gaps}
    filtered = [r for r in seen.values() if gap_skills & set(r.skills)]
    verified, dropped = verify(filtered, catalog)
    verified.sort(key=lambda r: r.resource_id)
    return verified, dropped, queries
