"""External search queries assembled by code from an allowlisted taxonomy.

Failure removed: a model free-typing a search query that carries employee
context (or an injected instruction) out to an external service. The model
never writes a query. Code composes them from gap skills that must exist in
the skills taxonomy table; anything else is refused, not sanitized.
"""
from __future__ import annotations

TEMPLATES = ("{skill} course", "{skill} certification preparation", "{skill} hands-on lab")


class OffTaxonomyError(ValueError):
    """A search term was requested that is not in the allowlisted taxonomy."""


def build_queries(gap_skills: list[str], taxonomy: set[str]) -> list[str]:
    queries: list[str] = []
    for skill in gap_skills:
        if skill not in taxonomy:
            raise OffTaxonomyError(f"{skill!r} is not an allowlisted taxonomy term")
        queries.extend(t.format(skill=skill) for t in TEMPLATES)
    return queries
