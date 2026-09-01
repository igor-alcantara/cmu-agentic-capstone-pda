"""Retrieval safeguards from checkpoint 3.1, in the order they run.

Failure removed: confident wrong retrieval, where a passage from the wrong
role's document clears a similarity cutoff and every downstream branch
inherits it. Similarity is not comparable across queries, so no fixed cutoff
can cover that failure. The layers here are:

1. Metadata precondition (deterministic). Is there a document for this role at
   all, and exactly one current profile? No document means an empty candidate
   set and a labeled fallback. No score is consulted.
2. Metadata filter on the search itself. Only this role's chunks compete.
3. Per-query relevance check (a short model call in real mode, a keyword
   overlap heuristic in mock mode). Relative to this query, is the passage
   about what was asked?
4. Similarity floor, demoted to a coarse sanity check that only removes
   near-zero matches.
"""
from __future__ import annotations

import re
from typing import Callable

from pda.models import PreconditionResult, RoleDocChunk
from pda.retrieval.index import RoleDocIndex

RelevanceChecker = Callable[[str, RoleDocChunk], bool]

_STOP = {"the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with", "at", "by",
         "is", "are", "what", "how", "does", "do", "role", "skills", "skill", "level"}


def metadata_precondition(index: RoleDocIndex, role: str) -> PreconditionResult:
    docs = index.docs_for_role(role)
    if not docs:
        return PreconditionResult(status="no_role_doc",
                                  detail=f"no role document exists for {role!r}; retrieval skipped")
    profiles = [d for d in docs if d.kind == "role_profile"]
    if len(profiles) > 1:
        ids = sorted(d.doc_id for d in profiles)
        return PreconditionResult(status="conflicting_docs", doc_ids=ids,
                                  detail=f"{len(profiles)} role profiles for {role!r}: {ids}")
    return PreconditionResult(status="ok", doc_ids=sorted(d.doc_id for d in docs))


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in _STOP and len(w) > 2}


def keyword_overlap_checker(query: str, chunk: RoleDocChunk) -> bool:
    """Mock-mode relevance: at least two content words of the query appear in the chunk."""
    q = _words(query)
    if not q:
        return False
    return len(q & _words(chunk.section + " " + chunk.text)) >= min(2, len(q))


def make_rare_term_checker(index: RoleDocIndex) -> RelevanceChecker:
    """Mock-mode relevance with a little more discrimination than raw overlap:
    at least one of the query's three rarest content words (by chunk frequency
    in the index) must appear in the passage, plus the overlap rule. A passage
    about Airflow does not pass a Spark query just because both say 'gap'.
    This is a stand-in for the per-passage model call in real mode, not a
    claim about retrieval quality."""
    df: dict[str, int] = {}
    for c in index.chunks:
        for w in _words(c.section + " " + c.text):
            df[w] = df.get(w, 0) + 1

    def check(query: str, chunk: RoleDocChunk) -> bool:
        if not keyword_overlap_checker(query, chunk):
            return False
        q = sorted((w for w in _words(query) if w in df), key=lambda w: df[w])
        if not q:
            return False
        return bool(set(q[:3]) & _words(chunk.section + " " + chunk.text))

    return check


def relevance_check(query: str, chunks: list[RoleDocChunk], checker: RelevanceChecker) -> list[RoleDocChunk]:
    out = []
    for c in chunks:
        ok = bool(checker(query, c))
        out.append(c.model_copy(update={"relevant": ok}))
    return [c for c in out if c.relevant]


def coarse_floor(chunks: list[RoleDocChunk], floor: float) -> list[RoleDocChunk]:
    return [c for c in chunks if c.similarity >= floor]


def retrieve(index: RoleDocIndex, role: str, query: str, *, top_k: int, keep_min: int, keep_max: int,
             floor: float, checker: RelevanceChecker) -> tuple[PreconditionResult, list[RoleDocChunk]]:
    pre = metadata_precondition(index, role)
    if pre.status != "ok":
        return pre, []  # deliberately no search: the answer is settled by metadata
    candidates = index.search(query, k=top_k, role=role)
    relevant = relevance_check(query, candidates, checker)
    kept = relevant[:keep_max]
    if len(kept) < keep_min:
        pre = pre.model_copy(update={"detail": f"only {len(kept)} of {len(candidates)} passages passed the relevance check"})
    return pre, coarse_floor(kept, floor)
